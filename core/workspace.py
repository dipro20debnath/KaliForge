"""Workspace manager — each engagement/investigation gets an isolated folder
(evidence, output, reports, notes) and its own scope and findings in the DB."""
from __future__ import annotations

import re
from pathlib import Path

from core.config import Settings, workspaces_root
from database.database import Database


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-").lower()
    return slug or "workspace"


class WorkspaceManager:
    def __init__(self, db: Database, settings: Settings):
        self.db = db
        self.settings = settings
        self.root = workspaces_root(settings)
        self._active: dict | None = None
        self.ensure_default()

    def ensure_default(self) -> dict:
        existing = self.db.workspace_by_name("Default")
        if existing:
            self._active = existing
            return existing
        workspace = self.create("Default", description="Default workspace")
        return workspace

    def create(self, name: str, client: str = "", description: str = "") -> dict:
        path = self.root / _slug(name)
        for sub in ("evidence", "output", "reports", "notes"):
            (path / sub).mkdir(parents=True, exist_ok=True)
        existing = self.db.workspace_by_name(name)
        if existing:
            return existing
        ws_id = self.db.create_workspace(name, str(path), client, description)
        workspace = self.db.workspace(ws_id)
        self._active = workspace
        return workspace

    def list(self) -> list[dict]:
        return self.db.workspaces()

    def active(self) -> dict:
        if self._active is None:
            self._active = self.ensure_default()
        return self._active

    def set_active(self, workspace_id: int) -> dict | None:
        workspace = self.db.workspace(workspace_id)
        if workspace:
            self._active = workspace
            self.settings.set("workspace.active", workspace["name"])
        return workspace

    def path(self, sub: str = "") -> Path:
        base = Path(self.active()["path"])
        return base / sub if sub else base

    def output_dir(self) -> Path:
        path = self.path("output")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def reports_dir(self) -> Path:
        path = self.path("reports")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def delete(self, workspace_id: int) -> None:
        workspace = self.db.workspace(workspace_id)
        if workspace and workspace["name"] == "Default":
            raise ValueError("the Default workspace cannot be deleted")
        self.db.delete_workspace(workspace_id)
        if self._active and self._active["id"] == workspace_id:
            self._active = self.ensure_default()
