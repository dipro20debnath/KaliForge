"""AI Command Assistant — natural-language → command suggestions. Works fully
offline; uses the Anthropic API when a key is configured in Settings."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from ui.async_task import run_async
from ui.widgets.common import Card


class AssistantPage(QWidget):
    run_command = Signal(str, str)   # command, tool_id

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title = QLabel("AI Command Assistant")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        self.mode_lbl = QLabel("")
        self.mode_lbl.setObjectName("Hint")
        layout.addWidget(self.mode_lbl)

        row = QHBoxLayout()
        self.prompt = QLineEdit()
        self.prompt.setPlaceholderText("e.g. 'find live hosts on 192.168.56.0/24' or "
                                       "'enumerate subdomains of example.com'")
        self.prompt.returnPressed.connect(self.ask)
        ask = QPushButton("Ask")
        ask.setObjectName("Primary")
        ask.clicked.connect(self.ask)
        row.addWidget(self.prompt, 1)
        row.addWidget(ask)
        layout.addLayout(row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.host = QWidget()
        self.results = QVBoxLayout(self.host)
        self.results.addStretch(1)
        self.scroll.setWidget(self.host)
        layout.addWidget(self.scroll, 1)
        self._update_mode()

    def _update_mode(self) -> None:
        if self.app.ai.provider() == "claude" and self.app.ai.has_key():
            self.mode_lbl.setText("Mode: Claude API (online) — suggestions are reviewed before running.")
        else:
            self.mode_lbl.setText("Mode: offline rule engine — no network, no API key needed. "
                                  "Add a key in Settings to enable the Claude API.")

    def showEvent(self, event):  # noqa: N802
        self._update_mode()
        super().showEvent(event)

    def ask(self) -> None:
        prompt = self.prompt.text().strip()
        if not prompt:
            return
        self._clear()
        self._add_note("Thinking…")
        scope_hint = ", ".join(e.value for e in self.app.scope.entries())
        run_async(self.app.ai.ask, self._show, lambda e: self._show_error(e), prompt, scope_hint)

    def _show(self, response) -> None:
        self._clear()
        if response.error and not response.suggestions:
            self._add_note(f"Error: {response.error}")
        if response.text and not response.suggestions:
            self._add_note(response.text)
        for sug in response.suggestions:
            self._add_suggestion(sug)
        if response.error and response.suggestions:
            self._add_note(f"(online lookup failed: {response.error} — showing offline suggestions)")
        self._update_mode()

    def _show_error(self, err: str) -> None:
        self._clear()
        self._add_note(f"Error: {err}")

    def _add_suggestion(self, sug) -> None:
        card = Card()
        cmd = QLabel(sug.command)
        cmd.setObjectName("CardTitle")
        cmd.setWordWrap(True)
        cmd.setTextInteractionFlags(Qt.TextSelectableByMouse)
        card.layout().addWidget(cmd)
        if sug.rationale:
            why = QLabel(sug.rationale)
            why.setObjectName("Hint")
            why.setWordWrap(True)
            card.layout().addWidget(why)
        row = QHBoxLayout()
        run = QPushButton("Build & Run")
        run.setObjectName("Primary")
        run.clicked.connect(lambda _=False, c=sug.command, t=sug.tool_id: self.run_command.emit(c, t))
        src = QLabel(f"source: {sug.source}")
        src.setObjectName("Hint")
        row.addWidget(run)
        row.addStretch(1)
        row.addWidget(src)
        card.layout().addLayout(row)
        self.results.insertWidget(self.results.count() - 1, card)

    def _add_note(self, text: str) -> None:
        lbl = QLabel(text)
        lbl.setObjectName("PageSub")
        lbl.setWordWrap(True)
        self.results.insertWidget(self.results.count() - 1, lbl)

    def _clear(self) -> None:
        while self.results.count() > 1:
            item = self.results.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
