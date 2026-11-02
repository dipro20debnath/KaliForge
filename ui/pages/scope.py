"""Scope Manager — define and review the authorised engagement scope. This is
the gate every guarded command is checked against."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from core.scope_manager import classify


class ScopePage(QWidget):
    KINDS = ["auto", "ip", "cidr", "range", "domain", "url"]

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Scope Manager")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        sub = QLabel("Only targets listed here may be tested by lab-only tools. "
                     "This is your authorisation boundary — keep it accurate.")
        sub.setObjectName("PageSub")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        add_row = QHBoxLayout()
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("192.168.56.0/24, example.com, https://app.test, 10.0.0.1-10.0.0.50")
        self.value_input.returnPressed.connect(self.add_entry)
        self.kind_box = QComboBox()
        self.kind_box.addItems(self.KINDS)
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("note (optional)")
        add_btn = QPushButton("Add to scope")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self.add_entry)
        add_row.addWidget(self.value_input, 3)
        add_row.addWidget(self.kind_box, 1)
        add_row.addWidget(self.note_input, 2)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Value", "Kind", "Note", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

        tester = QHBoxLayout()
        self.test_input = QLineEdit()
        self.test_input.setPlaceholderText("Test a target against the scope…")
        self.test_input.returnPressed.connect(self.test_target)
        test_btn = QPushButton("Check")
        test_btn.clicked.connect(self.test_target)
        self.test_result = QLabel("")
        tester.addWidget(self.test_input, 2)
        tester.addWidget(test_btn)
        tester.addWidget(self.test_result, 1)
        layout.addLayout(tester)

    def add_entry(self) -> None:
        value = self.value_input.text().strip()
        if not value:
            return
        kind = self.kind_box.currentText()
        if kind == "auto":
            kind = classify(value)
        self.app.scope.add(value, kind, self.note_input.text().strip())
        self.value_input.clear()
        self.note_input.clear()
        self.refresh()

    def refresh(self) -> None:
        rows = self.app.scope.raw_entries()
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(row["value"]))
            self.table.setItem(i, 1, QTableWidgetItem(row["kind"]))
            self.table.setItem(i, 2, QTableWidgetItem(row.get("note", "")))
            remove = QPushButton("Remove")
            remove.setObjectName("Ghost")
            remove.clicked.connect(lambda _=False, sid=row.get("id"): self._remove(sid))
            self.table.setCellWidget(i, 3, remove)

    def _remove(self, scope_id) -> None:
        if scope_id is None:
            return
        self.app.scope.remove(scope_id)
        self.refresh()

    def test_target(self) -> None:
        target = self.test_input.text().strip()
        if not target:
            return
        ok = self.app.scope.in_scope(target)
        self.test_result.setText("✓ in scope" if ok else "✗ NOT in scope")
        self.test_result.setObjectName("SevLow" if ok else "SevCrit")
        self.test_result.setStyleSheet("")
        self.test_result.style().unpolish(self.test_result)
        self.test_result.style().polish(self.test_result)
