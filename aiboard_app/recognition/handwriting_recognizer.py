from __future__ import annotations

from aiboard_app.app.config import AppSettings
from aiboard_app.recognition.google_vision_provider import GoogleVisionProvider
from aiboard_app.recognition.ocr_service import OcrService
from aiboard_app.recognition.paddle_ocr_provider import PaddleOcrProvider
from aiboard_app.recognition.tesseract_provider import TesseractProvider
from aiboard_app.recognition.trocr_provider import TrOcrProvider

HandwritingRecognizer = OcrService


def build_handwriting_recognizer(settings: AppSettings, client=None) -> OcrService:  # type: ignore[no-untyped-def]
    google = None
    if settings.google_vision_enabled:
        google = GoogleVisionProvider(
            settings.google_application_credentials,
            settings.google_cloud_project_id,
        )
    return OcrService(
        paddle=PaddleOcrProvider(settings.ocr_language),
        trocr=TrOcrProvider(settings.local_handwriting_model),
        tesseract=TesseractProvider(settings.tesseract_cmd, settings.tesseract_language),
        google=google,
        high_confidence=settings.ocr_confidence_high,
        medium_confidence=settings.ocr_confidence_medium,
    )
