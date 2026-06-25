from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout

from aiboard_app.recognition.ocr_result import OcrResult


class RecognizedTextPanel(QFrame):
    """Editable confidence-aware staging area before EdTalkies submission."""

    ask_requested = Signal()
    rewrite_requested = Signal()
    google_vision_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("RecognizedTextPanel")
        self._band = "none"
        self._programmatic_change = False
        self._low_confidence_edited = False

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
        self._rewrite_button = QPushButton("Rewrite")
        self._rewrite_button.clicked.connect(self.rewrite_requested.emit)
        self._google_button = QPushButton("Use Google Vision OCR")
        self._google_button.clicked.connect(self.google_vision_requested.emit)
        self._ask_button = QPushButton("Ask EdTalkies")
        self._ask_button.setObjectName("RecognizedTextAskButton")
        self._ask_button.clicked.connect(self.ask_requested.emit)

        header.addWidget(title)
        header.addWidget(self._status, 1)
        header.addWidget(clear_button)
        header.addWidget(self._rewrite_button)
        header.addWidget(self._google_button)
        header.addWidget(self._ask_button)
        layout.addLayout(header)

        self._editor = QTextEdit()
        self._editor.setObjectName("RecognizedTextEditor")
        self._editor.setPlaceholderText("Recognized handwriting or a typed question will appear here.")
        self._editor.setMaximumHeight(100)
        self._editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._editor)
        self.clear()

    @property
    def confidence_band(self) -> str:
        return self._band

    @property
    def can_submit(self) -> bool:
        if not self.text():
            return False
        return self._band in {"high", "medium", "manual"} or self._low_confidence_edited

    def text(self) -> str:
        return self._editor.toPlainText().strip()

    def set_text(self, text: str, source: str = "input") -> None:
        self._set_plain_text(text)
        self._band = "manual"
        self._low_confidence_edited = True
        self._status.setText(f"Ready to review and send ({source}).")
        self._rewrite_button.hide()
        self._google_button.hide()
        self._ask_button.setEnabled(bool(text.strip()))
        self._editor.setFocus()

    def set_recognition_result(
        self,
        result: OcrResult,
        high_threshold: float,
        medium_threshold: float,
        google_available: bool,
    ) -> None:
        self._set_plain_text(result.text)
        confidence = result.confidence or 0.0
        self._low_confidence_edited = False

        if confidence >= high_threshold:
            self._band = "high"
            self._status.setText(
                f"Recognized by {result.provider} ({confidence:.0%}). Ready to send."
            )
            self._rewrite_button.hide()
            self._google_button.hide()
            self._ask_button.setEnabled(True)
            self._ask_button.setText("Ask EdTalkies")
        elif confidence >= medium_threshold:
            self._band = "medium"
            self._status.setText(
                f"Recognition confidence is {confidence:.0%}. Review highlighted words."
            )
            self._highlight_uncertain_words(result, high_threshold)
            self._rewrite_button.show()
            self._google_button.setVisible(google_available)
            self._ask_button.setEnabled(True)
            self._ask_button.setText("Confirm & Ask EdTalkies")
        else:
            self._band = "low"
            action = "Rewrite or use Google Vision OCR." if google_available else "Rewrite or edit the text."
            self._status.setText(f"Low OCR confidence ({confidence:.0%}). {action}")
            self._highlight_uncertain_words(result, medium_threshold)
            self._rewrite_button.show()
            self._google_button.setVisible(google_available)
            self._ask_button.setEnabled(False)
            self._ask_button.setText("Edit Text to Continue")

        self._editor.setFocus()

    def clear(self) -> None:
        self._set_plain_text("")
        self._band = "none"
        self._low_confidence_edited = False
        self._status.setText("Write on the board, then click Ask AI to convert it to text.")
        self._rewrite_button.hide()
        self._google_button.hide()
        self._ask_button.setEnabled(False)
        self._ask_button.setText("Ask EdTalkies")

    def set_status(self, message: str) -> None:
        self._status.setText(message)

    def _set_plain_text(self, text: str) -> None:
        self._programmatic_change = True
        self._editor.setPlainText(text)
        self._editor.setExtraSelections([])
        self._programmatic_change = False

    def _on_text_changed(self) -> None:
        if self._programmatic_change:
            return
        if self._band == "low" and self.text():
            self._low_confidence_edited = True
            self._status.setText("Low-confidence text was edited. Review carefully before sending.")
            self._ask_button.setText("Use Edited Text")
        self._ask_button.setEnabled(self.can_submit)

    def _highlight_uncertain_words(self, result: OcrResult, threshold: float) -> None:
        selections: list[QTextEdit.ExtraSelection] = []
        cursor = self._editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        warning_format = QTextCharFormat()
        warning_format.setBackground(QColor("#fde68a"))
        warning_format.setForeground(QColor("#7c2d12"))

        for word in result.words:
            found = self._editor.document().find(word.text, cursor)
            if found.isNull():
                continue
            cursor = found
            if word.confidence < threshold:
                selection = QTextEdit.ExtraSelection()
                selection.cursor = found
                selection.format = warning_format
                selections.append(selection)
        self._editor.setExtraSelections(selections)
