"""Dashboard / Home — stat tiles, quick access, live system monitor and recent
activity."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from core.system_monitor import human_bytes
from database.models import SEVERITIES
from ui.theme import palette, severity_color
from ui.widgets.charts import BarChart, DonutChart, Legend
from ui.widgets.common import Card, Meter, StatCard

QUICK = [
    ("Recon", "recon"), ("Web Audit", "web"), ("Network", "network"),
    ("Password", "password"), ("Forensics", "forensics"), ("Terminal", "__terminal__"),
]


class DashboardPage(QWidget):
    navigate = Signal(str)          # category id or special token
    open_page = Signal(str)         # page key

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._build()
        self._timer = QTimer(self)
        self._timer.setInterval(int(self.app.settings.get("monitor.interval_ms", 1000)))
        self._timer.timeout.connect(self.refresh_monitor)

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        head = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("PageTitle")
        sub = QLabel("Cybersecurity Command Center — system online")
        sub.setObjectName("PageSub")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        head.addLayout(title_box)
        head.addStretch(1)
        layout.addLayout(head)

        # stat cards
        self.cards: dict[str, StatCard] = {}
        grid = QGridLayout()
        grid.setSpacing(14)
        defs = [
            ("total", "Tools Available", "in the arsenal"),
            ("installed", "Installed", "detected on this host"),
            ("missing", "Not Installed", "install guide available"),
            ("categories", "Categories", "security domains"),
        ]
        for col, (key, label, caption) in enumerate(defs):
            card = StatCard("—", label, caption)
            self.cards[key] = card
            grid.addWidget(card, 0, col)
        layout.addLayout(grid)

        # charts row
        charts = QHBoxLayout()
        charts.setSpacing(14)
        sev_card = Card()
        sev_card.layout().addWidget(_h("Findings by Severity"))
        donut_row = QHBoxLayout()
        self.sev_donut = DonutChart()
        donut_row.addWidget(self.sev_donut, 1)
        sev_card.layout().addLayout(donut_row)
        self.sev_legend = Legend()
        sev_card.layout().addWidget(self.sev_legend)
        charts.addWidget(sev_card, 1)

        tools_card = Card()
        tools_card.layout().addWidget(_h("Tool Arsenal Status"))
        self.tools_bar = BarChart()
        tools_card.layout().addWidget(self.tools_bar)
        charts.addWidget(tools_card, 1)
        layout.addLayout(charts)

        # quick access
        quick_card = Card()
        quick_card.layout().addWidget(_h("Quick Access"))
        row = QHBoxLayout()
        row.setSpacing(10)
        for label, token in QUICK:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, t=token: self._quick(t))
            row.addWidget(btn)
        row.addStretch(1)
        quick_card.layout().addLayout(row)
        layout.addWidget(quick_card)

        # monitor + activity side by side
        split = QHBoxLayout()
        split.setSpacing(14)

        self.monitor_card = Card()
        self.monitor_card.layout().addWidget(_h("System Monitor · LIVE"))
        self.cpu_meter = Meter("CPU Usage")
        self.ram_meter = Meter("RAM Usage")
        self.disk_meter = Meter("Disk Usage")
        self.monitor_card.layout().addWidget(self.cpu_meter)
        self.monitor_card.layout().addWidget(self.ram_meter)
        self.monitor_card.layout().addWidget(self.disk_meter)
        self.proc_lbl = QLabel("Processes: —")
        self.proc_lbl.setObjectName("Hint")
        self.monitor_card.layout().addWidget(self.proc_lbl)
        self.monitor_card.layout().addStretch(1)
        split.addWidget(self.monitor_card, 1)

        self.activity_card = Card()
        self.activity_card.layout().addWidget(_h("Recent Activity"))
        self.activity_box = QVBoxLayout()
        self.activity_card.layout().addLayout(self.activity_box)
        self.activity_card.layout().addStretch(1)
        split.addWidget(self.activity_card, 1)
        layout.addLayout(split)
        layout.addStretch(1)

    def _quick(self, token: str) -> None:
        if token == "__terminal__":
            self.open_page.emit("terminal")
        else:
            self.navigate.emit(token)

    # --------------------------------------------------------------- refresh
    def showEvent(self, event):  # noqa: N802
        self.refresh()
        self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event):  # noqa: N802
        self._timer.stop()
        super().hideEvent(event)

    def refresh(self) -> None:
        stats = self.app.dashboard_stats()
        for key, card in self.cards.items():
            card.set_value(stats.get(key, "—"))
        self.refresh_charts(stats)
        self.refresh_monitor()
        self.refresh_activity()

    def refresh_charts(self, stats: dict) -> None:
        theme = self.app.settings.get("appearance.theme", "kali_neon")
        pal = palette(theme)
        self.sev_donut.set_theme(pal["panel"], pal["text"], pal["bg"])
        self.tools_bar.set_theme(pal["bg_alt"], pal["text"], pal["text_dim"])
        counts = self.app.db.severity_counts(self.app.active_workspace_id())
        segments, legend = [], []
        for sev in SEVERITIES:
            n = counts.get(sev, 0)
            color = severity_color(theme, sev)
            if n:
                segments.append((sev, n, color))
            legend.append((f"{sev} {n}", color))
        total = sum(counts.get(s, 0) for s in SEVERITIES)
        self.sev_donut.set_data(segments, str(total))
        self.sev_legend.set_items(legend)
        pal = {"installed": "#2ecc71", "builtin": "#3fa9ff", "missing": "#ff8c1a"}
        self.tools_bar.set_data([
            ("Installed", stats.get("installed", 0), pal["installed"]),
            ("Built-in", stats.get("builtin", 0), pal["builtin"]),
            ("Missing", stats.get("missing", 0), pal["missing"]),
        ])

    def refresh_monitor(self) -> None:
        sample = self.app.monitor.sample()
        if not sample.available:
            self.cpu_meter.set_value(0, "n/a")
            self.ram_meter.set_value(0, "n/a")
            self.disk_meter.set_value(0, "n/a")
            self.proc_lbl.setText("System metrics unavailable (psutil not installed)")
            return
        self.cpu_meter.set_value(sample.cpu_percent, f"{sample.cpu_percent:.0f}%")
        self.ram_meter.set_value(
            sample.mem_percent,
            f"{human_bytes(sample.mem_used)} / {human_bytes(sample.mem_total)}")
        self.disk_meter.set_value(
            sample.disk_percent,
            f"{human_bytes(sample.disk_used)} / {human_bytes(sample.disk_total)}")
        load = " ".join(f"{x:.2f}" for x in sample.load_avg)
        self.proc_lbl.setText(f"Processes: {sample.process_count}   ·   Load: {load}")

    def refresh_activity(self) -> None:
        while self.activity_box.count():
            item = self.activity_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        rows = self.app.audit.tail(8)
        if not rows:
            empty = QLabel("No activity yet — launch a tool or run a command.")
            empty.setObjectName("Hint")
            self.activity_box.addWidget(empty)
            return
        for row in rows:
            ts = (row.get("ts", "") or "")[11:19]
            text = f"{ts}  ·  {row.get('source', '')}  ·  {(row.get('command') or row.get('tool') or '')[:46]}"
            lbl = QLabel(text)
            lbl.setObjectName("Hint")
            self.activity_box.addWidget(lbl)


def _h(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("CardTitle")
    return lbl
