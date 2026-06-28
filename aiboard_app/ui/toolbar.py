from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSlider,
)


class WhiteboardToolbar(QFrame):
    color_changed = Signal(QColor)
    width_changed = Signal(int)
    eraser_toggled = Signal(bool)
    clear_requested = Signal()
    undo_requested = Signal()
    redo_requested = Signal()
    ask_requested = Signal()
    keyboard_requested = Signal()
    document_requested = Signal()
    console_requested = Signal()
    save_requested = Signal()
    exit_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("WhiteboardToolbar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)

        pen_button = self._button("✎ Pen")
        pen_button.setCheckable(True)
        pen_button.setChecked(True)
        pen_button.clicked.connect(lambda: self.eraser_toggled.emit(False))

        eraser_button = self._button("⌫ Eraser")
        eraser_button.setCheckable(True)
        eraser_button.clicked.connect(lambda: self.eraser_toggled.emit(True))

        self._tool_group.addButton(pen_button)
        self._tool_group.addButton(eraser_button)

        color_button = self._button("◉ Color")
        color_button.clicked.connect(self._choose_color)

        width_slider = QSlider(Qt.Orientation.Horizontal)
        width_slider.setMinimum(2)
        width_slider.setMaximum(24)
        width_slider.setValue(6)
        width_slider.setFixedWidth(150)
        width_slider.valueChanged.connect(self.width_changed.emit)

        actions = [
            pen_button,
            eraser_button,
            color_button,
            self._button("↶ Undo", self.undo_requested.emit),
            self._button("↷ Redo", self.redo_requested.emit),
            self._button("⟲ Clear", self.clear_requested.emit),
            self._button("✨ Ask AI", self.ask_requested.emit, "AskAiButton"),
            self._button("⌨ Keyboard", self.keyboard_requested.emit),
            self._button("⇪ Upload", self.document_requested.emit),
            self._button("▤ Console", self.console_requested.emit),
            self._button("💾 Save", self.save_requested.emit),
            self._button("⏻ Exit", self.exit_requested.emit, "ExitButton"),
        ]
        for widget in actions[:3]:
            layout.addWidget(widget)
        layout.addWidget(width_slider)
        for widget in actions[3:]:
            layout.addWidget(widget)

    def _button(self, label: str, callback=None, object_name: str = "") -> QPushButton:  # type: ignore[no-untyped-def]
        button = QPushButton(label)
        button.setMinimumHeight(44)
        button.setMinimumWidth(84)
        if object_name:
            button.setObjectName(object_name)
        if callback:
            button.clicked.connect(callback)
        return button

    def set_busy(self, busy: bool) -> None:
        for button in self.findChildren(QPushButton):
            button.setEnabled("Console" in button.text() or not busy)

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(QColor("#ffffff"), self, "Choose pen color")
        if color.isValid():
            self.color_changed.emit(color)
