from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class RecognitionResult:
    text: str
    confidence: float | None = None
    provider: str = "unknown"


class OcrProvider(ABC):
    @abstractmethod
    def recognize(self, image_bytes: bytes) -> RecognitionResult:
        raise NotImplementedError
