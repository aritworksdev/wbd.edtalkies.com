from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from aiboard_app.ui.icon_assets import IconName, load_icon


class FloatingPanelHost(QFrame):
    """Reusable shell for panels that can be docked, floated, pinned, or hidden."""

    pin_requested = Signal()
    float_requested = Signal()
    close_requested = Signal()

    def __init__(self, title: str, content: QWidget, allow_close: bool = True) -> None:
        super().__init__()
        self.setObjectName("FloatingPanelHost")
        self._title_text = title
        self._content = content
        self._floating = False
        self._icon_buttons: list[QPushButton] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("FloatingPanelHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 8, 8)
        header_layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("FloatingPanelTitle")
        header_layout.addWidget(title_label, 1)

        self._pin_button = self._icon_button(IconName.UPDATE, "Pin panel")
        self._float_button = self._icon_button(IconName.UPLOAD, "Float panel")
        self._close_button = self._icon_button(IconName.CLOSE, "Close panel")
        self._pin_button.clicked.connect(self.pin_requested.emit)
        self._float_button.clicked.connect(self.float_requested.emit)
        self._close_button.clicked.connect(self.close_requested.emit)
        header_layout.addWidget(self._pin_button)
        header_layout.addWidget(self._float_button)
        if allow_close:
            header_layout.addWidget(self._close_button)

        layout.addWidget(header)
        layout.addWidget(content, 1)

    @property
    def title(self) -> str:
        return self._title_text

    def set_floating(self, floating: bool) -> None:
        self._floating = floating
        pin_tip = "Dock and pin panel" if floating else "Keep panel pinned"
        float_tip = "Panel is floating" if floating else "Float panel"
        self._pin_button.setToolTip(pin_tip)
        self._pin_button.setAccessibleName(pin_tip)
        self._float_button.setToolTip(float_tip)
        self._float_button.setAccessibleName(float_tip)
        self._float_button.setEnabled(not floating)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._apply_icon_sizes()
        super().resizeEvent(event)

    def _icon_button(self, icon_name: str, tooltip: str) -> QPushButton:
        button = QPushButton()
        button.setText("")
        button.setIcon(load_icon(icon_name))
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        button.setProperty("iconOnly", True)
        button.setProperty("smallIcon", True)
        self._icon_buttons.append(button)
        self._apply_icon_size(button)
        return button

    def _apply_icon_sizes(self) -> None:
        for button in self._icon_buttons:
            self._apply_icon_size(button)

    def _apply_icon_size(self, button: QPushButton) -> None:
        width = self.window().width() if self.window() else self.width()
        if width >= 1800:
            icon_size, touch_size = 28, 40
        elif width >= 1200:
            icon_size, touch_size = 24, 36
        else:
            icon_size, touch_size = 22, 34
        button.setIconSize(QSize(icon_size, icon_size))
        button.setMinimumSize(touch_size, touch_size)
        button.setMaximumSize(touch_size, touch_size)


class FloatingPanelDialog(QDialog):
    panel_closed = Signal(FloatingPanelHost)

    def __init__(self, host: FloatingPanelHost, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._host = host
        self._detached = False
        self.setWindowTitle(host.title)
        self.setObjectName("FloatingPanelDialog")
        self.setWindowFlag(Qt.WindowType.Tool, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(host)
        self.resize(430, 620)

    def detach_host(self) -> FloatingPanelHost:
        if not self._detached:
            self.layout().removeWidget(self._host)
            self._host.setParent(None)
            self._detached = True
        return self._host

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if not self._detached:
            host = self.detach_host()
            self.panel_closed.emit(host)
        super().closeEvent(event)
