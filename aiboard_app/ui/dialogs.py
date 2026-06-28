from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QVBoxLayout

from aiboard_app.ui.theme import EdTalkiesTheme


class RecognitionConfirmDialog(QDialog):
    def __init__(
        self,
        recognized_text: str,
        parent=None,  # type: ignore[no-untyped-def]
        title: str = "Confirm question",
        instructions: str = "Review or edit the text before sending it to EdTalkies.",
        proceed_label: str = "OK",
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(EdTalkiesTheme.app_stylesheet())
        self.setWindowTitle(title)
        self.setMinimumSize(680, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(instructions))
        self._editor = QPlainTextEdit()
        self._editor.setPlainText(recognized_text)
        self._editor.setMinimumHeight(260)
        layout.addWidget(self._editor)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        proceed_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if proceed_button is not None:
            proceed_button.setText(proceed_label)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def text(self) -> str:
        return self._editor.toPlainText().strip()
