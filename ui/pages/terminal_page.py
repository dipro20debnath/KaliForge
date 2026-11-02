"""Integrated Command Center — multi-tab PTY terminal with a scope-aware
command bar, profiles, output export and a split view."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QInputDialog,
                               QLabel, QLineEdit, QMessageBox, QPushButton,
                               QSplitter, QTabWidget, QToolButton, QVBoxLayout,
                               QWidget)

from core.config import sessions_dir
from core.terminal_manager import TerminalSession
from ui.widgets.terminal_view import TerminalView


class TerminalPane(QWidget):
    """One terminal tab = possibly split into 1-2 sessions side by side."""

    def __init__(self, app, parent=None, record: bool = False, cwd: str | None = None):
        super().__init__(parent)
        self.app = app
        self.record = record
        self._cwd = cwd
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(self.splitter, 1)
        self.views: list[TerminalView] = []
        self._focused: TerminalView | None = None
        self.add_view()

    def cwd(self) -> str:
        return self._cwd or str(self.app.workspaces.path("output"))

    def _profile(self) -> dict:
        name = self.app.settings.get("terminal.default_profile", "Default")
        for prof in self.app.settings.get("terminal.profiles", []) or []:
            if prof.get("name") == name:
                return prof
        return {"shell": "", "font_family": "DejaVu Sans Mono", "font_size": 11}

    def add_view(self) -> TerminalView:
        if len(self.views) >= 2:
            return self._focused or self.views[0]
        prof = self._profile()
        cwd = self._cwd or (str(self.app.workspaces.path("output"))
                            if hasattr(self.app, "workspaces") else None)
        self._cwd = cwd
        record_path = None
        if self.record:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            record_path = str(sessions_dir() / f"rec_{stamp}_{len(self.views)}.log")
        session = TerminalSession(
            shell=prof.get("shell") or None,
            cwd=cwd,
            scrollback=int(self.app.settings.get("terminal.scrollback", 10000)),
            record_path=record_path,
        )
        session.start()
        view = TerminalView(session, prof.get("font_family", "DejaVu Sans Mono"),
                            int(prof.get("font_size", 11)))
        self.splitter.addWidget(view)
        self.views.append(view)
        self._focused = view
        return view

    def focused_view(self) -> TerminalView | None:
        widget = self.focusWidget()
        if isinstance(widget, TerminalView):
            self._focused = widget
        return self._focused or (self.views[0] if self.views else None)

    def run_command(self, command: str) -> None:
        view = self.focused_view()
        if view and view.session.is_alive():
            view.session.send_line(command)
            view.setFocus()

    def close_all(self) -> None:
        for view in self.views:
            try:
                view.session.terminate()
            except Exception:
                pass


class TerminalPage(QWidget):
    status_message = Signal(str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Command Center")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)

        self.profile_box = QComboBox()
        for prof in self.app.settings.get("terminal.profiles", []) or []:
            self.profile_box.addItem(prof.get("name", "Default"))
        current = self.app.settings.get("terminal.default_profile", "Default")
        idx = self.profile_box.findText(current)
        if idx >= 0:
            self.profile_box.setCurrentIndex(idx)
        self.profile_box.currentTextChanged.connect(
            lambda name: self.app.settings.set("terminal.default_profile", name))
        header.addWidget(QLabel("Profile:"))
        header.addWidget(self.profile_box)

        self.record_btn = QToolButton()
        self.record_btn.setText("⏺ Record")
        self.record_btn.setCheckable(True)
        self.record_btn.setChecked(bool(self.app.settings.get("terminal.record_sessions", False)))
        self.record_btn.toggled.connect(self._toggle_record)
        header.addWidget(self.record_btn)

        for text, slot, name in [
            ("＋ Tab", self.new_tab, "Primary"),
            ("⬌ Split", self.split_current, "Ghost"),
            ("⇩ Export", self.export_output, "Ghost"),
            ("💾 Save", self.save_session, "Ghost"),
            ("↺ Restore", self.restore_session, "Ghost"),
            ("✕ Close", self.close_tab, "Ghost"),
        ]:
            btn = QPushButton(text)
            btn.setObjectName(name)
            btn.clicked.connect(slot)
            header.addWidget(btn)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_index)
        layout.addWidget(self.tabs, 1)

        bar = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Type a command and press Enter — it runs in the focused terminal…")
        self.cmd_input.returnPressed.connect(self._send_from_bar)
        send = QPushButton("Run")
        send.setObjectName("Primary")
        send.clicked.connect(self._send_from_bar)
        bar.addWidget(self.cmd_input, 1)
        bar.addWidget(send)
        layout.addLayout(bar)

        self._recording = self.record_btn.isChecked()
        if self.app.settings.get("terminal.restore_last_session", False):
            if not self.restore_session(silent=True):
                self.new_tab()
        else:
            self.new_tab()

    # ------------------------------------------------------------------ tabs
    def new_tab(self, cwd: str | None = None) -> TerminalPane:
        pane = TerminalPane(self.app, record=self._recording, cwd=cwd)
        index = self.tabs.addTab(pane, f"Terminal {self.tabs.count() + 1}")
        self.tabs.setCurrentIndex(index)
        return pane

    def _toggle_record(self, on: bool) -> None:
        self._recording = on
        self.app.settings.set("terminal.record_sessions", on)
        self.status_message.emit(
            "Recording new terminals to session logs." if on else "Recording off.")

    def current_pane(self) -> TerminalPane | None:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, TerminalPane) else None

    def split_current(self) -> None:
        pane = self.current_pane()
        if pane:
            if len(pane.views) >= 2:
                self.status_message.emit("Terminal already split (max 2 panes).")
                return
            pane.add_view()

    def close_tab(self) -> None:
        self._close_index(self.tabs.currentIndex())

    def _close_index(self, index: int) -> None:
        if index < 0:
            return
        pane = self.tabs.widget(index)
        if isinstance(pane, TerminalPane):
            running = any(v.session.is_alive() for v in pane.views)
            if running and self.app.settings.get("terminal.confirm_close_running", True):
                reply = QMessageBox.question(
                    self, "Close terminal", "A process may still be running. Close anyway?")
                if reply != QMessageBox.Yes:
                    return
            pane.close_all()
        self.tabs.removeTab(index)
        if self.tabs.count() == 0:
            self.new_tab()

    # --------------------------------------------------------------- command
    def run_command(self, command: str, focus: bool = True) -> None:
        pane = self.current_pane() or self.new_tab()
        pane.run_command(command)
        if focus:
            self.cmd_input.clearFocus()
        self.app.audit.record(source="terminal", command=command, decision="sent")
        self.app.db.add_history(command, workspace_id=self.app.active_workspace_id())

    def _send_from_bar(self) -> None:
        command = self.cmd_input.text().strip()
        if not command:
            return
        self.run_command(command)
        self.cmd_input.clear()

    def export_output(self) -> None:
        pane = self.current_pane()
        if not pane:
            return
        view = pane.focused_view()
        if not view:
            return
        default = str(self.app.workspaces.path("output") / "terminal_export.txt")
        path, _ = QFileDialog.getSaveFileName(self, "Export terminal output", default,
                                              "Text (*.txt);;Log (*.log)")
        if path:
            view.session.export_output(path)
            self.status_message.emit(f"Output exported to {path}")

    # --------------------------------------------------------------- sessions
    def _layout(self) -> dict:
        tabs = []
        for i in range(self.tabs.count()):
            pane = self.tabs.widget(i)
            if isinstance(pane, TerminalPane):
                tabs.append({"cwd": pane.cwd(), "panes": len(pane.views)})
        return {"tabs": tabs}

    def _session_path(self, name: str = "last_session") -> Path:
        return sessions_dir() / f"{name}.json"

    def save_session(self, name: str | None = None, silent: bool = False) -> None:
        if name is None and not silent:
            name, ok = QInputDialog.getText(self, "Save session", "Session name:",
                                            text="last_session")
            if not ok or not name.strip():
                return
            name = name.strip()
        path = self._session_path(name or "last_session")
        try:
            path.write_text(json.dumps(self._layout(), indent=2), encoding="utf-8")
        except OSError:
            return
        if not silent:
            self.status_message.emit(f"Session layout saved to {path.name}")

    def restore_session(self, name: str = "last_session", silent: bool = False) -> bool:
        path = self._session_path(name)
        if not path.exists():
            if not silent:
                self.status_message.emit("No saved session found.")
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        tabs = data.get("tabs", [])
        if not tabs:
            return False
        # clear existing tabs
        while self.tabs.count():
            pane = self.tabs.widget(0)
            if isinstance(pane, TerminalPane):
                pane.close_all()
            self.tabs.removeTab(0)
        for tab in tabs:
            pane = self.new_tab(cwd=tab.get("cwd"))
            if tab.get("panes", 1) >= 2:
                pane.add_view()
        if not silent:
            self.status_message.emit(f"Restored {len(tabs)} terminal tab(s).")
        return True

    def shutdown(self) -> None:
        if self.app.settings.get("terminal.restore_last_session", False):
            self.save_session(silent=True)
        for i in range(self.tabs.count()):
            pane = self.tabs.widget(i)
            if isinstance(pane, TerminalPane):
                pane.close_all()
