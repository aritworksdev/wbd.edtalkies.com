from __future__ import annotations

import json
from typing import Any

from aiboard_app.recognition.ocr_provider_base import OcrProvider
from aiboard_app.recognition.ocr_result import OcrResult, OcrWord
from aiboard_app.recognition.image_preprocessor import document_variants, normalized_color_image


class PaddleOcrProvider(OcrProvider):
    """Primary local OCR provider using PaddleOCR."""

    def __init__(self, language: str = "en") -> None:
        self._language = language
        self._engine: Any = None

    def recognize(self, image_bytes: bytes) -> OcrResult:
        if not image_bytes:
            return OcrResult.empty("paddleocr")
        try:
            import cv2  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("PaddleOCR image dependencies are not installed.") from exc

        self._load_engine()
        image = normalized_color_image(image_bytes)

        if hasattr(self._engine, "predict"):
            raw = list(self._engine.predict(input=image))
            words = self._parse_v3(raw)
        else:
            raw = self._engine.ocr(image, cls=True)
            words = self._parse_v2(raw)
        return self._result(words)

    def recognize_document(self, image_bytes: bytes) -> OcrResult:
        import cv2

        self._load_engine()
        candidates: list[OcrResult] = []
        for variant in document_variants(image_bytes):
            image = cv2.cvtColor(variant, cv2.COLOR_GRAY2BGR)
            if hasattr(self._engine, "predict"):
                words = self._parse_v3(list(self._engine.predict(input=image)))
            else:
                words = self._parse_v2(self._engine.ocr(image, cls=True))
            result = self._result(words)
            if result.text:
                candidates.append(result)
        return max(candidates, key=lambda item: item.confidence or 0.0) if candidates else OcrResult.empty("paddleocr")

    def _load_engine(self) -> None:
        if self._engine is not None:
            return
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise RuntimeError(
                "PaddleOCR is unavailable. Install PaddlePaddle and PaddleOCR "
                "using the Windows instructions in README.md."
            ) from exc
        try:
            self._engine = PaddleOCR(
                lang=self._language,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        except TypeError:
            self._engine = PaddleOCR(lang=self._language, use_angle_cls=True, show_log=False)

    @staticmethod
    def _parse_v3(results: list[Any]) -> list[OcrWord]:
        words: list[OcrWord] = []
        for result in results:
            data = getattr(result, "json", None)
            if callable(data):
                data = data()
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except ValueError:
                    data = None
            if not isinstance(data, dict):
                data = getattr(result, "res", None)
            if isinstance(data, dict) and isinstance(data.get("res"), dict):
                data = data["res"]
            if not isinstance(data, dict):
                continue
            texts = data.get("rec_texts") or []
            scores = data.get("rec_scores") or []
            for text, score in zip(texts, scores):
                words.extend(PaddleOcrProvider._split_words(str(text), float(score)))
        return words

    @staticmethod
    def _parse_v2(results: Any) -> list[OcrWord]:
        words: list[OcrWord] = []
        for page in results or []:
            for item in page or []:
                if not isinstance(item, (list, tuple)) or len(item) < 2:
                    continue
                recognition = item[1]
                if not isinstance(recognition, (list, tuple)) or len(recognition) < 2:
                    continue
                words.extend(
                    PaddleOcrProvider._split_words(str(recognition[0]), float(recognition[1]))
                )
        return words

    @staticmethod
    def _split_words(text: str, confidence: float) -> list[OcrWord]:
        return [OcrWord(token, confidence) for token in text.split() if token]

    @staticmethod
    def _result(words: list[OcrWord]) -> OcrResult:
        text = " ".join(word.text for word in words)
        confidence = sum(word.confidence for word in words) / len(words) if words else 0.0
        return OcrResult(text, confidence, "paddleocr", tuple(words))
