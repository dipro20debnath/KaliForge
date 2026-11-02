"""Tool Arsenal — searchable, category-filtered grid of tool cards. Also serves
category-specific pages by pre-selecting a filter."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from core.categories import CATEGORIES
from ui.widgets.common import Chip, FlowLayout
from ui.widgets.tool_card import ToolCard


class ArsenalPage(QWidget):
    open_tool = Signal(str)
    show_details = Signal(str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._category = "all"
        self._build()
        self.rebuild()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 10)
        layout.setSpacing(12)

        head = QHBoxLayout()
        title = QLabel("Tool Arsenal")
        title.setObjectName("PageTitle")
        head.addWidget(title)
        head.addStretch(1)
        self.count_lbl = QLabel("")
        self.count_lbl.setObjectName("Hint")
        head.addWidget(self.count_lbl)
        refresh = QPushButton("⟳ Re-detect")
        refresh.setObjectName("Ghost")
        refresh.setToolTip("Re-scan the system for newly installed tools")
        refresh.clicked.connect(self.redetect)
        head.addWidget(refresh)
        layout.addLayout(head)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search Nmap, Burp, Wireshark, hashcat, tags…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.rebuild)
        layout.addWidget(self.search)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)
        self._chip_group = QButtonGroup(self)
        self._chip_group.setExclusive(True)
        all_chip = Chip("All")
        all_chip.setChecked(True)
        all_chip.clicked.connect(lambda: self._set_category("all"))
        self._chip_group.addButton(all_chip)
        chips_row.addWidget(all_chip)
        self._chips = {"all": all_chip}
        for cat in CATEGORIES:
            chip = Chip(cat["label"])
            chip.clicked.connect(lambda _=False, cid=cat["id"]: self._set_category(cid))
            self._chip_group.addButton(chip)
            self._chips[cat["id"]] = chip
            chips_row.addWidget(chip)
        chips_row.addStretch(1)
        chips_wrap = QScrollArea()
        chips_wrap.setFixedHeight(48)
        chips_wrap.setWidgetResizable(True)
        chips_wrap.setFrameShape(QScrollArea.NoFrame)
        chips_wrap.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        chips_wrap.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setLayout(chips_row)
        chips_wrap.setWidget(inner)
        layout.addWidget(chips_wrap)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.grid_host = QWidget()
        self.flow = FlowLayout(self.grid_host, margin=2, spacing=12)
        self.scroll.setWidget(self.grid_host)
        layout.addWidget(self.scroll, 1)

    def showEvent(self, event):  # noqa: N802
        # re-scan every time the page is shown so newly installed tools appear
        self.app.tools.detect_all()
        self.rebuild()
        super().showEvent(event)

    def redetect(self) -> None:
        counts = self.app.tools.detect_all()
        self.rebuild()
        installed = sum(1 for s in self.app.tools._status.values()
                        if s.installed and not s.builtin)
        self.count_lbl.setText(f"re-scanned · {installed} installed")

    def set_category(self, category: str) -> None:
        """Called externally (sidebar / dashboard quick access)."""
        chip = self._chips.get(category)
        if chip:
            chip.setChecked(True)
        self._set_category(category)

    def _set_category(self, category: str) -> None:
        self._category = category
        self.rebuild()

    def rebuild(self) -> None:
        # clear
        while self.flow.count():
            item = self.flow.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        query = self.search.text().strip()
        tools = self.app.catalog.search(query) if query else self.app.catalog.all()
        if self._category != "all":
            tools = [t for t in tools if t["category"] == self._category]
        tools.sort(key=lambda t: (not self.app.tools.is_favorite(t["id"]), t["name"].lower()))
        for tool in tools:
            status = self.app.tools.status(tool["id"])
            card = ToolCard(tool, status)
            card.open_requested.connect(self.open_tool.emit)
            card.details_requested.connect(self.show_details.emit)
            card.favorite_toggled.connect(self._toggle_fav)
            self.flow.addWidget(card)
        self.count_lbl.setText(f"{len(tools)} tools")

    def _toggle_fav(self, tool_id: str) -> None:
        self.app.tools.toggle_favorite(tool_id)
        self.rebuild()
