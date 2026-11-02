"""Command Vault & Knowledge Base — save/categorise/search commands, and keep
free-form pentest notes per workspace."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QFormLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMessageBox, QPlainTextEdit,
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QTabWidget, QVBoxLayout, QWidget)


class VaultPage(QWidget):
    run_command = Signal(str, str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._build()
        self.refresh_vault()
        self.refresh_notes()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title = QLabel("Command Vault & Notes")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        tabs = QTabWidget()
        tabs.addTab(self._vault_tab(), "Command Vault")
        tabs.addTab(self._notes_tab(), "Knowledge Base")
        layout.addWidget(tabs, 1)

    # ---------------------------------------------------------------- vault
    def _vault_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        row = QHBoxLayout()
        self.vault_search = QLineEdit()
        self.vault_search.setPlaceholderText("Search commands, tags, categories…")
        self.vault_search.textChanged.connect(self.refresh_vault)
        add = QPushButton("＋ Save command")
        add.setObjectName("Primary")
        add.clicked.connect(self._add_vault)
        row.addWidget(self.vault_search, 1)
        row.addWidget(add)
        layout.addLayout(row)

        self.vault_table = QTableWidget(0, 5)
        self.vault_table.setHorizontalHeaderLabels(["Title", "Command", "Category", "Uses", ""])
        self.vault_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.vault_table.verticalHeader().setVisible(False)
        self.vault_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.vault_table, 1)
        return widget

    def refresh_vault(self) -> None:
        rows = self.app.db.vault(self.vault_search.text().strip())
        self._vault_rows = rows
        self.vault_table.setRowCount(len(rows))
        for i, v in enumerate(rows):
            self.vault_table.setItem(i, 0, QTableWidgetItem(v["title"]))
            self.vault_table.setItem(i, 1, QTableWidgetItem(v["command"]))
            self.vault_table.setItem(i, 2, QTableWidgetItem(v["category"]))
            self.vault_table.setItem(i, 3, QTableWidgetItem(str(v["uses"])))
            cell = QWidget()
            hl = QHBoxLayout(cell)
            hl.setContentsMargins(0, 0, 0, 0)
            run = QPushButton("Run")
            run.clicked.connect(lambda _=False, vid=v["id"], c=v["command"]: self._run_vault(vid, c))
            delete = QPushButton("✕")
            delete.setObjectName("Ghost")
            delete.setFixedWidth(30)
            delete.clicked.connect(lambda _=False, vid=v["id"]: self._del_vault(vid))
            hl.addWidget(run)
            hl.addWidget(delete)
            self.vault_table.setCellWidget(i, 4, cell)

    def _add_vault(self) -> None:
        dialog = _VaultDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.data()
            if data["title"] and data["command"]:
                self.app.db.add_vault(**data)
                self.refresh_vault()

    def _run_vault(self, vault_id: int, command: str) -> None:
        self.app.db.bump_vault(vault_id)
        self.run_command.emit(command, "")
        self.refresh_vault()

    def _del_vault(self, vault_id: int) -> None:
        self.app.db.delete_vault(vault_id)
        self.refresh_vault()

    # ---------------------------------------------------------------- notes
    def _notes_tab(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        left = QVBoxLayout()
        self.notes_list = QListWidget()
        self.notes_list.currentRowChanged.connect(self._load_note)
        add = QPushButton("＋ New note")
        add.clicked.connect(self._new_note)
        left.addWidget(self.notes_list, 1)
        left.addWidget(add)
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        self.note_title = QLineEdit()
        self.note_title.setPlaceholderText("Note title")
        self.note_body = QPlainTextEdit()
        self.note_body.setPlaceholderText("Markdown / plain text notes and cheat-sheets…")
        save_row = QHBoxLayout()
        save = QPushButton("Save note")
        save.setObjectName("Primary")
        save.clicked.connect(self._save_note)
        delete = QPushButton("Delete")
        delete.setObjectName("Danger")
        delete.clicked.connect(self._delete_note)
        save_row.addWidget(save)
        save_row.addWidget(delete)
        save_row.addStretch(1)
        right.addWidget(self.note_title)
        right.addWidget(self.note_body, 1)
        right.addLayout(save_row)
        layout.addLayout(right, 2)
        return widget

    def refresh_notes(self) -> None:
        self._notes = self.app.db.notes(self.app.active_workspace_id())
        self.notes_list.clear()
        for note in self._notes:
            self.notes_list.addItem(QListWidgetItem(note["title"]))

    def _load_note(self, row: int) -> None:
        if 0 <= row < len(self._notes):
            note = self._notes[row]
            self.note_title.setText(note["title"])
            self.note_body.setPlainText(note["body"])
            self._current_note = note["id"]
        else:
            self._current_note = None

    def _new_note(self) -> None:
        self.note_title.clear()
        self.note_body.clear()
        self._current_note = None
        self.notes_list.clearSelection()

    def _save_note(self) -> None:
        title = self.note_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Note", "A title is required.")
            return
        body = self.note_body.toPlainText()
        current = getattr(self, "_current_note", None)
        if current:
            self.app.db.update_note(current, title, body)
        else:
            self.app.db.add_note(title, body, workspace_id=self.app.active_workspace_id())
        self.refresh_notes()

    def _delete_note(self) -> None:
        current = getattr(self, "_current_note", None)
        if current:
            self.app.db.delete_note(current)
            self._new_note()
            self.refresh_notes()


class _VaultDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save command")
        self.setMinimumWidth(460)
        form = QFormLayout(self)
        self.title = QLineEdit()
        self.command = QPlainTextEdit()
        self.command.setFixedHeight(60)
        self.category = QLineEdit("General")
        self.tags = QLineEdit()
        self.description = QLineEdit()
        form.addRow("Title*", self.title)
        form.addRow("Command*", self.command)
        form.addRow("Category", self.category)
        form.addRow("Tags", self.tags)
        form.addRow("Description", self.description)
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
            "title": self.title.text().strip(),
            "command": self.command.toPlainText().strip(),
            "category": self.category.text().strip() or "General",
            "tags": self.tags.text().strip(),
            "description": self.description.text().strip(),
        }
