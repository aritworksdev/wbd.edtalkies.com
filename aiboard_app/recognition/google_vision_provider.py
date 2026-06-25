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
        return self.availability_reason == ""

    @property
    def availability_reason(self) -> str:
        if not self._credentials_path.is_file():
            return f"credential file not found: {self._credentials_path}"
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
        }
        try:
            payload = json.loads(self._credentials_path.read_text(encoding="utf-8"))
        except OSError as exc:
            return f"credential file cannot be read: {exc}"
        except ValueError:
            return "credential file is not valid JSON"
        if not isinstance(payload, dict) or not required.issubset(payload):
            missing = sorted(required.difference(payload if isinstance(payload, dict) else {}))
            return f"credential JSON is missing fields: {', '.join(missing)}"
        if payload.get("type") != "service_account":
            return "credential JSON type must be service_account"
        if any("REPLACE_" in str(payload.get(key, "")) for key in required):
            return "credential JSON still contains template placeholders"
        return ""

    def recognize(self, image_bytes: bytes) -> OcrResult:
        if not self.available:
            raise RuntimeError(f"Google Vision unavailable: {self.availability_reason}")
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
        return OcrResult(
            text,
            confidence,
            "google-vision",
            tuple(words),
            model_name=self.model_name,
        )
    @property
    def model_name(self) -> str:
        return "Google Cloud Vision document_text_detection"
