from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from aiboard_app.ai.prompt_builder import PromptBuilder
from aiboard_app.ai.response_parser import ParsedResponse
from aiboard_app.ai.response_parser import ResponseParser
from aiboard_app.app.config import AppSettings, EdTalkiesSettings
from aiboard_app.chat.chat_record import ChatRecord
from aiboard_app.documents.document_manager import DocumentManager
from aiboard_app.system.shutdown_manager import ShutdownManager
from aiboard_app.ui.chat_history_panel import ChatHistoryPanel
from aiboard_app.ui.icon_assets import IconName, icon_path
from aiboard_app.ui.icon_assets import logo_path
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
        IconName.CHATS,
        IconName.COPY,
        IconName.KEYBOARD,
        IconName.REDO,
        IconName.UNDO,
        IconName.PLUS_OUTLINE,
    ):
        assert icon_path(icon_name).exists()
    assert logo_path("edtalkies_header_logo.png").exists()


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


def test_response_request_panel_has_no_old_labels() -> None:
    html = ResponsePanel._wrap_html(
        "AI response",
        ChatRecord(
            id="chat-1",
            request_text="What is photosynthesis?",
            response=ParsedResponse("Title", "AI response", ""),
            created_at=__import__("datetime").datetime(2026, 6, 29, 10, 30),
        ),
    )

    assert "Recognized Text" not in html
    assert "Request</h3>" not in html
    assert "class=\"request-text\"" in html
    assert "class=\"created-at\"" in html


def test_chat_history_uses_short_request_preview() -> None:
    record = ChatRecord(
        id="chat-1",
        request_text="Explain photosynthesis in simple terms for class six",
        response=ParsedResponse("Title", "Long response", ""),
        created_at=__import__("datetime").datetime(2026, 6, 29, 10, 30),
    )

    assert ChatHistoryPanel._item_text(record).splitlines()[0] == "Explain photosynthesis in simple..."


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


def test_console_and_chat_panels_can_float_and_dock(tmp_path) -> None:
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

    window._float_panel(window._console_panel)
    assert window._console_panel in window._floating_dialogs
    window._dock_panel(window._console_panel, visible=True)
    assert window._console_panel not in window._floating_dialogs
    assert window._body_layout.indexOf(window._console_panel) >= 0

    window._float_panel(window._chat_history_host)
    assert window._chat_history_host in window._floating_dialogs
    window._hide_panel(window._chat_history_host)
    assert window._chat_history_host not in window._floating_dialogs
    assert window._body_layout.indexOf(window._chat_history_host) >= 0


def test_ask_ai_empty_blackboard_does_not_start_ocr(tmp_path, monkeypatch) -> None:
    _app()
    settings = _settings(tmp_path)

    class RecognizerThatFailsIfCalled:
        google_available = False

        def recognize(self, _image_bytes):  # type: ignore[no-untyped-def]
            raise AssertionError("OCR should not run for an empty blackboard")

    window = MainWindow(
        settings=settings,
        client=FakeClient(),
        recognizer=RecognizerThatFailsIfCalled(),
        response_parser=ResponseParser(),
        prompt_builder=PromptBuilder(),
        document_manager=DocumentManager(tmp_path),
        shutdown_manager=ShutdownManager(settings),
    )
    monkeypatch.setattr("aiboard_app.ui.main_window.QMessageBox.information", lambda *args: None)

    window._ask_ai()

    assert not window._recognition_in_progress
    assert window._busy_count == 0
