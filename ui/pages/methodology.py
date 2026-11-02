"""Methodology Checklist page — track progress through OWASP WSTG / PTES per
workspace, with per-item notes and a progress bar."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QProgressBar,
                               QPushButton, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QWidget)

from tools.methodology_data import TEMPLATES, TEMPLATE_BY_ID, total_items


class MethodologyPage(QWidget):
    status_message = Signal(str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._building = False
        self._build()
        self.load()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        head = QHBoxLayout()
        title = QLabel("Methodology Checklist")
        title.setObjectName("PageTitle")
        head.addWidget(title)
        head.addStretch(1)
        self.template_box = QComboBox()
        for t in TEMPLATES:
            self.template_box.addItem(t["name"], t["id"])
        self.template_box.currentIndexChanged.connect(self.load)
        head.addWidget(self.template_box)
        reset = QPushButton("Reset")
        reset.setObjectName("Ghost")
        reset.clicked.connect(self._reset)
        head.addWidget(reset)
        layout.addLayout(head)

        prog_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress_lbl = QLabel("0 / 0")
        self.progress_lbl.setObjectName("Hint")
        prog_row.addWidget(self.progress, 1)
        prog_row.addWidget(self.progress_lbl)
        layout.addLayout(prog_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Item", "Done"])
        self.tree.setColumnWidth(0, 640)
        self.tree.itemChanged.connect(self._item_changed)
        layout.addWidget(self.tree, 1)

    def _template_id(self) -> str:
        return self.template_box.currentData()

    def showEvent(self, event):  # noqa: N802
        self.load()
        super().showEvent(event)

    def load(self) -> None:
        self._building = True
        self.tree.clear()
        template = TEMPLATE_BY_ID.get(self._template_id())
        if not template:
            self._building = False
            return
        state = self.app.db.checklist_state(self.app.active_workspace_id(), template["id"])
        for section in template["sections"]:
            parent = QTreeWidgetItem([section["name"], ""])
            parent.setFlags(parent.flags() & ~Qt.ItemIsUserCheckable)
            font = parent.font(0)
            font.setBold(True)
            parent.setFont(0, font)
            self.tree.addTopLevelItem(parent)
            parent.setExpanded(True)
            for item in section["items"]:
                child = QTreeWidgetItem([item["text"], ""])
                child.setData(0, Qt.UserRole, item["id"])
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                checked = state.get(item["id"], {}).get("checked", False)
                child.setCheckState(1, Qt.Checked if checked else Qt.Unchecked)
                parent.addChild(child)
        self._building = False
        self._update_progress()

    def _item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._building or column != 1:
            return
        item_id = item.data(0, Qt.UserRole)
        if not item_id:
            return
        checked = item.checkState(1) == Qt.Checked
        self.app.db.set_checklist_item(self.app.active_workspace_id(),
                                       self._template_id(), item_id, checked)
        self._update_progress()

    def _update_progress(self) -> None:
        template_id = self._template_id()
        total = total_items(template_id)
        state = self.app.db.checklist_state(self.app.active_workspace_id(), template_id)
        done = sum(1 for v in state.values() if v["checked"])
        pct = int(done / total * 100) if total else 0
        self.progress.setValue(pct)
        self.progress_lbl.setText(f"{done} / {total}  ({pct}%)")

    def _reset(self) -> None:
        self.app.db.execute(
            "DELETE FROM checklist_state WHERE workspace_id IS ? AND template=?",
            (self.app.active_workspace_id(), self._template_id()))
        self.load()
        self.status_message.emit("Checklist reset for this workspace.")
