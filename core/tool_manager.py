"""Tool manager — installation detection, version probing, install guidance and
favourites. Detection is cheap (``shutil.which``) and safe to call often; version
probing shells out and is therefore optional / lazy.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field

from tools.catalog import Catalog

_VERSION_RE = re.compile(r"(\d+\.\d+(?:\.\d+)?(?:[\w.\-]*)?)")

# Tools whose version should be read from a non-standard flag.
_VERSION_FLAGS = {
    "nmap": ["--version"], "sqlmap": ["--version"], "hydra": ["-h"],
    "john": ["--help"], "hashcat": ["--version"], "metasploit": ["version"],
    "ffuf": ["-V"], "nuclei": ["-version"], "subfinder": ["-version"],
    "httpx": ["-version"], "amass": ["-version"], "gobuster": ["version"],
}


@dataclass
class ToolStatus:
    tool_id: str
    installed: bool = False
    path: str = ""
    version: str = ""
    builtin: bool = False
    favorite: bool = False
    error: str = ""

    def state(self) -> str:
        if self.builtin:
            return "builtin"
        return "installed" if self.installed else "missing"


class ToolManager:
    def __init__(self, catalog: Catalog, db=None):
        self.catalog = catalog
        self.db = db
        self._status: dict[str, ToolStatus] = {}
        self._favorites: set[str] = set()
        self.refresh_favorites()

    # ------------------------------------------------------------- favorites
    def refresh_favorites(self) -> None:
        if self.db is not None:
            self._favorites = self.db.favorites()

    def is_favorite(self, tool_id: str) -> bool:
        return tool_id in self._favorites

    def toggle_favorite(self, tool_id: str) -> bool:
        if self.db is not None:
            state = self.db.toggle_favorite(tool_id)
        else:
            state = tool_id not in self._favorites
        if state:
            self._favorites.add(tool_id)
        else:
            self._favorites.discard(tool_id)
        if tool_id in self._status:
            self._status[tool_id].favorite = state
        return state

    # ------------------------------------------------------------- detection
    def detect(self, tool: dict) -> ToolStatus:
        tool_id = tool["id"]
        binary = tool.get("binary", "")
        status = ToolStatus(tool_id=tool_id, favorite=self.is_favorite(tool_id))
        if binary == "__builtin__":
            status.builtin = True
            status.installed = True
            status.version = "built-in"
        else:
            path = shutil.which(binary) if binary else None
            if path:
                status.installed = True
                status.path = path
        self._status[tool_id] = status
        return status

    def detect_all(self) -> dict[str, ToolStatus]:
        for tool in self.catalog.all():
            self.detect(tool)
        return self._status

    def status(self, tool_id: str) -> ToolStatus | None:
        if tool_id not in self._status:
            tool = self.catalog.get(tool_id)
            if tool:
                return self.detect(tool)
            return None
        return self._status[tool_id]

    def counts(self) -> dict[str, int]:
        if not self._status:
            self.detect_all()
        installed = sum(1 for s in self._status.values() if s.installed and not s.builtin)
        missing = sum(1 for s in self._status.values() if not s.installed)
        builtin = sum(1 for s in self._status.values() if s.builtin)
        return {
            "total": self.catalog.count(),
            "installed": installed,
            "builtin": builtin,
            "missing": missing,
            "favorites": len(self._favorites),
        }

    # --------------------------------------------------------------- version
    def probe_version(self, tool: dict, timeout: float = 4.0) -> str:
        """Best-effort version string. Shells out, so call off the UI thread."""
        binary = tool.get("binary", "")
        if not binary or binary == "__builtin__":
            return ""
        if not shutil.which(binary):
            return ""
        flags = _VERSION_FLAGS.get(tool["id"], ["--version"])
        for flag in (flags, ["-V"], ["-v"], ["version"]):
            try:
                proc = subprocess.run(
                    [binary, *flag], capture_output=True, text=True,
                    timeout=timeout, check=False,
                )
                blob = (proc.stdout or "") + (proc.stderr or "")
                match = _VERSION_RE.search(blob)
                if match:
                    version = match.group(1)
                    if tool["id"] in self._status:
                        self._status[tool["id"]].version = version
                    return version
            except (subprocess.TimeoutExpired, OSError):
                continue
        return ""

    # --------------------------------------------------------------- install
    @staticmethod
    def install_guide(tool: dict) -> dict:
        """Return a structured, copy-pasteable installation guide. KaliForge
        never installs automatically — it shows the user exactly what to run."""
        package = tool.get("package", "")
        name = tool["name"]
        if package:
            command = f"sudo apt update && sudo apt install -y {package}"
            note = f"{name} ships in the Kali repositories as the '{package}' package."
        else:
            command = ""
            note = (f"{name} is not available as a standard apt package. "
                    f"See the project homepage for installation instructions.")
        steps = []
        if command:
            steps.append(command)
        if tool.get("homepage"):
            steps.append(f"# Homepage: {tool['homepage']}")
        if tool.get("docs"):
            steps.append(f"# Docs: {tool['docs']}")
        return {"command": command, "note": note, "steps": steps,
                "homepage": tool.get("homepage", ""), "docs": tool.get("docs", "")}
