"""Main window — hosts the sidebar + a stacked set of pages and wires the
cross-page signals (run a command → terminal, open details, etc.)."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                               QMainWindow, QPushButton, QStackedWidget,
                               QStatusBar, QVBoxLayout, QWidget)

from core.categories import CATEGORY_BY_ID
from ui.widgets.common import apply_pointer_cursors

from core.config import APP_NAME
from ui.pages.ai_assistant import AssistantPage
from ui.pages.arsenal import ArsenalPage
from ui.pages.attack_surface import AttackSurfacePage
from ui.pages.credentials import CredentialsPage
from ui.pages.dashboard import DashboardPage
from ui.pages.evidence import EvidencePage
from ui.pages.hosts import HostsPage
from ui.pages.methodology import MethodologyPage
from ui.pages.importer import ImporterPage
from ui.pages.installer import InstallerPage
from ui.pages.lab_env import LabEnvPage
from ui.pages.learning import LearningPage
from ui.pages.monitor import MonitorPage
from ui.pages.payloads import PayloadsPage
from ui.pages.plugins import PluginsPage
from ui.pages.reports import ReportsPage
from ui.pages.scope import ScopePage
from ui.pages.settings import SettingsPage
from ui.pages.terminal_page import TerminalPage
from ui.pages.tool_health import ToolHealthPage
from ui.pages.toolkit import ToolkitPage
from ui.pages.vault import VaultPage
from ui.pages.vulnerability import VulnerabilityPage
from ui.pages.workflows import WorkflowsPage
from ui.pages.workspaces import WorkspacesPage
from ui.run_controller import RunController
from ui.sidebar import NAV, Sidebar
from ui.theme import stylesheet
from ui.widgets.command_palette import CommandPalette, PaletteEntry
from ui.widgets.tool_detail import ToolDetailDialog

# key -> (icon, title) for the top header bar
PAGE_META = {
    "dashboard": ("📊", "Dashboard"), "arsenal": ("🧰", "Tool Arsenal"),
    "terminal": ("💻", "Command Center"), "vulnerability": ("🛡", "Vulnerability Assessment"),
    "workflows": ("⚙", "Workflows"), "assistant": ("🤖", "AI Command Assistant"),
    "scope": ("🎯", "Scope Manager"), "methodology": ("✅", "Methodology Checklist"),
    "monitor": ("📈", "System Monitor"), "attack_surface": ("🕸", "Attack Surface Mapper"),
    "hosts": ("🖥", "Hosts"), "tool_health": ("🩺", "Tool Health Monitor"),
    "installer": ("📦", "Installation Manager"), "learning": ("🎓", "Learning & Practice"),
    "lab_env": ("🐳", "Lab Environments"), "toolkit": ("🔧", "Crypto Toolkit"),
    "payloads": ("🐚", "Payload Generator"), "importer": ("📥", "Scan Import"),
    "workspaces": ("🗂", "Workspaces"), "vault": ("📓", "Vault & Notes"),
    "credentials": ("🔑", "Credentials Manager"), "evidence": ("🔬", "Evidence & Labs"),
    "reports": ("📄", "Reports"), "plugins": ("🧩", "Plugins"), "settings": ("⚙", "Settings"),
}


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

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self._build_header())
        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack, 1)
        root.addWidget(right, 1)

        self._pages: dict[str, QWidget] = {}
        self._page_anim = None
        self._build_pages()

        self.setStatusBar(QStatusBar())
        self._apply_theme(self.app.settings.get("appearance.theme", "kali_neon"))
        self._install_shortcuts()
        self._refresh_ws_chip()
        apply_pointer_cursors(self)

        self.sidebar.select("dashboard")
        self.navigate("dashboard")

    # ------------------------------------------------------------- header
    def _build_header(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(58)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(22, 0, 20, 0)
        layout.setSpacing(12)
        self.header_icon = QLabel("📊")
        self.header_icon.setObjectName("TopIcon")
        self.header_title = QLabel("Dashboard")
        self.header_title.setObjectName("TopTitle")
        layout.addWidget(self.header_icon)
        layout.addWidget(self.header_title)
        layout.addStretch(1)
        self.ws_chip = QLabel("")
        self.ws_chip.setObjectName("WsChip")
        layout.addWidget(self.ws_chip)
        search = QPushButton("  ⌕  Search    Ctrl+K")
        search.setObjectName("SearchBtn")
        search.setMinimumWidth(190)
        search.clicked.connect(self.open_palette)
        layout.addWidget(search)
        return bar

    def _refresh_ws_chip(self) -> None:
        ws = self.app.workspaces.active()
        self.ws_chip.setText(f"◆ {ws['name']}" if ws else "")

    def _set_header(self, key: str) -> None:
        meta = PAGE_META.get(key)
        if not meta and key.startswith("cat:"):
            cat = CATEGORY_BY_ID.get(key.split(":", 1)[1].replace("recon2", "recon"))
            if cat:
                meta = (cat.get("icon", "🧰"), cat["name"])
        if meta:
            self.header_icon.setText(meta[0])
            self.header_title.setText(meta[1])

    # ------------------------------------------------------------- shortcuts
    def _install_shortcuts(self) -> None:
        shortcuts = {
            "Ctrl+K": self.open_palette,
            "Ctrl+P": self.open_palette,
            "Ctrl+T": lambda: self.navigate("terminal"),
            "Ctrl+D": lambda: self.navigate("dashboard"),
            "Ctrl+L": lambda: self.navigate("arsenal"),
            "Ctrl+R": lambda: self.navigate("reports"),
            "Ctrl+Shift+S": lambda: self.navigate("scope"),
        }
        for seq, slot in shortcuts.items():
            QShortcut(QKeySequence(seq), self, activated=slot)

    def open_palette(self) -> None:
        entries: list[PaletteEntry] = []
        for section, items in NAV:
            for key, text in items:
                entries.append(PaletteEntry(
                    label=text, hint=f"go to · {section.lower()}",
                    action=lambda k=key: self.navigate(k), keywords=section))
        for tool in self.app.catalog.all():
            entries.append(PaletteEntry(
                label=tool["name"], hint="open tool · " + tool["category"],
                action=lambda tid=tool["id"]: self._show_details(tid),
                keywords=" ".join(tool.get("tags", []))))
        for v in self.app.db.vault():
            entries.append(PaletteEntry(
                label=v["title"], hint="run · vault",
                action=lambda c=v["command"]: self._run_from_signal(c, ""),
                keywords=v.get("tags", "")))
        # global search: findings, notes, hosts
        ws = self.app.active_workspace_id()
        for f in self.app.db.findings(ws):
            entries.append(PaletteEntry(
                label=f["title"], hint=f"finding · {f.get('severity', '')} · {f.get('host', '')}",
                action=lambda: self.navigate("vulnerability"),
                keywords=f"{f.get('cve', '')} {f.get('host', '')}"))
        for n in self.app.db.notes(ws):
            entries.append(PaletteEntry(
                label=n["title"], hint="note", action=lambda: self.navigate("vault"),
                keywords=n.get("tags", "")))
        from core.hosts import host_overview
        for h in host_overview(self.app.db, ws):
            entries.append(PaletteEntry(
                label=h.host, hint=f"host · {h.open_ports} ports · {h.top_severity}",
                action=lambda: self.navigate("hosts")))
        CommandPalette(entries, self).exec()

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

        # advanced (phase 3-5) pages
        self.attack_surface = AttackSurfacePage(self.app)
        self.attack_surface.status_message.connect(self._status)
        self.tool_health = ToolHealthPage(self.app)
        self.tool_health.status_message.connect(self._status)
        self.installer = InstallerPage(self.app)
        self.installer.status_message.connect(self._status)
        self.installer.run_in_terminal.connect(self._run_in_terminal)
        self.learning = LearningPage(self.app)
        self.lab_env = LabEnvPage(self.app)
        self.lab_env.status_message.connect(self._status)

        # feature set: hosts, toolkit, payloads, scan import
        self.hosts = HostsPage(self.app)
        self.hosts.status_message.connect(self._status)
        self.hosts.add_to_scope.connect(self._add_host_to_scope)
        self.toolkit = ToolkitPage(self.app)
        self.payloads = PayloadsPage(self.app)
        self.payloads.status_message.connect(self._status)
        self.payloads.run_in_terminal.connect(self._run_in_terminal)
        self.importer = ImporterPage(self.app)
        self.importer.status_message.connect(self._status)
        self.importer.data_imported.connect(self._on_imported)

        # phase: charts/checklist/creds/workspaces
        self.methodology = MethodologyPage(self.app)
        self.methodology.status_message.connect(self._status)
        self.credentials = CredentialsPage(self.app)
        self.credentials.status_message.connect(self._status)
        self.workspaces_page = WorkspacesPage(self.app)
        self.workspaces_page.status_message.connect(self._status)
        self.workspaces_page.workspace_switched.connect(self._on_workspace_switched)

        for key, page in [
            ("dashboard", self.dashboard), ("arsenal", self.arsenal),
            ("terminal", self.terminal), ("vulnerability", self.vulnerability),
            ("workflows", self.workflows), ("assistant", self.assistant),
            ("scope", self.scope), ("monitor", self.monitor),
            ("reports", self.reports), ("vault", self.vault),
            ("evidence", self.evidence), ("plugins", self.plugins),
            ("settings", self.settings_page),
            ("attack_surface", self.attack_surface), ("tool_health", self.tool_health),
            ("installer", self.installer), ("learning", self.learning),
            ("lab_env", self.lab_env), ("hosts", self.hosts),
            ("toolkit", self.toolkit), ("payloads", self.payloads),
            ("importer", self.importer), ("methodology", self.methodology),
            ("credentials", self.credentials), ("workspaces", self.workspaces_page),
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
            self._set_header(key)
            self._fade_in(self.arsenal)
            return
        page = self._pages.get(key)
        if page:
            self.stack.setCurrentWidget(page)
            self.sidebar.select(key)
            self._set_header(key)
            self._fade_in(page)
            if key == "vulnerability":
                self.vulnerability.refresh()
            elif key == "dashboard":
                self.dashboard.refresh()
            elif key == "hosts":
                self.hosts.refresh()

    def _fade_in(self, widget: QWidget) -> None:
        """Brief fade/opacity transition when a page becomes current."""
        try:
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b"opacity", self)
            anim.setDuration(170)
            anim.setStartValue(0.35)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.finished.connect(lambda: widget.setGraphicsEffect(None))
            anim.start()
            self._page_anim = anim
        except Exception:  # noqa: BLE001
            pass

    def _add_host_to_scope(self, host: str) -> None:
        if host:
            self.app.scope.add(host)
            self._status(f"Added {host} to scope.")

    def _on_imported(self) -> None:
        self.vulnerability.refresh()
        self.hosts.refresh()
        self.attack_surface.refresh()
        self._status("Scan data imported into findings, hosts and attack surface.")

    def _on_workspace_switched(self) -> None:
        self._refresh_ws_chip()
        # the active workspace changed — refresh everything workspace-scoped
        for page in (self.dashboard, self.vulnerability, self.hosts, self.scope,
                     self.attack_surface, self.methodology, self.credentials,
                     self.evidence):
            if hasattr(page, "refresh"):
                try:
                    page.refresh()
                except Exception:  # noqa: BLE001
                    pass

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
        # repaint theme-aware custom-drawn widgets
        if hasattr(self, "dashboard"):
            try:
                self.dashboard.refresh_charts(self.app.dashboard_stats())
            except Exception:  # noqa: BLE001
                pass
        if hasattr(self, "attack_surface"):
            try:
                self.attack_surface.refresh()
            except Exception:  # noqa: BLE001
                pass

    def closeEvent(self, event):  # noqa: N802
        try:
            self.terminal.shutdown()
        except Exception:
            pass
        self.app.close()
        super().closeEvent(event)
