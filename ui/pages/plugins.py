"""Plugins & Custom Tool Import — enable/disable plugins and register your own
scripts as tool cards in the arsenal."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QFormLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QMessageBox,
                               QPlainTextEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from core.categories import CATEGORIES


class PluginsPage(QWidget):
    catalog_changed = Signal()

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._build()
        self.refresh_plugins()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title = QLabel("Plugins & Custom Tools")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        tabs = QTabWidget()
        tabs.addTab(self._plugins_tab(), "Plugins")
        tabs.addTab(self._custom_tab(), "Custom Tool Import")
        layout.addWidget(tabs, 1)

    # ---------------------------------------------------------------- plugins
    def _plugins_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        hint = QLabel("Plugins add tool cards and integrations. They are declarative "
                      "(no code runs on load). Drop a plugin folder into your config "
                      "plugins directory and reload.")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        reload_btn = QPushButton("Reload plugins")
        reload_btn.clicked.connect(self._reload)
        layout.addWidget(reload_btn)
        self.plugin_table = QTableWidget(0, 5)
        self.plugin_table.setHorizontalHeaderLabels(["Plugin", "Version", "Tools", "Status", ""])
        self.plugin_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.plugin_table.verticalHeader().setVisible(False)
        self.plugin_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.plugin_table, 1)
        return widget

    def refresh_plugins(self) -> None:
        plugins = list(self.app.plugins.plugins.values())
        self.plugin_table.setRowCount(len(plugins))
        for i, plugin in enumerate(plugins):
            self.plugin_table.setItem(i, 0, QTableWidgetItem(plugin.name))
            self.plugin_table.setItem(i, 1, QTableWidgetItem(plugin.version))
            self.plugin_table.setItem(i, 2, QTableWidgetItem(str(len(plugin.tools))))
            self.plugin_table.setItem(i, 3, QTableWidgetItem("enabled" if plugin.enabled else "disabled"))
            toggle = QPushButton("Disable" if plugin.enabled else "Enable")
            toggle.clicked.connect(lambda _=False, pid=plugin.id, en=not plugin.enabled: self._toggle(pid, en))
            self.plugin_table.setCellWidget(i, 4, toggle)

    def _toggle(self, plugin_id: str, enabled: bool) -> None:
        self.app.plugins.set_enabled(plugin_id, enabled)
        self._reload()

    def _reload(self) -> None:
        self.app.reload_plugins()
        self.refresh_plugins()
        self.catalog_changed.emit()

    # ---------------------------------------------------------------- custom
    def _custom_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        add = QPushButton("＋ Import custom tool")
        add.setObjectName("Primary")
        add.clicked.connect(self._add_custom)
        layout.addWidget(add)
        self.custom_table = QTableWidget(0, 4)
        self.custom_table.setHorizontalHeaderLabels(["ID", "Name", "Category", ""])
        self.custom_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.custom_table.verticalHeader().setVisible(False)
        self.custom_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.custom_table, 1)
        self.refresh_custom()
        return widget

    def refresh_custom(self) -> None:
        rows = self.app.db.custom_tools()
        self._custom_rows = rows
        self.custom_table.setRowCount(len(rows))
        for i, tool in enumerate(rows):
            self.custom_table.setItem(i, 0, QTableWidgetItem(tool.get("id", "")))
            self.custom_table.setItem(i, 1, QTableWidgetItem(tool.get("name", "")))
            self.custom_table.setItem(i, 2, QTableWidgetItem(tool.get("category", "")))
            delete = QPushButton("Remove")
            delete.setObjectName("Ghost")
            delete.clicked.connect(lambda _=False, tid=tool.get("id"): self._del_custom(tid))
            self.custom_table.setCellWidget(i, 3, delete)

    def _add_custom(self) -> None:
        dialog = _CustomToolDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            tool = dialog.tool()
            if not tool["id"] or not tool["name"]:
                return
            self.app.db.save_custom_tool(tool["id"], tool)
            self._reload()
            self.refresh_custom()

    def _del_custom(self, tool_id: str) -> None:
        self.app.db.delete_custom_tool(tool_id)
        self._reload()
        self.refresh_custom()


class _CustomToolDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import custom tool")
        self.setMinimumWidth(480)
        form = QFormLayout(self)
        self.id = QLineEdit()
        self.id.setPlaceholderText("unique-id (lowercase)")
        self.name = QLineEdit()
        self.category = QComboBox()
        for cat in CATEGORIES:
            self.category.addItem(cat["label"], cat["id"])
        self.binary = QLineEdit()
        self.binary.setPlaceholderText("executable name for detection, e.g. mytool")
        self.desc = QLineEdit()
        self.command = QPlainTextEdit()
        self.command.setPlaceholderText("Command template, e.g. mytool -t {target}")
        self.command.setFixedHeight(60)
        form.addRow("ID*", self.id)
        form.addRow("Name*", self.name)
        form.addRow("Category", self.category)
        form.addRow("Binary", self.binary)
        form.addRow("Description", self.desc)
        form.addRow("Command template", self.command)
        buttons = QHBoxLayout()
        ok = QPushButton("Import")
        ok.setObjectName("Primary")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        form.addRow(buttons)

    def tool(self) -> dict:
        tid = self.id.text().strip().lower().replace(" ", "-")
        commands = []
        template = self.command.toPlainText().strip()
        if template:
            commands.append({"label": "Run", "template": template, "scope": "{target}" in template})
        return {
            "id": tid, "name": self.name.text().strip(),
            "category": self.category.currentData(),
            "binary": self.binary.text().strip() or tid,
            "desc": self.desc.text().strip() or "Custom imported tool.",
            "risk": "caution", "lab_only": False, "custom": True,
            "tags": ["custom"], "commands": commands,
        }
