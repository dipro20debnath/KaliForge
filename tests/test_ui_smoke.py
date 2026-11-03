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
            "hosts", "toolkit", "payloads", "importer", "methodology",
            "credentials", "workspaces"]
    for key in keys:
        window.navigate(key)
        qapp.processEvents(QEventLoop.AllEvents, 20)

    assert window.stack.count() == 25
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


def test_workflow_updates_cross_thread(qapp, app):
    """Regression: the workflow engine runs on a worker thread; its step/finish
    callbacks must reach the UI (a worker-thread QTimer.singleShot would not
    fire). The page bridges them with queued signals."""
    import threading
    import time

    from PySide6.QtCore import QEventLoop
    from core.workflow_engine import StepResult, WorkflowRun
    from ui.pages.workflows import WorkflowsPage

    page = WorkflowsPage(app)
    done = {"finished": False}
    page._run_finished.connect(lambda run: done.__setitem__("finished", True))

    def worker():  # emulate the engine's background thread
        page._on_step(StepResult(index=0, tool="nmap", command="nmap x", status="done"))
        page._on_done(WorkflowRun(name="t", target="x", outdir="/tmp"))

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    for _ in range(40):
        qapp.processEvents(QEventLoop.AllEvents, 20)
        time.sleep(0.01)
        if done["finished"]:
            break
    assert page.table.rowCount() >= 1   # step rendered on the UI thread
    assert done["finished"]             # finish delivered to the UI thread


def test_scope_roundtrip_in_ui(qapp, app):
    from ui.pages.scope import ScopePage
    page = ScopePage(app)
    page.value_input.setText("10.10.0.0/24")
    page.add_entry()
    assert app.scope.in_scope("10.10.0.5")
    page.test_input.setText("10.10.0.5")
    page.test_target()
    assert "in scope" in page.test_result.text()
