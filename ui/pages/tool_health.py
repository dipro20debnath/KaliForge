"""Tool Health Monitor page — version + dependency health of installed tools."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ui.async_task import run_async
from ui.widgets.common import StatCard

_STATUS_STYLE = {"ok": "SevLow", "degraded": "SevMed", "missing": "SevHigh", "builtin": "SevInfo"}


class ToolHealthPage(QWidget):
    status_message = Signal(str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._build()
        self.refresh(probe=False)

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        head = QHBoxLayout()
        title = QLabel("Tool Health Monitor")
        title.setObjectName("PageTitle")
        head.addWidget(title)
        head.addStretch(1)
        self.check_btn = QPushButton("Probe versions & dependencies")
        self.check_btn.setObjectName("Primary")
        self.check_btn.clicked.connect(lambda: self.refresh(probe=True))
        head.addWidget(self.check_btn)
        layout.addLayout(head)

        cards = QHBoxLayout()
        self.cards = {}
        for key, label in [("ok", "Healthy"), ("degraded", "Degraded"),
                           ("builtin", "Built-in"), ("missing", "Missing")]:
            card = StatCard("0", label)
            self.cards[key] = card
            cards.addWidget(card)
        layout.addLayout(cards)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Tool", "Status", "Version", "Notes"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

    def showEvent(self, event):  # noqa: N802
        self.app.tools.detect_all()   # reflect newly installed tools
        self.refresh(probe=False)
        super().showEvent(event)

    def refresh(self, probe: bool = False) -> None:
        if probe:
            self.check_btn.setEnabled(False)
            self.status_message.emit("Probing tool versions and dependencies…")
            run_async(self.app.health.check_installed, self._show,
                      lambda e: self._show([]), self.app.catalog, True)
        else:
            self._show(self.app.health.check_installed(self.app.catalog, probe_version=False))

    def _show(self, reports) -> None:
        self.check_btn.setEnabled(True)
        # include missing count from installer
        summary = self.app.health.summary(reports)
        summary["missing"] = len(self.app.installer.missing())
        for key, card in self.cards.items():
            card.set_value(summary.get(key, 0))
        self.table.setRowCount(len(reports))
        for i, r in enumerate(reports):
            self.table.setItem(i, 0, QTableWidgetItem(r.name))
            status_item = QTableWidgetItem(r.status.upper())
            self.table.setItem(i, 1, status_item)
            self.table.setItem(i, 2, QTableWidgetItem(r.version or "—"))
            self.table.setItem(i, 3, QTableWidgetItem(r.notes))
        if reports:
            self.status_message.emit("Tool health updated.")
