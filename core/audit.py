"""Audit logging — every command decision is written to the DB and a rotating
JSONL file so there is a tamper-evident local trail of who ran what, when."""
from __future__ import annotations

import getpass
import json
import threading
from datetime import datetime, timezone

from core.config import logs_dir


class AuditLog:
    def __init__(self, db=None, enabled: bool = True):
        self.db = db
        self.enabled = enabled
        self._lock = threading.Lock()
        self._file = logs_dir() / "audit.jsonl"
        try:
            self.user = getpass.getuser()
        except Exception:
            self.user = "unknown"

    def record(self, *, source: str, tool: str = "", command: str = "",
               targets: str = "", risk: str = "", decision: str = "",
               detail: str = "", workspace_id: int | None = None) -> dict:
        entry = {
            "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "user": self.user,
            "workspace_id": workspace_id,
            "source": source,
            "tool": tool,
            "command": command,
            "targets": targets,
            "risk": risk,
            "decision": decision,
            "detail": detail,
        }
        if not self.enabled:
            return entry
        with self._lock:
            try:
                with open(self._file, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(entry) + "\n")
            except OSError:
                pass
            if self.db is not None:
                try:
                    self.db.add_audit(entry)
                except Exception:
                    pass
        return entry

    def tail(self, limit: int = 200) -> list[dict]:
        if self.db is not None:
            return self.db.audit(limit)
        out: list[dict] = []
        try:
            with open(self._file, "r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue
        except OSError:
            return []
        return out[-limit:][::-1]
