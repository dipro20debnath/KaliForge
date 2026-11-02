"""Settings — appearance, security guard-rails, AI provider and terminal."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QSpinBox,
                               QTabWidget, QVBoxLayout, QWidget)

from ui.theme import THEMES


class SettingsPage(QWidget):
    theme_changed = Signal(str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.s = app.settings
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        tabs = QTabWidget()
        tabs.addTab(self._appearance_tab(), "Appearance")
        tabs.addTab(self._security_tab(), "Security")
        tabs.addTab(self._ai_tab(), "AI Assistant")
        tabs.addTab(self._terminal_tab(), "Terminal")
        layout.addWidget(tabs, 1)

    # ------------------------------------------------------------- appearance
    def _appearance_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self.theme_box = QComboBox()
        for key, data in THEMES.items():
            self.theme_box.addItem(data["name"], key)
        current = self.s.get("appearance.theme", "kali_neon")
        idx = self.theme_box.findData(current)
        if idx >= 0:
            self.theme_box.setCurrentIndex(idx)
        self.theme_box.currentIndexChanged.connect(self._apply_theme)
        form.addRow("Theme", self.theme_box)

        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 16)
        self.font_spin.setValue(int(self.s.get("appearance.ui_font_size", 10)))
        self.font_spin.valueChanged.connect(
            lambda v: self.s.set("appearance.ui_font_size", v))
        form.addRow("UI font size", self.font_spin)

        self.tips_chk = QCheckBox("Show beginner tips")
        self.tips_chk.setChecked(bool(self.s.get("appearance.show_beginner_tips", True)))
        self.tips_chk.toggled.connect(lambda v: self.s.set("appearance.show_beginner_tips", v))
        form.addRow(self.tips_chk)
        note = QLabel("Theme changes apply immediately; font size applies on next launch.")
        note.setObjectName("Hint")
        form.addRow(note)
        return widget

    def _apply_theme(self) -> None:
        theme = self.theme_box.currentData()
        self.s.set("appearance.theme", theme)
        self.theme_changed.emit(theme)

    # --------------------------------------------------------------- security
    def _security_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self.scope_mode = QComboBox()
        self.scope_mode.addItem("Enforce — block out-of-scope targets", "enforce")
        self.scope_mode.addItem("Warn — confirm out-of-scope targets", "warn")
        self.scope_mode.addItem("Off — no scope checks (not recommended)", "off")
        idx = self.scope_mode.findData(self.s.get("security.scope_mode", "warn"))
        if idx >= 0:
            self.scope_mode.setCurrentIndex(idx)
        self.scope_mode.currentIndexChanged.connect(
            lambda: self.s.set("security.scope_mode", self.scope_mode.currentData()))
        form.addRow("Scope mode", self.scope_mode)

        self._check(form, "Require scope for lab-only tools",
                    "security.require_scope_for_lab_only", True)
        self._check(form, "Confirm destructive commands", "security.confirm_destructive", True)
        self._check(form, "Confirm sudo / privileged commands", "security.confirm_sudo", True)
        self._check(form, "Allow launching as root (not recommended)",
                    "security.allow_root_launch", False)
        self._check(form, "Write audit log of every command", "security.audit_logging", True)
        return widget

    def _check(self, form: QFormLayout, label: str, key: str, default: bool) -> None:
        box = QCheckBox(label)
        box.setChecked(bool(self.s.get(key, default)))
        box.toggled.connect(lambda v, k=key: self.s.set(k, v))
        form.addRow(box)

    # --------------------------------------------------------------- ai
    def _ai_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self.ai_provider = QComboBox()
        self.ai_provider.addItem("Offline rule engine (no key)", "offline")
        self.ai_provider.addItem("Claude API (requires key)", "claude")
        idx = self.ai_provider.findData(self.s.get("ai.provider", "offline"))
        if idx >= 0:
            self.ai_provider.setCurrentIndex(idx)
        self.ai_provider.currentIndexChanged.connect(
            lambda: self.s.set("ai.provider", self.ai_provider.currentData()))
        form.addRow("Provider", self.ai_provider)

        self.ai_key = QLineEdit()
        self.ai_key.setEchoMode(QLineEdit.Password)
        self.ai_key.setPlaceholderText(
            "sk-ant-…  " + ("(key already stored — leave blank to keep)"
                            if self.app.ai.has_key() else "(encrypted at rest)"))
        save_key = QPushButton("Save key")
        save_key.clicked.connect(self._save_key)
        clear_key = QPushButton("Clear")
        clear_key.setObjectName("Ghost")
        clear_key.clicked.connect(self._clear_key)
        key_row = QHBoxLayout()
        key_row.addWidget(self.ai_key, 1)
        key_row.addWidget(save_key)
        key_row.addWidget(clear_key)
        key_wrap = QWidget()
        key_wrap.setLayout(key_row)
        form.addRow("API key", key_wrap)
        self.vault_lbl = QLabel(f"Key store: {self.app.vault.backend}"
                                + (" · key set" if self.app.ai.has_key() else " · no key"))
        self.vault_lbl.setObjectName("Hint")
        form.addRow(self.vault_lbl)

        self.ai_model = QLineEdit(self.s.get("ai.model", "claude-opus-5-5"))
        self.ai_model.editingFinished.connect(
            lambda: self.s.set("ai.model", self.ai_model.text().strip()))
        form.addRow("Model", self.ai_model)
        note = QLabel("The assistant only suggests commands; nothing runs without the "
                      "normal confirmation flow. The key is stored in your user config.")
        note.setObjectName("Hint")
        note.setWordWrap(True)
        form.addRow(note)
        return widget

    def _save_key(self) -> None:
        value = self.ai_key.text().strip()
        if not value:
            return
        backend = self.app.ai.set_api_key(value)
        self.ai_key.clear()
        self.vault_lbl.setText(f"Key store: {backend} · key set")

    def _clear_key(self) -> None:
        self.app.vault.delete(self.app.ai.KEY_NAME)
        self.s.set("ai.api_key", "")
        self.ai_key.clear()
        self.vault_lbl.setText(f"Key store: {self.app.vault.backend} · no key")

    # --------------------------------------------------------------- terminal
    def _terminal_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self.scrollback = QSpinBox()
        self.scrollback.setRange(500, 100000)
        self.scrollback.setSingleStep(500)
        self.scrollback.setValue(int(self.s.get("terminal.scrollback", 10000)))
        self.scrollback.valueChanged.connect(lambda v: self.s.set("terminal.scrollback", v))
        form.addRow("Scrollback lines", self.scrollback)
        self._check(form, "Confirm before closing a terminal with a running process",
                    "terminal.confirm_close_running", True)
        self._check(form, "Record terminal sessions to disk", "terminal.record_sessions", False)
        self._check(form, "Save & restore terminal tab layout between runs",
                    "terminal.restore_last_session", False)
        return widget
