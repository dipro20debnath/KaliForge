"""Attack Surface Mapper page — visualise the engagement's asset graph and seed
it from scope, findings, manual entry or pasted tool output."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPlainTextEdit, QPushButton,
                               QVBoxLayout, QWidget)

from ui.widgets.graph_view import KIND_COLORS, GraphView


class AttackSurfacePage(QWidget):
    status_message = Signal(str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("Attack Surface Mapper")
        title.setObjectName("PageTitle")
        head.addWidget(title)
        head.addStretch(1)
        self.stats_lbl = QLabel("")
        self.stats_lbl.setObjectName("Hint")
        head.addWidget(self.stats_lbl)
        layout.addLayout(head)

        controls = QHBoxLayout()
        for text, slot, name in [
            ("Seed from scope", self._seed_scope, "Ghost"),
            ("Seed from findings", self._seed_findings, "Ghost"),
            ("＋ Add asset", self._add_asset, "Primary"),
            ("Import output", self._import_output, "Ghost"),
            ("Fit", self._fit, "Ghost"),
            ("Clear", self._clear, "Danger"),
        ]:
            btn = QPushButton(text)
            btn.setObjectName(name)
            btn.clicked.connect(slot)
            controls.addWidget(btn)
        controls.addStretch(1)
        layout.addLayout(controls)

        legend = QHBoxLayout()
        legend.addWidget(_hint("Legend:"))
        for kind, color in KIND_COLORS.items():
            chip = QLabel(f"● {kind}")
            chip.setStyleSheet(f"color: {color}; font-weight: 600;")
            legend.addWidget(chip)
        legend.addStretch(1)
        layout.addLayout(legend)

        self.graph = GraphView()
        layout.addWidget(self.graph, 1)

    def refresh(self) -> None:
        surface = self.app.attack_surface()
        graph = surface.build()
        self.graph.set_graph(graph)
        stats = graph.stats()
        self.stats_lbl.setText(
            " · ".join(f"{k}: {v}" for k, v in stats.items() if k != "total")
            + f"   (total {stats.get('total', 0)})")

    def showEvent(self, event):  # noqa: N802
        self.refresh()
        super().showEvent(event)

    # ------------------------------------------------------------------ slots
    def _seed_scope(self) -> None:
        n = self.app.attack_surface().seed_from_scope(self.app.scope.entries())
        self.refresh()
        self.status_message.emit(f"Seeded {n} scope entries into the surface.")

    def _seed_findings(self) -> None:
        n = self.app.attack_surface().seed_from_findings()
        self.refresh()
        self.status_message.emit(f"Seeded {n} hosts from findings.")

    def _add_asset(self) -> None:
        dialog = _AssetDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            kind, value, parent = dialog.data()
            if value:
                self.app.attack_surface().add(kind, value, parent)
                self.refresh()

    def _import_output(self) -> None:
        dialog = _ImportDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text, root = dialog.data()
            if text.strip():
                n = self.app.attack_surface().import_text(text, root)
                self.refresh()
                self.status_message.emit(f"Imported {n} assets from output.")

    def _fit(self) -> None:
        self.graph.fit()

    def _clear(self) -> None:
        self.app.attack_surface().clear()
        self.refresh()


def _hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Hint")
    return lbl


class _AssetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add asset")
        form = QFormLayout(self)
        self.kind = QComboBox()
        self.kind.addItems(["domain", "subdomain", "host", "ip", "url", "port", "service"])
        self.value = QLineEdit()
        self.parent_val = QLineEdit()
        self.parent_val.setPlaceholderText("parent asset value (optional)")
        form.addRow("Kind", self.kind)
        form.addRow("Value*", self.value)
        form.addRow("Parent", self.parent_val)
        row = QHBoxLayout()
        ok = QPushButton("Add")
        ok.setObjectName("Primary")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(ok)
        form.addRow(row)

    def data(self):
        return self.kind.currentText(), self.value.text().strip(), self.parent_val.text().strip()


class _ImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import from tool output")
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Paste nmap / recon output — hosts, IPs and open "
                                "ports are extracted automatically."))
        self.root = QLineEdit()
        self.root.setPlaceholderText("root asset to attach under (optional, e.g. example.com)")
        layout.addWidget(self.root)
        self.text = QPlainTextEdit()
        layout.addWidget(self.text, 1)
        row = QHBoxLayout()
        ok = QPushButton("Import")
        ok.setObjectName("Primary")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(ok)
        layout.addLayout(row)

    def data(self):
        return self.text.toPlainText(), self.root.text().strip()
