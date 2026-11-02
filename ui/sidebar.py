"""Persistent left navigation."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QLabel, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from core.config import APP_NAME, APP_TAGLINE, APP_VERSION

# (key, label) grouped by section. keys map to stacked page keys.
NAV = [
    ("OVERVIEW", [
        ("dashboard", "Dashboard"),
        ("arsenal", "Tool Arsenal"),
    ]),
    ("DOMAINS", [
        ("cat:recon", "Recon Center"),
        ("cat:web", "Web Security"),
        ("cat:network", "Network Lab"),
        ("vulnerability", "Vulnerability"),
        ("cat:password", "Password Lab"),
        ("cat:wireless", "Wireless Lab"),
        ("cat:forensics", "Digital Forensics"),
        ("cat:reverse", "Reverse Engineering"),
        ("cat:recon2", "OSINT Center"),
    ]),
    ("OPERATE", [
        ("terminal", "Command Center"),
        ("workflows", "Workflows"),
        ("assistant", "AI Assistant"),
        ("scope", "Scope Manager"),
        ("monitor", "System Monitor"),
    ]),
    ("MANAGE", [
        ("vault", "Vault & Notes"),
        ("evidence", "Evidence & Labs"),
        ("reports", "Reports"),
        ("plugins", "Plugins"),
        ("settings", "Settings"),
    ]),
]


class Sidebar(QWidget):
    navigate = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(224)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 18, 10, 14)
        outer.setSpacing(2)

        brand = QLabel(APP_NAME)
        brand.setObjectName("Brand")
        outer.addWidget(brand)
        sub = QLabel(APP_TAGLINE)
        sub.setObjectName("BrandSub")
        sub.setWordWrap(True)
        outer.addWidget(sub)
        pill = QLabel("● SYSTEM ONLINE")
        pill.setObjectName("StatusPill")
        pill.setAlignment(Qt.AlignCenter)
        outer.addWidget(pill)
        outer.addSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        host = QWidget()
        nav_layout = QVBoxLayout(host)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(2)
        for section, items in NAV:
            label = QLabel(section)
            label.setObjectName("NavSection")
            nav_layout.addWidget(label)
            for key, text in items:
                btn = QPushButton(text)
                btn.setObjectName("NavItem")
                btn.setCheckable(True)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda _=False, k=key: self.navigate.emit(k))
                self._group.addButton(btn)
                self._buttons[key] = btn
                nav_layout.addWidget(btn)
        nav_layout.addStretch(1)
        scroll.setWidget(host)
        outer.addWidget(scroll, 1)

        version = QLabel(f"v{APP_VERSION}")
        version.setObjectName("Hint")
        outer.addWidget(version)

    def select(self, key: str) -> None:
        btn = self._buttons.get(key)
        if btn:
            btn.setChecked(True)
