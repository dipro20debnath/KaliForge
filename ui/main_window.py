"""Main window — hosts the sidebar + a stacked set of pages and wires the
cross-page signals (run a command → terminal, open details, etc.)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMainWindow, QStackedWidget,
                               QStatusBar, QWidget)

from core.config import APP_NAME
from ui.pages.ai_assistant import AssistantPage
from ui.pages.arsenal import ArsenalPage
from ui.pages.dashboard import DashboardPage
from ui.pages.evidence import EvidencePage
from ui.pages.monitor import MonitorPage
from ui.pages.plugins import PluginsPage
from ui.pages.reports import ReportsPage
from ui.pages.scope import ScopePage
from ui.pages.settings import SettingsPage
from ui.pages.terminal_page import TerminalPage
from ui.pages.vault import VaultPage
from ui.pages.vulnerability import VulnerabilityPage
from ui.pages.workflows import WorkflowsPage
from ui.run_controller import RunController
from ui.sidebar import Sidebar
from ui.theme import stylesheet
from ui.widgets.tool_detail import ToolDetailDialog


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle(f"{APP_NAME} — Cybersecurity Command Center")
        self.resize(1280, 820)
        self.runner = RunController(app, self)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.navigate.connect(self.navigate)
        root.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self._pages: dict[str, QWidget] = {}
        self._build_pages()

        self.setStatusBar(QStatusBar())
        self._apply_theme(self.app.settings.get("appearance.theme", "kali_neon"))

        self.sidebar.select("dashboard")
        self.navigate("dashboard")

    # ------------------------------------------------------------- pages
    def _build_pages(self) -> None:
        self.dashboard = DashboardPage(self.app)
        self.dashboard.navigate.connect(lambda cid: self.navigate(f"cat:{cid}"))
        self.dashboard.open_page.connect(self.navigate)

        self.arsenal = ArsenalPage(self.app)
        self.arsenal.open_tool.connect(self._open_tool)
        self.arsenal.show_details.connect(self._show_details)

        self.terminal = TerminalPage(self.app)
        self.terminal.status_message.connect(self._status)
        self.runner.request_terminal.connect(self._run_in_terminal)

        self.vulnerability = VulnerabilityPage(self.app)
        self.vulnerability.status_message.connect(self._status)

        self.workflows = WorkflowsPage(self.app)
        self.workflows.status_message.connect(self._status)

        self.assistant = AssistantPage(self.app)
        self.assistant.run_command.connect(self._run_from_signal)

        self.scope = ScopePage(self.app)
        self.monitor = MonitorPage(self.app)
        self.reports = ReportsPage(self.app)
        self.reports.status_message.connect(self._status)
        self.vault = VaultPage(self.app)
        self.vault.run_command.connect(self._run_from_signal)
        self.evidence = EvidencePage(self.app)
        self.evidence.status_message.connect(self._status)
        self.plugins = PluginsPage(self.app)
        self.plugins.catalog_changed.connect(self.arsenal.rebuild)
        self.settings_page = SettingsPage(self.app)
        self.settings_page.theme_changed.connect(self._apply_theme)

        for key, page in [
            ("dashboard", self.dashboard), ("arsenal", self.arsenal),
            ("terminal", self.terminal), ("vulnerability", self.vulnerability),
            ("workflows", self.workflows), ("assistant", self.assistant),
            ("scope", self.scope), ("monitor", self.monitor),
            ("reports", self.reports), ("vault", self.vault),
            ("evidence", self.evidence), ("plugins", self.plugins),
            ("settings", self.settings_page),
        ]:
            self._pages[key] = page
            self.stack.addWidget(page)

    # ------------------------------------------------------------- navigation
    def navigate(self, key: str) -> None:
        if key.startswith("cat:"):
            category = key.split(":", 1)[1]
            if category == "recon2":
                category = "recon"
            self.arsenal.set_category(category)
            self.stack.setCurrentWidget(self.arsenal)
            self.sidebar.select(key)
            return
        page = self._pages.get(key)
        if page:
            self.stack.setCurrentWidget(page)
            self.sidebar.select(key)
            if key == "vulnerability":
                self.vulnerability.refresh()
            elif key == "dashboard":
                self.dashboard.refresh()

    # ------------------------------------------------------------- tool launch
    def _open_tool(self, tool_id: str) -> None:
        tool = self.app.catalog.get(tool_id)
        if not tool:
            return
        status = self.app.tools.status(tool_id)
        if status and not status.installed and not status.builtin:
            self._show_details(tool_id)
            return
        commands = tool.get("commands", [])
        if not commands:
            self._show_details(tool_id)
            return
        # single launch command → open directly in terminal via builder
        self._show_details(tool_id)

    def _show_details(self, tool_id: str) -> None:
        tool = self.app.catalog.get(tool_id)
        if not tool:
            return
        dialog = ToolDetailDialog(self.app, tool, self)
        dialog.run_command.connect(lambda cmd, tid: self._run_tool_command(cmd, tid))
        dialog.install_tool.connect(self._run_in_terminal)
        dialog.exec()
        self.arsenal.rebuild()

    def _run_tool_command(self, command: str, tool_id: str) -> None:
        tool = self.app.catalog.get(tool_id)
        self.runner.launch(command, tool=tool, source="arsenal", parent_widget=self)

    def _run_from_signal(self, command: str, tool_id: str) -> None:
        tool = self.app.catalog.get(tool_id) if tool_id else None
        self.runner.launch(command, tool=tool, source="assistant", parent_widget=self)

    def _run_in_terminal(self, command: str) -> None:
        self.navigate("terminal")
        self.terminal.run_command(command)

    # ------------------------------------------------------------- misc
    def _status(self, message: str) -> None:
        self.statusBar().showMessage(message, 6000)

    def _apply_theme(self, theme: str) -> None:
        size = int(self.app.settings.get("appearance.ui_font_size", 10))
        self.setStyleSheet(stylesheet(theme, size))

    def closeEvent(self, event):  # noqa: N802
        try:
            self.terminal.shutdown()
        except Exception:
            pass
        self.app.close()
        super().closeEvent(event)
