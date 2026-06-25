from __future__ import annotations

from pathlib import Path
import json

from aiboard_app.recognition.google_vision_provider import GoogleVisionProvider
from aiboard_app.recognition.ocr_result import OcrResult, OcrWord
from aiboard_app.recognition.ocr_service import OcrService


class FakeProvider:
    def __init__(self, result: OcrResult | None = None, error: Exception | None = None) -> None:
        self.result = result or OcrResult.empty("fake")
        self.error = error
        self.calls = 0

    def recognize(self, image_bytes: bytes) -> OcrResult:
        self.calls += 1
        if self.error:
            raise self.error
        return self.result

    def recognize_document(self, image_bytes: bytes) -> OcrResult:
        return self.recognize(image_bytes)


def _result(provider: str, confidence: float, text: str = "hello world") -> OcrResult:
    return OcrResult(
        text=text,
        confidence=confidence,
        provider=provider,
        words=(OcrWord("hello", confidence), OcrWord("world", confidence)),
    )


def test_high_confidence_paddle_stops_pipeline() -> None:
    paddle = FakeProvider(_result("paddleocr", 0.91))
    trocr = FakeProvider(_result("trocr", 0.99))
    tesseract = FakeProvider(_result("tesseract", 0.99))
    service = OcrService(paddle, trocr, tesseract, None, 0.85, 0.65)

    result = service.recognize(b"image")

    assert result.provider == "paddleocr"
    assert paddle.calls == 1
    assert trocr.calls == 0
    assert tesseract.calls == 0


def test_low_paddle_uses_handwriting_fallback() -> None:
    service = OcrService(
        FakeProvider(_result("paddleocr", 0.52)),
        FakeProvider(_result("trocr", 0.82)),
        FakeProvider(_result("tesseract", 0.55)),
        None,
        0.85,
        0.65,
    )

    result = service.recognize(b"image")

    assert result.provider == "trocr"
    assert "FakeProvider" in result.attempts


def test_google_runs_automatically_when_best_local_confidence_is_below_high() -> None:
    class FakeGoogle:
        available = True
        model_name = "Google Cloud Vision document_text_detection"

        def __init__(self) -> None:
            self.calls = 0

        def recognize(self, image_bytes: bytes) -> OcrResult:
            self.calls += 1
            return _result("google-vision", 0.96, "cloud result")

    google = FakeGoogle()
    service = OcrService(
        FakeProvider(_result("paddleocr", 0.52)),
        FakeProvider(_result("trocr", 0.46)),
        FakeProvider(_result("tesseract", 0.61)),
        google,  # type: ignore[arg-type]
        0.85,
        0.65,
    )

    result = service.recognize(b"image")

    assert google.calls == 1
    assert result.provider == "google-vision"
    assert result.text == "cloud result"
    assert result.attempts[-1] == "Google Cloud Vision document_text_detection"


def test_google_failure_preserves_best_local_result() -> None:
    class FailingGoogle:
        available = True
        model_name = "Google Cloud Vision document_text_detection"

        def recognize(self, image_bytes: bytes) -> OcrResult:
            raise RuntimeError("network unavailable")

    service = OcrService(
        FakeProvider(_result("paddleocr", 0.40)),
        FakeProvider(_result("trocr", 0.46)),
        FakeProvider(_result("tesseract", 0.62)),
        FailingGoogle(),  # type: ignore[arg-type]
        0.85,
        0.65,
    )

    result = service.recognize(b"image")

    assert result.provider == "tesseract"
    assert result.confidence == 0.62
    assert any("network unavailable" in error for error in result.errors)


def test_tesseract_runs_when_primary_local_providers_fail() -> None:
    service = OcrService(
        FakeProvider(error=RuntimeError("paddle unavailable")),
        FakeProvider(error=RuntimeError("trocr unavailable")),
        FakeProvider(_result("tesseract", 0.73)),
        None,
        0.85,
        0.65,
    )

    result = service.recognize(b"image")

    assert result.provider == "tesseract"
    assert len(result.errors) == 2


def test_document_pipeline_prefers_tesseract_before_trocr() -> None:
    paddle = FakeProvider(error=RuntimeError("paddle unavailable"))
    trocr = FakeProvider(_result("trocr", 0.84, "handwriting guess"))
    tesseract = FakeProvider(_result("tesseract", 0.92, "printed document"))
    service = OcrService(paddle, trocr, tesseract, None, 0.85, 0.65)

    result = service.recognize_document(b"image")

    assert result.provider == "tesseract"
    assert tesseract.calls == 1
    assert trocr.calls == 0


def test_google_is_unavailable_without_valid_credentials(tmp_path: Path) -> None:
    missing = GoogleVisionProvider(tmp_path / "missing.json", "edtalkies")
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{}", encoding="utf-8")
    invalid = GoogleVisionProvider(invalid_path, "edtalkies")

    assert missing.available is False
    assert invalid.available is False


def test_google_is_available_with_service_account_shape(tmp_path: Path) -> None:
    credentials = tmp_path / "google.json"
    credentials.write_text(
        json.dumps(
            {
                "type": "service_account",
                "project_id": "edtalkies",
                "private_key_id": "id",
                "private_key": "key",
                "client_email": "ocr@example.test",
                "client_id": "client",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": "https://example.test/cert",
                "universe_domain": "googleapis.com",
            }
        ),
        encoding="utf-8",
    )

    assert GoogleVisionProvider(credentials, "edtalkies").available is True


def test_multiple_google_pages_are_combined() -> None:
    class FakeGoogle:
        available = True

        def __init__(self) -> None:
            self.calls = 0

        def recognize(self, image_bytes: bytes) -> OcrResult:
            self.calls += 1
            return _result("google-vision", 0.9, image_bytes.decode())

    google = FakeGoogle()
    service = OcrService(
        FakeProvider(_result("paddleocr", 0.9)),
        FakeProvider(),
        FakeProvider(),
        google,  # type: ignore[arg-type]
        0.85,
        0.65,
    )

    result = service.recognize_many_with_google((b"page one", b"page two"))

    assert result.text == "page one\n\npage two"
    assert google.calls == 2


def test_empty_document_pipeline_returns_diagnostics_for_google_fallback() -> None:
    service = OcrService(
        FakeProvider(error=RuntimeError("paddle unavailable")),
        FakeProvider(OcrResult.empty("trocr")),
        FakeProvider(error=RuntimeError("tesseract unavailable")),
        None,
        0.85,
        0.65,
    )

    result = service.recognize_document(b"image")

    assert result.text == ""
    assert result.confidence == 0.0
    assert result.model_name == "No local OCR model returned text"
    assert len(result.attempts) == 3
