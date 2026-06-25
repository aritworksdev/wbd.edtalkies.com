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

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover - depends on Qt package availability.
    QWebEngineView = None  # type: ignore[assignment]


class ResponsePanel(QFrame):
    close_requested = Signal()
    document_open_requested = Signal(str, str)
    document_download_requested = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("ResponsePanel")
        self.setMinimumWidth(420)
        self.setMaximumWidth(720)

        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        self._title = QLabel("EdTalkies Response")
        self._title.setObjectName("ResponseTitle")
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close_requested.emit)
        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self._copy_response)
        save_button = QPushButton("Save")
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
        self._current_response = ParsedResponse("", "", "")

    def show_response(self, response: ParsedResponse) -> None:
        self._current_response = response
        self._title.setText(response.title)
        html = self._wrap_html(response.html or response.text)
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

    @staticmethod
    def _wrap_html(content: str) -> str:
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
    body {{ font-family: Arial, sans-serif; font-size: 22px; line-height: 1.45; color: #1f2933; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; }}
    th {{ background: #eef2f7; }}
    code, pre {{ background: #f1f5f9; border-radius: 4px; padding: 2px 5px; }}
    img {{ max-width: 100%; height: auto; }}
  </style>
</head>
<body>{content}</body>
</html>
"""
