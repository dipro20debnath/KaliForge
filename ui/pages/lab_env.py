"""One-Click Lab Environment page — start/stop Docker-based vulnerable targets
for authorised practice, and add them to scope."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from core.lab_env import LABS
from ui.widgets.common import Card, FlowLayout

_DIFF_COLOR = {"beginner": "#2ecc71", "intermediate": "#ffd23f", "advanced": "#ff8c1a"}


class LabEnvPage(QWidget):
    status_message = Signal(str)
    # worker-thread → UI-thread bridges (docker runs on a ManagedProcess thread)
    _start_result = Signal(object)
    _stop_result = Signal()

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._cards: dict[str, "LabCard"] = {}
        self._start_result.connect(self._handle_start_done)
        self._stop_result.connect(self.refresh)
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        head = QHBoxLayout()
        title = QLabel("Lab Environments")
        title.setObjectName("PageTitle")
        head.addWidget(title)
        head.addStretch(1)
        refresh = QPushButton("Refresh status")
        refresh.clicked.connect(self.refresh)
        head.addWidget(refresh)
        layout.addLayout(head)

        self.docker_lbl = QLabel("")
        self.docker_lbl.setObjectName("Hint")
        self.docker_lbl.setWordWrap(True)
        layout.addWidget(self.docker_lbl)

        warn = QLabel("⚠ These targets are intentionally vulnerable — run them only on "
                      "an isolated lab host, never on a production or shared network.")
        warn.setObjectName("SevMed")
        warn.setWordWrap(True)
        layout.addWidget(warn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        host = QWidget()
        self.flow = FlowLayout(host, margin=2, spacing=12)
        for lab in LABS:
            card = LabCard(lab)
            card.start_requested.connect(self._start)
            card.stop_requested.connect(self._stop)
            card.scope_requested.connect(self._add_scope)
            card.open_requested.connect(self._open)
            self._cards[lab.id] = card
            self.flow.addWidget(card)
        scroll.setWidget(host)
        layout.addWidget(scroll, 1)

    def refresh(self) -> None:
        available = self.app.labs_env.docker_available()
        if not available:
            self.docker_lbl.setText("Docker is not installed. Install docker.io to use lab "
                                    "environments:  sudo apt install -y docker.io")
        elif not self.app.labs_env.docker_running():
            self.docker_lbl.setText("Docker is installed but the daemon is not reachable. "
                                    "Start it with:  sudo systemctl start docker")
        else:
            self.docker_lbl.setText("Docker is available.")
        for lab_id, card in self._cards.items():
            from core.lab_env import LAB_BY_ID
            status = self.app.labs_env.status(LAB_BY_ID[lab_id])
            card.set_status(status.running, available)

    def _start(self, lab) -> None:
        if not self.app.labs_env.docker_available():
            QMessageBox.warning(
                self, "Docker",
                "Docker is not installed.\n\nInstall it with:\n"
                "  sudo apt install -y docker.io\n  sudo systemctl start docker\n"
                "  sudo usermod -aG docker $USER   (then log out and back in)")
            return
        if not self.app.labs_env.docker_running():
            QMessageBox.warning(
                self, "Docker",
                "The Docker daemon isn't reachable. Either it isn't running, or "
                "your user lacks access to it.\n\nTry:\n"
                "  sudo systemctl start docker\n"
                "  sudo usermod -aG docker $USER   (then log out and back in)\n\n"
                "Check in a terminal with:  docker ps")
            return
        self.status_message.emit(
            f"Starting {lab.name}… the first run pulls the image and can take a minute.")
        # on_done fires on the worker thread → emit a signal to reach the UI thread
        self.app.labs_env.start(lab, on_done=lambda r: self._start_result.emit(r))
        QTimer.singleShot(4000, self.refresh)   # from the UI thread — OK

    def _handle_start_done(self, result) -> None:
        self.refresh()
        if result.ok:
            self.status_message.emit("Lab started.")
        else:
            tail = "\n".join(result.output.splitlines()[-6:]) or result.error
            self.status_message.emit("Lab failed to start — see details.")
            QMessageBox.critical(self, "Lab failed to start",
                                 f"`{result.command}` exited with code {result.returncode}.\n\n{tail}")

    def _stop(self, lab) -> None:
        self.status_message.emit(f"Stopping {lab.name} …")
        self.app.labs_env.stop(lab, on_done=lambda r: self._stop_result.emit())
        QTimer.singleShot(1500, self.refresh)   # from the UI thread — OK

    def _add_scope(self, lab) -> None:
        self.app.scope.add(lab.target.split(":")[0])
        self.status_message.emit(f"Added {lab.target} to scope.")

    def _open(self, lab) -> None:
        QDesktopServices.openUrl(QUrl(lab.url))


class LabCard(Card):
    start_requested = Signal(object)
    stop_requested = Signal(object)
    scope_requested = Signal(object)
    open_requested = Signal(object)

    def __init__(self, lab, parent=None):
        super().__init__(parent)
        self.lab = lab
        self.setMinimumWidth(300)
        self.setMaximumWidth(380)
        self.setMinimumHeight(196)

        top = QHBoxLayout()
        name = QLabel(lab.name)
        name.setObjectName("CardTitle")
        top.addWidget(name)
        top.addStretch(1)
        diff = QLabel(lab.difficulty)
        diff.setStyleSheet(f"color: {_DIFF_COLOR.get(lab.difficulty, '#7f9499')}; font-weight:700;")
        top.addWidget(diff)
        self.layout().addLayout(top)

        desc = QLabel(lab.description)
        desc.setObjectName("PageSub")
        desc.setWordWrap(True)
        self.layout().addWidget(desc)

        self.url_lbl = QLabel(lab.url)
        self.url_lbl.setObjectName("Hint")
        self.layout().addWidget(self.url_lbl)

        self.status_lbl = QLabel("● stopped")
        self.status_lbl.setObjectName("BadgeMissing")
        self.layout().addWidget(self.status_lbl)
        self.layout().addStretch(1)

        row = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.setObjectName("Primary")
        self.start_btn.clicked.connect(lambda: self.start_requested.emit(self.lab))
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("Danger")
        self.stop_btn.clicked.connect(lambda: self.stop_requested.emit(self.lab))
        self.open_btn = QPushButton("Open")
        self.open_btn.setObjectName("Ghost")
        self.open_btn.clicked.connect(lambda: self.open_requested.emit(self.lab))
        scope_btn = QPushButton("→ Scope")
        scope_btn.setObjectName("Ghost")
        scope_btn.clicked.connect(lambda: self.scope_requested.emit(self.lab))
        row.addWidget(self.start_btn)
        row.addWidget(self.stop_btn)
        row.addWidget(self.open_btn)
        row.addWidget(scope_btn)
        self.layout().addLayout(row)

    def set_status(self, running: bool, docker_available: bool) -> None:
        if running:
            self.status_lbl.setText("● running")
            self.status_lbl.setObjectName("BadgeInstalled")
        else:
            self.status_lbl.setText("● stopped")
            self.status_lbl.setObjectName("BadgeMissing")
        self.status_lbl.style().unpolish(self.status_lbl)
        self.status_lbl.style().polish(self.status_lbl)
        self.start_btn.setEnabled(docker_available and not running)
        self.stop_btn.setEnabled(docker_available and running)
        self.open_btn.setEnabled(running)
