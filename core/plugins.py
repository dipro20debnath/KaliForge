"""Plugin architecture.

A plugin is a directory with a ``plugin.json`` manifest and optionally a
``tools.json`` adding custom tool cards to the catalog. This gives KaliForge a
forward-compatible extension point (new tool categories / integrations) without
touching the core. Plugins are declarative by default — no code is executed on
load — which keeps the attack surface of the dashboard itself small.

Manifest:
    {
      "id": "my-plugin",
      "name": "My Plugin",
      "version": "1.0.0",
      "author": "...",
      "description": "...",
      "tools": "tools.json"        # optional, relative path
    }
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from core.config import plugins_dir


@dataclass
class Plugin:
    id: str
    name: str
    path: Path
    version: str = "0.0.0"
    author: str = ""
    description: str = ""
    tools: list[dict] = field(default_factory=list)
    enabled: bool = True
    error: str = ""


class PluginManager:
    def __init__(self, settings=None, extra_dirs: list[Path] | None = None):
        self.settings = settings
        self.dirs = [plugins_dir()]
        if extra_dirs:
            self.dirs.extend(Path(d) for d in extra_dirs)
        self.plugins: dict[str, Plugin] = {}

    def enabled_ids(self) -> set[str]:
        if self.settings:
            return set(self.settings.get("plugins.enabled", []) or [])
        return set()

    def discover(self) -> list[Plugin]:
        self.plugins.clear()
        enabled = self.enabled_ids()
        for directory in self.dirs:
            if not directory.exists():
                continue
            for manifest in sorted(directory.glob("*/plugin.json")):
                plugin = self._load(manifest)
                if plugin is None:
                    continue
                # if an allow-list exists, honour it; otherwise default enabled
                if enabled:
                    plugin.enabled = plugin.id in enabled
                self.plugins[plugin.id] = plugin
        return list(self.plugins.values())

    def _load(self, manifest_path: Path) -> Plugin | None:
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        pid = data.get("id") or manifest_path.parent.name
        plugin = Plugin(
            id=pid,
            name=data.get("name", pid),
            path=manifest_path.parent,
            version=data.get("version", "0.0.0"),
            author=data.get("author", ""),
            description=data.get("description", ""),
        )
        tools_ref = data.get("tools")
        if isinstance(tools_ref, list):
            plugin.tools = tools_ref
        elif isinstance(tools_ref, str):
            tools_file = plugin.path / tools_ref
            try:
                loaded = json.loads(tools_file.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    plugin.tools = loaded
            except (OSError, ValueError) as exc:
                plugin.error = f"tools file error: {exc}"
        return plugin

    def enabled_tools(self) -> list[dict]:
        """All custom tool cards contributed by enabled plugins."""
        out: list[dict] = []
        for plugin in self.plugins.values():
            if plugin.enabled:
                for tool in plugin.tools:
                    record = dict(tool)
                    record.setdefault("custom", True)
                    record["plugin"] = plugin.id
                    out.append(record)
        return out

    def set_enabled(self, plugin_id: str, enabled: bool) -> None:
        if plugin_id in self.plugins:
            self.plugins[plugin_id].enabled = enabled
        if self.settings:
            current = set(self.settings.get("plugins.enabled", []) or [])
            if enabled:
                current.add(plugin_id)
            else:
                current.discard(plugin_id)
            self.settings.set("plugins.enabled", sorted(current))
