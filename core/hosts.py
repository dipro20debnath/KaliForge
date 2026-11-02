"""Host-centric aggregation — collects everything known about each host in the
active workspace (open ports/services from assets, and findings) into one view.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from database.database import Database
from database.models import SEVERITIES


@dataclass
class HostView:
    host: str
    ports: list[dict] = field(default_factory=list)      # {port, service}
    findings: list[dict] = field(default_factory=list)
    severity_counts: dict = field(default_factory=dict)

    @property
    def top_severity(self) -> str:
        for sev in SEVERITIES:
            if self.severity_counts.get(sev):
                return sev
        return "info"

    @property
    def open_ports(self) -> int:
        return len(self.ports)


def host_overview(db: Database, workspace_id: int | None) -> list[HostView]:
    hosts: dict[str, HostView] = {}

    def ensure(name: str) -> HostView:
        if name not in hosts:
            hosts[name] = HostView(host=name, severity_counts={s: 0 for s in SEVERITIES})
        return hosts[name]

    # ports come from port assets (parented to a host/ip value)
    for asset in db.assets(workspace_id, kind="port"):
        parent = asset.get("parent") or ""
        if not parent:
            continue
        view = ensure(parent)
        meta = asset.get("meta")
        service = ""
        if isinstance(meta, str):
            import json
            try:
                service = json.loads(meta).get("service", "")
            except ValueError:
                service = ""
        elif isinstance(meta, dict):
            service = meta.get("service", "")
        view.ports.append({"port": asset["value"], "service": service})

    # findings grouped by host
    for finding in db.findings(workspace_id):
        host = finding.get("host", "").strip()
        if not host:
            continue
        view = ensure(host)
        view.findings.append(finding)
        sev = finding.get("severity", "info")
        view.severity_counts[sev] = view.severity_counts.get(sev, 0) + 1

    order = {s: i for i, s in enumerate(SEVERITIES)}
    return sorted(hosts.values(),
                  key=lambda h: (order.get(h.top_severity, 9), -h.open_ports, h.host))
