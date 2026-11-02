"""Application paths and persistent settings for KaliForge.

Settings are layered:
  1. ``config.json`` shipped next to ``main.py`` (defaults, read-only)
  2. ``~/.config/kaliforge/settings.json`` (user overrides, written by the UI)

Every user-writable path honours the XDG base-directory spec. Setting the
``KALIFORGE_HOME`` environment variable relocates *all* runtime data into one
folder, which is used by the test-suite and is handy for portable installs.
"""
from __future__ import annotations

import copy
import json
import os
import threading
from pathlib import Path
from typing import Any

APP_NAME = "KaliForge"
APP_SLUG = "kaliforge"
APP_VERSION = "1.4.1"
APP_TAGLINE = "One Interface. Every Security Workflow."

BASE_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = BASE_DIR / "tools"
WORKFLOWS_DIR = BASE_DIR / "workflows"
ASSETS_DIR = BASE_DIR / "assets"
DEFAULT_CONFIG_FILE = BASE_DIR / "config.json"


def _home_override() -> Path | None:
    value = os.environ.get("KALIFORGE_HOME")
    return Path(value).expanduser() if value else None


def config_dir() -> Path:
    override = _home_override()
    if override:
        path = override / "config"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        path = base / APP_SLUG
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir() -> Path:
    override = _home_override()
    if override:
        path = override / "data"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        path = base / APP_SLUG
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def plugins_dir() -> Path:
    path = config_dir() / "plugins"
    path.mkdir(parents=True, exist_ok=True)
    return path


def sessions_dir() -> Path:
    path = data_dir() / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class Settings:
    """Thread-safe dotted-key settings store (``settings.get('terminal.font_size')``)."""

    def __init__(self, defaults_file: Path = DEFAULT_CONFIG_FILE, user_file: Path | None = None):
        self._lock = threading.RLock()
        self.defaults_file = defaults_file
        self.user_file = user_file or (config_dir() / "settings.json")
        self._defaults = self._read_json(defaults_file)
        self._user = self._read_json(self.user_file)
        self._merged = _deep_merge(self._defaults, self._user)

    @staticmethod
    def _read_json(path: Path) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            node: Any = self._merged
            for part in key.split("."):
                if not isinstance(node, dict) or part not in node:
                    return default
                node = node[part]
            return copy.deepcopy(node)

    def set(self, key: str, value: Any, save: bool = True) -> None:
        with self._lock:
            for target in (self._user, self._merged):
                node = target
                parts = key.split(".")
                for part in parts[:-1]:
                    if not isinstance(node.get(part), dict):
                        node[part] = {}
                    node = node[part]
                node[parts[-1]] = copy.deepcopy(value)
            if save:
                self.save()

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._user = {}
            else:
                node = self._user
                parts = key.split(".")
                for part in parts[:-1]:
                    node = node.get(part, {})
                if isinstance(node, dict):
                    node.pop(parts[-1], None)
            self._merged = _deep_merge(self._defaults, self._user)
            self.save()

    def save(self) -> None:
        with self._lock:
            self.user_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.user_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(self._user, handle, indent=2, sort_keys=True)
            os.replace(tmp, self.user_file)
            try:
                os.chmod(self.user_file, 0o600)
            except OSError:
                pass

    def as_dict(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._merged)


def workspaces_root(settings: Settings) -> Path:
    override = _home_override()
    default = (override / "workspaces") if override else (Path.home() / "KaliForge" / "workspaces")
    path = Path(settings.get("workspace.root") or default).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path
