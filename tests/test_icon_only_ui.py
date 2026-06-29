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
        IconName.CALENDAR,
        IconName.EDIT_DB,
        IconName.KEYBOARD,
        IconName.PDF,
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


def test_response_panel_renders_image_and_markdown_content() -> None:
    image = ParsedResponse(
        "Poster",
        "https://example.test/poster.png",
        "",
        message_type="poster",
    )
    markdown = ParsedResponse(
        "Lesson",
        "# Heading\n\n- Item\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n$E=mc^2$",
        "",
    )

    image_html = ResponsePanel._render_content_html(image)
    markdown_html = ResponsePanel._render_content_html(markdown)

    assert "<img" in image_html
    assert "https://example.test/poster.png" in image_html
    assert "<h1>Heading</h1>" in markdown_html
    assert "<li>Item</li>" in markdown_html
    assert "<table>" in markdown_html
    assert "$E=mc^2$" in markdown_html


def test_response_panel_download_actions_follow_content_type() -> None:
    assert ResponsePanel._download_actions("Text") == [
        (IconName.PDF, "Download PDF", "pdf"),
        (IconName.DOCX, "Download Word", "docx"),
    ]
    assert ResponsePanel._download_actions("Slides") == [
        (IconName.PPTX, "Download PowerPoint", "pptx")
    ]
    assert ResponsePanel._download_actions("Sheet") == [
        (IconName.EXCEL, "Download Excel", "xlsx")
    ]
    assert ResponsePanel._download_actions("Schedule") == [
        (IconName.CALENDAR, "Download Calendar", "ics")
    ]
    assert ResponsePanel._download_actions("AiContentType.Slides") == [
        (IconName.PPTX, "Download PowerPoint", "pptx")
    ]


def test_generated_document_response_hides_raw_text() -> None:
    response = ParsedResponse(
        "Slides",
        "Create a presentation slide show on matrices.",
        "",
        unique_id="deck-1",
        is_downloadable=False,
        intent_content_type="AiContentType.Slides",
    )

    html = ResponsePanel._render_content_html(response)

    assert "Slides is ready" in html
    assert "Create a presentation slide show on matrices." not in html


def test_generated_document_response_open_does_not_require_downloadable_flag() -> None:
    _app()
    panel = ResponsePanel()
    response = ParsedResponse(
        "Sheet",
        "Generated spreadsheet content should not render as text.",
        "",
        unique_id="sheet-1",
        is_downloadable=False,
        intent_content_type="Sheet",
    )

    panel.show_response(response)
    tooltips = {button.toolTip() for button in panel.findChildren(QPushButton)}

    assert "Open document" in tooltips
    assert "Download Excel" not in tooltips


def test_generated_document_response_shows_open_and_download_actions() -> None:
    _app()
    panel = ResponsePanel()
    response = ParsedResponse(
        "Slides",
        "Slides are ready.",
        "",
        unique_id="deck-1",
        is_downloadable=True,
        intent_content_type="Slides",
    )

    panel.show_response(response)
    tooltips = {button.toolTip() for button in panel.findChildren(QPushButton)}

    assert "Open document" in tooltips
    assert "Download PowerPoint" in tooltips


def test_chat_history_uses_short_request_preview() -> None:
    record = ChatRecord(
        id="chat-1",
        request_text="Explain photosynthesis in simple terms for class six",
        response=ParsedResponse("Title", "Long response", ""),
        created_at=__import__("datetime").datetime(2026, 6, 29, 10, 30),
    )

    assert ChatHistoryPanel._item_text(record).splitlines()[0] == "Explain photosynthesis in simple..."


class FakeClient:
    def generated_download_url(self, unique_id: str, file_format: str) -> str:
        return f"https://example.test/download?uniqueId={unique_id}&format={file_format}"


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


def test_generated_download_prefers_unique_id_format_url(tmp_path, monkeypatch) -> None:
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
    captured: dict[str, str] = {}

    def fake_run_background(message, task, on_success, error_title, show_progress=True, on_complete=None):  # type: ignore[no-untyped-def]
        captured["message"] = message
        result = task()
        on_success(result)

    monkeypatch.setattr(window, "_run_background", fake_run_background)
    monkeypatch.setattr(window, "_download_generated_complete", lambda path, fmt, open_doc: None)
    monkeypatch.setattr(
        window._document_manager,
        "download",
        lambda url, file_name: captured.update({"url": url, "file_name": file_name}) or tmp_path / file_name,
    )

    window._download_generated_response("deck-1", "pptx", "https://example.test/wrong-format")

    assert captured["url"] == "https://example.test/download?uniqueId=deck-1&format=pptx"
    assert captured["file_name"] == "EdTalkies_deck-1.pptx"
