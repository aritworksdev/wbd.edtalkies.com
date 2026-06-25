from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OcrWord:
    text: str
    confidence: float


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float | None
    provider: str
    words: tuple[OcrWord, ...] = ()
    attempts: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def with_pipeline_details(
        self,
        attempts: list[str],
        errors: list[str],
    ) -> "OcrResult":
        return OcrResult(
            text=self.text,
            confidence=self.confidence,
            provider=self.provider,
            words=self.words,
            attempts=tuple(attempts),
            errors=tuple(errors),
        )

    def uncertain_words(self, threshold: float) -> tuple[OcrWord, ...]:
        return tuple(word for word in self.words if word.confidence < threshold)

    @staticmethod
    def empty(provider: str = "none") -> "OcrResult":
        return OcrResult(text="", confidence=0.0, provider=provider)
