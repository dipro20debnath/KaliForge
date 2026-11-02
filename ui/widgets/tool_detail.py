"""Tool detail dialog — description, status, install guide, command templates
(each buildable/runnable) and documentation links."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPlainTextEdit,
                               QPushButton, QScrollArea, QTabWidget, QVBoxLayout,
                               QWidget)

from core.categories import category_name
from ui.widgets.command_builder_dialog import CommandBuilderDialog
from ui.widgets.common import Card


class ToolDetailDialog(QDialog):
    run_command = Signal(str, str)   # command, tool_id
    install_tool = Signal(str)        # install command to send to terminal

    def __init__(self, app, tool: dict, parent=None):
        super().__init__(parent)
        self.app = app
        self.tool = tool
        self.status = app.tools.status(tool["id"])
        self.setWindowTitle(f"{tool['name']} — details")
        self.setMinimumSize(620, 540)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        box = QVBoxLayout()
        name = QLabel(self.tool["name"])
        name.setObjectName("PageTitle")
        box.addWidget(name)
        meta = QLabel(category_name(self.tool["category"]))
        meta.setObjectName("PageSub")
        box.addWidget(meta)
        header.addLayout(box)
        header.addStretch(1)
        state = self.status.state() if self.status else "missing"
        badge = QLabel({"installed": "● Installed", "missing": "○ Not Installed",
                        "builtin": "◆ Built-in"}.get(state, state))
        badge.setObjectName({"installed": "BadgeInstalled", "missing": "BadgeMissing",
                             "builtin": "BadgeBuiltin"}.get(state, "BadgeMissing"))
        header.addWidget(badge)
        fav = QPushButton("★ Favorited" if (self.status and self.status.favorite) else "☆ Favorite")
        fav.clicked.connect(self._toggle_fav)
        self._fav_btn = fav
        header.addWidget(fav)
        layout.addLayout(header)

        tabs = QTabWidget()
        tabs.addTab(self._overview_tab(), "Overview")
        tabs.addTab(self._commands_tab(), "Commands")
        tabs.addTab(self._install_tab(), "Install / Update")
        layout.addWidget(tabs, 1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        if self.tool.get("docs"):
            docs = QPushButton("Documentation")
            docs.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.tool["docs"])))
            footer.addWidget(docs)
        if self.tool.get("homepage"):
            home = QPushButton("Homepage")
            home.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.tool["homepage"])))
            footer.addWidget(home)
        close = QPushButton("Close")
        close.setObjectName("Ghost")
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        layout.addLayout(footer)

    def _overview_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        desc = QLabel(self.tool["desc"])
        desc.setWordWrap(True)
        layout.addWidget(desc)
        info = []
        if self.status and self.status.path:
            info.append(f"Path: {self.status.path}")
        if self.status and self.status.version:
            info.append(f"Version: {self.status.version}")
        if self.tool.get("package"):
            info.append(f"Package: {self.tool['package']}")
        if self.tool.get("lab_only"):
            info.append("⚠ Lab-only: run only against authorised, in-scope targets.")
        if self.tool.get("tags"):
            info.append("Tags: " + ", ".join(self.tool["tags"]))
        for line in info:
            lbl = QLabel(line)
            lbl.setObjectName("Hint")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
        probe = QPushButton("Probe installed version")
        probe.clicked.connect(self._probe_version)
        self._version_lbl = QLabel("")
        self._version_lbl.setObjectName("Hint")
        layout.addWidget(probe)
        layout.addWidget(self._version_lbl)
        layout.addStretch(1)
        return widget

    def _commands_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        host = QWidget()
        layout = QVBoxLayout(host)
        commands = self.tool.get("commands", [])
        if not commands:
            layout.addWidget(QLabel("This tool has no preset command templates."))
        for cmd in commands:
            card = Card()
            card.layout().addWidget(_bold(cmd["label"]))
            tmpl = QLabel(cmd["template"])
            tmpl.setObjectName("Hint")
            tmpl.setWordWrap(True)
            card.layout().addWidget(tmpl)
            row = QHBoxLayout()
            build = QPushButton("Build & Run")
            build.setObjectName("Primary")
            build.clicked.connect(lambda _=False, t=cmd["template"]: self._build_command(t))
            row.addWidget(build)
            row.addStretch(1)
            card.layout().addLayout(row)
            layout.addWidget(card)
        layout.addStretch(1)
        scroll.setWidget(host)
        return scroll

    def _install_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        guide = self.app.tools.install_guide(self.tool)
        note = QLabel(guide["note"])
        note.setWordWrap(True)
        layout.addWidget(note)
        if guide["command"]:
            box = QPlainTextEdit(guide["command"])
            box.setReadOnly(True)
            box.setFixedHeight(60)
            layout.addWidget(box)
            run = QPushButton("Run install command in terminal")
            run.setObjectName("Primary")
            run.clicked.connect(lambda: self.install_tool.emit(guide["command"]))
            layout.addWidget(run)
        warn = QLabel("KaliForge never installs software automatically — review the "
                      "command above and run it yourself.")
        warn.setObjectName("Hint")
        warn.setWordWrap(True)
        layout.addWidget(warn)
        layout.addStretch(1)
        return widget

    # ------------------------------------------------------------------ slots
    def _toggle_fav(self) -> None:
        state = self.app.tools.toggle_favorite(self.tool["id"])
        self._fav_btn.setText("★ Favorited" if state else "☆ Favorite")

    def _probe_version(self) -> None:
        self._version_lbl.setText("Probing…")
        version = self.app.tools.probe_version(self.tool)
        self._version_lbl.setText(f"Version: {version}" if version else "Version not detected.")

    def _build_command(self, template: str) -> None:
        defaults = {}
        entries = self.app.scope.entries()
        if entries:
            first = entries[0].value
            defaults = {"target": first, "host": first, "domain": first,
                        "url": first if first.startswith("http") else f"http://{first}"}
        dialog = CommandBuilderDialog(template, defaults, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            command = dialog.command()
            if command:
                self.run_command.emit(command, self.tool["id"])
                self.accept()


def _bold(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("CardTitle")
    return lbl
