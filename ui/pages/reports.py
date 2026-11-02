"""Reports — assemble a report from the workspace findings and export to
Markdown / HTML / JSON / CSV / PDF."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
                               QPushButton, QTextBrowser, QVBoxLayout, QWidget)

from core.reporting import ReportGenerator, ReportModel


class ReportsPage(QWidget):
    status_message = Signal(str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title = QLabel("Report Generator")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self.title_input = QLineEdit("Security Assessment Report")
        self.client_input = QLineEdit()
        self.author_input = QLineEdit()
        self.summary_input = QPlainTextEdit()
        self.summary_input.setFixedHeight(80)
        form.addRow("Title", self.title_input)
        form.addRow("Client", self.client_input)
        form.addRow("Author", self.author_input)
        form.addRow("Executive summary", self.summary_input)
        layout.addLayout(form)

        controls = QHBoxLayout()
        self.fmt_box = QComboBox()
        self.fmt_box.addItems(["Markdown (.md)", "HTML (.html)", "JSON (.json)",
                               "CSV (.csv)", "PDF (.pdf)"])
        preview = QPushButton("Preview")
        preview.clicked.connect(self._preview)
        export = QPushButton("Export…")
        export.setObjectName("Primary")
        export.clicked.connect(self._export)
        controls.addWidget(QLabel("Format:"))
        controls.addWidget(self.fmt_box)
        controls.addWidget(preview)
        controls.addStretch(1)
        controls.addWidget(export)
        layout.addLayout(controls)

        self.preview_view = QTextBrowser()
        layout.addWidget(self.preview_view, 1)

    def _model(self) -> ReportModel:
        ws = self.app.workspaces.active()
        ws_id = ws["id"] if ws else None
        findings = self.app.db.findings(ws_id)
        scope = [e.value for e in self.app.scope.entries()]
        versions = []
        for tool_id, status in self.app.tools._status.items():
            if status.installed and status.version:
                tool = self.app.catalog.get(tool_id)
                versions.append({"name": tool["name"] if tool else tool_id, "version": status.version})
        return ReportModel(
            title=self.title_input.text().strip() or "Security Assessment Report",
            client=self.client_input.text().strip(),
            workspace=ws["name"] if ws else "",
            author=self.author_input.text().strip(),
            summary=self.summary_input.toPlainText().strip(),
            scope=scope, findings=findings, tool_versions=versions)

    def _fmt(self) -> str:
        return ["md", "html", "json", "csv", "pdf"][self.fmt_box.currentIndex()]

    def _preview(self) -> None:
        gen = ReportGenerator(self._model())
        fmt = self._fmt()
        if fmt == "html":
            self.preview_view.setHtml(gen.to_html())
        elif fmt == "json":
            self.preview_view.setPlainText(gen.to_json())
        elif fmt == "csv":
            self.preview_view.setPlainText(gen.to_csv())
        elif fmt == "pdf":
            self.preview_view.setMarkdown(gen.to_markdown())
            self.preview_view.append("\n\n*(PDF preview shows the Markdown source; "
                                     "export to generate the PDF.)*")
        else:
            self.preview_view.setMarkdown(gen.to_markdown())

    def _export(self) -> None:
        gen = ReportGenerator(self._model())
        fmt = self._fmt()
        if fmt == "pdf" and not gen.pdf_available():
            QMessageBox.warning(self, "Export",
                                "ReportLab is not installed — export HTML and print to PDF instead.")
            return
        ext = {"md": "md", "html": "html", "json": "json", "csv": "csv", "pdf": "pdf"}[fmt]
        default = str(self.app.workspaces.reports_dir() / f"report.{ext}")
        path, _ = QFileDialog.getSaveFileName(self, "Export report", default,
                                              f"{ext.upper()} (*.{ext})")
        if not path:
            return
        try:
            gen.save(path, fmt)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.status_message.emit(f"Report exported to {path}")
