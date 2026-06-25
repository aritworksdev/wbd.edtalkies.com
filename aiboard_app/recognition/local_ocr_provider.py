from __future__ import annotations

from aiboard_app.recognition.ocr_provider_base import OcrProvider, RecognitionResult


class LocalOcrProvider(OcrProvider):
    def recognize(self, image_bytes: bytes) -> RecognitionResult:
        return RecognitionResult(
            text="",
            confidence=None,
            provider="local-placeholder",
        )
