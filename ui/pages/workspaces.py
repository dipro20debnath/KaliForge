"""Workspaces page — create, switch and delete engagement workspaces, and
export/import them as portable ``.kfw`` backups."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QDialog, QFileDialog, QFormLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from core import backup


class WorkspacesPage(QWidget):
    workspace_switched = Signal()
    status_message = Signal(str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        head = QHBoxLayout()
        title = QLabel("Workspaces")
        title.setObjectName("PageTitle")
        head.addWidget(title)
        head.addStretch(1)
        for text, slot, name in [
            ("＋ New", self._create, "Primary"),
            ("⇩ Export", self._export, "Ghost"),
            ("⇧ Import", self._import, "Ghost"),
        ]:
            btn = QPushButton(text)
            btn.setObjectName(name)
            btn.clicked.connect(slot)
            head.addWidget(btn)
        layout.addLayout(head)
        sub = QLabel("Each workspace isolates its own scope, findings, assets, "
                     "evidence, credentials and checklist. Double-click to switch.")
        sub.setObjectName("PageSub")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Active", "Name", "Client", "Findings", ""])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(lambda r, _c: self._switch(r))
        layout.addWidget(self.table, 1)

    def showEvent(self, event):  # noqa: N802
        self.refresh()
        super().showEvent(event)

    def refresh(self) -> None:
        self._rows = self.app.workspaces.list()
        active = self.app.active_workspace_id()
        self.table.setRowCount(len(self._rows))
        for i, ws in enumerate(self._rows):
            mark = "●" if ws["id"] == active else ""
            item0 = QTableWidgetItem(mark)
            item0.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, item0)
            self.table.setItem(i, 1, QTableWidgetItem(ws["name"]))
            self.table.setItem(i, 2, QTableWidgetItem(ws.get("client", "")))
            n = sum(self.app.db.severity_counts(ws["id"]).values())
            self.table.setItem(i, 3, QTableWidgetItem(str(n)))
            cell = QWidget()
            hl = QHBoxLayout(cell)
            hl.setContentsMargins(0, 0, 0, 0)
            switch = QPushButton("Switch")
            switch.clicked.connect(lambda _=False, r=i: self._switch(r))
            delete = QPushButton("✕")
            delete.setObjectName("Ghost")
            delete.setFixedWidth(30)
            delete.clicked.connect(lambda _=False, r=i: self._delete(r))
            hl.addWidget(switch)
            hl.addWidget(delete)
            self.table.setCellWidget(i, 4, cell)

    def _create(self) -> None:
        dialog = _WorkspaceDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, client, desc = dialog.data()
            if name:
                ws = self.app.workspaces.create(name, client, desc)
                self.app.switch_workspace(ws["id"])
                self.refresh()
                self.workspace_switched.emit()
                self.status_message.emit(f"Created and switched to '{name}'.")

    def _switch(self, row: int) -> None:
        if 0 <= row < len(self._rows):
            self.app.switch_workspace(self._rows[row]["id"])
            self.refresh()
            self.workspace_switched.emit()
            self.status_message.emit(f"Switched to '{self._rows[row]['name']}'.")

    def _delete(self, row: int) -> None:
        if not (0 <= row < len(self._rows)):
            return
        ws = self._rows[row]
        if QMessageBox.question(self, "Delete workspace",
                                f"Delete '{ws['name']}' and all its data?") != QMessageBox.Yes:
            return
        try:
            self.app.workspaces.delete(ws["id"])
        except ValueError as exc:
            QMessageBox.warning(self, "Delete", str(exc))
            return
        self.app.switch_workspace(self.app.workspaces.active()["id"])
        self.refresh()
        self.workspace_switched.emit()

    def _export(self) -> None:
        ws = self.app.workspaces.active()
        default = str(Path.home() / f"{ws['name'].replace(' ', '_')}.kfw")
        path, _ = QFileDialog.getSaveFileName(self, "Export workspace", default,
                                              "KaliForge workspace (*.kfw)")
        if not path:
            return
        try:
            out = backup.export_workspace(self.app, ws["id"], path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.status_message.emit(f"Workspace exported to {out}")

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import workspace", "",
                                              "KaliForge workspace (*.kfw *.zip)")
        if not path:
            return
        try:
            result = backup.import_workspace(self.app, path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Import failed", str(exc))
            return
        self.app.switch_workspace(result["id"])
        self.refresh()
        self.workspace_switched.emit()
        self.status_message.emit(f"Imported '{result['name']}'.")


class _WorkspaceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New workspace")
        form = QFormLayout(self)
        self.name = QLineEdit()
        self.client = QLineEdit()
        self.desc = QLineEdit()
        form.addRow("Name*", self.name)
        form.addRow("Client", self.client)
        form.addRow("Description", self.desc)
        buttons = QHBoxLayout()
        ok = QPushButton("Create")
        ok.setObjectName("Primary")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        form.addRow(buttons)

    def data(self):
        return self.name.text().strip(), self.client.text().strip(), self.desc.text().strip()
