"""Command-preview / confirmation dialog shown before a guarded command runs."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QLabel,
                               QPlainTextEdit, QPushButton, QVBoxLayout)

from core.permission_manager import Decision

_RISK_STYLE = {"info": "SevInfo", "caution": "SevMed", "dangerous": "SevCrit"}


class CommandConfirmDialog(QDialog):
    """Shows the exact command, its risk and why confirmation is needed.

    Returns the possibly-edited command via :meth:`command` on accept.
    """

    def __init__(self, decision: Decision, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm command")
        self.setMinimumWidth(560)
        self.decision = decision
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        risk = QLabel(f"Risk level: {decision.risk.upper()}")
        risk.setObjectName(_RISK_STYLE.get(decision.risk, "SevInfo"))
        layout.addWidget(risk)

        layout.addWidget(QLabel("Command preview (editable):"))
        self.editor = QPlainTextEdit(decision.command)
        self.editor.setFixedHeight(80)
        layout.addWidget(self.editor)

        if decision.targets:
            layout.addWidget(QLabel("Targets: " + ", ".join(decision.targets)))
        if decision.out_of_scope:
            warn = QLabel("⚠ Out of scope: " + ", ".join(decision.out_of_scope))
            warn.setObjectName("SevHigh")
            warn.setWordWrap(True)
            layout.addWidget(warn)

        if decision.reasons:
            reasons = QLabel("• " + "\n• ".join(decision.reasons))
            reasons.setObjectName("Hint")
            reasons.setWordWrap(True)
            layout.addWidget(reasons)

        self.ack = QCheckBox("I am authorised to run this against the target(s).")
        layout.addWidget(self.ack)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.run_btn = QPushButton("Run command")
        self.run_btn.setObjectName("Danger" if decision.risk == "dangerous" else "Primary")
        self.run_btn.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(self.run_btn)
        layout.addLayout(buttons)

        needs_ack = decision.risk == "dangerous" or bool(decision.out_of_scope)
        if needs_ack:
            self.run_btn.setEnabled(False)
            self.ack.stateChanged.connect(
                lambda state: self.run_btn.setEnabled(state == Qt.Checked.value or bool(state)))
        else:
            self.ack.setChecked(True)
            self.ack.hide()

    def command(self) -> str:
        return self.editor.toPlainText().strip()
