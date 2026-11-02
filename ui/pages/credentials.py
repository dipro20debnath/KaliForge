"""Credentials Manager page — store discovered credentials (encrypted) per
workspace, with reveal/hide and copy."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QDialog, QFormLayout, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from core.credentials import Credential, CredentialStore


class CredentialsPage(QWidget):
    status_message = Signal(str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.store = CredentialStore(app.db, app.vault)
        self._revealed = False
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        head = QHBoxLayout()
        title = QLabel("Credentials Manager")
        title.setObjectName("PageTitle")
        head.addWidget(title)
        head.addStretch(1)
        add = QPushButton("＋ Add credential")
        add.setObjectName("Primary")
        add.clicked.connect(self._add)
        self.reveal_btn = QPushButton("👁 Reveal")
        self.reveal_btn.setCheckable(True)
        self.reveal_btn.toggled.connect(self._toggle_reveal)
        delete = QPushButton("Delete")
        delete.setObjectName("Danger")
        delete.clicked.connect(self._delete)
        head.addWidget(add)
        head.addWidget(self.reveal_btn)
        head.addWidget(delete)
        layout.addLayout(head)

        self.enc_lbl = QLabel("")
        self.enc_lbl.setObjectName("Hint")
        layout.addWidget(self.enc_lbl)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Host", "Service", "Username", "Password", "Note"])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellDoubleClicked.connect(self._copy_password)
        layout.addWidget(self.table, 1)

    def showEvent(self, event):  # noqa: N802
        self.refresh()
        super().showEvent(event)

    def refresh(self) -> None:
        self._rows = self.store.list(self.app.active_workspace_id(), reveal=self._revealed)
        self.table.setRowCount(len(self._rows))
        for i, c in enumerate(self._rows):
            self.table.setItem(i, 0, QTableWidgetItem(c.get("host", "")))
            self.table.setItem(i, 1, QTableWidgetItem(c.get("service", "")))
            self.table.setItem(i, 2, QTableWidgetItem(c.get("username", "")))
            self.table.setItem(i, 3, QTableWidgetItem(c.get("password", "")))
            self.table.setItem(i, 4, QTableWidgetItem(c.get("note", "")))
        enc = "encrypted at rest" if self.store.encrypted else "⚠ NOT encrypted (install cryptography)"
        self.enc_lbl.setText(f"Secrets are {enc}. Double-click a row to copy its password.")

    def _toggle_reveal(self, on: bool) -> None:
        self._revealed = on
        self.reveal_btn.setText("🙈 Hide" if on else "👁 Reveal")
        self.refresh()

    def _add(self) -> None:
        dialog = _CredDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cred = dialog.credential()
            if cred.username or cred.host:
                self.store.add(cred, self.app.active_workspace_id())
                self.refresh()
                self.status_message.emit("Credential stored (encrypted).")

    def _delete(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self._rows):
            self.store.delete(self._rows[row]["id"])
            self.refresh()

    def _copy_password(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._rows):
            from PySide6.QtWidgets import QApplication
            pwd = self.store.reveal(self._rows[row])
            QApplication.clipboard().setText(pwd)
            self.status_message.emit("Password copied to clipboard.")


class _CredDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add credential")
        self.setMinimumWidth(420)
        form = QFormLayout(self)
        self.host = QLineEdit()
        self.service = QLineEdit()
        self.service.setPlaceholderText("ssh, http, mysql…")
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.note = QLineEdit()
        form.addRow("Host", self.host)
        form.addRow("Service", self.service)
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)
        form.addRow("Note", self.note)
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

    def credential(self) -> Credential:
        return Credential(
            host=self.host.text().strip(), service=self.service.text().strip(),
            username=self.username.text().strip(), password=self.password.text(),
            note=self.note.text().strip())
