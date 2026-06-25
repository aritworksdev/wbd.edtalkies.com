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
