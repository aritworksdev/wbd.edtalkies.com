from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse


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
        intent = payload.get("Intent")
        if not isinstance(intent, dict):
            intent = {}

        title = str(
            payload.get("Title")
            or payload.get("title")
            or payload.get("heading")
            or "EdTalkies Response"
        )
        errors = payload.get("ErrorMessages")
        error_text = (
            "\n".join(str(error) for error in errors if error)
            if isinstance(errors, list)
            else ""
        )
        request_failed = (
            "IsSuccess" in payload and not self._as_bool(payload.get("IsSuccess"))
        ) or (
            "IsApiCallSuccess" in payload
            and not self._as_bool(payload.get("IsApiCallSuccess"))
        )
        if self._as_bool(payload.get("IsLimitReached")):
            text = str(
                payload.get("UpsellMessage")
                or payload.get("Message")
                or "The EdTalkies usage limit has been reached."
            )
        elif request_failed and error_text:
            text = error_text
        else:
            text = str(
                payload.get("Response")
                or payload.get("text")
                or payload.get("answer")
                or payload.get("Message")
                or payload.get("message")
                or intent.get("Message")
                or ""
            )
        html = str(
            payload.get("Html")
            or payload.get("html")
            or payload.get("FormattedHtml")
            or payload.get("formattedHtml")
            or ""
        )

        if not text and error_text:
            text = error_text

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

        if self._as_bool(payload.get("IsDownloadable")):
            download_url = str(payload.get("DownloadableLink") or "").strip()
            if download_url:
                documents.append(
                    ResponseDocument(
                        file_name=self._file_name(download_url),
                        file_type=self._file_type(download_url),
                        url=download_url,
                        status="available",
                    )
                )

        return ParsedResponse(title=title, text=text, html=html, documents=documents)

    @staticmethod
    def _as_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes"}

    @staticmethod
    def _file_name(url: str) -> str:
        name = PurePosixPath(unquote(urlparse(url).path)).name
        return name or "edtalkies-download"

    @staticmethod
    def _file_type(url: str) -> str:
        suffix = PurePosixPath(urlparse(url).path).suffix.lstrip(".")
        return suffix.upper() or "unknown"

    @staticmethod
    def _escape(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
