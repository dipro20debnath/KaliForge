"""Shared pytest fixtures. Every test runs against an isolated KALIFORGE_HOME so
nothing touches the real user config or the system."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _isolate_keyring():
    """Force the secret vault onto its isolated encrypted-file backend during
    tests. Without this, a machine with a working system keyring (e.g. GNOME
    Secret Service on Kali) stores test keys in the *real* keyring, which is not
    isolated by KALIFORGE_HOME — polluting the user's keyring and leaking state
    between tests. We install keyring's fail backend so `SecretVault` falls back
    to the per-test encrypted file under KALIFORGE_HOME."""
    try:
        import keyring
        from keyring.backends import fail
        previous = keyring.get_keyring()
        keyring.set_keyring(fail.Keyring())
    except Exception:  # keyring not installed — nothing to isolate
        yield
        return
    try:
        yield
    finally:
        try:
            keyring.set_keyring(previous)
        except Exception:
            pass


@pytest.fixture()
def kf_home(tmp_path, monkeypatch):
    home = tmp_path / "kfhome"
    home.mkdir()
    monkeypatch.setenv("KALIFORGE_HOME", str(home))
    return home


@pytest.fixture()
def settings(kf_home):
    from core.config import Settings
    return Settings()


@pytest.fixture()
def db(kf_home):
    from database.database import Database
    database = Database(kf_home / "test.db")
    yield database
    database.close()


@pytest.fixture()
def app(kf_home):
    from core.app_manager import AppManager
    manager = AppManager(plugin_dirs=[ROOT / "plugins"])
    manager.startup_detect()
    yield manager
    manager.close()
