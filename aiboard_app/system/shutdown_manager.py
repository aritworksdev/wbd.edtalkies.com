from __future__ import annotations

import subprocess
import sys

from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from aiboard_app.app.config import AppSettings


class ShutdownManager:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    def perform_exit(self, parent: QWidget) -> None:
        action = self._settings.exit_action
        if action not in {"quit", "shutdown", "reboot"}:
            action = "quit"

        # Power operations always require explicit confirmation. The setting
        # only controls whether the harmless "quit app" action also prompts.
        if self._settings.confirm_exit or action in {"shutdown", "reboot"}:
            message = {
                "quit": "Quit AiBoard App?",
                "shutdown": "Quit AiBoard App and shut down this device?",
                "reboot": "Quit AiBoard App and reboot this device?",
            }[action]
            result = QMessageBox.question(
                parent,
                "Confirm exit",
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if result != QMessageBox.StandardButton.Yes:
                return

        if action == "shutdown":
            command = ["shutdown", "/s", "/t", "0"] if sys.platform == "win32" else ["systemctl", "poweroff"]
            subprocess.Popen(command)
        elif action == "reboot":
            command = ["shutdown", "/r", "/t", "0"] if sys.platform == "win32" else ["systemctl", "reboot"]
            subprocess.Popen(command)

        QApplication.quit()
