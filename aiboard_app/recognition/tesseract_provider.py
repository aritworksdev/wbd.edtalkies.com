from __future__ import annotations

import io
from pathlib import Path

from aiboard_app.recognition.ocr_provider_base import OcrProvider
from aiboard_app.recognition.ocr_result import OcrResult, OcrWord
from aiboard_app.recognition.image_preprocessor import (
    dark_text_on_light,
    decode_grayscale,
    document_variants,
)


class TesseractProvider(OcrProvider):
    """Emergency local OCR fallback using the Tesseract executable."""

    def __init__(self, command: str = "", language: str = "eng") -> None:
        self._command = command
        self._language = language

    @property
    def model_name(self) -> str:
        return f"Tesseract 5 ({self._language})"

    def recognize(self, image_bytes: bytes) -> OcrResult:
        try:
            import pytesseract
            from PIL import Image
            from pytesseract import Output
        except ImportError as exc:
            raise RuntimeError("pytesseract and Pillow are required for Tesseract OCR.") from exc

        if self._command:
            pytesseract.pytesseract.tesseract_cmd = str(Path(self._command).expanduser())
        normalized = dark_text_on_light(decode_grayscale(image_bytes))
        return self._recognize_image(Image.fromarray(normalized), pytesseract, Output)

    def recognize_document(self, image_bytes: bytes) -> OcrResult:
        try:
            import pytesseract
            from PIL import Image
            from pytesseract import Output
        except ImportError as exc:
            raise RuntimeError("pytesseract and Pillow are required for Tesseract OCR.") from exc
        if self._command:
            pytesseract.pytesseract.tesseract_cmd = str(Path(self._command).expanduser())
        candidates = [
            self._recognize_image(Image.fromarray(variant), pytesseract, Output)
            for variant in document_variants(image_bytes)
        ]
        populated = [candidate for candidate in candidates if candidate.text]
        return max(populated, key=lambda item: item.confidence or 0.0) if populated else OcrResult.empty("tesseract")

    def _recognize_image(self, image, pytesseract, output):  # type: ignore[no-untyped-def]
        try:
            data = pytesseract.image_to_data(
                image,
                lang=self._language,
                config="--oem 3 --psm 6",
                output_type=output.DICT,
            )
        except pytesseract.TesseractNotFoundError as exc:
            raise RuntimeError(
                "Tesseract is not installed or TESSERACT_CMD is incorrect."
            ) from exc

        words: list[OcrWord] = []
        for text, raw_confidence in zip(data.get("text", []), data.get("conf", [])):
            text = str(text).strip()
            try:
                confidence = max(0.0, float(raw_confidence) / 100.0)
            except (TypeError, ValueError):
                confidence = 0.0
            if text:
                words.append(OcrWord(text, confidence))
        overall = sum(word.confidence for word in words) / len(words) if words else 0.0
        return OcrResult(
            text=" ".join(word.text for word in words),
            confidence=overall,
            provider="tesseract",
            words=tuple(words),
            model_name=self.model_name,
        )
