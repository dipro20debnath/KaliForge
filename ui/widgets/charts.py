"""Lightweight charts drawn with QPainter — no external plotting libraries.
A donut chart and a horizontal bar chart, themed via passed-in colours."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class DonutChart(QWidget):
    """Segments = list of (label, value, color_hex)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._segments: list[tuple[str, float, str]] = []
        self._center_label = ""
        self._hole = "#111a1d"
        self._text = "#d6e4e6"
        self._ring_gap = "#0a0e10"
        self.setMinimumHeight(180)

    def set_theme(self, hole: str, text: str, ring_gap: str) -> None:
        self._hole, self._text, self._ring_gap = hole, text, ring_gap
        self.update()

    def set_data(self, segments, center_label: str = "") -> None:
        self._segments = [(l, float(v), c) for l, v, c in segments]
        self._center_label = center_label
        self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        total = sum(v for _, v, _ in self._segments)
        side = min(self.width(), self.height()) - 16
        side = max(60, side)
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        if total <= 0:
            painter.setPen(QColor("#56696d"))
            painter.drawText(self.rect(), Qt.AlignCenter, "no data")
            painter.end()
            return
        start = 90 * 16
        for _label, value, color in self._segments:
            span = -int(360 * 16 * value / total)
            painter.setPen(QPen(QColor(self._ring_gap), 2))
            painter.setBrush(QColor(color))
            painter.drawPie(rect, start, span)
            start += span
        # punch the hole
        hole = side * 0.56
        hrect = QRectF((self.width() - hole) / 2, (self.height() - hole) / 2, hole, hole)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self._hole))
        painter.drawEllipse(hrect)
        painter.setPen(QColor(self._text))
        f = QFont("Inter", 13)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(hrect, Qt.AlignCenter, self._center_label or str(int(total)))
        painter.end()


class BarChart(QWidget):
    """Horizontal bars = list of (label, value, color_hex)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bars: list[tuple[str, float, str]] = []
        self._track = "#162226"
        self._text = "#d6e4e6"
        self._label = "#9fb0b3"
        self.setMinimumHeight(140)

    def set_theme(self, track: str, text: str, label: str) -> None:
        self._track, self._text, self._label = track, text, label
        self.update()

    def set_data(self, bars) -> None:
        self._bars = [(l, float(v), c) for l, v, c in bars]
        self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self._bars:
            painter.setPen(QColor("#56696d"))
            painter.drawText(self.rect(), Qt.AlignCenter, "no data")
            painter.end()
            return
        maxv = max((v for _, v, _ in self._bars), default=1) or 1
        pad = 8
        label_w = 92
        bar_h = 18
        gap = (self.height() - 2 * pad) / len(self._bars)
        painter.setFont(QFont("Inter", 9))
        for i, (label, value, color) in enumerate(self._bars):
            y = pad + i * gap + (gap - bar_h) / 2
            painter.setPen(QColor(self._label))
            painter.drawText(QRectF(0, y - 2, label_w - 6, bar_h + 4),
                             Qt.AlignVCenter | Qt.AlignRight, label)
            track = QRectF(label_w, y, self.width() - label_w - 40 - pad, bar_h)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(self._track))
            painter.drawRoundedRect(track, 4, 4)
            w = track.width() * (value / maxv)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(track.x(), y, max(2.0, w), bar_h), 4, 4)
            painter.setPen(QColor(self._text))
            painter.drawText(QRectF(track.right() + 6, y - 2, 40, bar_h + 4),
                             Qt.AlignVCenter | Qt.AlignLeft, str(int(value)))
        painter.end()


class Legend(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[tuple[str, str]] = []
        self.setMinimumHeight(24)

    def set_items(self, items) -> None:
        self._items = list(items)
        self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(QFont("Inter", 9))
        x = 2
        for label, color in self._items:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawEllipse(QRectF(x, self.height() / 2 - 5, 10, 10))
            x += 16
            painter.setPen(QColor("#9fb0b3"))
            w = painter.fontMetrics().horizontalAdvance(label)
            painter.drawText(QRectF(x, 0, w + 6, self.height()), Qt.AlignVCenter, label)
            x += w + 18
        painter.end()
