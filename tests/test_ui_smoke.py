"""Headless UI smoke test — constructs the whole window offscreen and visits
every page. Skips cleanly if a Qt platform plugin can't be initialised."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")


@pytest.fixture()
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_mainwindow_builds_and_navigates(qapp, app):
    from PySide6.QtCore import QEventLoop
    from ui.main_window import MainWindow

    window = MainWindow(app)
    window.resize(1200, 800)
    window.show()
    qapp.processEvents(QEventLoop.AllEvents, 50)

    keys = ["dashboard", "arsenal", "cat:recon", "cat:web", "cat:recon2",
            "vulnerability", "terminal", "workflows", "assistant", "scope",
            "monitor", "vault", "evidence", "plugins", "reports", "settings",
            "attack_surface", "tool_health", "installer", "learning", "lab_env",
            "hosts", "toolkit", "payloads", "importer"]
    for key in keys:
        window.navigate(key)
        qapp.processEvents(QEventLoop.AllEvents, 20)

    assert window.stack.count() == 22
    # the arsenal shows the full catalog with no filter
    window.navigate("arsenal")
    window.arsenal.set_category("all")
    window.arsenal.search.clear()
    qapp.processEvents(QEventLoop.AllEvents, 50)
    assert window.arsenal.flow.count() >= 100

    # rendering produces a non-empty pixmap
    pixmap = window.grab()
    assert not pixmap.isNull()

    window.terminal.shutdown()
    window.close()


def test_scope_roundtrip_in_ui(qapp, app):
    from ui.pages.scope import ScopePage
    page = ScopePage(app)
    page.value_input.setText("10.10.0.0/24")
    page.add_entry()
    assert app.scope.in_scope("10.10.0.5")
    page.test_input.setText("10.10.0.5")
    page.test_target()
    assert "in scope" in page.test_result.text()
