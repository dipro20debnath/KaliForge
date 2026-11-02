"""Workflows — pick an automated workflow, fill its inputs, run it against an
in-scope target and watch each step complete, writing output to the workspace."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QFormLayout, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QMessageBox, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from core.workflow_engine import WorkflowEngine, list_workflows
from core.config import WORKFLOWS_DIR


class WorkflowsPage(QWidget):
    status_message = Signal(str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.engine = WorkflowEngine(
            tool_manager=app.tools, scope=app.scope, audit=app.audit,
            enforce_scope=app.settings.get("security.scope_mode", "warn") != "off")
        self._workflows = list_workflows(WORKFLOWS_DIR)
        self._inputs: dict[str, QLineEdit] = {}
        self._run = None
        self._build()
        self._on_select(0)

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title = QLabel("Automated Workflows")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        top = QHBoxLayout()
        self.select = QComboBox()
        for wf in self._workflows:
            self.select.addItem(wf.get("name", wf.get("id", "workflow")))
        self.select.currentIndexChanged.connect(self._on_select)
        top.addWidget(QLabel("Workflow:"))
        top.addWidget(self.select, 1)
        layout.addLayout(top)

        self.desc = QLabel("")
        self.desc.setObjectName("PageSub")
        self.desc.setWordWrap(True)
        layout.addWidget(self.desc)

        self.form = QFormLayout()
        self.form_host = QWidget()
        self.form_host.setLayout(self.form)
        layout.addWidget(self.form_host)

        controls = QHBoxLayout()
        self.run_btn = QPushButton("Run workflow")
        self.run_btn.setObjectName("Primary")
        self.run_btn.clicked.connect(self.run_workflow)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("Danger")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        controls.addWidget(self.run_btn)
        controls.addWidget(self.cancel_btn)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["#", "Tool", "Status", "Detail"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

    def _current(self) -> dict | None:
        idx = self.select.currentIndex()
        return self._workflows[idx] if 0 <= idx < len(self._workflows) else None

    def _on_select(self, _index: int) -> None:
        wf = self._current()
        while self.form.rowCount():
            self.form.removeRow(0)
        self._inputs.clear()
        if not wf:
            return
        self.desc.setText(wf.get("description", ""))
        for name in wf.get("inputs", []):
            edit = QLineEdit()
            entries = self.app.scope.entries()
            if name in ("target", "domain", "host") and entries:
                edit.setText(entries[0].value)
            self._inputs[name] = edit
            self.form.addRow(name + ":", edit)

    def run_workflow(self) -> None:
        wf = self._current()
        if not wf:
            return
        values = {name: edit.text().strip() for name, edit in self._inputs.items()}
        if not any(values.values()):
            QMessageBox.warning(self, "Workflow", "Provide at least one input value.")
            return
        if self.app.scope.is_empty():
            QMessageBox.warning(self, "Workflow",
                                "No scope defined. Add your authorised targets in the "
                                "Scope Manager before running a workflow.")
            return
        outdir = self.app.workspaces.output_dir() / f"wf_{wf.get('id', 'run')}"
        self.table.setRowCount(0)
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.status_message.emit(f"Running workflow '{wf.get('name')}'…")
        self._run = self.engine.run(
            wf, values, outdir,
            on_step=self._on_step, on_done=self._on_done, background=True)

    def _on_step(self, step) -> None:
        # called from worker thread → marshal via Qt's queued signals would be
        # ideal; for simplicity we update directly (PySide allows cross-thread
        # item set for simple widgets, but we guard with a single-shot).
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._render_step(step))

    def _render_step(self, step) -> None:
        row = step.index
        if row >= self.table.rowCount():
            self.table.setRowCount(row + 1)
        self.table.setItem(row, 0, QTableWidgetItem(str(step.index + 1)))
        self.table.setItem(row, 1, QTableWidgetItem(step.tool))
        self.table.setItem(row, 2, QTableWidgetItem(step.status))
        self.table.setItem(row, 3, QTableWidgetItem(step.note or step.command))

    def _on_done(self, run) -> None:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._finish(run))

    def _finish(self, run) -> None:
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_message.emit(
            f"Workflow {run.status}: {len(run.steps)} steps · output in {run.outdir}")

    def _cancel(self) -> None:
        self.engine.cancel()
        self.cancel_btn.setEnabled(False)
