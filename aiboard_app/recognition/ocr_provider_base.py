from __future__ import annotations

from abc import ABC, abstractmethod
from aiboard_app.recognition.ocr_result import OcrResult

RecognitionResult = OcrResult


class OcrProvider(ABC):
    @abstractmethod
    def recognize(self, image_bytes: bytes) -> OcrResult:
        raise NotImplementedError
