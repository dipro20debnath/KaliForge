"""Scan Import page — paste or load tool output (nmap XML/normal, nuclei JSON,
gobuster), preview parsed findings/assets, then import them into the workspace."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QHeaderView,
                               QLabel, QPlainTextEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from core import parsers
from database.models import Asset


class ImporterPage(QWidget):
    status_message = Signal(str)
    data_imported = Signal()

    FORMATS = [("Auto-detect", None), ("Nmap XML (-oX)", "nmap-xml"),
               ("Nmap normal", "nmap-normal"), ("Nuclei JSON", "nuclei-json"),
               ("Gobuster", "gobuster")]

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._result = None
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title = QLabel("Scan Import")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        sub = QLabel("Turn tool output into findings and attack-surface assets.")
        sub.setObjectName("PageSub")
        layout.addWidget(sub)

        row = QHBoxLayout()
        self.fmt = QComboBox()
        for label, _ in self.FORMATS:
            self.fmt.addItem(label)
        load = QPushButton("Load file…")
        load.clicked.connect(self._load_file)
        parse_btn = QPushButton("Parse")
        parse_btn.setObjectName("Primary")
        parse_btn.clicked.connect(self._parse)
        row.addWidget(QLabel("Format:"))
        row.addWidget(self.fmt)
        row.addStretch(1)
        row.addWidget(load)
        row.addWidget(parse_btn)
        layout.addLayout(row)

        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("Paste nmap XML / nuclei JSON / gobuster output here…")
        self.input.setFixedHeight(150)
        layout.addWidget(self.input)

        self.preview = QTableWidget(0, 4)
        self.preview.setHorizontalHeaderLabels(["Kind", "Severity", "Host", "Detail"])
        self.preview.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.preview.verticalHeader().setVisible(False)
        self.preview.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.preview, 1)

        actions = QHBoxLayout()
        self.summary_lbl = QLabel("")
        self.summary_lbl.setObjectName("Hint")
        actions.addWidget(self.summary_lbl)
        actions.addStretch(1)
        self.import_btn = QPushButton("Import to workspace")
        self.import_btn.setObjectName("Primary")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._import)
        actions.addWidget(self.import_btn)
        layout.addLayout(actions)

    def _load_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open scan output", "",
            "Scan output (*.xml *.json *.txt *.gnmap *.nmap);;All files (*)")
        if path:
            try:
                self.input.setPlainText(Path(path).read_text(encoding="utf-8", errors="replace"))
            except OSError as exc:
                self.status_message.emit(f"Could not read file: {exc}")

    def _parse(self) -> None:
        text = self.input.toPlainText()
        if not text.strip():
            return
        fmt = self.FORMATS[self.fmt.currentIndex()][1]
        self._result = parsers.parse(text, fmt)
        self._render_preview()

    def _render_preview(self) -> None:
        r = self._result
        if r is None:
            return
        if r.error:
            self.summary_lbl.setText(f"Parse error: {r.error}")
            self.import_btn.setEnabled(False)
            self.preview.setRowCount(0)
            return
        rows = [("finding", f.get("severity", ""), f.get("host", ""),
                 f.get("title", "")) for f in r.findings]
        rows += [("asset", "", a.get("parent", ""), f"{a['kind']}: {a['value']}")
                 for a in r.assets]
        self.preview.setRowCount(len(rows))
        for i, (kind, sev, host, detail) in enumerate(rows):
            self.preview.setItem(i, 0, QTableWidgetItem(kind))
            self.preview.setItem(i, 1, QTableWidgetItem(sev))
            self.preview.setItem(i, 2, QTableWidgetItem(host))
            self.preview.setItem(i, 3, QTableWidgetItem(detail))
        self.summary_lbl.setText(f"Detected {r.source} · {r.summary()}")
        self.import_btn.setEnabled(bool(r.findings or r.assets))

    def _import(self) -> None:
        r = self._result
        if r is None:
            return
        ws = self.app.active_workspace_id()
        for finding in r.to_findings(ws):
            self.app.db.upsert_finding(finding)
        surface = self.app.attack_surface()
        for a in r.assets:
            surface.add(a["kind"], a["value"], a.get("parent", ""),
                        source="import", meta=a.get("meta"))
        self.app.audit.record(source="import", tool=r.source,
                              decision=f"imported {r.summary()}")
        self.status_message.emit(f"Imported {r.summary()} from {r.source}.")
        self.data_imported.emit()
