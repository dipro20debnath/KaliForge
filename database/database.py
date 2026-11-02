"""Thin, thread-safe SQLite wrapper used by every KaliForge manager."""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from core.config import data_dir
from database.models import SCHEMA, SCHEMA_VERSION, Asset, Finding, severity_from_cvss


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Database:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else data_dir() / "kaliforge.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(SCHEMA)
        self.set_meta("schema_version", str(SCHEMA_VERSION))
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    # ------------------------------------------------------------------ core
    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, tuple(params))
            self._conn.commit()
            return cur

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        with self._lock:
            return [dict(row) for row in self._conn.execute(sql, tuple(params)).fetchall()]

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> dict | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql: str, params: Iterable[Any] = ()) -> Any:
        with self._lock:
            row = self._conn.execute(sql, tuple(params)).fetchone()
            return row[0] if row else None

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ------------------------------------------------------------------ meta
    def set_meta(self, key: str, value: str) -> None:
        self.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def get_meta(self, key: str, default: str | None = None) -> str | None:
        value = self.scalar("SELECT value FROM meta WHERE key=?", (key,))
        return default if value is None else value

    # ------------------------------------------------------------ favorites
    def favorites(self) -> set[str]:
        return {row["tool_id"] for row in self.query("SELECT tool_id FROM favorites")}

    def toggle_favorite(self, tool_id: str) -> bool:
        if tool_id in self.favorites():
            self.execute("DELETE FROM favorites WHERE tool_id=?", (tool_id,))
            return False
        self.execute("INSERT INTO favorites(tool_id, ts) VALUES(?, ?)", (tool_id, utcnow()))
        return True

    # ------------------------------------------------------------- history
    def add_history(self, command: str, tool: str | None = None, workspace_id: int | None = None) -> None:
        self.execute(
            "INSERT INTO command_history(ts, command, tool, workspace_id) VALUES(?, ?, ?, ?)",
            (utcnow(), command, tool, workspace_id),
        )

    def history(self, limit: int = 500, tool: str | None = None) -> list[dict]:
        if tool:
            return self.query(
                "SELECT * FROM command_history WHERE tool=? ORDER BY id DESC LIMIT ?",
                (tool, limit),
            )
        return self.query("SELECT * FROM command_history ORDER BY id DESC LIMIT ?", (limit,))

    # ----------------------------------------------------------------- audit
    def add_audit(self, entry: dict) -> None:
        self.execute(
            "INSERT INTO audit_log(ts, user, workspace_id, source, tool, command, targets, risk, decision, detail) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry.get("ts", utcnow()),
                entry.get("user", ""),
                entry.get("workspace_id"),
                entry.get("source", ""),
                entry.get("tool", ""),
                entry.get("command", ""),
                entry.get("targets", ""),
                entry.get("risk", ""),
                entry.get("decision", ""),
                entry.get("detail", ""),
            ),
        )

    def audit(self, limit: int = 1000) -> list[dict]:
        return self.query("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))

    # ------------------------------------------------------------- workspaces
    def create_workspace(self, name: str, path: str, client: str = "", description: str = "") -> int:
        cur = self.execute(
            "INSERT INTO workspaces(name, client, description, path, created) VALUES(?, ?, ?, ?, ?)",
            (name, client, description, path, utcnow()),
        )
        return int(cur.lastrowid)

    def workspaces(self) -> list[dict]:
        return self.query("SELECT * FROM workspaces ORDER BY name")

    def workspace(self, workspace_id: int) -> dict | None:
        return self.query_one("SELECT * FROM workspaces WHERE id=?", (workspace_id,))

    def workspace_by_name(self, name: str) -> dict | None:
        return self.query_one("SELECT * FROM workspaces WHERE name=?", (name,))

    def delete_workspace(self, workspace_id: int) -> None:
        self.execute("DELETE FROM workspaces WHERE id=?", (workspace_id,))

    # ------------------------------------------------------------------ scope
    def add_scope(self, value: str, kind: str, workspace_id: int | None, note: str = "") -> None:
        self.execute(
            "INSERT OR IGNORE INTO scope_targets(workspace_id, value, kind, note, created) VALUES(?, ?, ?, ?, ?)",
            (workspace_id, value, kind, note, utcnow()),
        )

    def remove_scope(self, scope_id: int) -> None:
        self.execute("DELETE FROM scope_targets WHERE id=?", (scope_id,))

    def scope(self, workspace_id: int | None) -> list[dict]:
        return self.query(
            "SELECT * FROM scope_targets WHERE workspace_id IS ? OR workspace_id=? ORDER BY value",
            (workspace_id, workspace_id),
        )

    # --------------------------------------------------------------- findings
    def upsert_finding(self, finding: Finding) -> int:
        if finding.cvss is not None and finding.severity in (None, "", "info"):
            finding.severity = severity_from_cvss(finding.cvss)
        now = utcnow()
        fp = finding.fingerprint()
        existing = self.query_one(
            "SELECT id FROM findings WHERE workspace_id IS ? AND fingerprint=?",
            (finding.workspace_id, fp),
        )
        if existing:
            self.execute(
                "UPDATE findings SET severity=?, cvss=?, description=?, evidence=?, remediation=?, "
                "service=?, status=?, updated=? WHERE id=?",
                (finding.severity, finding.cvss, finding.description, finding.evidence,
                 finding.remediation, finding.service, finding.status, now, existing["id"]),
            )
            return int(existing["id"])
        cur = self.execute(
            "INSERT INTO findings(workspace_id, title, severity, cvss, cve, host, port, service, "
            "description, evidence, remediation, status, source, fingerprint, created, updated) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (finding.workspace_id, finding.title, finding.severity, finding.cvss, finding.cve,
             finding.host, finding.port, finding.service, finding.description, finding.evidence,
             finding.remediation, finding.status, finding.source, fp, now, now),
        )
        return int(cur.lastrowid)

    def findings(self, workspace_id: int | None, status: str | None = None) -> list[dict]:
        sql = "SELECT * FROM findings WHERE workspace_id IS ?"
        params: list[Any] = [workspace_id]
        if status:
            sql += " AND status=?"
            params.append(status)
        order = (
            " ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
            "WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END, id DESC"
        )
        return self.query(sql + order, params)

    def set_finding_status(self, finding_id: int, status: str) -> None:
        self.execute("UPDATE findings SET status=?, updated=? WHERE id=?", (status, utcnow(), finding_id))

    def delete_finding(self, finding_id: int) -> None:
        self.execute("DELETE FROM findings WHERE id=?", (finding_id,))

    def severity_counts(self, workspace_id: int | None) -> dict[str, int]:
        rows = self.query(
            "SELECT severity, COUNT(*) AS n FROM findings WHERE workspace_id IS ? GROUP BY severity",
            (workspace_id,),
        )
        return {row["severity"]: row["n"] for row in rows}

    # ----------------------------------------------------------------- assets
    def add_asset(self, asset: Asset, workspace_id: int | None) -> None:
        self.execute(
            "INSERT OR IGNORE INTO assets(workspace_id, kind, value, parent, meta, source, created) "
            "VALUES(?, ?, ?, ?, ?, ?, ?)",
            (workspace_id, asset.kind, asset.value, asset.parent,
             json.dumps(asset.meta), asset.source, utcnow()),
        )

    def assets(self, workspace_id: int | None, kind: str | None = None) -> list[dict]:
        if kind:
            return self.query(
                "SELECT * FROM assets WHERE workspace_id IS ? AND kind=? ORDER BY value",
                (workspace_id, kind),
            )
        return self.query("SELECT * FROM assets WHERE workspace_id IS ? ORDER BY kind, value", (workspace_id,))

    # ----------------------------------------------------------------- vault
    def add_vault(self, title: str, command: str, category: str = "General",
                  tags: str = "", description: str = "") -> int:
        now = utcnow()
        cur = self.execute(
            "INSERT INTO vault(title, command, category, tags, description, created, updated) "
            "VALUES(?, ?, ?, ?, ?, ?, ?)",
            (title, command, category, tags, description, now, now),
        )
        return int(cur.lastrowid)

    def vault(self, search: str = "") -> list[dict]:
        if search:
            like = f"%{search}%"
            return self.query(
                "SELECT * FROM vault WHERE title LIKE ? OR command LIKE ? OR tags LIKE ? OR category LIKE ? "
                "ORDER BY uses DESC, title",
                (like, like, like, like),
            )
        return self.query("SELECT * FROM vault ORDER BY uses DESC, title")

    def delete_vault(self, vault_id: int) -> None:
        self.execute("DELETE FROM vault WHERE id=?", (vault_id,))

    def bump_vault(self, vault_id: int) -> None:
        self.execute("UPDATE vault SET uses = uses + 1, updated=? WHERE id=?", (utcnow(), vault_id))

    # ----------------------------------------------------------------- notes
    def add_note(self, title: str, body: str = "", tags: str = "", workspace_id: int | None = None) -> int:
        now = utcnow()
        cur = self.execute(
            "INSERT INTO notes(workspace_id, title, body, tags, created, updated) VALUES(?, ?, ?, ?, ?, ?)",
            (workspace_id, title, body, tags, now, now),
        )
        return int(cur.lastrowid)

    def update_note(self, note_id: int, title: str, body: str, tags: str = "") -> None:
        self.execute(
            "UPDATE notes SET title=?, body=?, tags=?, updated=? WHERE id=?",
            (title, body, tags, utcnow(), note_id),
        )

    def notes(self, workspace_id: int | None) -> list[dict]:
        return self.query("SELECT * FROM notes WHERE workspace_id IS ? ORDER BY updated DESC", (workspace_id,))

    def delete_note(self, note_id: int) -> None:
        self.execute("DELETE FROM notes WHERE id=?", (note_id,))

    # ------------------------------------------------------------------ labs
    def add_lab(self, name: str, platform: str = "VirtualBox", vm_name: str = "",
                target: str = "", notes: str = "") -> int:
        cur = self.execute(
            "INSERT INTO labs(name, platform, vm_name, target, notes, created) VALUES(?, ?, ?, ?, ?, ?)",
            (name, platform, vm_name, target, notes, utcnow()),
        )
        return int(cur.lastrowid)

    def labs(self) -> list[dict]:
        return self.query("SELECT * FROM labs ORDER BY name")

    def delete_lab(self, lab_id: int) -> None:
        self.execute("DELETE FROM labs WHERE id=?", (lab_id,))

    # ------------------------------------------------------------- evidence
    def add_evidence(self, record: dict) -> int:
        cur = self.execute(
            "INSERT INTO evidence(workspace_id, finding_id, path, original_path, sha256, size, kind, note, tags, created) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record.get("workspace_id"), record.get("finding_id"), record["path"],
             record.get("original_path", ""), record["sha256"], record.get("size", 0),
             record.get("kind", "file"), record.get("note", ""), record.get("tags", ""), utcnow()),
        )
        return int(cur.lastrowid)

    def evidence(self, workspace_id: int | None) -> list[dict]:
        return self.query("SELECT * FROM evidence WHERE workspace_id IS ? ORDER BY id DESC", (workspace_id,))

    def delete_evidence(self, evidence_id: int) -> None:
        self.execute("DELETE FROM evidence WHERE id=?", (evidence_id,))

    # ------------------------------------------------------------ custom tools
    def save_custom_tool(self, tool_id: str, data: dict) -> None:
        self.execute(
            "INSERT INTO custom_tools(id, data, created) VALUES(?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
            (tool_id, json.dumps(data), utcnow()),
        )

    def custom_tools(self) -> list[dict]:
        out = []
        for row in self.query("SELECT * FROM custom_tools ORDER BY id"):
            try:
                out.append(json.loads(row["data"]))
            except ValueError:
                continue
        return out

    def delete_custom_tool(self, tool_id: str) -> None:
        self.execute("DELETE FROM custom_tools WHERE id=?", (tool_id,))

    # -------------------------------------------------------------- cve cache
    def cache_cve(self, cve_id: str, data: dict) -> None:
        self.execute(
            "INSERT INTO cve_cache(cve_id, data, fetched) VALUES(?, ?, ?) "
            "ON CONFLICT(cve_id) DO UPDATE SET data=excluded.data, fetched=excluded.fetched",
            (cve_id, json.dumps(data), utcnow()),
        )

    def cached_cve(self, cve_id: str) -> dict | None:
        row = self.query_one("SELECT * FROM cve_cache WHERE cve_id=?", (cve_id,))
        if not row:
            return None
        try:
            return {"data": json.loads(row["data"]), "fetched": row["fetched"]}
        except ValueError:
            return None

    # ---------------------------------------------------------- workflow runs
    def start_workflow_run(self, workflow: str, target: str, outdir: str, workspace_id: int | None) -> int:
        cur = self.execute(
            "INSERT INTO workflow_runs(workspace_id, workflow, target, status, outdir, started) "
            "VALUES(?, ?, ?, 'running', ?, ?)",
            (workspace_id, workflow, target, outdir, utcnow()),
        )
        return int(cur.lastrowid)

    def finish_workflow_run(self, run_id: int, status: str, summary: str = "") -> None:
        self.execute(
            "UPDATE workflow_runs SET status=?, finished=?, summary=? WHERE id=?",
            (status, utcnow(), summary, run_id),
        )

    def workflow_runs(self, workspace_id: int | None) -> list[dict]:
        return self.query("SELECT * FROM workflow_runs WHERE workspace_id IS ? ORDER BY id DESC", (workspace_id,))

    # ---------------------------------------------------------- checklist
    def set_checklist_item(self, workspace_id: int | None, template: str,
                           item_id: str, checked: bool, note: str = "") -> None:
        self.execute(
            "INSERT INTO checklist_state(workspace_id, template, item_id, checked, note, updated) "
            "VALUES(?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(workspace_id, template, item_id) DO UPDATE SET "
            "checked=excluded.checked, note=excluded.note, updated=excluded.updated",
            (workspace_id, template, item_id, 1 if checked else 0, note, utcnow()),
        )

    def checklist_state(self, workspace_id: int | None, template: str) -> dict[str, dict]:
        rows = self.query(
            "SELECT * FROM checklist_state WHERE workspace_id IS ? AND template=?",
            (workspace_id, template),
        )
        return {r["item_id"]: {"checked": bool(r["checked"]), "note": r["note"]} for r in rows}

    # -------------------------------------------------------- credentials
    def add_credential(self, record: dict) -> int:
        cur = self.execute(
            "INSERT INTO credentials(workspace_id, host, service, username, secret, note, created) "
            "VALUES(?, ?, ?, ?, ?, ?, ?)",
            (record.get("workspace_id"), record.get("host", ""), record.get("service", ""),
             record.get("username", ""), record.get("secret", ""), record.get("note", ""), utcnow()),
        )
        return int(cur.lastrowid)

    def credentials(self, workspace_id: int | None) -> list[dict]:
        return self.query("SELECT * FROM credentials WHERE workspace_id IS ? ORDER BY id DESC", (workspace_id,))

    def delete_credential(self, cred_id: int) -> None:
        self.execute("DELETE FROM credentials WHERE id=?", (cred_id,))
