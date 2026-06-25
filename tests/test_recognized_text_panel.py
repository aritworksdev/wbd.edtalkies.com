from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from aiboard_app.recognition.ocr_result import OcrResult, OcrWord
from aiboard_app.ui.recognized_text_panel import RecognizedTextPanel


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_low_confidence_requires_edit_and_hides_google_when_unavailable() -> None:
    _app()
    panel = RecognizedTextPanel()
    result = OcrResult(
        "uncertain text",
        0.42,
        "trocr",
        (OcrWord("uncertain", 0.3), OcrWord("text", 0.54)),
    )

    panel.set_recognition_result(result, 0.85, 0.65, google_available=False)

    assert panel.confidence_band == "low"
    assert panel.can_submit is False
    assert panel._google_button.isHidden()

    panel._editor.insertPlainText(" corrected")
    assert panel.can_submit is True


def test_high_confidence_enables_ask_edtalkies() -> None:
    _app()
    panel = RecognizedTextPanel()
    panel.set_recognition_result(
        OcrResult("clear text", 0.93, "paddleocr"),
        0.85,
        0.65,
        google_available=False,
    )

    assert panel.confidence_band == "high"
    assert panel.can_submit is True
    assert panel._ask_button.isEnabled()


def test_low_confidence_shows_google_only_when_available() -> None:
    _app()
    panel = RecognizedTextPanel()
    panel.set_recognition_result(
        OcrResult("uncertain", 0.4, "tesseract", (OcrWord("uncertain", 0.4),)),
        0.85,
        0.65,
        google_available=True,
    )

    assert panel._google_button.isHidden() is False
    assert panel._rewrite_button.isHidden() is False


def test_status_shows_selected_model_confidence_and_fallback_chain() -> None:
    _app()
    panel = RecognizedTextPanel()
    panel.set_recognition_result(
        OcrResult(
            "document text",
            0.72,
            "tesseract",
            model_name="Tesseract 5 (eng)",
            attempts=("PaddleOCR PP-OCRv5 (en)", "Tesseract 5 (eng)"),
        ),
        0.85,
        0.65,
        google_available=False,
    )

    status = panel._status.text()
    assert "Tesseract 5 (eng)" in status
    assert "72%" in status
    assert "PaddleOCR PP-OCRv5 (en) -> Tesseract 5 (eng)" in status
