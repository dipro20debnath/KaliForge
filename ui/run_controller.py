"""Mediates every command launch: evaluate permission → confirm if needed →
hand off to the terminal, and audit the decision. The one place guard-rails are
enforced for interactive launches, so no page can bypass them."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox

from core.permission_manager import Decision
from ui.widgets.confirm_dialog import CommandConfirmDialog


class RunController(QObject):
    request_terminal = Signal(str)   # command to run in the terminal page

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app

    def launch(self, command: str, tool: dict | None = None, source: str = "arsenal",
               parent_widget=None) -> bool:
        command = command.strip()
        if not command:
            return False
        decision: Decision = self.app.permissions.evaluate(command, tool=tool)
        tool_id = tool["id"] if tool else ""
        ws_id = self.app.active_workspace_id()

        if not decision.allowed:
            self.app.permissions.log_decision(decision, source, tool_id, "blocked", ws_id)
            QMessageBox.critical(
                parent_widget, "Command blocked",
                decision.summary() + "\n\nAdd the target to your authorised scope "
                "(Scope Manager) before running this.")
            return False

        if decision.needs_confirm:
            dialog = CommandConfirmDialog(decision, parent_widget)
            if dialog.exec() != dialog.DialogCode.Accepted:
                self.app.permissions.log_decision(decision, source, tool_id, "cancelled", ws_id)
                return False
            edited = dialog.command()
            if edited != decision.command:
                # re-evaluate the edited command for a hard block only
                recheck = self.app.permissions.evaluate(edited, tool=tool)
                if not recheck.allowed:
                    QMessageBox.critical(parent_widget, "Command blocked", recheck.summary())
                    return False
                command = edited
                decision = recheck

        self.app.permissions.log_decision(decision, source, tool_id, "launched", ws_id)
        self.request_terminal.emit(command)
        return True
