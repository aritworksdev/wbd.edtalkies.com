from __future__ import annotations

from PySide6.QtCore import Signal, QUrl
from PySide6.QtGui import QGuiApplication
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

        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        self._title = QLabel("EdTalkies Response")
        self._title.setObjectName("ResponseTitle")
        close_button = QPushButton("✕ Close")
        close_button.clicked.connect(self.close_requested.emit)
        copy_button = QPushButton("⧉ Copy")
        copy_button.clicked.connect(self._copy_response)
        save_button = QPushButton("💾 Save")
        save_button.clicked.connect(self._save_response)
        header.addWidget(self._title, 1)
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
        self._pdf_button = QPushButton("▣ PDF")
        self._docx_button = QPushButton("▤ Word / DOCX")
        self._txt_button = QPushButton("☰ Text")
        self._pdf_button.clicked.connect(lambda: self.export_requested.emit("pdf"))
        self._docx_button.clicked.connect(lambda: self.export_requested.emit("docx"))
        self._txt_button.clicked.connect(lambda: self.export_requested.emit("txt"))
        self._exports.addWidget(export_label)
        self._exports.addWidget(self._pdf_button)
        self._exports.addWidget(self._docx_button)
        self._exports.addWidget(self._txt_button)
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
            open_button = QPushButton("Download & Open")
            open_button.clicked.connect(
                lambda checked=False, url=document.url, name=document.file_name:
                    self.document_open_requested.emit(url, name)
            )
            download_button = QPushButton("Download")
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
        if self._current_chat is not None:
            text = (
                f"Created: {self._current_chat.created_at:%Y-%m-%d %H:%M:%S}\n\n"
                f"Request:\n{self._current_chat.request_text}\n\n"
                f"Response:\n{self._current_response.text or self._current_response.html}"
            )
        else:
            text = self._current_response.text or self._current_response.html
        QGuiApplication.clipboard().setText(text)

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
        self._pdf_button.setEnabled(enabled)
        self._docx_button.setEnabled(enabled)
        self._txt_button.setEnabled(enabled)

    @staticmethod
    def _wrap_html(content: str, chat: ChatRecord | None = None) -> str:
        chat_header = ""
        if chat is not None:
            chat_header = f"""
<section class="chat-meta">
  <div><strong>Created:</strong> {chat.created_at:%Y-%m-%d %H:%M:%S}</div>
  <h3>Recognized Text / Request</h3>
  <p>{ResponsePanel._escape(chat.request_text).replace(chr(10), '<br>')}</p>
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
    .chat-meta {{ background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid {EdTalkiesTheme.PURPLE}; border-radius: 12px; padding: 12px; margin-bottom: 16px; }}
    .chat-meta h3 {{ margin-bottom: 6px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; }}
    th {{ background: #eef2f7; }}
    code, pre {{ background: #eef2ff; border-radius: 4px; padding: 2px 5px; }}
    a {{ color: {EdTalkiesTheme.BLUE}; }}
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
