from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from aiboard_app.app.config import AppSettings, EdTalkiesSettings
from aiboard_app.system.shutdown_manager import ShutdownManager


def _settings(action: str, confirm_exit: bool) -> AppSettings:
    return AppSettings(
        app_env="test",
        fullscreen=False,
        export_dir=Path("."),
        handwriting_provider="mock",
        exit_action=action,
        confirm_exit=confirm_exit,
        log_level="INFO",
        edtalkies=EdTalkiesSettings("", "", "/query", "/ocr", 1, 0, "default", "teacher", "", "", ""),
    )


def test_shutdown_still_prompts_when_quit_confirmation_is_disabled(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    prompted = False

    def fake_question(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal prompted
        prompted = True
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", fake_question)

    ShutdownManager(_settings("shutdown", False)).perform_exit(None)  # type: ignore[arg-type]

    assert prompted is True
