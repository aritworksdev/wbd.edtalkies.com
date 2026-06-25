from __future__ import annotations

from aiboard_app.ai.edtalkies_client import EdTalkiesClient
from aiboard_app.app.config import AppSettings
from aiboard_app.recognition.edtalkies_ocr_provider import EdTalkiesOcrProvider
from aiboard_app.recognition.local_ocr_provider import LocalOcrProvider
from aiboard_app.recognition.ocr_provider_base import OcrProvider, RecognitionResult


class PlaceholderRecognizer(OcrProvider):
    def recognize(self, image_bytes: bytes) -> RecognitionResult:
        return RecognitionResult(
            text="Edit this recognized text before sending it to EdTalkies.",
            confidence=None,
            provider="placeholder",
        )


class HandwritingRecognizer:
    def __init__(self, provider: OcrProvider) -> None:
        self._provider = provider

    def recognize(self, image_bytes: bytes) -> RecognitionResult:
        return self._provider.recognize(image_bytes)


def build_handwriting_recognizer(settings: AppSettings, client: EdTalkiesClient) -> HandwritingRecognizer:
    provider_name = settings.handwriting_provider
    if provider_name == "edtalkies":
        provider: OcrProvider = EdTalkiesOcrProvider(client)
    elif provider_name == "local":
        provider = LocalOcrProvider(settings.local_handwriting_model)
    else:
        provider = PlaceholderRecognizer()
    return HandwritingRecognizer(provider)
