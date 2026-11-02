"""AppManager — the composition root.

Holds the single instances of every manager and wires their dependencies so the
UI (and the test-suite) can construct the whole backend with one call. Pure
Python: no Qt imports, so it can be exercised headless.
"""
from __future__ import annotations

from pathlib import Path

from core.ai_assistant import AIAssistant
from core.audit import AuditLog
from core.config import Settings
from core.installer import InstallManager
from core.intel import IntelService
from core.lab_env import LabManager
from core.permission_manager import PermissionManager
from core.plugins import PluginManager
from core.scope_manager import ScopeManager
from core.system_monitor import SystemMonitor
from core.tool_health import ToolHealth
from core.tool_manager import ToolManager
from core.workflow_engine import WorkflowEngine
from core.workspace import WorkspaceManager
from database.database import Database
from tools.catalog import Catalog


class AppManager:
    def __init__(self, db_path: str | Path | None = None,
                 settings: Settings | None = None,
                 plugin_dirs: list[Path] | None = None):
        self.settings = settings or Settings()
        self.db = Database(db_path)
        self.audit = AuditLog(self.db, enabled=self.settings.get("security.audit_logging", True))

        # plugins first so their tools can be merged into the catalog
        self.plugins = PluginManager(self.settings, extra_dirs=plugin_dirs)
        self.plugins.discover()
        self.catalog = Catalog(extra=self.plugins.enabled_tools())

        self.tools = ToolManager(self.catalog, self.db)
        self.workspaces = WorkspaceManager(self.db, self.settings)
        active = self.workspaces.active()
        self.scope = ScopeManager(self.db, workspace_id=active["id"] if active else None)
        self.permissions = PermissionManager(self.settings, self.scope, self.audit)
        self.workflows = WorkflowEngine(
            tool_manager=self.tools, scope=self.scope, audit=self.audit,
            enforce_scope=self.settings.get("security.scope_mode", "warn") != "off",
        )
        self.monitor = SystemMonitor()
        self.ai = AIAssistant(self.settings, self.catalog)
        self.intel = IntelService(self.settings, self.db)

        # advanced (phase 3-5) services
        self.health = ToolHealth(self.tools)
        self.installer = InstallManager(self.catalog, self.tools)
        self.labs_env = LabManager(self.audit)

    # ------------------------------------------------------------- workspace
    def switch_workspace(self, workspace_id: int) -> dict | None:
        workspace = self.workspaces.set_active(workspace_id)
        if workspace:
            self.scope.set_workspace(workspace["id"])
        return workspace

    def active_workspace_id(self) -> int | None:
        active = self.workspaces.active()
        return active["id"] if active else None

    def attack_surface(self):
        """A fresh AttackSurface bound to the active workspace."""
        from core.attack_surface import AttackSurface
        return AttackSurface(self.db, self.active_workspace_id())

    # --------------------------------------------------------------- startup
    def startup_detect(self) -> dict:
        if self.settings.get("tools.detect_on_startup", True):
            self.tools.detect_all()
        return self.tools.counts()

    def reload_plugins(self) -> None:
        self.plugins.discover()
        self.catalog.merge(self.plugins.enabled_tools())
        self.catalog.merge(self.db.custom_tools())
        self.tools.catalog = self.catalog

    def dashboard_stats(self) -> dict:
        counts = self.tools.counts()
        active = self.workspaces.active()
        ws_id = active["id"] if active else None
        counts["categories"] = len(self.catalog.categories_present())
        counts["scope_entries"] = len(self.scope.entries())
        counts["findings"] = sum(self.db.severity_counts(ws_id).values())
        counts["workspace"] = active["name"] if active else ""
        return counts

    def close(self) -> None:
        try:
            self.db.close()
        except Exception:
            pass
