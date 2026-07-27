"""Frameless translucent overlay for selecting a screen region."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import QWidget

HANDLE = 8
MIN_SIZE = 80


class OverlayWindow(QWidget):
    region_changed = Signal(QRect)

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setGeometry(120, 120, 640, 360)
        self._drag_mode: str | None = None
        self._drag_origin = QPoint()
        self._geom_origin = QRect()
        self._chrome_visible = True

    def geometry_rect(self) -> QRect:
        return self.geometry()

    def set_chrome_visible(self, visible: bool) -> None:
        self._chrome_visible = visible
        self.update()

    def chrome_visible(self) -> bool:
        return self._chrome_visible

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Keep the interior fully transparent; only a border (and move handle) is drawn.
        if self._chrome_visible:
            border = QPen(QColor(30, 144, 255, 230), 2)
            painter.setPen(border)
            painter.drawRect(1, 1, self.width() - 2, self.height() - 2)
            painter.fillRect(0, 0, 28, 28, QColor(30, 144, 255, 200))
            painter.setPen(QPen(QColor(255, 255, 255, 230), 1))
            painter.drawText(4, 18, "⠿")
        else:
            border = QPen(QColor(30, 144, 255, 40), 1)
            painter.setPen(border)
            painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

    def _hit_zone(self, pos: QPoint) -> str | None:
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        if self._chrome_visible and x <= 28 and y <= 28:
            return "move"
        near_left = x <= HANDLE
        near_right = x >= w - HANDLE
        near_top = y <= HANDLE
        near_bottom = y >= h - HANDLE
        if near_left and near_top:
            return "tl"
        if near_right and near_top:
            return "tr"
        if near_left and near_bottom:
            return "bl"
        if near_right and near_bottom:
            return "br"
        if near_left:
            return "l"
        if near_right:
            return "r"
        if near_top:
            return "t"
        if near_bottom:
            return "b"
        return None

    def mousePressEvent(self, event) -> None:  # noqa: ANN001, N802
        if event.button() != Qt.LeftButton:
            return
        self._drag_mode = self._hit_zone(event.position().toPoint())
        self._drag_origin = event.globalPosition().toPoint()
        self._geom_origin = self.geometry()

    def mouseMoveEvent(self, event) -> None:  # noqa: ANN001, N802
        if self._drag_mode is None:
            zone = self._hit_zone(event.position().toPoint())
            self._set_cursor(zone)
            return
        delta = event.globalPosition().toPoint() - self._drag_origin
        g = QRect(self._geom_origin)
        mode = self._drag_mode
        if mode == "move":
            g.translate(delta)
        else:
            if "l" in mode:
                g.setLeft(g.left() + delta.x())
            if "r" in mode:
                g.setRight(g.right() + delta.x())
            if "t" in mode:
                g.setTop(g.top() + delta.y())
            if "b" in mode:
                g.setBottom(g.bottom() + delta.y())
        if g.width() >= MIN_SIZE and g.height() >= MIN_SIZE:
            self.setGeometry(g)
            self.region_changed.emit(self.geometry())

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001, N802
        self._drag_mode = None
        self.region_changed.emit(self.geometry())

    def _set_cursor(self, zone: str | None) -> None:
        mapping = {
            "move": Qt.SizeAllCursor,
            "l": Qt.SizeHorCursor,
            "r": Qt.SizeHorCursor,
            "t": Qt.SizeVerCursor,
            "b": Qt.SizeVerCursor,
            "tl": Qt.SizeFDiagCursor,
            "br": Qt.SizeFDiagCursor,
            "tr": Qt.SizeBDiagCursor,
            "bl": Qt.SizeBDiagCursor,
        }
        self.setCursor(mapping.get(zone, Qt.ArrowCursor))
