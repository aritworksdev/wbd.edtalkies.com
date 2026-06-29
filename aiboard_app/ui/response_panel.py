from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal, QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QTextDocument
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from aiboard_app.ai.response_parser import ParsedResponse
from aiboard_app.chat.chat_record import ChatRecord
from aiboard_app.ui.icon_assets import IconName, load_icon
from aiboard_app.ui.theme import EdTalkiesTheme

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover - depends on Qt package availability.
    QWebEngineView = None  # type: ignore[assignment]


class ResponsePanel(QFrame):
    close_requested = Signal()
    document_open_requested = Signal(str, str)
    document_download_requested = Signal(str, str)
    export_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("ResponsePanel")
        self.setMinimumWidth(420)
        self.setMaximumWidth(720)
        self._icon_buttons: list[QPushButton] = []

        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        self._title = QLabel("EdTalkies Response")
        self._title.setObjectName("ResponseTitle")
        self._copied_label = QLabel("")
        self._copied_label.setObjectName("ResponseCopiedLabel")
        self._copied_label.hide()
        self._copied_timer = QTimer(self)
        self._copied_timer.setSingleShot(True)
        self._copied_timer.timeout.connect(self._copied_label.hide)
        copy_button = self._icon_button(
            IconName.COPY,
            "Copy response",
            small=True,
            accessible_name="Copy AI response",
        )
        copy_button.clicked.connect(self._copy_response)
        save_button = self._icon_button(IconName.UPDATE, "Save response", small=True)
        save_button.clicked.connect(self._save_response)
        close_button = self._icon_button(IconName.CLOSE, "Close response panel", small=True)
        close_button.clicked.connect(self.close_requested.emit)
        header.addWidget(self._title, 1)
        header.addWidget(self._copied_label)
        header.addWidget(copy_button)
        header.addWidget(save_button)
        header.addWidget(close_button)
        layout.addLayout(header)

        self._viewer: QWidget
        if QWebEngineView is not None:
            self._viewer = QWebEngineView()
        else:
            browser = QTextBrowser()
            browser.setOpenExternalLinks(True)
            self._viewer = browser
        layout.addWidget(self._viewer, 1)

        self._documents = QVBoxLayout()
        layout.addLayout(self._documents)
        self._exports = QHBoxLayout()
        export_label = QLabel("Export:")
        export_label.setObjectName("ResponseExportLabel")
        self._docx_button = self._icon_button(IconName.DOCX, "Export as Word", small=True)
        self._excel_button = self._icon_button(IconName.EXCEL, "Export as Excel", small=True)
        self._pptx_button = self._icon_button(IconName.PPTX, "Export as PowerPoint", small=True)
        self._docx_button.clicked.connect(lambda: self.export_requested.emit("docx"))
        self._excel_button.clicked.connect(lambda: self.export_requested.emit("xlsx"))
        self._pptx_button.clicked.connect(lambda: self.export_requested.emit("pptx"))
        self._exports.addWidget(export_label)
        self._exports.addWidget(self._docx_button)
        self._exports.addWidget(self._excel_button)
        self._exports.addWidget(self._pptx_button)
        self._exports.addStretch(1)
        layout.addLayout(self._exports)
        self._current_response = ParsedResponse("", "", "")
        self._current_chat: ChatRecord | None = None
        self._set_export_buttons_enabled(False)

    @property
    def current_chat(self) -> ChatRecord | None:
        return self._current_chat

    def show_response(self, response: ParsedResponse, chat: ChatRecord | None = None) -> None:
        self._current_response = response
        self._current_chat = chat
        self._title.setText(response.title)
        html = self._wrap_html(response.html or response.text, chat)
        if QWebEngineView is not None and isinstance(self._viewer, QWebEngineView):
            self._viewer.setHtml(html, QUrl("https://edtalkies.com/"))
        elif isinstance(self._viewer, QTextBrowser):
            self._viewer.setHtml(html)

        self._clear_documents()
        for document in response.documents:
            row = QHBoxLayout()
            label = QLabel(f"{document.file_name} ({document.file_type}) — {document.status}")
            open_button = self._icon_button(IconName.UPDATE, "Download and open document", small=True)
            open_button.clicked.connect(
                lambda checked=False, url=document.url, name=document.file_name:
                    self.document_open_requested.emit(url, name)
            )
            download_button = self._icon_button(IconName.UPLOAD, "Download document", small=True)
            download_button.clicked.connect(
                lambda checked=False, url=document.url, name=document.file_name:
                    self.document_download_requested.emit(url, name)
            )
            row.addWidget(label, 1)
            row.addWidget(download_button)
            row.addWidget(open_button)
            self._documents.addLayout(row)
        self._set_export_buttons_enabled(chat is not None)
        self.show()

    def _clear_documents(self) -> None:
        while self._documents.count():
            item = self._documents.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            child_layout = item.layout()
            if child_layout:
                while child_layout.count():
                    child = child_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

    def _copy_response(self) -> None:
        text = self._current_response.text or self._html_to_plain_text(self._current_response.html)
        QGuiApplication.clipboard().setText(text)
        self._copied_label.setText("Copied")
        self._copied_label.show()
        self._copied_timer.start(1600)

    def _save_response(self) -> None:
        file_name, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save AI response",
            "edtalkies-response.html" if self._current_response.html else "edtalkies-response.txt",
            "HTML files (*.html);;Text files (*.txt)",
        )
        if not file_name:
            return
        content = self._current_response.html if "HTML" in selected_filter else self._current_response.text
        try:
            with open(file_name, "w", encoding="utf-8") as output:
                output.write(content)
        except OSError as exc:
            QMessageBox.warning(self, "Save failed", str(exc))

    def _set_export_buttons_enabled(self, enabled: bool) -> None:
        self._docx_button.setEnabled(enabled)
        self._excel_button.setEnabled(enabled)
        self._pptx_button.setEnabled(enabled)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._apply_icon_sizes()
        super().resizeEvent(event)

    def _icon_button(
        self,
        icon_name: str,
        tooltip: str,
        small: bool = False,
        accessible_name: str = "",
    ) -> QPushButton:
        button = QPushButton()
        button.setText("")
        button.setIcon(load_icon(icon_name))
        button.setToolTip(tooltip)
        button.setAccessibleName(accessible_name or tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        button.setProperty("iconOnly", True)
        button.setProperty("smallIcon", small)
        self._icon_buttons.append(button)
        self._apply_icon_size(button)
        return button

    def _apply_icon_sizes(self) -> None:
        for button in self._icon_buttons:
            self._apply_icon_size(button)

    def _apply_icon_size(self, button: QPushButton) -> None:
        width = self.window().width() if self.window() else self.width()
        if width >= 1800:
            icon_size, touch_size = (34, 46) if button.property("smallIcon") else (44, 58)
        elif width >= 1200:
            icon_size, touch_size = (28, 40) if button.property("smallIcon") else (34, 48)
        else:
            icon_size, touch_size = (24, 36) if button.property("smallIcon") else (26, 40)
        button.setIconSize(QSize(icon_size, icon_size))
        button.setMinimumSize(touch_size, touch_size)
        button.setMaximumSize(touch_size, touch_size)

    @staticmethod
    def _wrap_html(content: str, chat: ChatRecord | None = None) -> str:
        chat_header = ""
        if chat is not None:
            chat_header = f"""
<section class="chat-meta">
  <div class="request-text">{ResponsePanel._escape(chat.request_text).replace(chr(10), '<br>')}</div>
  <div class="created-at">Created: {chat.created_at:%Y-%m-%d %I:%M %p}</div>
</section>
"""
        return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script>
    window.MathJax = {{tex: {{inlineMath: [['$', '$'], ['\\\\(', '\\\\)']]}}}};
  </script>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
  <style>
    body {{ font-family: {EdTalkiesTheme.FONT_BODY}; font-size: 22px; line-height: 1.5; color: {EdTalkiesTheme.RESPONSE_TEXT}; }}
    body {{ background: {EdTalkiesTheme.RESPONSE_BG}; }}
    .chat-meta {{ background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.18); border-left: 4px solid {EdTalkiesTheme.PURPLE}; border-radius: 12px; padding: 14px; margin-bottom: 16px; color: {EdTalkiesTheme.RESPONSE_TEXT}; }}
    .request-text {{ font-style: italic; font-size: 23px; }}
    .created-at {{ color: {EdTalkiesTheme.TEXT_SOFT}; font-size: 13px; font-style: italic; text-align: right; margin-top: 12px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
    th, td {{ border: 1px solid rgba(255, 255, 255, 0.22); padding: 8px 10px; text-align: left; }}
    th {{ background: rgba(255, 255, 255, 0.10); }}
    code, pre {{ background: rgba(0, 0, 0, 0.42); border-radius: 4px; padding: 2px 5px; }}
    a {{ color: {EdTalkiesTheme.CYAN}; }}
    img {{ max-width: 100%; height: auto; }}
  </style>
</head>
<body>{chat_header}{content}</body>
</html>
"""

    @staticmethod
    def _escape(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    @staticmethod
    def _html_to_plain_text(value: str) -> str:
        if not value:
            return ""
        document = QTextDocument()
        document.setHtml(value)
        return document.toPlainText()
