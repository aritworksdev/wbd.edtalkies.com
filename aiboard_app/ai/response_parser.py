from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResponseDocument:
    file_name: str
    file_type: str
    url: str
    status: str = "available"


@dataclass(frozen=True)
class ParsedResponse:
    title: str
    text: str
    html: str
    documents: list[ResponseDocument] = field(default_factory=list)


class ResponseParser:
    def parse(self, payload: dict[str, Any]) -> ParsedResponse:
        nested = payload.get("data")
        if isinstance(nested, dict):
            payload = {**payload, **nested}
        title = str(payload.get("title") or payload.get("heading") or "EdTalkies Response")
        text = str(payload.get("text") or payload.get("answer") or payload.get("message") or "")
        html = str(payload.get("html") or payload.get("formattedHtml") or "")

        if not html and text:
            html = f"<p>{self._escape(text).replace(chr(10), '<br>')}</p>"

        documents: list[ResponseDocument] = []
        raw_documents = payload.get("documents") or payload.get("files") or payload.get("attachments") or []
        if isinstance(raw_documents, dict):
            raw_documents = [raw_documents]
        for item in raw_documents:
            if not isinstance(item, dict):
                continue
            documents.append(
                ResponseDocument(
                    file_name=str(item.get("fileName") or item.get("name") or "document"),
                    file_type=str(item.get("fileType") or item.get("type") or "unknown"),
                    url=str(item.get("url") or item.get("downloadUrl") or ""),
                    status=str(item.get("status") or "available"),
                )
            )

        return ParsedResponse(title=title, text=text, html=html, documents=documents)

    @staticmethod
    def _escape(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
