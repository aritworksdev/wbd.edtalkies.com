from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QVBoxLayout,
    QWidget,
)

from aiboard_app.ai.edtalkies_client import AiQuery, EdTalkiesClient, EdTalkiesError
from aiboard_app.ai.prompt_builder import PromptBuilder
from aiboard_app.ai.response_parser import ResponseParser
from aiboard_app.app.config import AppSettings
from aiboard_app.documents.document_manager import DocumentManager
from aiboard_app.recognition.handwriting_recognizer import HandwritingRecognizer
from aiboard_app.recognition.ocr_provider_base import RecognitionResult
from aiboard_app.system.shutdown_manager import ShutdownManager
from aiboard_app.ui.dialogs import RecognitionConfirmDialog
from aiboard_app.ui.recognized_text_panel import RecognizedTextPanel
from aiboard_app.ui.response_panel import ResponsePanel
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
        self._progress: QProgressDialog | None = None
        self._active_workers: set[BackgroundWorker] = set()

        self.setWindowTitle("AiBoard App")
        self.setObjectName("AiBoardMainWindow")

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._header = self._build_header()
        self._toolbar = WhiteboardToolbar()
        self._canvas = WhiteboardCanvas()
        self._response_panel = ResponsePanel()
        self._response_panel.hide()
        self._recognized_text_panel = RecognizedTextPanel()
        self._footer = self._build_footer()

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._canvas, 1)
        body.addWidget(self._response_panel)

        root_layout.addWidget(self._header)
        root_layout.addWidget(self._toolbar)
        root_layout.addLayout(body, 1)
        root_layout.addWidget(self._recognized_text_panel)
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
        self._toolbar.clear_requested.connect(self._clear_board)
        self._toolbar.undo_requested.connect(self._canvas.undo)
        self._toolbar.redo_requested.connect(self._canvas.redo)
        self._toolbar.recognize_requested.connect(self._recognize_handwriting)
        self._toolbar.ask_requested.connect(self._ask_ai)
        self._toolbar.keyboard_requested.connect(self._keyboard_question)
        self._toolbar.save_requested.connect(self._save_board_image)
        self._toolbar.exit_requested.connect(self._exit)
        self._response_panel.close_requested.connect(self._response_panel.hide)
        self._response_panel.document_open_requested.connect(self._open_document)
        self._response_panel.document_download_requested.connect(self._download_document)
        self._recognized_text_panel.ask_requested.connect(self._ask_ai)

    def _recognize_handwriting(self) -> None:
        image_bytes = self._canvas.to_png_bytes()
        self._run_background(
            "Converting handwriting to text...",
            lambda: self._recognizer.recognize(image_bytes),
            self._display_recognized_text,
            "Recognition failed",
        )

    def _display_recognized_text(self, result: object) -> None:
        if not isinstance(result, RecognitionResult):
            QMessageBox.critical(self, "Recognition failed", "The recognizer returned an invalid result.")
            return
        if not result.text.strip():
            QMessageBox.information(
                self,
                "No handwriting recognized",
                "No readable text was found. Try writing larger and run Handwriting to Text again.",
            )
            return
        self._recognized_text_panel.set_recognition_result(result)

    def _keyboard_question(self) -> None:
        dialog = RecognitionConfirmDialog(
            "",
            self,
            title="Type a question",
            instructions="Type the question to send to EdTalkies.",
        )
        if dialog.exec() == RecognitionConfirmDialog.DialogCode.Accepted:
            self._recognized_text_panel.set_text(dialog.text(), "keyboard")

    def _ask_ai(self) -> None:
        self._submit_question(self._recognized_text_panel.text())

    def _clear_board(self) -> None:
        self._canvas.clear()
        self._recognized_text_panel.clear()

    def _submit_question(self, text: str) -> None:
        prompt = self._prompt_builder.build_teacher_prompt(text)
        if not prompt:
            QMessageBox.information(self, "No text", "Please enter a question before sending.")
            return
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
            QMessageBox.warning(self, "Empty response", "EdTalkies returned an empty response.")
            return
        self._response_panel.show_response(parsed)

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

    def _run_background(
        self,
        message: str,
        task: Callable[[], Any],
        on_success: Callable[[object], None],
        error_title: str,
    ) -> None:
        progress = QProgressDialog(message, "", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()
        self._progress = progress

        worker = BackgroundWorker(task)
        worker.signals.succeeded.connect(lambda result: self._finish_background(progress, on_success, result))
        worker.signals.failed.connect(lambda error: self._fail_background(progress, error_title, error))
        worker.signals.finished.connect(lambda: self._release_worker(worker))
        self._active_workers.add(worker)
        self._thread_pool.start(worker)

    def _release_worker(self, worker: BackgroundWorker) -> None:
        self._active_workers.discard(worker)

    def _finish_background(
        self,
        progress: QProgressDialog,
        callback: Callable[[object], None],
        result: object,
    ) -> None:
        progress.close()
        callback(result)

    def _fail_background(self, progress: QProgressDialog, title: str, error: str) -> None:
        progress.close()
        QMessageBox.critical(self, title, error)

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
        title = QLabel("EdTalkies Ai Blackboard")
        title.setObjectName("AppHeaderTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(title)
        layout.addStretch(1)
        return header

    def _build_footer(self) -> QFrame:
        footer = QFrame()
        footer.setObjectName("AppFooter")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(20, 8, 20, 8)
        label = QLabel("\u00a9 AR ITWORKS, LLC")
        label.setObjectName("AppFooterText")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label, 1)
        return footer

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            #AiBoardMainWindow { background: #000000; }
            #AppHeader, #AppFooter {
                background: #111827;
                border: 0;
            }
            #AppHeader { border-bottom: 1px solid #374151; }
            #AppFooter { border-top: 1px solid #374151; }
            #AppHeaderTitle {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
            }
            #AppFooterText {
                color: #d1d5db;
                font-size: 14px;
                font-weight: 600;
            }
            #WhiteboardToolbar {
                background: #17212f;
                border-bottom: 1px solid #0f172a;
            }
            #WhiteboardToolbar QPushButton {
                background: #f8fafc;
                color: #111827;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 16px;
            }
            #WhiteboardToolbar QPushButton:checked {
                background: #b8e986;
                border-color: #5fa041;
            }
            #ResponsePanel {
                background: #ffffff;
                border-left: 1px solid #cbd5e1;
            }
            #ResponseTitle {
                font-size: 22px;
                font-weight: 700;
                color: #111827;
            }
            #RecognizedTextPanel {
                background: #111827;
                border-top: 1px solid #374151;
            }
            #RecognizedTextTitle {
                color: #ffffff;
                font-size: 17px;
                font-weight: 700;
            }
            #RecognizedTextStatus {
                color: #9ca3af;
                font-size: 13px;
            }
            #RecognizedTextEditor {
                background: #f9fafb;
                color: #111827;
                border: 1px solid #6b7280;
                border-radius: 6px;
                padding: 6px;
                font-size: 18px;
            }
            #RecognizedTextPanel QPushButton {
                min-height: 34px;
                padding: 4px 12px;
                border-radius: 5px;
            }
            #RecognizedTextAskButton {
                background: #22c55e;
                color: #052e16;
                font-weight: 700;
            }
            """
        )
