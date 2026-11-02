"""PTY-backed terminal session.

A :class:`TerminalSession` owns a real pseudo-terminal running the user's shell
and a :mod:`pyte` screen that interprets the byte stream into a grid of cells.
The Qt terminal widget renders that grid; this module has **no** Qt dependency
so it can be unit-tested headless.
"""
from __future__ import annotations

import fcntl
import os
import pty
import select
import shlex
import signal
import struct
import termios
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pyte


def default_shell() -> str:
    return os.environ.get("SHELL") or "/bin/bash"


class TerminalSession:
    """One PTY + pyte screen. Thread-safe for the reader thread + UI thread."""

    def __init__(self, columns: int = 100, rows: int = 30, shell: str | None = None,
                 cwd: str | None = None, env: dict | None = None,
                 scrollback: int = 10000, record_path: str | None = None):
        self.columns = columns
        self.rows = rows
        self.shell = shell or default_shell()
        self.cwd = cwd or os.path.expanduser("~")
        self.scrollback = scrollback
        self._env = env
        self._lock = threading.RLock()
        self.screen = pyte.HistoryScreen(columns, rows, history=scrollback, ratio=0.5)
        self.stream = pyte.ByteStream(self.screen)
        self.pid: int | None = None
        self.fd: int | None = None
        self._reader: threading.Thread | None = None
        self._alive = False
        self._on_update: Callable[[], None] | None = None
        self._on_exit: Callable[[int], None] | None = None
        self.exit_code: int | None = None
        self._record_path = record_path
        self._record_handle = None

    # --------------------------------------------------------------- lifecycle
    def start(self) -> None:
        if self._alive:
            return
        env = dict(os.environ if self._env is None else self._env)
        env.setdefault("TERM", "linux")
        env.setdefault("KALIFORGE", "1")
        pid, fd = pty.fork()
        if pid == 0:  # child
            try:
                os.chdir(self.cwd)
            except OSError:
                pass
            shell_parts = shlex.split(self.shell) if " " in self.shell else [self.shell]
            try:
                os.execvpe(shell_parts[0], shell_parts, env)
            except OSError:
                os._exit(127)
        else:  # parent
            self.pid = pid
            self.fd = fd
            self._alive = True
            self.resize(self.columns, self.rows)
            if self._record_path:
                try:
                    self._record_handle = open(self._record_path, "ab")
                except OSError:
                    self._record_handle = None
            self._reader = threading.Thread(target=self._read_loop, daemon=True)
            self._reader.start()

    def _read_loop(self) -> None:
        fd = self.fd
        if fd is None:
            return
        while self._alive:
            fd = self.fd
            if fd is None:
                break
            try:
                ready, _, _ = select.select([fd], [], [], 0.2)
            except (OSError, ValueError):
                break
            if not ready:
                continue
            try:
                data = os.read(fd, 65536)
            except (OSError, TypeError):
                break
            if not data:
                break
            with self._lock:
                self.stream.feed(data)
            if self._record_handle is not None:
                try:
                    self._record_handle.write(data)
                    self._record_handle.flush()
                except OSError:
                    pass
            if self._on_update:
                self._on_update()
        self._finish()

    def _finish(self) -> None:
        self._alive = False
        code = 0
        if self.pid:
            try:
                _, status = os.waitpid(self.pid, os.WNOHANG)
                if os.WIFEXITED(status):
                    code = os.WEXITSTATUS(status)
                elif os.WIFSIGNALED(status):
                    code = -os.WTERMSIG(status)
            except OSError:
                pass
        self.exit_code = code
        if self._record_handle is not None:
            try:
                self._record_handle.close()
            except OSError:
                pass
        if self._on_exit:
            self._on_exit(code)

    # --------------------------------------------------------------- I/O
    def write(self, data: str | bytes) -> None:
        if not self._alive or self.fd is None:
            return
        if isinstance(data, str):
            data = data.encode("utf-8", "replace")
        try:
            os.write(self.fd, data)
        except OSError:
            pass

    def send_line(self, line: str) -> None:
        self.write(line.rstrip("\n") + "\n")

    def resize(self, columns: int, rows: int) -> None:
        columns = max(2, columns)
        rows = max(2, rows)
        self.columns, self.rows = columns, rows
        with self._lock:
            self.screen.resize(rows, columns)
        if self.fd is not None:
            try:
                winsize = struct.pack("HHHH", rows, columns, 0, 0)
                fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)
            except OSError:
                pass

    # --------------------------------------------------------------- state
    def is_alive(self) -> bool:
        return self._alive

    def display(self) -> list[str]:
        with self._lock:
            return list(self.screen.display)

    def cursor(self) -> tuple[int, int]:
        with self._lock:
            return self.screen.cursor.x, self.screen.cursor.y

    # --------------------------------------------------------------- scrollback
    def scroll_up(self, pages: int = 1) -> None:
        with self._lock:
            for _ in range(max(1, pages)):
                try:
                    self.screen.prev_page()
                except Exception:
                    break

    def scroll_down(self, pages: int = 1) -> None:
        with self._lock:
            for _ in range(max(1, pages)):
                try:
                    self.screen.next_page()
                except Exception:
                    break

    def scroll_to_bottom(self) -> None:
        with self._lock:
            try:
                for _ in range(200):
                    self.screen.next_page()
            except Exception:
                pass

    def buffer_snapshot(self):
        """Return (history_lines, screen) under lock for the renderer."""
        with self._lock:
            return self.screen

    def plain_text(self) -> str:
        """Current visible screen as plain text (used for 'export output')."""
        return "\n".join(line.rstrip() for line in self.display())

    def set_callbacks(self, on_update: Callable[[], None] | None = None,
                      on_exit: Callable[[int], None] | None = None) -> None:
        self._on_update = on_update
        self._on_exit = on_exit

    # --------------------------------------------------------------- control
    def interrupt(self) -> None:
        self.write(b"\x03")

    def terminate(self) -> None:
        self._alive = False
        if self.pid:
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.kill(self.pid, sig)
                    break
                except OSError:
                    continue
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None

    def export_output(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        header = f"# KaliForge terminal export — {datetime.now(timezone.utc).isoformat()}\n"
        path.write_text(header + self.plain_text() + "\n", encoding="utf-8")
        return path
