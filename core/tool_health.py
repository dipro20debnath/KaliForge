"""Tool Health Monitor — checks installed tools for presence, version and their
runtime dependencies, producing a health status per tool.

Dependencies are declared in :data:`DEPENDENCIES` (tool id → list of binaries
that must also be present). Health levels:
    ok        installed, version detected, deps satisfied
    degraded  installed but version unknown or a dependency is missing
    missing   not installed
    builtin   shipped with the OS / KaliForge
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field

from core.tool_manager import ToolManager

# tool id -> extra binaries it needs at runtime
DEPENDENCIES: dict[str, list[str]] = {
    "metasploit": ["ruby"],
    "msfvenom": ["ruby"],
    "wpscan": ["ruby"],
    "zsteg": ["ruby"],
    "aircrack-ng": ["airmon-ng"],
    "airodump-ng": ["airmon-ng"],
    "wifite": ["aircrack-ng"],
    "objection": ["frida"],
    "jadx": ["java"],
    "ghidra": ["java"],
    "burpsuite": ["java"],
    "zaproxy": ["java"],
    "mobsf": ["docker"],
    "dradis": ["docker"],
    "photorec": ["testdisk"],
    "volatility": ["python3"],
}


@dataclass
class HealthReport:
    tool_id: str
    name: str
    status: str = "missing"        # ok | degraded | missing | builtin
    installed: bool = False
    version: str = ""
    missing_deps: list[str] = field(default_factory=list)
    notes: str = ""


class ToolHealth:
    def __init__(self, tool_manager: ToolManager):
        self.tools = tool_manager

    def check(self, tool: dict, probe_version: bool = True) -> HealthReport:
        status = self.tools.status(tool["id"])
        report = HealthReport(tool_id=tool["id"], name=tool["name"])
        if status and status.builtin:
            report.status = "builtin"
            report.installed = True
            report.version = status.version or "built-in"
            return report
        if not status or not status.installed:
            report.status = "missing"
            report.notes = "not installed"
            return report

        report.installed = True
        if probe_version:
            report.version = status.version or self.tools.probe_version(tool)
        else:
            report.version = status.version

        for dep in DEPENDENCIES.get(tool["id"], []):
            if not shutil.which(dep):
                report.missing_deps.append(dep)

        if report.missing_deps:
            report.status = "degraded"
            report.notes = "missing dependencies: " + ", ".join(report.missing_deps)
        elif not report.version:
            report.status = "degraded"
            report.notes = "version could not be determined"
        else:
            report.status = "ok"
        return report

    def check_installed(self, catalog, probe_version: bool = True) -> list[HealthReport]:
        """Health report for every installed/built-in tool."""
        reports = []
        for tool in catalog.all():
            status = self.tools.status(tool["id"])
            if status and (status.installed or status.builtin):
                reports.append(self.check(tool, probe_version=probe_version))
        order = {"degraded": 0, "ok": 1, "builtin": 2, "missing": 3}
        reports.sort(key=lambda r: (order.get(r.status, 9), r.name.lower()))
        return reports

    def summary(self, reports: list[HealthReport]) -> dict[str, int]:
        out = {"ok": 0, "degraded": 0, "builtin": 0, "missing": 0}
        for r in reports:
            out[r.status] = out.get(r.status, 0) + 1
        return out
