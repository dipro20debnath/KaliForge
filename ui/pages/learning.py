"""Learning & Practice Mode page — per-tool learning modules plus a live command
explainer that breaks any command into explained parts."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QScrollArea,
                               QTabWidget, QTextBrowser, QVBoxLayout, QWidget)

from core import learning
from ui.widgets.common import Card

_LEVEL_COLOR = {"Beginner": "#2ecc71", "Intermediate": "#ffd23f", "Advanced": "#ff8c1a"}
_ROLE_COLOR = {"program": "#27e0a1", "flag": "#ffd23f", "target": "#ff8c1a",
               "subcommand": "#13c2c2", "value": "#7f9499"}


class LearningPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title = QLabel("Learning & Practice Mode")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        tabs = QTabWidget()
        tabs.addTab(self._modules_tab(), "Tool Lessons")
        tabs.addTab(self._explainer_tab(), "Command Explainer")
        layout.addWidget(tabs, 1)

    # ---------------------------------------------------------------- modules
    def _modules_tab(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        self.tool_list = QListWidget()
        for tool_id in learning.learnable_tool_ids():
            tool = self.app.catalog.get(tool_id)
            name = tool["name"] if tool else tool_id
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, tool_id)
            self.tool_list.addItem(item)
        self.tool_list.currentRowChanged.connect(self._load_modules)
        layout.addWidget(self.tool_list, 1)

        self.modules_scroll = QScrollArea()
        self.modules_scroll.setWidgetResizable(True)
        self.modules_scroll.setFrameShape(QScrollArea.NoFrame)
        self.modules_host = QWidget()
        self.modules_layout = QVBoxLayout(self.modules_host)
        self.modules_layout.addStretch(1)
        self.modules_scroll.setWidget(self.modules_host)
        layout.addWidget(self.modules_scroll, 2)
        if self.tool_list.count():
            self.tool_list.setCurrentRow(0)
        return widget

    def _load_modules(self, row: int) -> None:
        while self.modules_layout.count() > 1:
            item = self.modules_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if row < 0:
            return
        tool_id = self.tool_list.item(row).data(Qt.UserRole)
        for module in learning.modules_for(tool_id):
            card = Card()
            header = QLabel(f"{module['title']}")
            header.setObjectName("CardTitle")
            level = QLabel(module["level"])
            level.setStyleSheet(f"color: {_LEVEL_COLOR.get(module['level'], '#7f9499')}; font-weight: 700;")
            top = QHBoxLayout()
            top.addWidget(header)
            top.addStretch(1)
            top.addWidget(level)
            card.layout().addLayout(top)
            body = QLabel(module["body"])
            body.setWordWrap(True)
            body.setObjectName("PageSub")
            card.layout().addWidget(body)
            if module.get("example"):
                ex = QLabel(module["example"])
                ex.setStyleSheet("background:#0a0e0f; border:1px solid #1d2a2c; "
                                 "border-radius:6px; padding:8px; font-family:'DejaVu Sans Mono';")
                ex.setTextInteractionFlags(Qt.TextSelectableByMouse)
                ex.setWordWrap(True)
                card.layout().addWidget(ex)
            self.modules_layout.insertWidget(self.modules_layout.count() - 1, card)

    # -------------------------------------------------------------- explainer
    def _explainer_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Paste or type a command to see what each part does:"))
        self.explain_input = QLineEdit()
        self.explain_input.setPlaceholderText("nmap -sV -sC 192.168.56.101")
        self.explain_input.textChanged.connect(self._explain)
        layout.addWidget(self.explain_input)
        self.explain_output = QTextBrowser()
        layout.addWidget(self.explain_output, 1)
        return widget

    def _explain(self) -> None:
        command = self.explain_input.text().strip()
        if not command:
            self.explain_output.clear()
            return
        exp = learning.explain(command)
        rows = [f"<p style='color:#7f9499'>{exp.summary}</p>", "<table cellspacing='0' cellpadding='6'>"]
        for part in exp.parts:
            color = _ROLE_COLOR.get(part.role, "#d6e4e6")
            rows.append(
                f"<tr><td style='font-family:monospace;color:{color};font-weight:700'>{_esc(part.token)}</td>"
                f"<td style='color:#56696d'>{part.role}</td>"
                f"<td style='color:#d6e4e6'>{_esc(part.description)}</td></tr>")
        rows.append("</table>")
        self.explain_output.setHtml("\n".join(rows))


def _esc(text: str) -> str:
    import html
    return html.escape(text or "")
