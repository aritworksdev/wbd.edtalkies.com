from __future__ import annotations

from aiboard_app.app.config import load_settings


def test_load_settings_from_environment(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("AIBOARD_FULLSCREEN", "true")
    monkeypatch.setenv("EDTALKIES_API_BASE_URL", "https://example.test")
    monkeypatch.setenv("EDTALKIES_AI_QUERY_PATH", "/m18/query")
    monkeypatch.setenv("EDTALKIES_TIMEOUT_SECONDS", "12")

    settings = load_settings()

    assert settings.fullscreen is True
    assert settings.edtalkies.timeout_seconds == 12
    assert settings.edtalkies.build_url(settings.edtalkies.ai_query_path) == "https://example.test/m18/query"


def test_legacy_mock_provider_migrates_to_real_local_ocr(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("AIBOARD_HANDWRITING_PROVIDER", "mock")
    monkeypatch.delenv("AIBOARD_ALLOW_MOCK_RECOGNIZER", raising=False)

    settings = load_settings()

    assert settings.handwriting_provider == "local"


def test_ocr_and_google_settings(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    credentials = tmp_path / "google.json"
    monkeypatch.setenv("OCR_CONFIDENCE_HIGH", "0.9")
    monkeypatch.setenv("OCR_CONFIDENCE_MEDIUM", "0.7")
    monkeypatch.setenv("GOOGLE_VISION_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(credentials))

    settings = load_settings()

    assert settings.ocr_confidence_high == 0.9
    assert settings.ocr_confidence_medium == 0.7
    assert settings.google_vision_enabled is True
    assert settings.google_application_credentials == credentials
