from __future__ import annotations

import os
import json
from pathlib import Path

from aiboard_app.recognition.ocr_provider_base import OcrProvider
from aiboard_app.recognition.ocr_result import OcrResult, OcrWord


class GoogleVisionProvider(OcrProvider):
    """Optional explicit cloud fallback. It is never called automatically."""

    def __init__(self, credentials_path: Path, project_id: str = "") -> None:
        self._credentials_path = credentials_path
        self._project_id = project_id

    @property
    def available(self) -> bool:
        if not self._credentials_path.is_file():
            return False
        required = {
            "type",
            "project_id",
            "private_key_id",
            "private_key",
            "client_email",
            "client_id",
            "auth_uri",
            "token_uri",
            "auth_provider_x509_cert_url",
            "client_x509_cert_url",
            "universe_domain",
        }
        try:
            payload = json.loads(self._credentials_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        if not isinstance(payload, dict) or not required.issubset(payload):
            return False
        if payload.get("type") != "service_account":
            return False
        return not any("REPLACE_" in str(payload.get(key, "")) for key in required)

    def recognize(self, image_bytes: bytes) -> OcrResult:
        if not self.available:
            raise RuntimeError("Google Vision credentials are missing.")
        try:
            from google.cloud import vision
        except ImportError as exc:
            raise RuntimeError(
                "Google Vision support is not installed. Run: "
                "pip install google-cloud-vision"
            ) from exc

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(self._credentials_path.resolve())
        client = vision.ImageAnnotatorClient()
        response = client.document_text_detection(image=vision.Image(content=image_bytes))
        if response.error.message:
            raise RuntimeError(f"Google Vision OCR failed: {response.error.message}")

        annotation = response.full_text_annotation
        words: list[OcrWord] = []
        for page in annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        text = "".join(symbol.text for symbol in word.symbols)
                        confidence = float(getattr(word, "confidence", 0.0) or 0.0)
                        if text:
                            words.append(OcrWord(text, confidence))
        text = annotation.text.strip()
        confidence = sum(word.confidence for word in words) / len(words) if words else 0.0
        return OcrResult(text, confidence, "google-vision", tuple(words))
