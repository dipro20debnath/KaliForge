"""Crypto Toolkit page — offline encoder/decoder, hash identifier and hasher."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QPlainTextEdit, QPushButton,
                               QTableWidget, QTableWidgetItem, QTabWidget,
                               QVBoxLayout, QWidget)

from core import toolkit


class ToolkitPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title = QLabel("Crypto Toolkit")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        tabs = QTabWidget()
        tabs.addTab(self._codec_tab(), "Encoder / Decoder")
        tabs.addTab(self._hash_tab(), "Hash Identifier & Hasher")
        layout.addWidget(tabs, 1)

    # ---------------------------------------------------------------- codec
    def _codec_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        row = QHBoxLayout()
        self.op = QComboBox()
        self.op.addItems(list(toolkit.OPERATIONS.keys()))
        self.op.currentTextChanged.connect(self._run_codec)
        enc_btn = QPushButton("Encode ▼")
        enc_btn.setObjectName("Primary")
        enc_btn.clicked.connect(lambda: self._run_codec(decode=False))
        dec_btn = QPushButton("Decode ▲")
        dec_btn.clicked.connect(lambda: self._run_codec(decode=True))
        swap = QPushButton("⇅ Input↔Output")
        swap.setObjectName("Ghost")
        swap.clicked.connect(self._swap)
        row.addWidget(QLabel("Operation:"))
        row.addWidget(self.op, 1)
        row.addWidget(enc_btn)
        row.addWidget(dec_btn)
        row.addWidget(swap)
        layout.addLayout(row)

        layout.addWidget(QLabel("Input:"))
        self.codec_in = QPlainTextEdit()
        self.codec_in.textChanged.connect(lambda: self._run_codec(decode=False))
        layout.addWidget(self.codec_in, 1)
        layout.addWidget(QLabel("Output:"))
        self.codec_out = QPlainTextEdit()
        self.codec_out.setReadOnly(True)
        layout.addWidget(self.codec_out, 1)
        return widget

    def _run_codec(self, *_args, decode: bool = False) -> None:
        text = self.codec_in.toPlainText()
        if not text:
            self.codec_out.setPlainText("")
            return
        try:
            self.codec_out.setPlainText(toolkit.transform(self.op.currentText(), text, decode))
        except Exception as exc:  # noqa: BLE001
            self.codec_out.setPlainText(f"[error] {exc}")

    def _swap(self) -> None:
        out = self.codec_out.toPlainText()
        self.codec_in.setPlainText(out)

    # ---------------------------------------------------------------- hash
    def _hash_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Identify a hash or hash some text:"))
        self.hash_in = QLineEdit()
        self.hash_in.setPlaceholderText("paste a hash, or type text to hash…")
        self.hash_in.textChanged.connect(self._run_hash)
        layout.addWidget(self.hash_in)

        layout.addWidget(QLabel("Possible hash types:"))
        self.hash_table = QTableWidget(0, 2)
        self.hash_table.setHorizontalHeaderLabels(["Type", "Hashcat mode"])
        self.hash_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.hash_table.verticalHeader().setVisible(False)
        self.hash_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.hash_table.setMaximumHeight(170)
        layout.addWidget(self.hash_table)

        layout.addWidget(QLabel("Hashes of the input text:"))
        self.hash_out = QPlainTextEdit()
        self.hash_out.setReadOnly(True)
        layout.addWidget(self.hash_out, 1)
        return widget

    def _run_hash(self) -> None:
        value = self.hash_in.text()
        ids = toolkit.identify_hash(value)
        self.hash_table.setRowCount(len(ids))
        for i, item in enumerate(ids):
            self.hash_table.setItem(i, 0, QTableWidgetItem(item["name"]))
            self.hash_table.setItem(i, 1, QTableWidgetItem(item["hashcat"]))
        if value:
            digests = toolkit.hash_text(value)
            self.hash_out.setPlainText("\n".join(f"{k.upper():8} {v}" for k, v in digests.items()))
        else:
            self.hash_out.setPlainText("")
