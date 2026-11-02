"""Ctrl+K command palette — fuzzy-filter across pages, tools and saved vault
commands, then run the selected action."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QLineEdit, QListWidget, QListWidgetItem,
                               QVBoxLayout)


@dataclass
class PaletteEntry:
    label: str
    hint: str
    action: Callable[[], None]
    keywords: str = ""


def _score(query: str, text: str) -> int:
    """Simple subsequence fuzzy score; -1 = no match, lower = better."""
    text = text.lower()
    query = query.lower()
    if not query:
        return 0
    if query in text:
        return text.index(query)
    pos = 0
    gaps = 0
    last = -1
    for ch in query:
        idx = text.find(ch, pos)
        if idx < 0:
            return -1
        if last >= 0:
            gaps += idx - last - 1
        last = idx
        pos = idx + 1
    return 1000 + gaps


class CommandPalette(QDialog):
    def __init__(self, entries: list[PaletteEntry], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.setModal(True)
        self.setMinimumWidth(560)
        self._entries = entries
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Jump to a page, tool or saved command…")
        self.search.textChanged.connect(self._filter)
        self.search.returnPressed.connect(self._run_current)
        layout.addWidget(self.search)
        self.list = QListWidget()
        self.list.itemActivated.connect(lambda _it: self._run_current())
        layout.addWidget(self.list)
        self.search.installEventFilter(self)
        self._filter("")

    def eventFilter(self, obj, event):  # noqa: N802
        from PySide6.QtCore import QEvent
        if obj is self.search and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Down, Qt.Key_Up):
                row = self.list.currentRow()
                row += 1 if event.key() == Qt.Key_Down else -1
                row = max(0, min(self.list.count() - 1, row))
                self.list.setCurrentRow(row)
                return True
        return super().eventFilter(obj, event)

    def _filter(self, query: str) -> None:
        scored = []
        for entry in self._entries:
            hay = f"{entry.label} {entry.keywords} {entry.hint}"
            s = _score(query, hay)
            if s >= 0:
                scored.append((s, entry))
        scored.sort(key=lambda t: (t[0], t[1].label.lower()))
        self.list.clear()
        for _s, entry in scored[:60]:
            item = QListWidgetItem(f"{entry.label}    —    {entry.hint}")
            item.setData(Qt.UserRole, entry)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _run_current(self) -> None:
        item = self.list.currentItem()
        if not item:
            return
        entry: PaletteEntry = item.data(Qt.UserRole)
        self.accept()
        try:
            entry.action()
        except Exception:  # noqa: BLE001
            pass
