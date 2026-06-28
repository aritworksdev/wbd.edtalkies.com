from __future__ import annotations

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QConicalGradient,
    QImage,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QTabletEvent,
)
from PySide6.QtWidgets import QWidget


class WhiteboardCanvas(QWidget):
    content_changed = Signal(int)
    BOARD_COLOR = QColor("#000000")
    BORDER_WIDTH = 5
    BORDER_RADIUS = 24

    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StaticContents)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        self.setAutoFillBackground(True)
        self._pen_color = QColor("#ffffff")
        self._pen_width = 6
        self._eraser = False
        self._drawing = False
        self._last_point = QPoint()
        self._image = QImage(1280, 720, QImage.Format.Format_RGB32)
        self._image.fill(self.BOARD_COLOR)
        self._undo_stack: list[QImage] = []
        self._redo_stack: list[QImage] = []
        self._revision = 0
        self._animated_border = False
        self._border_hue = 0
        self._border_timer = QTimer(self)
        self._border_timer.setInterval(70)
        self._border_timer.timeout.connect(self._advance_border_animation)

    @property
    def revision(self) -> int:
        return self._revision

    def set_pen_color(self, color: QColor) -> None:
        self._pen_color = color
        self._eraser = False

    def set_pen_width(self, width: int) -> None:
        self._pen_width = max(1, width)

    def set_eraser(self, enabled: bool) -> None:
        self._eraser = enabled

    def set_processing_animation(self, enabled: bool) -> None:
        if self._animated_border == enabled:
            return
        self._animated_border = enabled
        if enabled:
            self._border_timer.start()
        else:
            self._border_timer.stop()
            self._border_hue = 0
        self.update()

    def clear(self) -> None:
        self._save_undo_state()
        self._image.fill(self.BOARD_COLOR)
        self.update()
        self._notify_content_changed()

    def undo(self) -> None:
        if not self._undo_stack:
            return
        self._redo_stack.append(self._image.copy())
        self._image = self._undo_stack.pop()
        self.update()
        self._notify_content_changed()

    def redo(self) -> None:
        if not self._redo_stack:
            return
        self._undo_stack.append(self._image.copy())
        self._image = self._redo_stack.pop()
        self.update()
        self._notify_content_changed()

    def save_image(self, path: str) -> bool:
        return self._image.save(path)

    def to_png_bytes(self) -> bytes:
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        self._image.save(buffer, "PNG")
        return bytes(byte_array)

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        if not self._animated_border:
            painter.drawImage(QPoint(0, 0), self._image)
            return
        board_path = QPainterPath()
        board_path.addRoundedRect(
            QRectF(self.rect()).adjusted(
                self.BORDER_WIDTH / 2,
                self.BORDER_WIDTH / 2,
                -self.BORDER_WIDTH / 2,
                -self.BORDER_WIDTH / 2,
            ),
            self.BORDER_RADIUS,
            self.BORDER_RADIUS,
        )
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.save()
        painter.setClipPath(board_path)
        painter.drawImage(QPoint(0, 0), self._image)
        painter.restore()
        self._draw_border(painter)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self.width() <= 0 or self.height() <= 0:
            return
        if self.width() == self._image.width() and self.height() == self._image.height():
            return
        new_image = QImage(self.width(), self.height(), QImage.Format.Format_RGB32)
        new_image.fill(self.BOARD_COLOR)
        painter = QPainter(new_image)
        painter.drawImage(QPoint(0, 0), self._image)
        painter.end()
        self._image = new_image
        super().resizeEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._save_undo_state()
            self._drawing = True
            self._last_point = event.position().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drawing and event.buttons() & Qt.MouseButton.LeftButton:
            self._draw_line_to(event.position().toPoint())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drawing:
            self._draw_line_to(event.position().toPoint())
            self._drawing = False
            self._notify_content_changed()

    def tabletEvent(self, event: QTabletEvent) -> None:
        point = event.position().toPoint()
        if event.type() == event.Type.TabletPress:
            self._save_undo_state()
            self._drawing = True
            self._last_point = point
            event.accept()
        elif event.type() == event.Type.TabletMove and self._drawing:
            self._draw_line_to(point)
            event.accept()
        elif event.type() == event.Type.TabletRelease and self._drawing:
            self._draw_line_to(point)
            self._drawing = False
            self._notify_content_changed()
            event.accept()
        else:
            super().tabletEvent(event)

    def _draw_line_to(self, end_point: QPoint) -> None:
        painter = QPainter(self._image)
        color = self.BOARD_COLOR if self._eraser else self._pen_color
        painter.setPen(
            QPen(
                color,
                self._pen_width * (3 if self._eraser else 1),
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.drawLine(self._last_point, end_point)
        painter.end()

        dirty_radius = self._pen_width * 4
        self.update(
            min(self._last_point.x(), end_point.x()) - dirty_radius,
            min(self._last_point.y(), end_point.y()) - dirty_radius,
            abs(self._last_point.x() - end_point.x()) + dirty_radius * 2,
            abs(self._last_point.y() - end_point.y()) + dirty_radius * 2,
        )
        self._last_point = end_point

    def _save_undo_state(self) -> None:
        self._undo_stack.append(self._image.copy())
        self._redo_stack.clear()
        if len(self._undo_stack) > 20:
            self._undo_stack.pop(0)

    def _notify_content_changed(self) -> None:
        self._revision += 1
        self.content_changed.emit(self._revision)

    def _advance_border_animation(self) -> None:
        self._border_hue = (self._border_hue + 6) % 360
        self.update()

    def _draw_border(self, painter: QPainter) -> None:
        if not self._animated_border:
            return
        border_rect = QRectF(self.rect()).adjusted(
            self.BORDER_WIDTH / 2,
            self.BORDER_WIDTH / 2,
            -self.BORDER_WIDTH / 2,
            -self.BORDER_WIDTH / 2,
        )
        gradient = QConicalGradient(border_rect.center(), self._border_hue)
        gradient.setColorAt(0.00, QColor("#ff0000"))
        gradient.setColorAt(0.14, QColor("#ffa500"))
        gradient.setColorAt(0.28, QColor("#ffff00"))
        gradient.setColorAt(0.42, QColor("#00ff00"))
        gradient.setColorAt(0.56, QColor("#00ffff"))
        gradient.setColorAt(0.70, QColor("#0000ff"))
        gradient.setColorAt(0.84, QColor("#8f00ff"))
        gradient.setColorAt(1.00, QColor("#ff0000"))
        pen = QPen(gradient, self.BORDER_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(border_rect, self.BORDER_RADIUS, self.BORDER_RADIUS)
