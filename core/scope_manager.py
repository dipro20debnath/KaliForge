"""Scope manager — the authorised-target gate.

Before any command that touches a remote target is run, its targets are checked
against the engagement scope. This is what keeps KaliForge an *authorised*
testing tool: lab-only tools refuse to run against anything outside the scope.

Scope entries are stored per workspace in the DB and matched here. Supported
entry kinds:
    ip        single IPv4/IPv6 address
    cidr      network range (e.g. 192.168.56.0/24)
    domain    a domain; matches the domain and any subdomain
    url       scheme://host[:port]/...; matched on host
    range     "a - b" inclusive IPv4 range
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass

_PRIVATE_HINT = re.compile(r"^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|127\.)")
_HOST_RE = re.compile(r"[a-zA-Z0-9.\-]+")


def classify(value: str) -> str:
    """Best-effort classification of a scope / target token."""
    value = value.strip()
    if "-" in value and "/" not in value and _looks_like_ip_range(value):
        return "range"
    if "/" in value and not value.startswith(("http://", "https://")):
        try:
            ipaddress.ip_network(value, strict=False)
            return "cidr"
        except ValueError:
            pass
    if value.startswith(("http://", "https://")):
        return "url"
    try:
        ipaddress.ip_address(value)
        return "ip"
    except ValueError:
        pass
    if "." in value:
        return "domain"
    return "host"


def _looks_like_ip_range(value: str) -> bool:
    parts = [p.strip() for p in value.split("-")]
    if len(parts) != 2:
        return False
    try:
        ipaddress.ip_address(parts[0])
        ipaddress.ip_address(parts[1])
        return True
    except ValueError:
        return False


def host_of(value: str) -> str:
    """Extract a host/domain from a URL or bare token."""
    value = value.strip()
    if value.startswith(("http://", "https://")):
        rest = value.split("://", 1)[1]
        rest = rest.split("/", 1)[0]
        rest = rest.split("@")[-1]
        rest = rest.split(":")[0]
        return rest
    return value


@dataclass
class ScopeEntry:
    value: str
    kind: str

    def matches(self, target: str) -> bool:
        target = target.strip()
        t_host = host_of(target)
        if self.kind == "ip":
            return self._match_ip(t_host)
        if self.kind == "cidr":
            return self._match_cidr(t_host)
        if self.kind == "range":
            return self._match_range(t_host)
        if self.kind in ("domain", "host"):
            return self._match_domain(t_host)
        if self.kind == "url":
            return host_of(self.value).lower() == t_host.lower()
        return False

    def _match_ip(self, target: str) -> bool:
        try:
            return ipaddress.ip_address(target) == ipaddress.ip_address(self.value)
        except ValueError:
            return target.lower() == self.value.lower()

    def _match_cidr(self, target: str) -> bool:
        try:
            net = ipaddress.ip_network(self.value, strict=False)
            return ipaddress.ip_address(target) in net
        except ValueError:
            return False

    def _match_range(self, target: str) -> bool:
        try:
            lo_s, hi_s = [p.strip() for p in self.value.split("-")]
            lo, hi, t = (ipaddress.ip_address(lo_s), ipaddress.ip_address(hi_s),
                         ipaddress.ip_address(target))
            return lo <= t <= hi
        except ValueError:
            return False

    def _match_domain(self, target: str) -> bool:
        target = target.lower().rstrip(".")
        base = self.value.lower().rstrip(".")
        return target == base or target.endswith("." + base)


class ScopeManager:
    def __init__(self, db=None, workspace_id: int | None = None):
        self.db = db
        self.workspace_id = workspace_id
        self._adhoc: list[ScopeEntry] = []

    # ------------------------------------------------------------- mutation
    def set_workspace(self, workspace_id: int | None) -> None:
        self.workspace_id = workspace_id

    def add(self, value: str, kind: str | None = None, note: str = "") -> ScopeEntry:
        value = value.strip()
        kind = kind or classify(value)
        if self.db is not None:
            self.db.add_scope(value, kind, self.workspace_id, note)
        else:
            self._adhoc.append(ScopeEntry(value, kind))
        return ScopeEntry(value, kind)

    def remove(self, scope_id: int) -> None:
        if self.db is not None:
            self.db.remove_scope(scope_id)

    def clear_adhoc(self) -> None:
        self._adhoc.clear()

    # ------------------------------------------------------------- querying
    def entries(self) -> list[ScopeEntry]:
        if self.db is not None:
            return [ScopeEntry(r["value"], r["kind"]) for r in self.db.scope(self.workspace_id)]
        return list(self._adhoc)

    def raw_entries(self) -> list[dict]:
        if self.db is not None:
            return self.db.scope(self.workspace_id)
        return [{"id": i, "value": e.value, "kind": e.kind, "note": ""} for i, e in enumerate(self._adhoc)]

    def is_empty(self) -> bool:
        return not self.entries()

    def in_scope(self, target: str) -> bool:
        target = host_of(target.strip())
        if not target:
            return False
        return any(entry.matches(target) for entry in self.entries())

    def check_targets(self, targets: list[str]) -> tuple[list[str], list[str]]:
        """Return (in_scope, out_of_scope) for a list of candidate targets."""
        allowed, denied = [], []
        for target in targets:
            (allowed if self.in_scope(target) else denied).append(target)
        return allowed, denied

    @staticmethod
    def is_private(target: str) -> bool:
        host = host_of(target)
        try:
            return ipaddress.ip_address(host).is_private
        except ValueError:
            return bool(_PRIVATE_HINT.match(host))
