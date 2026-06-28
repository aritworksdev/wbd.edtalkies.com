from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from aiboard_app.ai.prompt_builder import PromptBuilder
from aiboard_app.ai.response_parser import ResponseParser
from aiboard_app.app.config import AppSettings, EdTalkiesSettings
from aiboard_app.documents.document_manager import DocumentManager
from aiboard_app.system.shutdown_manager import ShutdownManager
from aiboard_app.ui.icon_assets import IconName, icon_path
from aiboard_app.ui.main_window import MainWindow
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


def test_required_toolbar_icons_exist_locally() -> None:
    for icon_name in (
        IconName.CONSOLE,
        IconName.KEYBOARD,
        IconName.REDO,
        IconName.UNDO,
        IconName.PLUS_OUTLINE,
    ):
        assert icon_path(icon_name).exists()


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


class FakeClient:
    pass


class FakeRecognizer:
    google_available = False


def _settings(export_dir: Path) -> AppSettings:
    return AppSettings(
        app_env="test",
        fullscreen=False,
        export_dir=export_dir,
        handwriting_provider="mock",
        exit_action="quit",
        confirm_exit=False,
        log_level="INFO",
        edtalkies=EdTalkiesSettings("", "", "/query", "/ocr", 1, 0, "default", "teacher", "", "", ""),
    )


def test_toolbar_is_embedded_in_header(tmp_path) -> None:
    _app()
    settings = _settings(tmp_path)
    window = MainWindow(
        settings=settings,
        client=FakeClient(),
        recognizer=FakeRecognizer(),
        response_parser=ResponseParser(),
        prompt_builder=PromptBuilder(),
        document_manager=DocumentManager(tmp_path),
        shutdown_manager=ShutdownManager(settings),
    )

    assert window._toolbar.parentWidget() is window._header
