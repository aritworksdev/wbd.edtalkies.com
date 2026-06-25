from __future__ import annotations

from abc import ABC, abstractmethod
from aiboard_app.recognition.ocr_result import OcrResult

RecognitionResult = OcrResult


class OcrProvider(ABC):
    @property
    def model_name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def recognize(self, image_bytes: bytes) -> OcrResult:
        raise NotImplementedError
