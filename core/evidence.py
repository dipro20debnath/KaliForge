"""Evidence manager — copies an artefact into the workspace evidence folder,
records its SHA-256 and metadata, and preserves a tamper-evident record."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from database.database import Database


def sha256_file(path: str | Path, chunk: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


class EvidenceManager:
    def __init__(self, db: Database, workspace_dir: Path | str):
        self.db = db
        self.workspace_dir = Path(workspace_dir)
        self.store = self.workspace_dir / "evidence"
        self.store.mkdir(parents=True, exist_ok=True)

    def add_file(self, src: str | Path, workspace_id: int | None = None,
                 finding_id: int | None = None, note: str = "", tags: str = "") -> dict:
        src = Path(src)
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(src)
        digest = sha256_file(src)
        dest_name = f"{digest[:12]}_{src.name}"
        dest = self.store / dest_name
        if not dest.exists():
            shutil.copy2(src, dest)
        record = {
            "workspace_id": workspace_id,
            "finding_id": finding_id,
            "path": str(dest),
            "original_path": str(src),
            "sha256": digest,
            "size": dest.stat().st_size,
            "kind": _kind_of(src),
            "note": note,
            "tags": tags,
        }
        record["id"] = self.db.add_evidence(record)
        return record

    def verify(self, record: dict) -> bool:
        path = Path(record["path"])
        if not path.exists():
            return False
        return sha256_file(path) == record["sha256"]

    def list(self, workspace_id: int | None) -> list[dict]:
        return self.db.evidence(workspace_id)


def _kind_of(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
        return "screenshot"
    if ext in {".pcap", ".pcapng", ".cap"}:
        return "capture"
    if ext in {".log", ".txt", ".out"}:
        return "log"
    if ext in {".json", ".xml", ".csv"}:
        return "data"
    return "file"
