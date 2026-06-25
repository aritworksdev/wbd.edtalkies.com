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
