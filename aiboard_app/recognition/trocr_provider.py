from __future__ import annotations

from aiboard_app.recognition.local_ocr_provider import LocalOcrProvider
from aiboard_app.recognition.ocr_result import OcrResult, OcrWord


class TrOcrProvider(LocalOcrProvider):
    """Handwriting-specialized fallback backed by Microsoft TrOCR."""

    def recognize(self, image_bytes: bytes) -> OcrResult:
        result = super().recognize(image_bytes)
        # Neural generation probabilities are systematically overconfident and
        # are not equivalent to OCR correctness. Calibrate them so uncertain
        # TrOCR output still receives teacher review and can expose cloud OCR.
        confidence = min((result.confidence or 0.0) * 0.85, 0.84)
        words = tuple(OcrWord(text, confidence) for text in result.text.split())
        return OcrResult(
            text=result.text,
            confidence=confidence,
            provider="trocr",
            words=words,
            model_name=self.model_name,
        )
    @property
    def model_name(self) -> str:
        return self._model_id
