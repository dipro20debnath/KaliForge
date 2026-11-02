"""Workspace export / import — package an entire engagement (findings, scope,
assets, notes, checklist, credentials and evidence files) into a single ``.kfw``
zip, and restore it as a new workspace.

Credentials are exported in their already-encrypted form; they only decrypt on
the machine whose vault key wrote them, so a backup moved elsewhere keeps the
secrets unreadable unless the vault key travels with it.
"""
from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

MANIFEST = "workspace.json"
FORMAT_VERSION = 1

# workspace-scoped tables to export (table -> columns kept, minus id/workspace_id)
_TABLES = {
    "scope_targets": ["value", "kind", "note"],
    "findings": ["title", "severity", "cvss", "cve", "host", "port", "service",
                 "description", "evidence", "remediation", "status", "source", "fingerprint"],
    "assets": ["kind", "value", "parent", "meta", "source"],
    "notes": ["title", "body", "tags"],
    "checklist_state": ["template", "item_id", "checked", "note"],
    "credentials": ["host", "service", "username", "secret", "note"],
    "evidence": ["finding_id", "path", "original_path", "sha256", "size", "kind", "note", "tags"],
}


def export_workspace(app, workspace_id: int, out_path: str | Path) -> Path:
    out_path = Path(out_path)
    ws = app.db.workspace(workspace_id)
    if not ws:
        raise ValueError("workspace not found")
    data: dict = {
        "format": FORMAT_VERSION,
        "exported": datetime.now(timezone.utc).isoformat(),
        "workspace": {"name": ws["name"], "client": ws.get("client", ""),
                      "description": ws.get("description", "")},
        "tables": {},
    }
    for table, cols in _TABLES.items():
        rows = app.db.query(
            f"SELECT {', '.join(cols)} FROM {table} WHERE workspace_id IS ?",
            (workspace_id,))
        data["tables"][table] = rows

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST, json.dumps(data, indent=2))
        # bundle evidence files
        for ev in data["tables"].get("evidence", []):
            src = Path(ev.get("path", ""))
            if src.exists():
                zf.write(src, f"evidence/{src.name}")
    return out_path


def import_workspace(app, in_path: str | Path, new_name: str | None = None) -> dict:
    in_path = Path(in_path)
    with zipfile.ZipFile(in_path, "r") as zf:
        manifest = json.loads(zf.read(MANIFEST).decode("utf-8"))
        ws_meta = manifest.get("workspace", {})
        name = new_name or f"{ws_meta.get('name', 'Imported')} (imported)"
        # ensure a unique name
        base, i = name, 2
        while app.db.workspace_by_name(name):
            name = f"{base} {i}"
            i += 1
        workspace = app.workspaces.create(
            name, client=ws_meta.get("client", ""), description=ws_meta.get("description", ""))
        ws_id = workspace["id"]
        ev_dir = Path(workspace["path"]) / "evidence"
        ev_dir.mkdir(parents=True, exist_ok=True)

        tables = manifest.get("tables", {})
        # restore evidence files first, remap paths
        path_map: dict[str, str] = {}
        for name_in_zip in zf.namelist():
            if name_in_zip.startswith("evidence/"):
                target = ev_dir / Path(name_in_zip).name
                with zf.open(name_in_zip) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                path_map[Path(name_in_zip).name] = str(target)

        _restore(app, ws_id, tables, path_map)
    return {"id": ws_id, "name": name,
            "counts": {t: len(rows) for t, rows in manifest.get("tables", {}).items()}}


def _restore(app, ws_id: int, tables: dict, path_map: dict) -> None:
    db = app.db
    for row in tables.get("scope_targets", []):
        db.add_scope(row["value"], row["kind"], ws_id, row.get("note", ""))
    for row in tables.get("findings", []):
        cols = list(row.keys())
        placeholders = ", ".join("?" for _ in cols) + ", ?, ?, ?"
        db.execute(
            f"INSERT INTO findings(workspace_id, {', '.join(cols)}, created, updated) "
            f"VALUES(?, {', '.join('?' for _ in cols)}, ?, ?)",
            [ws_id, *[row[c] for c in cols], _now(), _now()])
    for row in tables.get("assets", []):
        db.execute(
            "INSERT OR IGNORE INTO assets(workspace_id, kind, value, parent, meta, source, created) "
            "VALUES(?, ?, ?, ?, ?, ?, ?)",
            (ws_id, row["kind"], row["value"], row.get("parent", ""),
             row.get("meta", "{}"), row.get("source", ""), _now()))
    for row in tables.get("notes", []):
        db.add_note(row["title"], row.get("body", ""), row.get("tags", ""), ws_id)
    for row in tables.get("checklist_state", []):
        db.set_checklist_item(ws_id, row["template"], row["item_id"],
                              bool(row["checked"]), row.get("note", ""))
    for row in tables.get("credentials", []):
        db.add_credential({"workspace_id": ws_id, "host": row.get("host", ""),
                           "service": row.get("service", ""), "username": row.get("username", ""),
                           "secret": row.get("secret", ""), "note": row.get("note", "")})
    for row in tables.get("evidence", []):
        original = row.get("path", "")
        new_path = path_map.get(Path(original).name, original)
        db.add_evidence({"workspace_id": ws_id, "finding_id": None,
                         "path": new_path, "original_path": row.get("original_path", ""),
                         "sha256": row.get("sha256", ""), "size": row.get("size", 0),
                         "kind": row.get("kind", "file"), "note": row.get("note", ""),
                         "tags": row.get("tags", "")})


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
