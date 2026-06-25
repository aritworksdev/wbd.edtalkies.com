"""Compatibility-only mock recognizer for UI tests."""

from aiboard_app.recognition.ocr_provider_base import OcrProvider
from aiboard_app.recognition.ocr_result import OcrResult


class PlaceholderRecognizer(OcrProvider):
    def recognize(self, image_bytes: bytes) -> OcrResult:
        return OcrResult(
            text="Placeholder OCR text",
            confidence=0.0,
            provider="placeholder",
        )


__all__ = ["PlaceholderRecognizer"]
