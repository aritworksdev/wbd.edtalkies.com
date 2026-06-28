from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from aiboard_app.ui.whiteboard_canvas import WhiteboardCanvas


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_canvas_backing_image_does_not_shrink_on_resize() -> None:
    _app()
    canvas = WhiteboardCanvas()
    original_width = canvas._image.width()
    original_height = canvas._image.height()

    canvas.resize(original_width // 2, original_height // 2)

    assert canvas._image.width() == original_width
    assert canvas._image.height() == original_height
