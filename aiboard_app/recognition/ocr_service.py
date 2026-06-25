from __future__ import annotations

import logging

from aiboard_app.recognition.google_vision_provider import GoogleVisionProvider
from aiboard_app.recognition.ocr_provider_base import OcrProvider
from aiboard_app.recognition.ocr_result import OcrResult

LOGGER = logging.getLogger(__name__)


class OcrService:
    def __init__(
        self,
        paddle: OcrProvider,
        trocr: OcrProvider,
        tesseract: OcrProvider,
        google: GoogleVisionProvider | None,
        high_confidence: float,
        medium_confidence: float,
    ) -> None:
        self._paddle = paddle
        self._trocr = trocr
        self._tesseract = tesseract
        self._google = google
        self.high_confidence = high_confidence
        self.medium_confidence = medium_confidence

    @property
    def google_available(self) -> bool:
        return self._google is not None and self._google.available

    def recognize(self, image_bytes: bytes) -> OcrResult:
        attempts: list[str] = []
        errors: list[str] = []
        candidates: list[OcrResult] = []

        paddle = self._try_provider(self._paddle, image_bytes, attempts, errors)
        if paddle is not None:
            candidates.append(paddle)
            if self._confidence(paddle) >= self.high_confidence:
                return paddle.with_pipeline_details(attempts, errors)

        trocr = self._try_provider(self._trocr, image_bytes, attempts, errors)
        if trocr is not None:
            candidates.append(trocr)
            if self._confidence(trocr) >= self.medium_confidence:
                return self._best(candidates).with_pipeline_details(attempts, errors)

        tesseract = self._try_provider(self._tesseract, image_bytes, attempts, errors)
        if tesseract is not None:
            candidates.append(tesseract)

        if not candidates:
            message = "; ".join(errors) or "No OCR provider returned text."
            raise RuntimeError(message)
        return self._best(candidates).with_pipeline_details(attempts, errors)

    def recognize_document(self, image_bytes: bytes) -> OcrResult:
        """Printed-document path: PaddleOCR, enhanced Tesseract, then TrOCR."""
        attempts: list[str] = []
        errors: list[str] = []
        candidates: list[OcrResult] = []

        paddle = self._try_document_provider(self._paddle, image_bytes, attempts, errors)
        if paddle is not None:
            candidates.append(paddle)
            if self._confidence(paddle) >= self.high_confidence:
                return paddle.with_pipeline_details(attempts, errors)

        tesseract = self._try_document_provider(self._tesseract, image_bytes, attempts, errors)
        if tesseract is not None:
            candidates.append(tesseract)
            if self._confidence(tesseract) >= self.high_confidence:
                return tesseract.with_pipeline_details(attempts, errors)

        trocr = self._try_provider(self._trocr, image_bytes, attempts, errors)
        if trocr is not None:
            candidates.append(trocr)
        if not candidates:
            raise RuntimeError("; ".join(errors) or "No document OCR provider returned text.")
        return self._best(candidates).with_pipeline_details(attempts, errors)

    def recognize_with_google(self, image_bytes: bytes) -> OcrResult:
        if not self.google_available or self._google is None:
            raise RuntimeError("Google Vision OCR is disabled or credentials are missing.")
        result = self._google.recognize(image_bytes)
        return result.with_pipeline_details(["google-vision"], [])

    def recognize_many_with_google(self, images: tuple[bytes, ...]) -> OcrResult:
        if not images:
            raise RuntimeError("No document images are available for Google Vision OCR.")
        results = [self.recognize_with_google(image) for image in images]
        populated = [result for result in results if result.text.strip()]
        if not populated:
            return OcrResult.empty("google-vision")
        confidences = [result.confidence for result in populated if result.confidence is not None]
        confidence = sum(confidences) / len(confidences) if confidences else None
        return OcrResult(
            text="\n\n".join(result.text for result in populated),
            confidence=confidence,
            provider="google-vision",
            words=tuple(word for result in populated for word in result.words),
            attempts=("google-vision",),
        )

    @staticmethod
    def _confidence(result: OcrResult) -> float:
        return result.confidence or 0.0

    @classmethod
    def _best(cls, candidates: list[OcrResult]) -> OcrResult:
        return max(candidates, key=lambda result: (bool(result.text.strip()), cls._confidence(result)))

    @staticmethod
    def _try_provider(
        provider: OcrProvider,
        image_bytes: bytes,
        attempts: list[str],
        errors: list[str],
    ) -> OcrResult | None:
        name = provider.__class__.__name__
        attempts.append(name)
        try:
            result = provider.recognize(image_bytes)
        except Exception as exc:
            LOGGER.warning("%s failed: %s", name, exc)
            errors.append(f"{name}: {exc}")
            return None
        return result if result.text.strip() else None

    @staticmethod
    def _try_document_provider(
        provider: OcrProvider,
        image_bytes: bytes,
        attempts: list[str],
        errors: list[str],
    ) -> OcrResult | None:
        name = provider.__class__.__name__
        attempts.append(name)
        try:
            recognize_document = getattr(provider, "recognize_document", provider.recognize)
            result = recognize_document(image_bytes)
        except Exception as exc:
            LOGGER.warning("%s document OCR failed: %s", name, exc)
            errors.append(f"{name}: {exc}")
            return None
        return result if result.text.strip() else None
