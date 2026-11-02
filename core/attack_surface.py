"""Attack Surface Mapper — builds a relationship graph of the engagement's
assets (domains → subdomains → hosts → ports/services) from the workspace asset
store, and can seed that store from scope, findings and workflow output.

Qt-free: produces a plain node/edge model; the UI handles layout and drawing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from core.scope_manager import classify, host_of
from database.database import Database
from database.models import Asset

# Visual/relationship ordering of asset kinds (root → leaf).
KIND_LEVEL = {"domain": 0, "subdomain": 1, "host": 2, "ip": 2, "url": 3,
              "port": 3, "service": 4}
KIND_ORDER = ["domain", "subdomain", "host", "ip", "url", "port", "service"]

_HOST_IN_OUTPUT = re.compile(r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b")
_IP_IN_OUTPUT = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_PORT_LINE = re.compile(r"^(\d{1,5})/(tcp|udp)\s+(open|open\|filtered)\s+(\S+)", re.M)


@dataclass
class Node:
    id: str
    label: str
    kind: str
    parent: str | None = None
    meta: dict = field(default_factory=dict)

    @property
    def level(self) -> int:
        return KIND_LEVEL.get(self.kind, 2)


@dataclass
class Graph:
    nodes: list[Node] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)  # (parent_id, child_id)

    def roots(self) -> list[Node]:
        child_ids = {c for _, c in self.edges}
        return [n for n in self.nodes if n.id not in child_ids]

    def children_of(self, node_id: str) -> list[Node]:
        kids = [c for p, c in self.edges if p == node_id]
        by_id = {n.id: n for n in self.nodes}
        return [by_id[k] for k in kids if k in by_id]

    def stats(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for node in self.nodes:
            counts[node.kind] = counts.get(node.kind, 0) + 1
        counts["total"] = len(self.nodes)
        return counts


def _node_id(kind: str, value: str, parent: str = "") -> str:
    return f"{kind}:{value}@{parent}" if parent else f"{kind}:{value}"


class AttackSurface:
    def __init__(self, db: Database, workspace_id: int | None):
        self.db = db
        self.workspace_id = workspace_id

    # ------------------------------------------------------------------ seed
    def add(self, kind: str, value: str, parent: str = "", source: str = "manual",
            meta: dict | None = None) -> None:
        value = value.strip()
        if not value:
            return
        self.db.add_asset(Asset(kind=kind, value=value, parent=parent, meta=meta or {},
                                source=source), self.workspace_id)

    def seed_from_scope(self, scope_entries) -> int:
        added = 0
        for entry in scope_entries:
            value = entry.value
            kind = entry.kind
            if kind == "url":
                host = host_of(value)
                self.add("domain", host, source="scope")
                self.add("url", value, parent=host, source="scope")
            elif kind in ("domain", "host"):
                self.add("domain", value, source="scope")
            elif kind in ("ip",):
                self.add("ip", value, source="scope")
            elif kind in ("cidr", "range"):
                self.add("host", value, source="scope", meta={"kind": kind})
            added += 1
        return added

    def seed_from_findings(self) -> int:
        added = 0
        for finding in self.db.findings(self.workspace_id):
            host = finding.get("host", "").strip()
            if not host:
                continue
            kind = "ip" if _IP_IN_OUTPUT.fullmatch(host) else "host"
            self.add(kind, host, source="finding")
            port = finding.get("port", "")
            if port:
                self.add("port", f"{port}", parent=host, source="finding",
                         meta={"service": finding.get("service", "")})
            added += 1
        return added

    def import_text(self, text: str, root: str = "") -> int:
        """Parse hosts/IPs/open-ports out of tool output and add them."""
        added = 0
        for ip in set(_IP_IN_OUTPUT.findall(text)):
            self.add("ip", ip, parent=root, source="import")
            added += 1
        for host in set(_HOST_IN_OUTPUT.findall(text)):
            if _IP_IN_OUTPUT.fullmatch(host):
                continue
            if host.rsplit(".", 1)[-1].lower() in {"txt", "log", "out", "html", "xml"}:
                continue
            self.add("subdomain" if root else "domain", host,
                     parent=root, source="import")
            added += 1
        for port, proto, _state, service in _PORT_LINE.findall(text):
            parent = root or (next(iter(_IP_IN_OUTPUT.findall(text)), ""))
            self.add("port", f"{port}/{proto}", parent=parent, source="import",
                     meta={"service": service})
            added += 1
        return added

    def clear(self) -> None:
        self.db.execute("DELETE FROM assets WHERE workspace_id IS ?", (self.workspace_id,))

    # ------------------------------------------------------------------ build
    def build(self) -> Graph:
        rows = self.db.assets(self.workspace_id)
        graph = Graph()
        seen: set[str] = set()
        values_present = {r["value"] for r in rows}

        for row in rows:
            parent_val = row.get("parent", "") or ""
            nid = _node_id(row["kind"], row["value"], parent_val)
            if nid in seen:
                continue
            seen.add(nid)
            meta = row.get("meta")
            if isinstance(meta, str):
                import json
                try:
                    meta = json.loads(meta)
                except ValueError:
                    meta = {}
            graph.nodes.append(Node(id=nid, label=row["value"], kind=row["kind"],
                                    parent=parent_val or None, meta=meta or {}))

        node_by_value: dict[str, str] = {}
        for node in graph.nodes:
            node_by_value.setdefault(node.label, node.id)

        for node in graph.nodes:
            if node.parent and node.parent in node_by_value:
                graph.edges.append((node_by_value[node.parent], node.id))
        return graph
