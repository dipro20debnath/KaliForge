"""Non-interactive command runner.

Used by the workflow engine and the "run and capture" dialog. Unlike the PTY
terminal, this captures stdout/stderr line by line via a background thread and
supports stop/kill and a wall-clock timeout. No Qt dependency.
"""
from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ProcessResult:
    command: str
    returncode: int | None = None
    output: str = ""
    duration: float = 0.0
    timed_out: bool = False
    killed: bool = False
    error: str = ""
    lines: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out and not self.killed


class ManagedProcess:
    def __init__(self, command: str, cwd: str | None = None, env: dict | None = None,
                 timeout: float | None = None,
                 on_line: Callable[[str], None] | None = None,
                 on_done: Callable[[ProcessResult], None] | None = None):
        self.command = command
        self.cwd = cwd or os.path.expanduser("~")
        self.env = env
        self.timeout = timeout
        self.on_line = on_line
        self.on_done = on_done
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self.result = ProcessResult(command=command)
        self._stop = threading.Event()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def run(self) -> ProcessResult:
        """Blocking convenience wrapper (used in tests)."""
        self._run()
        return self.result

    def _run(self) -> None:
        start = time.monotonic()
        env = dict(os.environ if self.env is None else self.env)
        try:
            self._proc = subprocess.Popen(
                self.command, shell=True, cwd=self.cwd, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, text=True, bufsize=1,
                preexec_fn=os.setsid,
            )
        except OSError as exc:
            self.result.error = str(exc)
            self.result.returncode = 127
            self.result.duration = time.monotonic() - start
            if self.on_done:
                self.on_done(self.result)
            return

        watchdog = None
        if self.timeout:
            watchdog = threading.Timer(self.timeout, self._on_timeout)
            watchdog.start()

        assert self._proc.stdout is not None
        for raw in self._proc.stdout:
            line = raw.rstrip("\n")
            self.result.lines.append(line)
            self.result.output += raw
            if self.on_line:
                self.on_line(line)
            if self._stop.is_set():
                break
        self._proc.wait()
        if watchdog:
            watchdog.cancel()
        self.result.returncode = self._proc.returncode
        self.result.duration = time.monotonic() - start
        if self.on_done:
            self.on_done(self.result)

    def _on_timeout(self) -> None:
        self.result.timed_out = True
        self.kill()

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def stop(self) -> None:
        """Polite stop (SIGTERM to the process group)."""
        self._stop.set()
        self._signal(signal.SIGTERM)

    def kill(self) -> None:
        self.result.killed = True
        self._stop.set()
        self._signal(signal.SIGKILL)

    def _signal(self, sig) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                os.killpg(os.getpgid(self._proc.pid), sig)
            except OSError:
                try:
                    self._proc.send_signal(sig)
                except OSError:
                    pass
