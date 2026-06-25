from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from aiboard_app.ai.edtalkies_client import EdTalkiesClient
from aiboard_app.ai.prompt_builder import PromptBuilder
from aiboard_app.ai.response_parser import ResponseParser
from aiboard_app.app.config import load_settings
from aiboard_app.app.logger import configure_logging
from aiboard_app.documents.document_manager import DocumentManager
from aiboard_app.recognition.handwriting_recognizer import build_handwriting_recognizer
from aiboard_app.system.shutdown_manager import ShutdownManager
from aiboard_app.ui.main_window import MainWindow


def main() -> int:
    settings = load_settings()
    log_level = getattr(logging, settings.log_level, logging.INFO)
    configure_logging(log_level, settings.export_dir / "logs")

    app = QApplication(sys.argv)
    app.setApplicationName("AiBoard App")
    app.setOrganizationName("EdTalkies")
    app.setStyle("Fusion")
    client = EdTalkiesClient(settings.edtalkies)
    recognizer = build_handwriting_recognizer(settings, client)
    logging.getLogger(__name__).info(
        "Google Vision enabled=%s available=%s credentials=%s reason=%s",
        settings.google_vision_enabled,
        recognizer.google_available,
        settings.google_application_credentials,
        recognizer.google_availability_reason or "ready",
    )
    window = MainWindow(
        settings=settings,
        client=client,
        recognizer=recognizer,
        response_parser=ResponseParser(),
        prompt_builder=PromptBuilder(),
        document_manager=DocumentManager(
            settings.export_dir,
            settings.edtalkies.timeout_seconds,
            recognizer,
        ),
        shutdown_manager=ShutdownManager(settings),
    )
    window.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
