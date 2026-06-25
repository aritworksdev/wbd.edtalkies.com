from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

from aiboard_app.app.config import EdTalkiesSettings

LOGGER = logging.getLogger(__name__)


class EdTalkiesError(RuntimeError):
    """Raised when the EdTalkies API cannot return a usable response."""


@dataclass(frozen=True)
class AiQuery:
    text: str
    context: dict[str, Any] | None = None


class EdTalkiesClient:
    def __init__(self, settings: EdTalkiesSettings) -> None:
        self._settings = settings
        self._session = requests.Session()

    def ask(self, query: AiQuery) -> dict[str, Any]:
        if not query.text.strip():
            raise EdTalkiesError("Cannot send an empty question.")

        if not self._settings.is_configured:
            return self._mock_response(query.text)

        context = query.context or {}
        payload = {
            "Channel": str(context.get("Channel") or self._settings.quick_ask_channel),
            "Phone": str(context.get("Phone") or self._settings.quick_ask_phone),
            "Message": query.text.strip(),
            "Language": str(context.get("Language") or self._settings.quick_ask_language),
            "Source": str(context.get("Source") or self._settings.quick_ask_source),
            "Season": str(context.get("Season") or self._settings.quick_ask_season),
            "Genre": str(context.get("Genre") or self._settings.quick_ask_genre),
            "ContentSource": str(
                context.get("ContentSource") or self._settings.quick_ask_content_source
            ),
        }
        return self._post_json(self._settings.ai_query_path, payload)

    def recognize_handwriting(self, image_bytes: bytes, mime_type: str = "image/png") -> dict[str, Any]:
        if not image_bytes:
            raise EdTalkiesError("Cannot recognize an empty image.")
        if not self._settings.is_configured:
            return {"text": "Edit this recognized text before sending it to EdTalkies.", "provider": "mock"}

        headers = self._headers()
        files = {"file": ("whiteboard.png", image_bytes, mime_type)}
        data = {
            "schoolId": self._settings.school_id,
            "boardId": self._settings.board_id,
            "deviceId": self._settings.device_id,
            "sessionId": self._settings.session_id,
        }

        last_error: Exception | None = None
        for attempt in range(self._settings.retry_count + 1):
            try:
                response = self._session.post(
                    self._settings.build_url(self._settings.ocr_path),
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=self._settings.timeout_seconds,
                )
                return self._decode_response(response)
            except (requests.RequestException, EdTalkiesError) as exc:
                last_error = exc
                LOGGER.warning("EdTalkies OCR attempt %s failed: %s", attempt + 1, exc)
                if attempt < self._settings.retry_count:
                    time.sleep(min(2**attempt, 4))
        raise EdTalkiesError(str(last_error or "EdTalkies OCR request failed."))

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self._settings.retry_count + 1):
            try:
                response = self._session.post(
                    self._settings.build_url(path),
                    headers={**self._headers(), "Content-Type": "application/json"},
                    json=payload,
                    timeout=self._settings.timeout_seconds,
                )
                return self._decode_response(response)
            except (requests.RequestException, EdTalkiesError) as exc:
                last_error = exc
                LOGGER.warning("EdTalkies API attempt %s failed: %s", attempt + 1, exc)
                if attempt < self._settings.retry_count:
                    time.sleep(min(2**attempt, 4))
        raise EdTalkiesError(str(last_error or "EdTalkies request failed."))

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._settings.api_key:
            headers["Authorization"] = f"Bearer {self._settings.api_key}"
        return headers

    @staticmethod
    def _decode_response(response: requests.Response) -> dict[str, Any]:
        if response.status_code in {401, 403}:
            raise EdTalkiesError("Invalid or unauthorized EdTalkies API key.")
        if response.status_code >= 400:
            raise EdTalkiesError(f"EdTalkies API error {response.status_code}: {response.text[:300]}")
        if not response.content:
            raise EdTalkiesError("EdTalkies returned an empty response.")
        try:
            data = response.json()
        except ValueError as exc:
            raise EdTalkiesError("EdTalkies returned non-JSON content.") from exc
        if not isinstance(data, dict):
            raise EdTalkiesError("EdTalkies returned an unsupported response shape.")
        return data

    @staticmethod
    def _mock_response(question: str) -> dict[str, Any]:
        safe_question = (
            question.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return {
            "title": "AiBoard Mock Response",
            "text": (
                "The EdTalkies API is not configured, so AiBoard is running in mock mode. "
                f"Your question was: {question}"
            ),
            "html": (
                "<h2>Mock mode is active</h2>"
                "<p>Configure <code>EDTALKIES_API_BASE_URL</code> and "
                "<code>EDTALKIES_API_KEY</code> in <code>.env</code> to use the live service.</p>"
                f"<p><strong>Your question:</strong> {safe_question}</p>"
            ),
            "documents": [],
            "mock": True,
        }
