#!/usr/bin/env python3
"""KaliForge — Cybersecurity Command Center.

Entry point. Constructs the backend (AppManager), then the Qt UI. Running as
root is refused by default (a security tool should drop privilege), overridable
in Settings.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def _warn_if_root(settings) -> None:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        if not settings.get("security.allow_root_launch", False):
            print("⚠  KaliForge is running as root. For safety it is designed to run "
                  "as a normal user; individual commands can request sudo when needed.\n"
                  "   Enable 'Allow launching as root' in Settings to silence this.",
                  file=sys.stderr)


def main() -> int:
    from core.app_manager import AppManager
    from core.config import plugins_dir

    bundled_plugins = BASE_DIR / "plugins"
    app_manager = AppManager(plugin_dirs=[bundled_plugins, plugins_dir()])
    app_manager.startup_detect()
    # merge any user custom tools saved in the DB
    app_manager.catalog.merge(app_manager.db.custom_tools())
    _warn_if_root(app_manager.settings)

    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFont
    from core.config import APP_NAME
    from ui.main_window import MainWindow

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName(APP_NAME)
    qt_app.setOrganizationName("KaliForge")
    qt_app.setFont(QFont("Inter", int(app_manager.settings.get("appearance.ui_font_size", 10))))

    window = MainWindow(app_manager)
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
