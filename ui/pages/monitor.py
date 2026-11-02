"""System Resource Monitor — live CPU/RAM/disk/network meters plus a top-process
table."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from core.system_monitor import human_bytes
from ui.widgets.common import Card, Meter


class MonitorPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._last_net = None
        self._build()
        self._timer = QTimer(self)
        self._timer.setInterval(int(self.app.settings.get("monitor.interval_ms", 1000)))
        self._timer.timeout.connect(self.refresh)

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title = QLabel("System Resource Monitor")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        meters = Card()
        self.cpu = Meter("CPU")
        self.ram = Meter("Memory")
        self.swap = Meter("Swap")
        self.disk = Meter("Disk (/)")
        for m in (self.cpu, self.ram, self.swap, self.disk):
            meters.layout().addWidget(m)
        self.net_lbl = QLabel("Network: —")
        self.net_lbl.setObjectName("Hint")
        meters.layout().addWidget(self.net_lbl)
        layout.addWidget(meters)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["PID", "Process", "CPU %", "MEM %", "User"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

    def showEvent(self, event):  # noqa: N802
        self.refresh()
        self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event):  # noqa: N802
        self._timer.stop()
        super().hideEvent(event)

    def refresh(self) -> None:
        sample = self.app.monitor.sample()
        if not sample.available:
            self.cpu.set_value(0, "n/a")
            self.net_lbl.setText("psutil not available")
            return
        self.cpu.set_value(sample.cpu_percent, f"{sample.cpu_percent:.0f}%")
        self.ram.set_value(sample.mem_percent,
                           f"{human_bytes(sample.mem_used)} / {human_bytes(sample.mem_total)}")
        self.swap.set_value(sample.swap_percent, f"{sample.swap_percent:.0f}%")
        self.disk.set_value(sample.disk_percent,
                            f"{human_bytes(sample.disk_used)} / {human_bytes(sample.disk_total)}")
        if self._last_net is not None:
            ds = sample.net_sent - self._last_net[0]
            dr = sample.net_recv - self._last_net[1]
            self.net_lbl.setText(f"Network: ↑ {human_bytes(max(0, ds))}/s   ↓ {human_bytes(max(0, dr))}/s")
        self._last_net = (sample.net_sent, sample.net_recv)

        procs = self.app.monitor.top_processes(12)
        self.table.setRowCount(len(procs))
        for i, p in enumerate(procs):
            self.table.setItem(i, 0, QTableWidgetItem(str(p["pid"])))
            self.table.setItem(i, 1, QTableWidgetItem(p["name"]))
            self.table.setItem(i, 2, QTableWidgetItem(f"{p['cpu']:.1f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{p['mem']:.1f}"))
            self.table.setItem(i, 4, QTableWidgetItem(p["user"]))
