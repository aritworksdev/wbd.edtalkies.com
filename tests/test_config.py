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
    assert settings.auto_recognize is True
