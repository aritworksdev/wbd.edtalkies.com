from __future__ import annotations

from aiboard_app.ai.edtalkies_client import EdTalkiesClient
from aiboard_app.recognition.ocr_provider_base import OcrProvider, RecognitionResult


class EdTalkiesOcrProvider(OcrProvider):
    def __init__(self, client: EdTalkiesClient) -> None:
        self._client = client

    def recognize(self, image_bytes: bytes) -> RecognitionResult:
        payload = self._client.recognize_handwriting(image_bytes)
        text = str(payload.get("text") or payload.get("recognizedText") or payload.get("result") or "")
        confidence_value = payload.get("confidence")
        confidence = float(confidence_value) if isinstance(confidence_value, int | float) else None
        return RecognitionResult(text=text, confidence=confidence, provider="edtalkies")
