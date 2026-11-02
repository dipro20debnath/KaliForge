"""Command Builder dialog — fills a template's placeholders with a form and
previews the final command live. Returns the built command on accept."""
from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLabel,
                               QLineEdit, QPlainTextEdit, QVBoxLayout)

from core import command_builder


class CommandBuilderDialog(QDialog):
    def __init__(self, template: str, defaults: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Command Builder")
        self.setMinimumWidth(520)
        self.template = template
        self._fields: dict[str, QLineEdit] = {}
        defaults = defaults or {}

        layout = QVBoxLayout(self)
        tmpl_lbl = QLabel(f"Template:  {template}")
        tmpl_lbl.setObjectName("Hint")
        tmpl_lbl.setWordWrap(True)
        layout.addWidget(tmpl_lbl)

        form = QFormLayout()
        for name in command_builder.placeholders(template):
            edit = QLineEdit(defaults.get(name, ""))
            edit.setPlaceholderText(command_builder.hint_for(name))
            edit.textChanged.connect(self._update_preview)
            self._fields[name] = edit
            form.addRow(name + ":", edit)
        layout.addLayout(form)

        layout.addWidget(QLabel("Preview:"))
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFixedHeight(70)
        layout.addWidget(self.preview)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Run")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._update_preview()

    def values(self) -> dict[str, str]:
        return {name: edit.text() for name, edit in self._fields.items()}

    def _update_preview(self) -> None:
        command, missing = command_builder.build(self.template, self.values())
        self.preview.setPlainText(command)
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(not missing)

    def command(self) -> str:
        command, _ = command_builder.build(self.template, self.values())
        return command
