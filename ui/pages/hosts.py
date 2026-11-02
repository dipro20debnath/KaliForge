"""Hosts page — host-centric view aggregating open ports/services and findings
per host in the active workspace."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QPushButton,
                               QSplitter, QTableWidget, QTableWidgetItem,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from core.hosts import host_overview
from ui.theme import severity_color
from ui.widgets.common import Card


class HostsPage(QWidget):
    add_to_scope = Signal(str)
    status_message = Signal(str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._views = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        head = QHBoxLayout()
        title = QLabel("Hosts")
        title.setObjectName("PageTitle")
        head.addWidget(title)
        head.addStretch(1)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        head.addWidget(refresh)
        layout.addLayout(head)

        splitter = QSplitter(Qt.Horizontal)
        self.host_tree = QTreeWidget()
        self.host_tree.setHeaderLabels(["Host", "Ports", "Risk"])
        self.host_tree.setColumnWidth(0, 180)
        self.host_tree.currentItemChanged.connect(self._select_host)
        splitter.addWidget(self.host_tree)

        self.detail = QWidget()
        self.detail_layout = QVBoxLayout(self.detail)
        self.detail_layout.addWidget(QLabel("Select a host to see details."))
        self.detail_layout.addStretch(1)
        splitter.addWidget(self.detail)
        splitter.setSizes([340, 640])
        layout.addWidget(splitter, 1)

    def refresh(self) -> None:
        self._views = host_overview(self.app.db, self.app.active_workspace_id())
        self.host_tree.clear()
        theme = self.app.settings.get("appearance.theme", "kali_neon")
        for view in self._views:
            item = QTreeWidgetItem([view.host, str(view.open_ports),
                                    view.top_severity.upper()])
            item.setForeground(2, Qt.GlobalColor.white)
            from PySide6.QtGui import QColor
            item.setForeground(2, QColor(severity_color(theme, view.top_severity)))
            item.setData(0, Qt.UserRole, view)
            self.host_tree.addTopLevelItem(item)
        if self._views:
            self.host_tree.setCurrentItem(self.host_tree.topLevelItem(0))
        else:
            self._show_empty()

    def showEvent(self, event):  # noqa: N802
        self.refresh()
        super().showEvent(event)

    def _show_empty(self) -> None:
        self._clear_detail()
        self.detail_layout.insertWidget(0, QLabel(
            "No hosts yet. Import a scan (Scan Import) or add findings/assets."))

    def _clear_detail(self) -> None:
        while self.detail_layout.count():
            item = self.detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _select_host(self, current, _prev) -> None:
        if current is None:
            return
        view = current.data(0, Qt.UserRole)
        if view is None:
            return
        self._clear_detail()

        header = QHBoxLayout()
        name = QLabel(view.host)
        name.setObjectName("PageTitle")
        header.addWidget(name)
        header.addStretch(1)
        scope_btn = QPushButton("→ Add to scope")
        scope_btn.clicked.connect(lambda: self.add_to_scope.emit(view.host))
        header.addWidget(scope_btn)
        wrap = QWidget()
        wrap.setLayout(header)
        self.detail_layout.addWidget(wrap)

        ports_card = Card()
        ports_card.layout().addWidget(_bold(f"Open ports / services ({view.open_ports})"))
        if view.ports:
            ptable = QTableWidget(len(view.ports), 2)
            ptable.setHorizontalHeaderLabels(["Port", "Service"])
            ptable.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            ptable.verticalHeader().setVisible(False)
            ptable.setEditTriggers(QTableWidget.NoEditTriggers)
            ptable.setMaximumHeight(160)
            for i, p in enumerate(view.ports):
                ptable.setItem(i, 0, QTableWidgetItem(str(p["port"])))
                ptable.setItem(i, 1, QTableWidgetItem(p.get("service", "")))
            ports_card.layout().addWidget(ptable)
        else:
            ports_card.layout().addWidget(_hint("No ports recorded."))
        self.detail_layout.addWidget(ports_card)

        find_card = Card()
        find_card.layout().addWidget(_bold(f"Findings ({len(view.findings)})"))
        if view.findings:
            ftable = QTableWidget(len(view.findings), 3)
            ftable.setHorizontalHeaderLabels(["Severity", "Title", "Port"])
            ftable.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            ftable.verticalHeader().setVisible(False)
            ftable.setEditTriggers(QTableWidget.NoEditTriggers)
            for i, f in enumerate(view.findings):
                ftable.setItem(i, 0, QTableWidgetItem(f.get("severity", "").upper()))
                ftable.setItem(i, 1, QTableWidgetItem(f.get("title", "")))
                ftable.setItem(i, 2, QTableWidgetItem(str(f.get("port", ""))))
            find_card.layout().addWidget(ftable)
        else:
            find_card.layout().addWidget(_hint("No findings for this host."))
        self.detail_layout.addWidget(find_card)
        self.detail_layout.addStretch(1)


def _bold(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("CardTitle")
    return lbl


def _hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Hint")
    return lbl
