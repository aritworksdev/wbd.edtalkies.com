from __future__ import annotations

from aiboard_app.recognition.paddle_ocr_provider import PaddleOcrProvider


def test_parse_paddle_v3_result() -> None:
    class Result:
        json = {
            "res": {
                "rec_texts": ["What is", "gravity?"],
                "rec_scores": [0.91, 0.72],
            }
        }

    words = PaddleOcrProvider._parse_v3([Result()])

    assert [word.text for word in words] == ["What", "is", "gravity?"]
    assert words[-1].confidence == 0.72
