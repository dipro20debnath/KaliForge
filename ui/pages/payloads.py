"""Payload Generator page — reverse/bind shell one-liners and listeners for
authorised testing. Nothing is executed here; commands can be sent to the
terminal through the normal confirmation flow."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit,
                               QPlainTextEdit, QPushButton, QVBoxLayout, QWidget)

from core import payloads
from ui.widgets.common import Card


class PayloadsPage(QWidget):
    run_in_terminal = Signal(str)
    status_message = Signal(str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._build()
        self._generate()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title = QLabel("Payload Generator")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        warn = QLabel("For authorised testing only. Build a reverse shell, start the "
                      "matching listener, then run against systems you may test.")
        warn.setObjectName("Hint")
        warn.setWordWrap(True)
        layout.addWidget(warn)

        form = QHBoxLayout()
        self.lhost = QLineEdit()
        self.lhost.setPlaceholderText("LHOST (your IP)")
        self.lport = QLineEdit("4444")
        self.lport.setPlaceholderText("LPORT")
        self.shell = QComboBox()
        self.shell.addItems(list(payloads.REVERSE_SHELLS.keys()))
        for w in (self.lhost, self.lport, self.shell):
            if hasattr(w, "textChanged"):
                w.textChanged.connect(self._generate)
        self.shell.currentTextChanged.connect(self._generate)
        form.addWidget(QLabel("LHOST:"))
        form.addWidget(self.lhost, 1)
        form.addWidget(QLabel("LPORT:"))
        form.addWidget(self.lport)
        form.addWidget(QLabel("Type:"))
        form.addWidget(self.shell, 1)
        layout.addLayout(form)

        rs_card = Card()
        rs_card.layout().addWidget(_bold("Reverse shell"))
        self.rs_out = QPlainTextEdit()
        self.rs_out.setReadOnly(True)
        self.rs_out.setFixedHeight(90)
        rs_card.layout().addWidget(self.rs_out)
        rs_row = QHBoxLayout()
        for text, slot in [("Copy", self._copy_rs), ("URL-encode", self._url),
                           ("Base64", self._b64), ("PS -enc", self._psenc)]:
            btn = QPushButton(text)
            btn.setObjectName("Ghost")
            btn.clicked.connect(slot)
            rs_row.addWidget(btn)
        rs_row.addStretch(1)
        rs_card.layout().addLayout(rs_row)
        layout.addWidget(rs_card)

        lis_card = Card()
        lis_card.layout().addWidget(_bold("Listener"))
        lrow = QHBoxLayout()
        self.listener = QComboBox()
        self.listener.addItems(list(payloads.LISTENERS.keys()))
        self.listener.currentTextChanged.connect(self._generate)
        lrow.addWidget(self.listener, 1)
        run_lis = QPushButton("Start listener in terminal")
        run_lis.setObjectName("Primary")
        run_lis.clicked.connect(self._run_listener)
        lrow.addWidget(run_lis)
        lis_card.layout().addLayout(lrow)
        self.lis_out = QPlainTextEdit()
        self.lis_out.setReadOnly(True)
        self.lis_out.setFixedHeight(50)
        lis_card.layout().addWidget(self.lis_out)
        layout.addWidget(lis_card)

        tips = QLabel("Shell upgrade:  " + "   ·   ".join(payloads.SHELL_UPGRADES[:2]))
        tips.setObjectName("Hint")
        tips.setWordWrap(True)
        layout.addWidget(tips)
        layout.addStretch(1)

    def _generate(self) -> None:
        ip = self.lhost.text().strip()
        port = self.lport.text().strip()
        self.rs_out.setPlainText(payloads.reverse_shell(self.shell.currentText(), ip, port))
        self.lis_out.setPlainText(payloads.listener(self.listener.currentText(), ip, port))

    def _copy_to_clip(self, text: str) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        self.status_message.emit("Copied to clipboard.")

    def _copy_rs(self) -> None:
        self._copy_to_clip(self.rs_out.toPlainText())

    def _url(self) -> None:
        self.rs_out.setPlainText(payloads.url_encode(self.rs_out.toPlainText()))

    def _b64(self) -> None:
        self.rs_out.setPlainText(payloads.base64_encode(self.rs_out.toPlainText()))

    def _psenc(self) -> None:
        self.rs_out.setPlainText(payloads.powershell_encoded(self.rs_out.toPlainText()))

    def _run_listener(self) -> None:
        self.run_in_terminal.emit(self.lis_out.toPlainText())


def _bold(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("CardTitle")
    return lbl
