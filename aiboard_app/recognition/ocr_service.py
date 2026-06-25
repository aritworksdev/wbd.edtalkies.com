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

    @property
    def google_availability_reason(self) -> str:
        if self._google is None:
            return "GOOGLE_VISION_ENABLED is false"
        return self._google.availability_reason

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

        tesseract = self._try_provider(self._tesseract, image_bytes, attempts, errors)
        if tesseract is not None:
            candidates.append(tesseract)

        if not candidates:
            message = "; ".join(errors) or "No OCR provider returned text."
            raise RuntimeError(message)
        local_result = self._best(candidates)
        return self._use_google_below_high_confidence(
            local_result,
            image_bytes,
            attempts,
            errors,
        )

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
            local_result = OcrResult(
                text="",
                confidence=0.0,
                provider="local-ocr",
                model_name="No local OCR model returned text",
            )
        else:
            local_result = self._best(candidates)
        return self._use_google_below_high_confidence(
            local_result,
            image_bytes,
            attempts,
            errors,
        )

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
            model_name="Google Cloud Vision document_text_detection",
        )

    def _use_google_below_high_confidence(
        self,
        local_result: OcrResult,
        image_bytes: bytes,
        attempts: list[str],
        errors: list[str],
    ) -> OcrResult:
        if self._confidence(local_result) >= self.high_confidence:
            return local_result.with_pipeline_details(attempts, errors)
        if not self.google_available or self._google is None:
            errors.append(f"Google Vision skipped: {self.google_availability_reason}")
            return local_result.with_pipeline_details(attempts, errors)

        google_name = self._provider_name(self._google)
        attempts.append(google_name)
        try:
            google_result = self._google.recognize(image_bytes)
        except Exception as exc:
            LOGGER.warning("%s failed: %s", google_name, exc)
            errors.append(f"{google_name}: {exc}")
            return local_result.with_pipeline_details(attempts, errors)

        if not google_result.text.strip():
            errors.append(f"{google_name}: returned no text")
            return local_result.with_pipeline_details(attempts, errors)
        return google_result.with_pipeline_details(attempts, errors)

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
        name = OcrService._provider_name(provider)
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
        name = OcrService._provider_name(provider)
        attempts.append(name)
        try:
            recognize_document = getattr(provider, "recognize_document", provider.recognize)
            result = recognize_document(image_bytes)
        except Exception as exc:
            LOGGER.warning("%s document OCR failed: %s", name, exc)
            errors.append(f"{name}: {exc}")
            return None
        return result if result.text.strip() else None

    @staticmethod
    def _provider_name(provider: OcrProvider) -> str:
        return str(getattr(provider, "model_name", provider.__class__.__name__))
