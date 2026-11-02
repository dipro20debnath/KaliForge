"""Reusable presentational widgets shared across pages."""
from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLayout, QProgressBar,
                               QPushButton, QSizePolicy, QVBoxLayout, QWidget)


class Card(QFrame):
    """A rounded panel container with an object name for QSS styling."""

    def __init__(self, parent=None, object_name="Card"):
        super().__init__(parent)
        self.setObjectName(object_name)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(10)

    def layout(self) -> QVBoxLayout:  # type: ignore[override]
        return self._layout


class StatCard(Card):
    """Big-number dashboard tile (value + label + optional caption)."""

    clicked = Signal()

    def __init__(self, value: str, label: str, caption: str = "", parent=None):
        super().__init__(parent)
        self.value_lbl = QLabel(str(value))
        self.value_lbl.setObjectName("StatValue")
        self.label_lbl = QLabel(label.upper())
        self.label_lbl.setObjectName("StatLabel")
        self._layout.addWidget(self.value_lbl)
        self._layout.addWidget(self.label_lbl)
        if caption:
            cap = QLabel(caption)
            cap.setObjectName("Hint")
            self._layout.addWidget(cap)
        self._layout.addStretch(1)
        self.setMinimumHeight(118)

    def set_value(self, value) -> None:
        self.value_lbl.setText(str(value))

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class Meter(QWidget):
    """Labelled horizontal progress meter (CPU/RAM/Disk)."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        row = QHBoxLayout()
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("Hint")
        self.value_lbl = QLabel("0%")
        self.value_lbl.setAlignment(Qt.AlignRight)
        row.addWidget(self.title_lbl)
        row.addWidget(self.value_lbl)
        layout.addLayout(row)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        layout.addWidget(self.bar)

    def set_value(self, percent: float, caption: str | None = None) -> None:
        percent = max(0, min(100, int(round(percent))))
        self.bar.setValue(percent)
        self.value_lbl.setText(caption if caption is not None else f"{percent}%")


class Badge(QLabel):
    def __init__(self, text: str, object_name: str = "BadgeInstalled", parent=None):
        super().__init__(text, parent)
        self.setObjectName(object_name)


class Chip(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("Chip")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)


def section_title(text: str, sub: str = "") -> QWidget:
    wrap = QWidget()
    layout = QVBoxLayout(wrap)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    title = QLabel(text)
    title.setObjectName("PageTitle")
    layout.addWidget(title)
    if sub:
        sub_lbl = QLabel(sub)
        sub_lbl.setObjectName("PageSub")
        layout.addWidget(sub_lbl)
    return wrap


class FlowLayout(QLayout):
    """A wrapping flow layout (cards reflow to the available width)."""

    def __init__(self, parent=None, margin=0, spacing=12):
        super().__init__(parent)
        self._items: list = []
        self._spacing = spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):  # noqa: N802
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):  # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):  # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):  # noqa: N802
        return True

    def heightForWidth(self, width):  # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):  # noqa: N802
        return self.minimumSize()

    def minimumSize(self):  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        left, top, right, bottom = self.getContentsMargins()
        effective = rect.adjusted(left, top, -right, -bottom)
        x, y, line_height = effective.x(), effective.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + self._spacing
            if next_x - self._spacing > effective.right() and line_height > 0:
                x = effective.x()
                y = y + line_height + self._spacing
                next_x = x + hint.width() + self._spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(x, y, hint.width(), hint.height()))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + bottom
