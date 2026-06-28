from __future__ import annotations

import re
from html import unescape
from pathlib import Path

from aiboard_app.chat.chat_record import ChatRecord


class ChatExporter:
    def __init__(self, export_dir: Path) -> None:
        self._export_dir = export_dir / "chat_exports"

    def default_path(self, chat: ChatRecord, file_type: str) -> Path:
        stamp = chat.created_at.strftime("%Y%m%d_%H%M%S")
        suffix = file_type.lower().lstrip(".")
        return self._export_dir / f"AiBoard_Chat_{stamp}.{suffix}"

    def export(self, chat: ChatRecord, file_type: str, destination: Path | None = None) -> Path:
        suffix = file_type.lower().lstrip(".")
        path = destination or self.default_path(chat, suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        if suffix == "txt":
            self._export_txt(chat, path)
        elif suffix == "docx":
            self._export_docx(chat, path)
        elif suffix == "pdf":
            self._export_pdf(chat, path)
        else:
            raise ValueError(f"Unsupported export type: {file_type}")
        return path

    def _export_txt(self, chat: ChatRecord, path: Path) -> None:
        path.write_text(self._plain_content(chat), encoding="utf-8")

    def _export_docx(self, chat: ChatRecord, path: Path) -> None:
        try:
            from docx import Document
        except ImportError as exc:  # pragma: no cover - dependency is declared.
            raise RuntimeError("DOCX export requires python-docx.") from exc

        document = Document()
        document.add_heading("AiBoard Chat", level=1)
        document.add_paragraph(f"Created: {chat.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        document.add_paragraph(f"Chat ID: {chat.id}")
        if chat.session_id:
            document.add_paragraph(f"Session ID: {chat.session_id}")
        document.add_heading("Recognized Text / Request", level=2)
        document.add_paragraph(chat.request_text)
        document.add_heading(chat.response.title or "EdTalkies Response", level=2)
        document.add_paragraph(self._response_text(chat))
        document.save(path)

    def _export_pdf(self, chat: ChatRecord, path: Path) -> None:
        try:
            import fitz
        except ImportError as exc:  # pragma: no cover - dependency is declared.
            raise RuntimeError("PDF export requires PyMuPDF.") from exc

        doc = fitz.open()
        page = doc.new_page()
        margin = 54
        cursor_y = margin
        lines = self._plain_content(chat).splitlines()
        for line in lines:
            if cursor_y > page.rect.height - margin:
                page = doc.new_page()
                cursor_y = margin
            page.insert_text(
                (margin, cursor_y),
                line or " ",
                fontsize=11,
                fontname="helv",
                color=(0, 0, 0),
            )
            cursor_y += 16
        doc.save(path)
        doc.close()

    def _plain_content(self, chat: ChatRecord) -> str:
        return "\n".join(
            [
                "AiBoard Chat",
                f"Created: {chat.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Chat ID: {chat.id}",
                "",
                "Recognized Text / Request:",
                chat.request_text,
                "",
                f"{chat.response.title or 'EdTalkies Response'}:",
                self._response_text(chat),
                "",
            ]
        )

    @staticmethod
    def _response_text(chat: ChatRecord) -> str:
        if chat.response.text.strip():
            return chat.response.text.strip()
        html = chat.response.html
        text = re.sub(r"(?i)<br\s*/?>", "\n", html)
        text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", text)
        text = re.sub(r"<[^>]+>", "", text)
        return unescape(text).strip()
