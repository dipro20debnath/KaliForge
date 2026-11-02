"""Evidence Manager & Lab Manager — register artefacts with SHA-256 integrity,
and track lab/VM targets."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QFormLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QMessageBox, QPlainTextEdit, QPushButton,
                               QTableWidget, QTableWidgetItem, QTabWidget,
                               QVBoxLayout, QWidget)

from core.evidence import EvidenceManager


class EvidencePage(QWidget):
    status_message = Signal(str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._evidence = EvidenceManager(app.db, app.workspaces.path())
        self._build()
        self.refresh_evidence()
        self.refresh_labs()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title = QLabel("Evidence & Lab Manager")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        tabs = QTabWidget()
        tabs.addTab(self._evidence_tab(), "Evidence")
        tabs.addTab(self._labs_tab(), "Labs")
        layout.addWidget(tabs, 1)

    # ---------------------------------------------------------------- evidence
    def _evidence_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        row = QHBoxLayout()
        add = QPushButton("＋ Add evidence file")
        add.setObjectName("Primary")
        add.clicked.connect(self._add_evidence)
        verify = QPushButton("Verify integrity")
        verify.clicked.connect(self._verify)
        row.addWidget(add)
        row.addWidget(verify)
        row.addStretch(1)
        layout.addLayout(row)
        self.ev_table = QTableWidget(0, 5)
        self.ev_table.setHorizontalHeaderLabels(["File", "Kind", "SHA-256", "Size", "Note"])
        self.ev_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.ev_table.verticalHeader().setVisible(False)
        self.ev_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.ev_table, 1)
        return widget

    def refresh_evidence(self) -> None:
        rows = self._evidence.list(self.app.active_workspace_id())
        self._ev_rows = rows
        self.ev_table.setRowCount(len(rows))
        for i, e in enumerate(rows):
            self.ev_table.setItem(i, 0, QTableWidgetItem(Path(e["original_path"] or e["path"]).name))
            self.ev_table.setItem(i, 1, QTableWidgetItem(e["kind"]))
            self.ev_table.setItem(i, 2, QTableWidgetItem(e["sha256"]))
            self.ev_table.setItem(i, 3, QTableWidgetItem(str(e["size"])))
            self.ev_table.setItem(i, 4, QTableWidgetItem(e.get("note", "")))

    def _add_evidence(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select evidence file")
        if not path:
            return
        try:
            self._evidence.add_file(path, workspace_id=self.app.active_workspace_id())
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Evidence", str(exc))
            return
        self.refresh_evidence()
        self.status_message.emit("Evidence registered with SHA-256 hash.")

    def _verify(self) -> None:
        row = self.ev_table.currentRow()
        if row < 0 or row >= len(self._ev_rows):
            return
        ok = self._evidence.verify(self._ev_rows[row])
        QMessageBox.information(self, "Integrity",
                                "✓ Hash matches — evidence intact." if ok
                                else "✗ Hash mismatch or file missing!")

    # ---------------------------------------------------------------- labs
    def _labs_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        add = QPushButton("＋ Add lab")
        add.setObjectName("Primary")
        add.clicked.connect(self._add_lab)
        layout.addWidget(add)
        self.lab_table = QTableWidget(0, 5)
        self.lab_table.setHorizontalHeaderLabels(["Name", "Platform", "VM", "Target", ""])
        self.lab_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.lab_table.verticalHeader().setVisible(False)
        self.lab_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.lab_table, 1)
        return widget

    def refresh_labs(self) -> None:
        rows = self.app.db.labs()
        self._lab_rows = rows
        self.lab_table.setRowCount(len(rows))
        for i, lab in enumerate(rows):
            self.lab_table.setItem(i, 0, QTableWidgetItem(lab["name"]))
            self.lab_table.setItem(i, 1, QTableWidgetItem(lab["platform"]))
            self.lab_table.setItem(i, 2, QTableWidgetItem(lab["vm_name"]))
            self.lab_table.setItem(i, 3, QTableWidgetItem(lab["target"]))
            add_scope = QPushButton("Add target to scope")
            add_scope.clicked.connect(lambda _=False, t=lab["target"]: self._scope_lab(t))
            self.lab_table.setCellWidget(i, 4, add_scope)

    def _add_lab(self) -> None:
        dialog = _LabDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.data()
            if data["name"]:
                self.app.db.add_lab(**data)
                self.refresh_labs()

    def _scope_lab(self, target: str) -> None:
        if target:
            self.app.scope.add(target)
            self.status_message.emit(f"Added {target} to scope.")


class _LabDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add lab")
        form = QFormLayout(self)
        self.name = QLineEdit()
        self.platform = QComboBox()
        self.platform.addItems(["VirtualBox", "VMware", "Docker", "QEMU/KVM", "Cloud", "Other"])
        self.vm = QLineEdit()
        self.target = QLineEdit()
        self.target.setPlaceholderText("e.g. 192.168.56.101")
        self.notes = QPlainTextEdit()
        self.notes.setFixedHeight(60)
        form.addRow("Name*", self.name)
        form.addRow("Platform", self.platform)
        form.addRow("VM name", self.vm)
        form.addRow("Target IP", self.target)
        form.addRow("Notes", self.notes)
        buttons = QHBoxLayout()
        ok = QPushButton("Save")
        ok.setObjectName("Primary")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        form.addRow(buttons)

    def data(self) -> dict:
        return {
            "name": self.name.text().strip(),
            "platform": self.platform.currentText(),
            "vm_name": self.vm.text().strip(),
            "target": self.target.text().strip(),
            "notes": self.notes.toPlainText().strip(),
        }
