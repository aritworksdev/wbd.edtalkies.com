from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSlider,
)

from aiboard_app.ui.icon_assets import IconName, load_icon


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
    chats_requested = Signal()
    save_requested = Signal()
    exit_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("WhiteboardToolbar")
        self._icon_buttons: list[QPushButton] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)

        pen_button = self._button(IconName.EDIT, "Drawing mode")
        pen_button.setCheckable(True)
        pen_button.setChecked(True)
        pen_button.clicked.connect(lambda: self.eraser_toggled.emit(False))

        eraser_button = self._button(IconName.ERASE, "Erase mode")
        eraser_button.setCheckable(True)
        eraser_button.clicked.connect(lambda: self.eraser_toggled.emit(True))

        self._tool_group.addButton(pen_button)
        self._tool_group.addButton(eraser_button)

        color_button = self._button(IconName.COLOR_WHEEL, "Choose pen color")
        color_button.clicked.connect(self._choose_color)

        width_slider = QSlider(Qt.Orientation.Horizontal)
        width_slider.setMinimum(2)
        width_slider.setMaximum(24)
        width_slider.setValue(6)
        width_slider.setFixedWidth(120)
        width_slider.valueChanged.connect(self.width_changed.emit)

        actions = [
            pen_button,
            eraser_button,
            color_button,
            self._button(IconName.UNDO, "Undo", self.undo_requested.emit),
            self._button(IconName.REDO, "Redo", self.redo_requested.emit),
            self._button(IconName.PLUS_OUTLINE, "Clear board", self.clear_requested.emit),
            self._button(IconName.ASK_AI, "Ask AI", self.ask_requested.emit, "AskAiButton"),
            self._button(IconName.KEYBOARD, "Keyboard mode", self.keyboard_requested.emit),
            self._button(IconName.UPLOAD, "Upload document", self.document_requested.emit),
            self._button(
                IconName.CHATS,
                "Chats",
                self.chats_requested.emit,
                accessible_name="Open previous chats",
            ),
            self._button(IconName.CONSOLE, "Console Log", self.console_requested.emit),
            self._button(IconName.UPDATE, "Save board image", self.save_requested.emit),
            self._button(IconName.CLOSE, "Exit", self.exit_requested.emit, "ExitButton"),
        ]
        for widget in actions[:3]:
            layout.addWidget(widget)
        layout.addWidget(width_slider)
        for widget in actions[3:]:
            layout.addWidget(widget)
        self._apply_responsive_icon_size()

    def _button(
        self,
        icon_name: str,
        tooltip: str,
        callback=None,  # type: ignore[no-untyped-def]
        object_name: str = "",
        accessible_name: str = "",
    ) -> QPushButton:
        button = QPushButton()
        button.setText("")
        button.setIcon(load_icon(icon_name))
        button.setToolTip(tooltip)
        button.setAccessibleName(accessible_name or tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        button.setProperty("iconOnly", True)
        if object_name:
            button.setObjectName(object_name)
        if callback:
            button.clicked.connect(callback)
        self._icon_buttons.append(button)
        return button

    def set_busy(self, busy: bool) -> None:
        for button in self._icon_buttons:
            button.setEnabled(button.toolTip() in {"Console Log", "Chats"} or not busy)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._apply_responsive_icon_size()
        super().resizeEvent(event)

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(QColor("#ffffff"), self, "Choose pen color")
        if color.isValid():
            self.color_changed.emit(color)

    def _apply_responsive_icon_size(self) -> None:
        width = self.window().width() if self.window() else self.width()
        if width >= 1800:
            icon_size, touch_size = 44, 56
        elif width >= 1200:
            icon_size, touch_size = 34, 46
        else:
            icon_size, touch_size = 26, 38
        size = QSize(icon_size, icon_size)
        for button in self._icon_buttons:
            button.setIconSize(size)
            button.setMinimumSize(touch_size, touch_size)
            button.setMaximumSize(touch_size, touch_size)
