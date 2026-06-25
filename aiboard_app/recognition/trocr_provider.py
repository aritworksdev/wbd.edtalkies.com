from __future__ import annotations

from aiboard_app.recognition.local_ocr_provider import LocalOcrProvider
from aiboard_app.recognition.ocr_result import OcrResult, OcrWord


class TrOcrProvider(LocalOcrProvider):
    """Handwriting-specialized fallback backed by Microsoft TrOCR."""

    def recognize(self, image_bytes: bytes) -> OcrResult:
        result = super().recognize(image_bytes)
        confidence = result.confidence or 0.0
        words = tuple(OcrWord(text, confidence) for text in result.text.split())
        return OcrResult(
            text=result.text,
            confidence=result.confidence,
            provider="trocr",
            words=words,
        )
