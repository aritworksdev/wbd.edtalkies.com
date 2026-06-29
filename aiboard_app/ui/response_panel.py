from __future__ import annotations

import re

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
    edit_requested = Signal(str)
    generated_download_requested = Signal(str, str, str)
    generated_open_requested = Signal(str, str, str)
    image_download_requested = Signal(str, str)

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
        self._actions = QHBoxLayout()
        self._actions.setSpacing(8)
        layout.addLayout(self._actions)
        self._current_response = ParsedResponse("", "", "")
        self._current_chat: ChatRecord | None = None

    @property
    def current_chat(self) -> ChatRecord | None:
        return self._current_chat

    def show_response(self, response: ParsedResponse, chat: ChatRecord | None = None) -> None:
        self._current_response = response
        self._current_chat = chat
        self._title.setText(response.title)
        html = self._wrap_html(self._render_content_html(response), chat)
        if QWebEngineView is not None and isinstance(self._viewer, QWebEngineView):
            self._viewer.setHtml(html, QUrl("https://edtalkies.com/"))
        elif isinstance(self._viewer, QTextBrowser):
            self._viewer.setHtml(html)

        self._clear_documents()
        self._clear_actions()
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
        self._build_actions(response)
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

    def _clear_actions(self) -> None:
        while self._actions.count():
            item = self._actions.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

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

    def _build_actions(self, response: ParsedResponse) -> None:
        if not (response.text or response.html or response.documents):
            return
        edit_button = self._icon_button(
            IconName.EDIT_DB,
            "Edit response",
            small=True,
            accessible_name="Edit AI response",
        )
        edit_button.clicked.connect(lambda: self.edit_requested.emit(response.unique_id))
        self._actions.addWidget(edit_button)

        if response.is_image_response:
            image_button = self._icon_button(
                IconName.UPLOAD,
                "Download image",
                small=True,
                accessible_name="Download image response",
            )
            image_button.clicked.connect(
                lambda: self.image_download_requested.emit(
                    response.text or response.html,
                    "edtalkies-image.png",
                )
            )
            self._actions.addWidget(image_button)
        elif response.is_downloadable:
            if self._is_generated_document_content(response.intent_content_type):
                open_format = self._primary_download_format(response.intent_content_type)
                open_button = self._icon_button(
                    IconName.UPDATE,
                    "Open document",
                    small=True,
                    accessible_name="Open generated document",
                )
                open_button.clicked.connect(
                    lambda checked=False, fmt=open_format:
                        self.generated_open_requested.emit(response.unique_id, fmt, response.downloadable_link)
                )
                self._actions.addWidget(open_button)
            for icon_name, tooltip, file_format in self._download_actions(response.intent_content_type):
                button = self._icon_button(
                    icon_name,
                    tooltip,
                    small=True,
                    accessible_name=tooltip,
                )
                button.clicked.connect(
                    lambda checked=False, fmt=file_format:
                        self.generated_download_requested.emit(response.unique_id, fmt, response.downloadable_link)
                )
                self._actions.addWidget(button)

        self._actions.addStretch(1)

    @staticmethod
    def _download_actions(content_type: str) -> list[tuple[str, str, str]]:
        normalized = ResponsePanel._normalize_content_type(content_type)
        if normalized in {"text", "lesson"}:
            return [
                (IconName.PDF, "Download PDF", "pdf"),
                (IconName.DOCX, "Download Word", "docx"),
            ]
        if normalized == "slides":
            return [(IconName.PPTX, "Download PowerPoint", "pptx")]
        if normalized == "sheet":
            return [(IconName.EXCEL, "Download Excel", "xlsx")]
        if normalized == "schedule":
            return [(IconName.CALENDAR, "Download Calendar", "ics")]
        return []

    @staticmethod
    def _is_generated_document_content(content_type: str) -> bool:
        return ResponsePanel._normalize_content_type(content_type) in {"slides", "sheet", "schedule"}

    @staticmethod
    def _primary_download_format(content_type: str) -> str:
        normalized = ResponsePanel._normalize_content_type(content_type)
        if normalized == "slides":
            return "pptx"
        if normalized == "sheet":
            return "xlsx"
        if normalized == "schedule":
            return "ics"
        return "pdf"

    @staticmethod
    def _normalize_content_type(content_type: str) -> str:
        normalized = content_type.strip().lower()
        if "." in normalized:
            normalized = normalized.rsplit(".", 1)[-1]
        return normalized

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
            icon_size, touch_size = (25, 36) if button.property("smallIcon") else (44, 58)
        elif width >= 1200:
            icon_size, touch_size = (25, 36) if button.property("smallIcon") else (34, 48)
        else:
            icon_size, touch_size = (23, 34) if button.property("smallIcon") else (26, 40)
        button.setIconSize(QSize(icon_size, icon_size))
        button.setMinimumSize(touch_size, touch_size)
        button.setMaximumSize(touch_size, touch_size)

    @staticmethod
    def _render_content_html(response: ParsedResponse) -> str:
        content = response.text or response.html
        if response.is_image_response:
            return ResponsePanel._image_html(content)
        if response.is_downloadable and ResponsePanel._is_generated_document_content(response.intent_content_type):
            return ResponsePanel._generated_document_html(response.intent_content_type)
        if response.text.strip():
            return ResponsePanel._markdown_to_html(response.text)
        if response.html and response.html.strip().startswith("<"):
            return ResponsePanel._sanitize_html(response.html)
        if content.strip():
            return ResponsePanel._markdown_to_html(content)
        return "<p><em>EdTalkies returned an empty response.</em></p>"

    @staticmethod
    def _image_html(source: str) -> str:
        source = source.strip()
        if not source:
            return "<p><em>Image response was empty.</em></p>"
        image_src = ResponsePanel._escape(source)
        if not source.startswith(("http://", "https://", "data:image/")):
            image_src = f"data:image/png;base64,{image_src}"
        return (
            '<div class="image-response">'
            f'<img src="{image_src}" alt="EdTalkies image response">'
            '<p class="image-hint">Use the download icon below to save this image.</p>'
            "</div>"
        )

    @staticmethod
    def _generated_document_html(content_type: str) -> str:
        label = ResponsePanel._normalize_content_type(content_type).title() or "Document"
        return (
            '<div class="generated-document-response">'
            f"<h2>{ResponsePanel._escape(label)} is ready</h2>"
            "<p>Use the Open icon below to open the generated document, "
            "or use the format icon to download it.</p>"
            "</div>"
        )

    @staticmethod
    def _markdown_to_html(markdown: str) -> str:
        lines = markdown.replace("\r\n", "\n").split("\n")
        html: list[str] = []
        in_code = False
        code_lines: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if stripped.startswith("```"):
                if in_code:
                    html.append(f"<pre><code>{ResponsePanel._escape(chr(10).join(code_lines))}</code></pre>")
                    code_lines = []
                    in_code = False
                else:
                    in_code = True
                i += 1
                continue
            if in_code:
                code_lines.append(line)
                i += 1
                continue
            if not stripped:
                i += 1
                continue
            if ResponsePanel._is_markdown_table(lines, i):
                table_lines = []
                while i < len(lines) and "|" in lines[i]:
                    table_lines.append(lines[i])
                    i += 1
                html.append(ResponsePanel._table_to_html(table_lines))
                continue
            heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if heading:
                level = min(len(heading.group(1)), 4)
                html.append(f"<h{level}>{ResponsePanel._inline_markdown(heading.group(2))}</h{level}>")
            elif re.match(r"^[-*]\s+", stripped):
                items = []
                while i < len(lines) and re.match(r"^[-*]\s+", lines[i].strip()):
                    items.append(re.sub(r"^[-*]\s+", "", lines[i].strip()))
                    i += 1
                html.append("<ul>" + "".join(f"<li>{ResponsePanel._inline_markdown(item)}</li>" for item in items) + "</ul>")
                continue
            elif re.match(r"^\d+\.\s+", stripped):
                items = []
                while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                    items.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                    i += 1
                html.append("<ol>" + "".join(f"<li>{ResponsePanel._inline_markdown(item)}</li>" for item in items) + "</ol>")
                continue
            else:
                html.append(f"<p>{ResponsePanel._inline_markdown(stripped)}</p>")
            i += 1
        if in_code:
            html.append(f"<pre><code>{ResponsePanel._escape(chr(10).join(code_lines))}</code></pre>")
        return "\n".join(html)

    @staticmethod
    def _inline_markdown(value: str) -> str:
        text = ResponsePanel._escape(value)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
        return text

    @staticmethod
    def _is_markdown_table(lines: list[str], index: int) -> bool:
        return (
            index + 1 < len(lines)
            and "|" in lines[index]
            and re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[index + 1]) is not None
        )

    @staticmethod
    def _table_to_html(lines: list[str]) -> str:
        rows = [
            [ResponsePanel._inline_markdown(cell.strip()) for cell in line.strip().strip("|").split("|")]
            for line in lines
            if not re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", line)
        ]
        if not rows:
            return ""
        header = "".join(f"<th>{cell}</th>" for cell in rows[0])
        body = "".join(
            "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
            for row in rows[1:]
        )
        return f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"

    @staticmethod
    def _sanitize_html(value: str) -> str:
        cleaned = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", value, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"\son\w+\s*=\s*(['\"]).*?\1", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"javascript:", "", cleaned, flags=re.IGNORECASE)
        return cleaned

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
    .image-response {{ text-align: center; margin: 10px 0 18px; }}
    .image-response img {{ width: 80%; max-width: 100%; height: auto; border-radius: 10px; }}
    .image-hint {{ color: {EdTalkiesTheme.TEXT_SOFT}; font-size: 14px; font-style: italic; }}
    .generated-document-response {{ background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 12px; padding: 18px; text-align: center; }}
    .generated-document-response h2 {{ margin-top: 0; }}
    .generated-document-response p {{ color: {EdTalkiesTheme.TEXT_MUTED}; }}
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
