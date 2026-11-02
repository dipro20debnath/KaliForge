"""Installation Manager — identifies missing tools and builds a safe,
copy-pasteable installation plan (KaliForge never installs automatically).

Tools that ship as apt packages are grouped into a single ``apt install`` line;
tools without an apt package are listed separately with their homepage.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.categories import category_label
from tools.catalog import Catalog
from core.tool_manager import ToolManager


@dataclass
class InstallPlan:
    apt_packages: list[str] = field(default_factory=list)
    apt_command: str = ""
    manual: list[dict] = field(default_factory=list)   # {name, homepage, docs}
    selected: list[str] = field(default_factory=list)  # tool ids

    @property
    def is_empty(self) -> bool:
        return not self.apt_packages and not self.manual


class InstallManager:
    def __init__(self, catalog: Catalog, tool_manager: ToolManager):
        self.catalog = catalog
        self.tools = tool_manager

    def missing(self) -> list[dict]:
        out = []
        for tool in self.catalog.all():
            status = self.tools.status(tool["id"])
            if status and not status.installed and not status.builtin:
                out.append(tool)
        out.sort(key=lambda t: (t["category"], t["name"].lower()))
        return out

    def missing_by_category(self) -> dict[str, list[dict]]:
        grouped: dict[str, list[dict]] = {}
        for tool in self.missing():
            grouped.setdefault(category_label(tool["category"]), []).append(tool)
        return grouped

    def plan(self, tool_ids: list[str]) -> InstallPlan:
        plan = InstallPlan(selected=list(tool_ids))
        for tool_id in tool_ids:
            tool = self.catalog.get(tool_id)
            if not tool:
                continue
            package = tool.get("package", "")
            if package:
                if package not in plan.apt_packages:
                    plan.apt_packages.append(package)
            else:
                plan.manual.append({
                    "name": tool["name"],
                    "homepage": tool.get("homepage", ""),
                    "docs": tool.get("docs", ""),
                })
        if plan.apt_packages:
            plan.apt_command = "sudo apt update && sudo apt install -y " + " ".join(sorted(set(plan.apt_packages)))
        return plan

    def plan_all_missing(self) -> InstallPlan:
        return self.plan([t["id"] for t in self.missing()])

    def script(self, plan: InstallPlan) -> str:
        """A commented install script for the selected tools."""
        lines = ["#!/usr/bin/env bash",
                 "# KaliForge — generated installation script",
                 "# Review before running. Requires sudo for apt.",
                 "set -e", ""]
        if plan.apt_command:
            lines.append(plan.apt_command)
            lines.append("")
        if plan.manual:
            lines.append("# The following tools are not standard apt packages —")
            lines.append("# install them manually from their project pages:")
            for item in plan.manual:
                ref = item["homepage"] or item["docs"] or "(see project docs)"
                lines.append(f"#   - {item['name']}: {ref}")
        return "\n".join(lines) + "\n"
