from __future__ import annotations

import logging
import base64
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from PySide6.QtCore import QObject, QRectF, QRunnable, QThreadPool, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QConicalGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from aiboard_app.ai.edtalkies_client import AiQuery, EdTalkiesClient
from aiboard_app.ai.prompt_builder import PromptBuilder
from aiboard_app.ai.response_parser import ParsedResponse, ResponseParser
from aiboard_app.app.config import AppSettings
from aiboard_app.chat.chat_exporter import ChatExporter
from aiboard_app.chat.chat_record import ChatRecord
from aiboard_app.chat.chat_store import ChatStore
from aiboard_app.documents.document_manager import DocumentManager
from aiboard_app.documents.document_text_extractor import DocumentExtraction
from aiboard_app.recognition.handwriting_recognizer import HandwritingRecognizer
from aiboard_app.recognition.ocr_result import OcrResult
from aiboard_app.system.shutdown_manager import ShutdownManager
from aiboard_app.ui.chat_history_panel import ChatHistoryPanel
from aiboard_app.ui.dialogs import RecognitionConfirmDialog
from aiboard_app.ui.floating_panel import FloatingPanelDialog, FloatingPanelHost
from aiboard_app.ui.icon_assets import logo_path
from aiboard_app.ui.response_panel import ResponsePanel
from aiboard_app.ui.theme import EdTalkiesTheme
from aiboard_app.ui.toolbar import WhiteboardToolbar
from aiboard_app.ui.whiteboard_canvas import WhiteboardCanvas

LOGGER = logging.getLogger(__name__)


class WorkerSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()


class BackgroundWorker(QRunnable):
    def __init__(self, task: Callable[[], Any]) -> None:
        super().__init__()
        self._task = task
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.succeeded.emit(self._task())
        except Exception as exc:
            LOGGER.exception("Background operation failed")
            self.signals.failed.emit(str(exc))
        finally:
            self.signals.finished.emit()


class ProcessingFrame(QWidget):
    BORDER_WIDTH = 3

    def __init__(self) -> None:
        super().__init__()
        self._processing = False
        self._border_angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(70)
        self._timer.timeout.connect(self._advance_border)

    def set_processing_animation(self, enabled: bool) -> None:
        if self._processing == enabled:
            return
        self._processing = enabled
        if enabled:
            self._timer.start()
        else:
            self._timer.stop()
            self._border_angle = 0
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().paintEvent(event)
        if not self._processing:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        border_rect = QRectF(self.rect()).adjusted(
            self.BORDER_WIDTH / 2,
            self.BORDER_WIDTH / 2,
            -self.BORDER_WIDTH / 2,
            -self.BORDER_WIDTH / 2,
        )
        gradient = QConicalGradient(border_rect.center(), self._border_angle)
        gradient.setColorAt(0.00, QColor("#ff0000"))
        gradient.setColorAt(0.14, QColor("#ffa500"))
        gradient.setColorAt(0.28, QColor("#ffff00"))
        gradient.setColorAt(0.42, QColor("#00ff00"))
        gradient.setColorAt(0.56, QColor("#00ffff"))
        gradient.setColorAt(0.70, QColor("#0000ff"))
        gradient.setColorAt(0.84, QColor("#8f00ff"))
        gradient.setColorAt(1.00, QColor("#ff0000"))
        pen = QPen(gradient, self.BORDER_WIDTH)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(border_rect)

    def _advance_border(self) -> None:
        self._border_angle = (self._border_angle + 6) % 360
        self.update()


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: AppSettings,
        client: EdTalkiesClient,
        recognizer: HandwritingRecognizer,
        response_parser: ResponseParser,
        prompt_builder: PromptBuilder,
        document_manager: DocumentManager,
        shutdown_manager: ShutdownManager,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._client = client
        self._recognizer = recognizer
        self._response_parser = response_parser
        self._prompt_builder = prompt_builder
        self._document_manager = document_manager
        self._shutdown_manager = shutdown_manager
        self._thread_pool = QThreadPool.globalInstance()
        self._thread_pool.setMaxThreadCount(max(2, min(4, self._thread_pool.maxThreadCount())))
        self._active_workers: set[BackgroundWorker] = set()
        self._busy_count = 0
        self._recognized_revision: int | None = None
        self._recognition_in_progress = False
        self._google_ocr_sources: tuple[bytes, ...] = ()
        self._current_input_text = ""
        self._input_mode = "whiteboard"
        self._pending_request_text = ""
        self._chat_store = ChatStore(settings.export_dir)
        self._chat_exporter = ChatExporter(settings.export_dir)
        self._chats = self._chat_store.load()
        self._floating_dialogs: dict[FloatingPanelHost, FloatingPanelDialog] = {}

        self.setWindowTitle("AiBoard App")
        self.setObjectName("AiBoardMainWindow")

        root = ProcessingFrame()
        root.setObjectName("AppRoot")
        self._processing_frame = root
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(
            ProcessingFrame.BORDER_WIDTH,
            ProcessingFrame.BORDER_WIDTH,
            ProcessingFrame.BORDER_WIDTH,
            ProcessingFrame.BORDER_WIDTH,
        )
        root_layout.setSpacing(0)

        self._toolbar = WhiteboardToolbar()
        self._header = self._build_header()
        self._canvas = WhiteboardCanvas()
        self._response_panel = ResponsePanel()
        self._response_panel.hide()
        console_content, self._console_output = self._build_console_panel()
        self._console_panel = FloatingPanelHost("Console Log", console_content)
        self._console_panel.hide()
        self._chat_history_panel = ChatHistoryPanel()
        self._chat_history_panel.set_chats(self._chats)
        self._chat_history_host = FloatingPanelHost(
            "Previous Chats",
            self._chat_history_panel,
            close_tooltip="Close chats",
        )
        self._footer = self._build_footer()

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self._body_layout = body
        body.addWidget(self._canvas, 1)
        body.addWidget(self._response_panel)
        body.addWidget(self._console_panel)
        body.addWidget(self._chat_history_host)

        root_layout.addWidget(self._header)
        root_layout.addLayout(body, 1)
        root_layout.addWidget(self._footer)
        self.setCentralWidget(root)

        self._connect_signals()
        self._apply_styles()

    def start(self) -> None:
        if self._settings.fullscreen:
            self.showFullScreen()
        else:
            self.resize(1280, 800)
            self.show()

    def _connect_signals(self) -> None:
        self._toolbar.color_changed.connect(self._canvas.set_pen_color)
        self._toolbar.width_changed.connect(self._canvas.set_pen_width)
        self._toolbar.eraser_toggled.connect(self._canvas.set_eraser)
        self._toolbar.eraser_toggled.connect(lambda _enabled: self._switch_to_whiteboard_mode())
        self._toolbar.clear_requested.connect(self._clear_board)
        self._toolbar.undo_requested.connect(self._canvas.undo)
        self._toolbar.redo_requested.connect(self._canvas.redo)
        self._toolbar.ask_requested.connect(self._ask_ai)
        self._toolbar.keyboard_requested.connect(self._keyboard_question)
        self._toolbar.document_requested.connect(self._upload_document)
        self._toolbar.console_requested.connect(self._toggle_console)
        self._toolbar.chats_requested.connect(self._toggle_chats)
        self._toolbar.save_requested.connect(self._save_board_image)
        self._toolbar.exit_requested.connect(self._exit)
        self._canvas.content_changed.connect(self._on_canvas_content_changed)
        self._response_panel.close_requested.connect(self._response_panel.hide)
        self._response_panel.document_open_requested.connect(self._open_document)
        self._response_panel.document_download_requested.connect(self._download_document)
        self._response_panel.export_requested.connect(self._export_current_chat)
        self._response_panel.edit_requested.connect(self._edit_response)
        self._response_panel.generated_download_requested.connect(self._download_generated_response)
        self._response_panel.generated_open_requested.connect(self._open_generated_response)
        self._response_panel.image_download_requested.connect(self._download_image_response)
        self._chat_history_panel.chat_selected.connect(self._open_chat)
        self._console_panel.float_requested.connect(lambda: self._float_panel(self._console_panel))
        self._console_panel.pin_requested.connect(lambda: self._dock_panel(self._console_panel, visible=True))
        self._console_panel.close_requested.connect(lambda: self._hide_panel(self._console_panel))
        self._chat_history_host.float_requested.connect(lambda: self._float_panel(self._chat_history_host))
        self._chat_history_host.pin_requested.connect(lambda: self._dock_panel(self._chat_history_host, visible=True))
        self._chat_history_host.close_requested.connect(lambda: self._hide_panel(self._chat_history_host))

    def _recognize_handwriting(self) -> None:
        if self._recognition_in_progress:
            return
        revision = self._canvas.revision
        image_bytes = self._canvas.to_png_bytes()
        self._google_ocr_sources = (image_bytes,)
        self._recognition_in_progress = True
        self._log_console("OCR started for whiteboard handwriting.")
        self._run_background(
            "Converting handwriting to text...",
            lambda: self._recognizer.recognize(image_bytes),
            lambda result: self._submit_recognized_text(result, revision),
            "Recognition failed",
            on_complete=self._complete_recognition,
        )

    def _submit_recognized_text(self, result: object, revision: int) -> None:
        if revision != self._canvas.revision:
            self._log_console("OCR completed, but the board changed before API submission.")
            QMessageBox.information(
                self,
                "Board changed",
                "The board changed during recognition. Click Ask AI again.",
            )
            return
        if not isinstance(result, OcrResult):
            self._log_console("OCR completed with an invalid result.")
            QMessageBox.critical(self, "Recognition failed", "The recognizer returned an invalid result.")
            return
        self._log_console(
            f"OCR completed using {result.model_name or result.provider}; "
            f"confidence {(result.confidence or 0.0):.0%}."
        )
        text = result.text.strip()
        if not text:
            QMessageBox.information(
                self,
                "No handwriting recognized",
                "No readable text was found. Try writing larger and click Ask AI again.",
            )
            return
        confirmed_text = self._confirm_recognized_text(text)
        if confirmed_text is None:
            self._log_console("Ask AI cancelled after OCR confirmation.")
            return
        self._current_input_text = confirmed_text
        self._recognized_revision = revision
        self._submit_question(confirmed_text)

    def _confirm_recognized_text(self, text: str) -> str | None:
        dialog = RecognitionConfirmDialog(
            text,
            self,
            title="Confirm recognized text",
            instructions="I recognized the following text. Do you want to send this to EdTalkies AI?",
            proceed_label="Proceed",
        )
        if dialog.exec() != RecognitionConfirmDialog.DialogCode.Accepted:
            return None
        return dialog.text()

    def _complete_recognition(self) -> None:
        self._recognition_in_progress = False

    def _keyboard_question(self) -> None:
        self._input_mode = "keyboard"
        self._google_ocr_sources = ()
        self._log_console("Keyboard mode selected.")
        dialog = RecognitionConfirmDialog(
            self._current_input_text,
            self,
            title="Type a question",
            instructions="Type the question to send to EdTalkies AI.",
            proceed_label="Proceed",
        )
        if dialog.exec() != RecognitionConfirmDialog.DialogCode.Accepted:
            self._log_console("Keyboard input cancelled.")
            return
        text = dialog.text()
        if not text:
            QMessageBox.information(self, "No text", "Please type a question before sending.")
            return
        self._current_input_text = text
        self._recognized_revision = self._canvas.revision
        self._submit_question(text)

    def _upload_document(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Upload document and extract text",
            "",
            (
                "Supported documents (*.pdf *.docx *.txt *.md *.markdown *.html *.htm "
                "*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;"
                "PDF files (*.pdf);;Word files (*.docx);;Text files (*.txt *.md *.markdown);;"
                "HTML files (*.html *.htm);;Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
            ),
        )
        if not file_name:
            return
        path = Path(file_name)
        self._input_mode = "document"
        self._log_console(f"Document extraction started: {path.name}.")
        self._run_background(
            f"Extracting text from {path.name}...",
            lambda: self._extract_document_payload(path),
            self._display_document_text,
            "Document extraction failed",
        )

    def _extract_document_payload(self, path: Path) -> tuple[DocumentExtraction, Path]:
        return self._document_manager.extract_text(path), path

    def _display_document_text(self, payload: object) -> None:
        if not isinstance(payload, tuple) or len(payload) != 2:
            QMessageBox.warning(self, "Extraction error", "The document extractor returned invalid data.")
            return
        extraction, path = payload
        if not isinstance(path, Path):
            QMessageBox.warning(self, "Extraction error", "The selected document path is invalid.")
            return
        if not isinstance(extraction, DocumentExtraction):
            QMessageBox.warning(self, "Extraction error", "The document extraction result is invalid.")
            return
        result = extraction.result
        if not isinstance(result, OcrResult):
            QMessageBox.warning(self, "Extraction error", "The document OCR result is invalid.")
            return
        self._google_ocr_sources = extraction.google_vision_images
        if not result.text.strip():
            self._log_console(f"Document extraction completed with no readable text: {path.name}.")
            QMessageBox.warning(
                self,
                "No text found",
                f"No readable text could be extracted from {path.name}.",
            )
            return
        self._current_input_text = result.text.strip()
        self._log_console(
            f"Document extraction completed: {path.name}; "
            f"OCR {result.model_name or result.provider}; confidence {(result.confidence or 0.0):.0%}."
        )
        self._recognized_revision = self._canvas.revision

    def _ask_ai(self) -> None:
        if self._input_mode == "document" and self._current_input_text:
            self._submit_question(self._current_input_text)
            return
        if not self._canvas.has_content:
            self._log_console("Ask AI cancelled: blackboard is empty.")
            QMessageBox.information(
                self,
                "Nothing to ask yet",
                "Please write something on the blackboard before asking AI.",
            )
            return
        self._input_mode = "whiteboard"
        self._recognize_handwriting()

    def _clear_board(self) -> None:
        self._canvas.clear()
        self._recognized_revision = None
        self._google_ocr_sources = ()
        self._current_input_text = ""
        self._input_mode = "whiteboard"
        self._pending_request_text = ""

    def _submit_question(self, text: str) -> None:
        prompt = self._prompt_builder.build_teacher_prompt(text)
        if not prompt:
            QMessageBox.information(self, "No text", "Please enter a question before sending.")
            return
        self._pending_request_text = prompt
        self._log_console("Ask AI API request started.")
        self._run_background(
            "Asking EdTalkies AI…",
            lambda: self._client.ask(AiQuery(text=prompt)),
            self._show_api_response,
            "EdTalkies API error",
        )

    def _show_api_response(self, payload: object) -> None:
        if not isinstance(payload, dict):
            QMessageBox.critical(self, "Invalid response", "EdTalkies returned an unsupported response.")
            return
        parsed = self._response_parser.parse(payload)
        if not parsed.text and not parsed.html and not parsed.documents:
            self._log_console("Ask AI API response received, but it was empty.")
            QMessageBox.warning(self, "Empty response", "EdTalkies returned an empty response.")
            return
        self._log_console("Ask AI API response received.")
        chat = self._create_chat(parsed)
        self._persist_chat(chat)
        self._response_panel.show_response(parsed, chat)

    def _create_chat(self, response: ParsedResponse) -> ChatRecord:
        return ChatRecord(
            id=str(uuid4()),
            request_text=self._pending_request_text or self._current_input_text,
            response=response,
            created_at=datetime.now(),
            session_id=self._settings.edtalkies.session_id,
        )

    def _persist_chat(self, chat: ChatRecord) -> None:
        try:
            self._chats = self._chat_store.save_chat(chat)
        except OSError as exc:
            self._log_console(f"Chat history save failed: {exc}")
            return
        self._chat_history_panel.set_chats(self._chats)
        self._log_console("Ask AI chat saved to local history.")

    def _open_chat(self, chat_id: str) -> None:
        chat = next((record for record in self._chats if record.id == chat_id), None)
        if chat is None:
            QMessageBox.warning(self, "Chat unavailable", "The selected chat could not be found.")
            return
        self._response_panel.show_response(chat.response, chat)
        self._log_console("Previous chat opened.")

    def _export_current_chat(self, file_type: str) -> None:
        chat = self._response_panel.current_chat
        if chat is None:
            QMessageBox.information(self, "No chat selected", "Open or create a chat before exporting.")
            return
        default_path = self._chat_exporter.default_path(chat, file_type)
        filters = {
            "pdf": "PDF files (*.pdf)",
            "docx": "Word documents (*.docx)",
            "txt": "Text files (*.txt)",
            "xlsx": "Excel workbooks (*.xlsx)",
            "pptx": "PowerPoint presentations (*.pptx)",
        }
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            f"Export chat as {file_type.upper()}",
            str(default_path),
            filters.get(file_type, "All files (*)"),
        )
        if not file_name:
            return
        try:
            path = self._chat_exporter.export(chat, file_type, Path(file_name))
        except Exception as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
            self._log_console(f"Chat export failed: {exc}")
            return
        QMessageBox.information(self, "Export complete", f"Saved to:\n{path}")
        self._log_console(f"Chat exported as {file_type.upper()}.")

    def _save_board_image(self) -> None:
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save whiteboard image",
            str(self._settings.export_dir / "whiteboard.png"),
            "PNG Images (*.png)",
        )
        if not file_name:
            return
        if not self._canvas.save_image(file_name):
            QMessageBox.warning(self, "Save failed", "The whiteboard image could not be saved.")

    def _open_document(self, url: str, file_name: str) -> None:
        if not url:
            QMessageBox.warning(self, "Document unavailable", "No document URL was provided.")
            return
        self._run_background(
            f"Downloading {file_name}…",
            lambda: self._document_manager.download(url, file_name),
            lambda path: self._open_downloaded_file(path),
            "Document error",
        )

    def _open_downloaded_file(self, path: object) -> None:
        try:
            self._document_manager.open_file(path)
        except Exception as exc:
            QMessageBox.warning(self, "Open failed", str(exc))

    def _download_document(self, url: str, file_name: str) -> None:
        if not url:
            QMessageBox.warning(self, "Document unavailable", "No document URL was provided.")
            return
        self._run_background(
            f"Downloading {file_name}…",
            lambda: self._document_manager.download(url, file_name),
            lambda path: QMessageBox.information(self, "Download complete", f"Saved to:\n{path}"),
            "Download failed",
        )

    def _edit_response(self, unique_id: str) -> None:
        self._log_console(f"Edit requested for response: {unique_id or 'unknown'}")
        QMessageBox.information(
            self,
            "Edit response",
            "Response editing is not implemented yet. The request was logged.",
        )

    def _download_generated_response(self, unique_id: str, file_format: str, download_url: str) -> None:
        self._fetch_generated_response(unique_id, file_format, download_url, open_after_download=False)

    def _open_generated_response(self, unique_id: str, file_format: str, download_url: str) -> None:
        self._fetch_generated_response(unique_id, file_format, download_url, open_after_download=True)

    def _fetch_generated_response(
        self,
        unique_id: str,
        file_format: str,
        download_url: str,
        open_after_download: bool,
    ) -> None:
        if not unique_id and not download_url:
            QMessageBox.warning(self, "Download unavailable", "This response does not include a download id.")
            self._log_console("Generated response download failed: missing UniqueId.")
            return
        file_format = file_format.lower()
        file_name = self._generated_download_name(unique_id, file_format)
        try:
            url = self._client.generated_download_url(unique_id, file_format) if unique_id else download_url
        except Exception as exc:
            QMessageBox.warning(self, "Download unavailable", str(exc))
            self._log_console(f"Generated response download failed: {exc}")
            return
        action = "open" if open_after_download else "download"
        self._log_console(f"Generated response {action} started: {file_format.upper()}.")
        self._run_background(
            f"Downloading {file_name}...",
            lambda: self._document_manager.download(url, file_name),
            lambda path: self._download_generated_complete(path, file_format, open_after_download),
            "Download failed",
        )

    def _download_generated_complete(self, path: object, file_format: str, open_after_download: bool) -> None:
        if open_after_download:
            try:
                self._document_manager.open_file(path)
            except Exception as exc:
                QMessageBox.warning(self, "Open failed", str(exc))
                self._log_console(f"Generated response open failed: {exc}")
                return
            self._log_console(f"Generated response opened as {file_format.upper()}.")
            return
        QMessageBox.information(self, "Download complete", f"Saved to:\n{path}")
        self._log_console(f"Generated response downloaded as {file_format.upper()}.")

    def _download_image_response(self, source: str, file_name: str) -> None:
        source = source.strip()
        if not source:
            QMessageBox.warning(self, "Image unavailable", "The image response was empty.")
            self._log_console("Image download failed: empty image response.")
            return
        if source.startswith(("http://", "https://")):
            self._log_console("Image response download started.")
            self._run_background(
                f"Downloading {file_name}...",
                lambda: self._document_manager.download(source, file_name),
                lambda path: self._download_image_complete(path),
                "Image download failed",
            )
            return
        try:
            image_bytes = self._decode_image_source(source)
            image_path = self._settings.export_dir / "downloads" / file_name
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(image_bytes)
        except Exception as exc:
            QMessageBox.warning(self, "Image download failed", str(exc))
            self._log_console(f"Image download failed: {exc}")
            return
        QMessageBox.information(self, "Download complete", f"Saved to:\n{image_path}")
        self._log_console("Image response downloaded.")

    def _download_image_complete(self, path: object) -> None:
        QMessageBox.information(self, "Download complete", f"Saved to:\n{path}")
        self._log_console("Image response downloaded.")

    @staticmethod
    def _decode_image_source(source: str) -> bytes:
        if "," in source and source.strip().lower().startswith("data:image/"):
            source = source.split(",", 1)[1]
        return base64.b64decode(source, validate=True)

    @staticmethod
    def _generated_download_name(unique_id: str, file_format: str) -> str:
        safe_id = "".join(char for char in unique_id if char.isalnum() or char in {"-", "_"}) or "response"
        extension = "xlsx" if file_format == "excel" else file_format
        if extension == "calendar":
            extension = "ics"
        return f"EdTalkies_{safe_id}.{extension}"

    def _run_background(
        self,
        message: str,
        task: Callable[[], Any],
        on_success: Callable[[object], None],
        error_title: str,
        show_progress: bool = True,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        self._set_busy(True, message if show_progress else "")

        worker = BackgroundWorker(task)
        worker.signals.succeeded.connect(lambda result: self._finish_background(on_success, result))
        worker.signals.failed.connect(
            lambda error: self._fail_background(error_title, error, show_progress)
        )
        worker.signals.finished.connect(lambda: self._release_worker(worker, on_complete))
        self._active_workers.add(worker)
        self._thread_pool.start(worker)

    def _release_worker(
        self,
        worker: BackgroundWorker,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        self._active_workers.discard(worker)
        self._set_busy(False)
        if on_complete is not None:
            on_complete()

    def _finish_background(
        self,
        callback: Callable[[object], None],
        result: object,
    ) -> None:
        callback(result)

    def _fail_background(
        self,
        title: str,
        error: str,
        show_dialog: bool = True,
    ) -> None:
        self._log_console(f"{title}: {error}")
        if show_dialog:
            QMessageBox.critical(self, title, error)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        was_busy = self._busy_count > 0
        self._busy_count = max(0, self._busy_count + (1 if busy else -1))
        is_busy = self._busy_count > 0
        self._toolbar.set_busy(is_busy)
        self._processing_frame.set_processing_animation(is_busy)
        self._canvas.setEnabled(not is_busy)
        if is_busy and not was_busy:
            self._log_console("Processing animation started.")
        elif was_busy and not is_busy:
            self._log_console("Processing animation stopped.")
        QApplication.processEvents()

    def _on_canvas_content_changed(self, revision: int) -> None:
        self._switch_to_whiteboard_mode()

    def _switch_to_whiteboard_mode(self) -> None:
        self._input_mode = "whiteboard"
        self._recognized_revision = None
        self._current_input_text = ""

    def _toggle_console(self) -> None:
        if self._console_panel in self._floating_dialogs:
            dialog = self._floating_dialogs[self._console_panel]
            dialog.setVisible(not dialog.isVisible())
            if dialog.isVisible():
                dialog.raise_()
                dialog.activateWindow()
            return
        self._console_panel.setVisible(not self._console_panel.isVisible())

    def _toggle_chats(self) -> None:
        if self._chat_history_host in self._floating_dialogs:
            dialog = self._floating_dialogs[self._chat_history_host]
            dialog.setVisible(not dialog.isVisible())
            if dialog.isVisible():
                dialog.raise_()
                dialog.activateWindow()
            return
        self._chat_history_host.setVisible(not self._chat_history_host.isVisible())

    def _float_panel(self, host: FloatingPanelHost) -> None:
        if host in self._floating_dialogs:
            dialog = self._floating_dialogs[host]
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            return
        self._body_layout.removeWidget(host)
        host.setParent(None)
        host.set_floating(True)
        dialog = FloatingPanelDialog(host, self)
        dialog.panel_closed.connect(self._handle_floating_panel_closed)
        self._floating_dialogs[host] = dialog
        dialog.show()

    def _dock_panel(self, host: FloatingPanelHost, visible: bool = True) -> None:
        dialog = self._floating_dialogs.pop(host, None)
        if dialog is not None:
            dialog.panel_closed.disconnect(self._handle_floating_panel_closed)
            dialog.detach_host()
            dialog.close()
        if host.parentWidget() is not self.centralWidget():
            host.setParent(None)
        host.set_floating(False)
        if self._body_layout.indexOf(host) < 0:
            self._body_layout.addWidget(host)
        host.setVisible(visible)

    def _hide_panel(self, host: FloatingPanelHost) -> None:
        dialog = self._floating_dialogs.pop(host, None)
        if dialog is not None:
            dialog.panel_closed.disconnect(self._handle_floating_panel_closed)
            dialog.detach_host()
            dialog.close()
        self._dock_panel(host, visible=False)

    def _handle_floating_panel_closed(self, host: FloatingPanelHost) -> None:
        self._floating_dialogs.pop(host, None)
        self._dock_panel(host, visible=False)

    def _log_console(self, message: str) -> None:
        if not hasattr(self, "_console_output"):
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._console_output.appendPlainText(f"[{timestamp}] {message}")

    def _exit(self) -> None:
        self._shutdown_manager.perform_exit(self)

    def keyPressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key() == Qt.Key.Key_Escape and not self._settings.fullscreen:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.spontaneous():
            event.ignore()
            self._exit()
            return
        event.accept()

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("AppHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        logo = QLabel("e")
        logo.setObjectName("AppHeaderLogo")
        logo.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        logo_file = logo_path("edtalkies_header_logo.png")
        if logo_file.exists():
            pixmap = QPixmap(str(logo_file))
            if not pixmap.isNull():
                logo.setText("")
                logo.setPixmap(
                    pixmap.scaled(
                        54,
                        54,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                logo.setFixedSize(60, 58)
        title = QLabel("EdTalkies Ai Blackboard")
        title.setObjectName("AppHeaderTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(self._toolbar, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return header

    def _build_console_panel(self) -> tuple[QFrame, QPlainTextEdit]:
        panel = QFrame()
        panel.setObjectName("ConsoleLogContent")
        panel.setMinimumWidth(360)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        output = QPlainTextEdit()
        output.setObjectName("ConsoleLogOutput")
        output.setReadOnly(True)
        output.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        output.setPlaceholderText("Runtime logs will appear here.")

        layout.addWidget(output, 1)
        return panel, output

    def _build_footer(self) -> QFrame:
        footer = QFrame()
        footer.setObjectName("AppFooter")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(20, 8, 20, 8)
        label = QLabel("Powered by EdTalkies AI  •  © AR ITWORKS, LLC")
        label.setObjectName("AppFooterText")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label, 1)
        return footer

    def _apply_styles(self) -> None:
        self.setStyleSheet(EdTalkiesTheme.app_stylesheet())
