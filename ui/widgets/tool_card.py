"""Tool card used in the Arsenal grid and category pages."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from core.categories import category_label
from ui.widgets.common import Card

_RISK_TAG = {"info": "", "caution": "CAUTION", "dangerous": "LAB-ONLY"}


class ToolCard(Card):
    open_requested = Signal(str)       # tool_id
    details_requested = Signal(str)
    favorite_toggled = Signal(str)

    def __init__(self, tool: dict, status, parent=None):
        super().__init__(parent)
        self.tool_id = tool["id"]
        self.setMinimumWidth(246)
        self.setMaximumWidth(360)
        self.setMinimumHeight(176)
        self.setCursor(Qt.PointingHandCursor)

        top = QHBoxLayout()
        state = status.state() if status else "missing"
        badge = QLabel({"installed": "● Installed", "missing": "○ Missing",
                        "builtin": "◆ Built-in"}.get(state, state))
        badge.setObjectName({"installed": "BadgeInstalled", "missing": "BadgeMissing",
                             "builtin": "BadgeBuiltin"}.get(state, "BadgeMissing"))
        top.addWidget(badge)
        top.addStretch(1)
        self.fav_btn = QPushButton("★" if (status and status.favorite) else "☆")
        self.fav_btn.setObjectName("Ghost")
        self.fav_btn.setFixedWidth(30)
        self.fav_btn.setCursor(Qt.PointingHandCursor)
        self.fav_btn.clicked.connect(lambda: self.favorite_toggled.emit(self.tool_id))
        top.addWidget(self.fav_btn)
        self._layout.addLayout(top)

        name = QLabel(tool["name"])
        name.setObjectName("CardTitle")
        self._layout.addWidget(name)

        meta = QLabel(category_label(tool["category"]) +
                      (f"  ·  {_RISK_TAG[tool['risk']]}" if _RISK_TAG.get(tool["risk"]) else ""))
        meta.setObjectName("Hint")
        self._layout.addWidget(meta)

        desc = QLabel(tool["desc"])
        desc.setObjectName("PageSub")
        desc.setWordWrap(True)
        self._layout.addWidget(desc)
        self._layout.addStretch(1)

        row = QHBoxLayout()
        if state == "missing":
            action = QPushButton("Install Guide")
        else:
            action = QPushButton("Open Tool")
            action.setObjectName("Primary")
        action.clicked.connect(lambda: self.open_requested.emit(self.tool_id))
        details = QPushButton("Details")
        details.setObjectName("Ghost")
        details.clicked.connect(lambda: self.details_requested.emit(self.tool_id))
        row.addWidget(action)
        row.addWidget(details)
        self._layout.addLayout(row)

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        self.details_requested.emit(self.tool_id)
