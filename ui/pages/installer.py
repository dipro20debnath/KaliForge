"""Installation Manager page — select missing tools and generate a safe install
plan / script (never auto-installs)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QPlainTextEdit,
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from core.categories import category_label


class InstallerPage(QWidget):
    run_in_terminal = Signal(str)
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
        title = QLabel("Installation Manager")
        title.setObjectName("PageTitle")
        head.addWidget(title)
        head.addStretch(1)
        self.count_lbl = QLabel("")
        self.count_lbl.setObjectName("Hint")
        head.addWidget(self.count_lbl)
        layout.addLayout(head)

        controls = QHBoxLayout()
        select_all = QPushButton("Select all")
        select_all.clicked.connect(lambda: self._set_all(True))
        select_none = QPushButton("Select none")
        select_none.clicked.connect(lambda: self._set_all(False))
        gen = QPushButton("Generate install plan")
        gen.setObjectName("Primary")
        gen.clicked.connect(self._generate)
        controls.addWidget(select_all)
        controls.addWidget(select_none)
        controls.addStretch(1)
        controls.addWidget(gen)
        layout.addLayout(controls)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["✓", "Tool", "Category", "Package"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 34)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

        self.plan_box = QPlainTextEdit()
        self.plan_box.setReadOnly(True)
        self.plan_box.setFixedHeight(120)
        self.plan_box.setPlaceholderText("Generated install command will appear here.")
        layout.addWidget(self.plan_box)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.run_btn = QPushButton("Run apt install in terminal")
        self.run_btn.setObjectName("Primary")
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._run)
        actions.addWidget(self.run_btn)
        layout.addLayout(actions)

    def showEvent(self, event):  # noqa: N802
        self.app.tools.detect_all()   # reflect tools installed since last view
        self.refresh()
        super().showEvent(event)

    def refresh(self) -> None:
        self._missing = self.app.installer.missing()
        self.table.setRowCount(len(self._missing))
        self._checks: list = []
        from PySide6.QtWidgets import QCheckBox
        for i, tool in enumerate(self._missing):
            chk = QCheckBox()
            chk.setChecked(bool(tool.get("package")))
            self._checks.append(chk)
            self.table.setCellWidget(i, 0, chk)
            self.table.setItem(i, 1, QTableWidgetItem(tool["name"]))
            self.table.setItem(i, 2, QTableWidgetItem(category_label(tool["category"])))
            self.table.setItem(i, 3, QTableWidgetItem(tool.get("package") or "— (manual)"))
        self.count_lbl.setText(f"{len(self._missing)} tools not installed")

    def _set_all(self, value: bool) -> None:
        for chk in self._checks:
            chk.setChecked(value)

    def _selected_ids(self) -> list[str]:
        return [self._missing[i]["id"] for i, chk in enumerate(self._checks) if chk.isChecked()]

    def _generate(self) -> None:
        ids = self._selected_ids()
        if not ids:
            self.status_message.emit("Select at least one tool.")
            return
        self._plan = self.app.installer.plan(ids)
        self.plan_box.setPlainText(self.app.installer.script(self._plan))
        self.run_btn.setEnabled(bool(self._plan.apt_command))

    def _run(self) -> None:
        if getattr(self, "_plan", None) and self._plan.apt_command:
            self.run_in_terminal.emit(self._plan.apt_command)
            self.status_message.emit("Install command sent to terminal — review before confirming.")
