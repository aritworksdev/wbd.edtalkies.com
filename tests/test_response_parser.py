from __future__ import annotations

from aiboard_app.ai.response_parser import ResponseParser


def test_parse_text_and_documents() -> None:
    parsed = ResponseParser().parse(
        {
            "title": "Answer",
            "answer": "E = mc^2",
            "documents": [{"fileName": "lesson.pdf", "fileType": "PDF", "url": "https://example.test/lesson.pdf"}],
        }
    )

    assert parsed.title == "Answer"
    assert "E = mc^2" in parsed.html
    assert parsed.documents[0].file_name == "lesson.pdf"


def test_parse_nested_data_response() -> None:
    parsed = ResponseParser().parse({"data": {"answer": "Nested answer"}})
    assert parsed.text == "Nested answer"


def test_parse_quickask_teacher_response() -> None:
    parsed = ResponseParser().parse(
        {
            "Intent": {
                "Message": "Explaining Einstein's equation clearly",
            },
            "Title": "Einstein's Theory of Relativity in Physics",
            "Response": "",
            "Message": "",
            "IsDownloadable": "false",
            "IsApiCallSuccess": "true",
            "IsSuccess": True,
            "ErrorMessages": [],
        }
    )

    assert parsed.title == "Einstein's Theory of Relativity in Physics"
    assert parsed.text == "Explaining Einstein's equation clearly"
    assert parsed.documents == []


def test_parse_quickask_downloadable_response() -> None:
    parsed = ResponseParser().parse(
        {
            "Title": "Worksheet",
            "Response": "Your worksheet is ready.",
            "IsDownloadable": "true",
            "DownloadableLink": "https://example.test/files/relativity.pdf",
        }
    )

    assert parsed.text == "Your worksheet is ready."
    assert parsed.documents[0].file_name == "relativity.pdf"
    assert parsed.documents[0].file_type == "PDF"


def test_parse_quickask_limit_response() -> None:
    parsed = ResponseParser().parse(
        {
            "Title": "Daily limit reached",
            "IsLimitReached": "true",
            "UpsellMessage": "Please upgrade your EdTalkies plan.",
            "IsSuccess": True,
        }
    )

    assert parsed.text == "Please upgrade your EdTalkies plan."
