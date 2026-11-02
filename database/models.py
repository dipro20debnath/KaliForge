"""SQLite schema and light-weight dataclass models for KaliForge."""
from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    client TEXT DEFAULT '',
    description TEXT DEFAULT '',
    path TEXT NOT NULL,
    created TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scope_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER,
    value TEXT NOT NULL,
    kind TEXT NOT NULL,
    note TEXT DEFAULT '',
    created TEXT NOT NULL,
    UNIQUE(workspace_id, value)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    user TEXT,
    workspace_id INTEGER,
    source TEXT,
    tool TEXT,
    command TEXT,
    targets TEXT,
    risk TEXT,
    decision TEXT,
    detail TEXT
);

CREATE TABLE IF NOT EXISTS command_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    command TEXT NOT NULL,
    tool TEXT,
    workspace_id INTEGER
);

CREATE TABLE IF NOT EXISTS favorites (
    tool_id TEXT PRIMARY KEY,
    ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vault (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    command TEXT NOT NULL,
    category TEXT DEFAULT 'General',
    tags TEXT DEFAULT '',
    description TEXT DEFAULT '',
    uses INTEGER DEFAULT 0,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER,
    title TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',
    cvss REAL,
    cve TEXT DEFAULT '',
    host TEXT DEFAULT '',
    port TEXT DEFAULT '',
    service TEXT DEFAULT '',
    description TEXT DEFAULT '',
    evidence TEXT DEFAULT '',
    remediation TEXT DEFAULT '',
    status TEXT DEFAULT 'open',
    source TEXT DEFAULT 'manual',
    fingerprint TEXT,
    created TEXT NOT NULL,
    updated TEXT NOT NULL,
    UNIQUE(workspace_id, fingerprint)
);

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER,
    kind TEXT NOT NULL,
    value TEXT NOT NULL,
    parent TEXT DEFAULT '',
    meta TEXT DEFAULT '{}',
    source TEXT DEFAULT '',
    created TEXT NOT NULL,
    UNIQUE(workspace_id, kind, value, parent)
);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER,
    finding_id INTEGER,
    path TEXT NOT NULL,
    original_path TEXT DEFAULT '',
    sha256 TEXT NOT NULL,
    size INTEGER DEFAULT 0,
    kind TEXT DEFAULT 'file',
    note TEXT DEFAULT '',
    tags TEXT DEFAULT '',
    created TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER,
    title TEXT NOT NULL,
    body TEXT DEFAULT '',
    tags TEXT DEFAULT '',
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS labs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    platform TEXT DEFAULT 'VirtualBox',
    vm_name TEXT DEFAULT '',
    target TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    status TEXT DEFAULT 'unknown',
    last_tested TEXT DEFAULT '',
    created TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_tools (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    created TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cve_cache (
    cve_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    fetched TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id INTEGER,
    workflow TEXT NOT NULL,
    target TEXT,
    status TEXT,
    outdir TEXT,
    started TEXT,
    finished TEXT,
    summary TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);
CREATE INDEX IF NOT EXISTS idx_findings_ws ON findings(workspace_id);
CREATE INDEX IF NOT EXISTS idx_assets_ws ON assets(workspace_id);
"""

SEVERITIES = ["critical", "high", "medium", "low", "info"]
SEVERITY_WEIGHT = {"critical": 10.0, "high": 7.5, "medium": 5.0, "low": 2.5, "info": 0.0}
FINDING_STATUSES = ["open", "confirmed", "remediated", "accepted", "false-positive"]


def severity_from_cvss(score: float | None) -> str:
    """CVSS v3.x qualitative rating scale (FIRST specification, section 5)."""
    if score is None:
        return "info"
    if score >= 9.0:
        return "critical"
    if score >= 7.0:
        return "high"
    if score >= 4.0:
        return "medium"
    if score >= 0.1:
        return "low"
    return "info"


@dataclass
class Finding:
    title: str
    severity: str = "info"
    host: str = ""
    port: str = ""
    service: str = ""
    cve: str = ""
    cvss: float | None = None
    description: str = ""
    evidence: str = ""
    remediation: str = ""
    status: str = "open"
    source: str = "manual"
    id: int | None = None
    workspace_id: int | None = None
    created: str = ""
    updated: str = ""

    def fingerprint(self) -> str:
        return "|".join([self.title.strip().lower(), self.host, str(self.port), self.cve])


@dataclass
class Asset:
    kind: str
    value: str
    parent: str = ""
    meta: dict = field(default_factory=dict)
    source: str = ""
