"""Compatibility exports for future handwriting recognizers."""

from aiboard_app.recognition.ocr_provider_base import OcrProvider as RecognizerBase
from aiboard_app.recognition.ocr_provider_base import RecognitionResult

__all__ = ["RecognizerBase", "RecognitionResult"]
