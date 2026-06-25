from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout

from aiboard_app.recognition.ocr_provider_base import RecognitionResult


class RecognizedTextPanel(QFrame):
    """Visible, editable staging area between recognition and AI submission."""

    ask_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("RecognizedTextPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("Recognized Text")
        title.setObjectName("RecognizedTextTitle")
        self._status = QLabel("Write on the board, then click Ask AI to convert it to text.")
        self._status.setObjectName("RecognizedTextStatus")
        clear_button = QPushButton("Clear Text")
        clear_button.clicked.connect(self.clear)
        ask_button = QPushButton("Ask AI")
        ask_button.setObjectName("RecognizedTextAskButton")
        ask_button.clicked.connect(self.ask_requested.emit)

        header.addWidget(title)
        header.addWidget(self._status, 1)
        header.addWidget(clear_button)
        header.addWidget(ask_button)
        layout.addLayout(header)

        self._editor = QPlainTextEdit()
        self._editor.setObjectName("RecognizedTextEditor")
        self._editor.setPlaceholderText("Recognized handwriting or a typed question will appear here.")
        self._editor.setMaximumHeight(90)
        layout.addWidget(self._editor)

    def text(self) -> str:
        return self._editor.toPlainText().strip()

    def set_text(self, text: str, source: str = "input") -> None:
        self._editor.setPlainText(text)
        self._status.setText(f"Ready to review and send ({source}).")
        self._editor.setFocus()

    def set_recognition_result(self, result: RecognitionResult) -> None:
        self._editor.setPlainText(result.text)
        confidence = ""
        if result.confidence is not None:
            confidence = f", confidence {result.confidence:.0%}"
        self._status.setText(f"Recognized by {result.provider}{confidence}. Review before asking AI.")
        self._editor.setFocus()
        self._editor.selectAll()

    def clear(self) -> None:
        self._editor.clear()
        self._status.setText("Write on the board, then click Ask AI to convert it to text.")

    def set_status(self, message: str) -> None:
        self._status.setText(message)
