from __future__ import annotations

import io
import logging
from collections.abc import Sequence
from typing import Any

from aiboard_app.recognition.ocr_provider_base import OcrProvider, RecognitionResult

LOGGER = logging.getLogger(__name__)


class LocalOcrProvider(OcrProvider):
    """Offline handwriting OCR using Microsoft's TrOCR handwritten model.

    Heavy ML imports and model loading are deferred until the first recognition
    request, keeping normal application startup responsive.
    """

    def __init__(self, model_id: str = "microsoft/trocr-base-handwritten") -> None:
        self._model_id = model_id
        self._processor: Any = None
        self._model: Any = None
        self._torch: Any = None

    def recognize(self, image_bytes: bytes) -> RecognitionResult:
        if not image_bytes:
            raise ValueError("The whiteboard image is empty.")

        line_images = self._extract_handwritten_lines(image_bytes)
        if not line_images:
            return RecognitionResult(text="", confidence=None, provider="local-trocr")

        self._load_model()
        recognized_lines: list[str] = []
        confidence_values: list[float] = []

        for line_image in line_images:
            pixel_values = self._processor(images=line_image, return_tensors="pt").pixel_values
            with self._torch.inference_mode():
                generated = self._model.generate(
                    pixel_values,
                    return_dict_in_generate=True,
                    output_scores=True,
                    max_new_tokens=128,
                )
            text = self._processor.batch_decode(generated.sequences, skip_special_tokens=True)[0].strip()
            if text:
                recognized_lines.append(text)
            confidence = self._sequence_confidence(generated.scores)
            if confidence is not None:
                confidence_values.append(confidence)

        average_confidence = (
            sum(confidence_values) / len(confidence_values) if confidence_values else None
        )
        return RecognitionResult(
            text="\n".join(recognized_lines),
            confidence=average_confidence,
            provider="local-trocr",
        )

    def _load_model(self) -> None:
        if self._processor is not None and self._model is not None:
            return
        try:
            import torch
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        except ImportError as exc:
            raise RuntimeError(
                "Local handwriting OCR dependencies are missing. "
                "Run: pip install -r requirements.txt"
            ) from exc

        LOGGER.info("Loading handwriting model %s", self._model_id)
        try:
            self._processor = TrOCRProcessor.from_pretrained(self._model_id, use_fast=False)
            self._model = VisionEncoderDecoderModel.from_pretrained(self._model_id)
        except Exception as exc:
            raise RuntimeError(
                f"Could not load handwriting model {self._model_id!r}. "
                "The first use requires internet access to download the model."
            ) from exc
        self._model.eval()
        self._torch = torch

    @staticmethod
    def _extract_handwritten_lines(image_bytes: bytes) -> list[Any]:
        """Convert the blackboard PNG into cropped black-on-white line images."""
        try:
            import cv2
            import numpy as np
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError(
                "Image preprocessing dependencies are missing. "
                "Run: pip install -r requirements.txt"
            ) from exc

        encoded = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError("The whiteboard image could not be decoded.")

        # Board strokes are light on black. Threshold them, then use a small
        # horizontal closing operation so letters on the same line group well.
        _, ink = cv2.threshold(image, 35, 255, cv2.THRESH_BINARY)
        if cv2.countNonZero(ink) < 20:
            return []

        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
        grouped = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, horizontal_kernel)
        active_rows = cv2.reduce(grouped, 1, cv2.REDUCE_MAX).reshape(-1) > 0
        row_ranges = LocalOcrProvider._contiguous_ranges(active_rows.tolist(), minimum_size=4)

        lines: list[Any] = []
        height, width = ink.shape
        for top, bottom in row_ranges:
            top = max(0, top - 12)
            bottom = min(height, bottom + 12)
            band = ink[top:bottom, :]
            active_columns = cv2.reduce(band, 0, cv2.REDUCE_MAX).reshape(-1) > 0
            column_ranges = LocalOcrProvider._contiguous_ranges(active_columns.tolist(), minimum_size=2)
            if not column_ranges:
                continue
            left = max(0, column_ranges[0][0] - 12)
            right = min(width, column_ranges[-1][1] + 12)
            crop = ink[top:bottom, left:right]

            # TrOCR expects dark handwriting on a light page.
            paper = cv2.bitwise_not(crop)
            rgb = cv2.cvtColor(paper, cv2.COLOR_GRAY2RGB)
            lines.append(Image.open(io.BytesIO(LocalOcrProvider._encode_png(rgb))).convert("RGB"))
        return lines

    @staticmethod
    def _encode_png(image: Any) -> bytes:
        import cv2

        ok, encoded = cv2.imencode(".png", image)
        if not ok:
            raise ValueError("Could not prepare handwriting for recognition.")
        return encoded.tobytes()

    @staticmethod
    def _contiguous_ranges(flags: Sequence[bool], minimum_size: int) -> list[tuple[int, int]]:
        ranges: list[tuple[int, int]] = []
        start: int | None = None
        for index, active in enumerate([*flags, False]):
            if active and start is None:
                start = index
            elif not active and start is not None:
                if index - start >= minimum_size:
                    ranges.append((start, index))
                start = None
        return ranges

    def _sequence_confidence(self, scores: Sequence[Any]) -> float | None:
        if not scores:
            return None
        token_confidences = [
            float(self._torch.softmax(score, dim=-1).max(dim=-1).values.mean().item())
            for score in scores
        ]
        return sum(token_confidences) / len(token_confidences)
