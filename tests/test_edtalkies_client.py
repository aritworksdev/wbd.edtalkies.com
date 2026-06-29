from __future__ import annotations

import requests

from aiboard_app.ai.edtalkies_client import AiQuery, EdTalkiesClient
from aiboard_app.app.config import EdTalkiesSettings


class FakeResponse:
    status_code = 200
    content = b'{"answer": "ok"}'
    text = '{"answer": "ok"}'

    def json(self) -> dict[str, str]:
        return {"answer": "ok"}


class FakeSession:
    def __init__(self) -> None:
        self.payload = None
        self.url = ""

    def post(self, url: str, **kwargs) -> FakeResponse:  # type: ignore[no-untyped-def]
        self.url = url
        self.payload = kwargs.get("json")
        return FakeResponse()


class TimeoutSession:
    def __init__(self) -> None:
        self.calls = 0

    def post(self, url: str, **kwargs) -> FakeResponse:  # type: ignore[no-untyped-def]
        self.calls += 1
        raise requests.ReadTimeout("read timed out")


def test_ask_posts_configured_payload() -> None:
    settings = EdTalkiesSettings(
        api_base_url="https://example.test",
        api_key="key",
        ai_query_path="/m18/query",
        ocr_path="/m18/ocr",
        timeout_seconds=3,
        retry_count=0,
        model="m18",
        assistant_mode="teacher_board",
        school_id="school",
        board_id="board",
        device_id="device",
    )
    client = EdTalkiesClient(settings)
    fake_session = FakeSession()
    client._session = fake_session  # type: ignore[attr-defined]

    result = client.ask(AiQuery(text="What is gravity?"))

    assert result == {"answer": "ok"}
    assert fake_session.url == "https://example.test/m18/query"
    assert fake_session.payload == {
        "Channel": "WEB",
        "Phone": "",
        "Message": "What is gravity?",
        "Language": "English",
        "Source": "SendPulse",
        "Season": "Any Level",
        "Genre": "Any Subject",
        "ContentSource": "Any Curriculum",
    }


def test_ask_allows_quickask_context_overrides() -> None:
    settings = EdTalkiesSettings(
        api_base_url="https://example.test",
        api_key="",
        ai_query_path="/quick-ask",
        ocr_path="/ocr",
        timeout_seconds=3,
        retry_count=0,
        model="default",
        assistant_mode="teacher_board",
        school_id="",
        board_id="",
        device_id="",
    )
    client = EdTalkiesClient(settings)
    fake_session = FakeSession()
    client._session = fake_session  # type: ignore[attr-defined]

    client.ask(
        AiQuery(
            text="Explain photosynthesis",
            context={
                "Language": "Hindi",
                "Season": "Grade 6",
                "Genre": "Biology",
                "ContentSource": "CBSE",
            },
        )
    )

    assert fake_session.payload["Language"] == "Hindi"
    assert fake_session.payload["Season"] == "Grade 6"
    assert fake_session.payload["Genre"] == "Biology"
    assert fake_session.payload["ContentSource"] == "CBSE"


def test_ask_does_not_retry_non_idempotent_quickask_timeout() -> None:
    settings = EdTalkiesSettings(
        api_base_url="https://example.test",
        api_key="",
        ai_query_path="/quick-ask",
        ocr_path="/ocr",
        timeout_seconds=3,
        retry_count=2,
        model="default",
        assistant_mode="teacher_board",
        school_id="",
        board_id="",
        device_id="",
    )
    client = EdTalkiesClient(settings)
    fake_session = TimeoutSession()
    client._session = fake_session  # type: ignore[attr-defined]

    try:
        client.ask(AiQuery(text="Create a presentation about matrices"))
    except Exception as exc:
        assert "read timed out" in str(exc)
    else:
        raise AssertionError("Expected timeout error")

    assert fake_session.calls == 1


def test_ask_uses_mock_when_base_url_is_blank() -> None:
    settings = EdTalkiesSettings(
        api_base_url="",
        api_key="",
        ai_query_path="/query",
        ocr_path="/ocr",
        timeout_seconds=3,
        retry_count=0,
        model="default",
        assistant_mode="teacher_board",
        school_id="",
        board_id="",
        device_id="",
    )

    result = EdTalkiesClient(settings).ask(AiQuery(text="Explain gravity"))

    assert result["mock"] is True
    assert "Explain gravity" in result["text"]
