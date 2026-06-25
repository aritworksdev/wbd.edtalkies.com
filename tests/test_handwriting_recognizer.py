from __future__ import annotations

from aiboard_app.recognition.edtalkies_ocr_provider import EdTalkiesOcrProvider


class FakeEdTalkiesClient:
    def recognize_handwriting(self, image_bytes: bytes) -> dict:
        assert image_bytes
        return {"data": {"recognizedText": "What is photosynthesis?", "confidence": 0.94}}


def test_edtalkies_ocr_provider_parses_nested_recognition_result() -> None:
    result = EdTalkiesOcrProvider(FakeEdTalkiesClient()).recognize(b"png")

    assert result.text == "What is photosynthesis?"
    assert result.confidence == 0.94
    assert result.provider == "edtalkies"
