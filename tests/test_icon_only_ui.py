from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from aiboard_app.ui.response_panel import ResponsePanel
from aiboard_app.ui.toolbar import WhiteboardToolbar


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_toolbar_buttons_are_icon_only_with_accessible_names() -> None:
    _app()
    toolbar = WhiteboardToolbar()

    buttons = toolbar.findChildren(QPushButton)

    assert buttons
    assert all(button.text() == "" for button in buttons)
    assert all(button.toolTip() for button in buttons)
    assert all(button.accessibleName() for button in buttons)


def test_response_panel_export_controls_are_icon_only() -> None:
    _app()
    panel = ResponsePanel()

    icon_buttons = [
        button
        for button in panel.findChildren(QPushButton)
        if button.property("iconOnly")
    ]

    assert icon_buttons
    assert all(button.text() == "" for button in icon_buttons)
    assert all(button.toolTip() for button in icon_buttons)
    assert all(button.accessibleName() for button in icon_buttons)
