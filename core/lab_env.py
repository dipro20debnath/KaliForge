"""One-Click Lab Environment — manage Docker-based deliberately-vulnerable
targets for authorised practice (OWASP Juice Shop, DVWA, WebGoat, bWAPP, …).

KaliForge builds the exact ``docker`` commands and runs them through the normal
process/audit flow; it does not pull or run anything silently. These targets are
intentionally vulnerable — run them only on an isolated lab host.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field

from core.process_manager import ManagedProcess


@dataclass
class LabEnv:
    id: str
    name: str
    description: str
    image: str
    container: str
    host_port: int
    container_port: int
    difficulty: str = "beginner"
    path: str = "/"

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.host_port}{self.path}"

    @property
    def target(self) -> str:
        return f"127.0.0.1:{self.host_port}"

    def run_command(self) -> str:
        return (f"docker run -d --rm --name {self.container} "
                f"-p 127.0.0.1:{self.host_port}:{self.container_port} {self.image}")

    def stop_command(self) -> str:
        return f"docker stop {self.container}"


LABS: list[LabEnv] = [
    LabEnv("juiceshop", "OWASP Juice Shop", "Modern, intentionally insecure web app — the OWASP flagship training target.",
           "bkimminich/juice-shop", "kf-juiceshop", 3000, 3000, "beginner"),
    LabEnv("dvwa", "DVWA", "Damn Vulnerable Web Application (PHP/MySQL) with selectable security levels.",
           "vulnerables/web-dvwa", "kf-dvwa", 8081, 80, "beginner"),
    LabEnv("webgoat", "WebGoat", "OWASP's deliberately insecure teaching application (Java).",
           "webgoat/webgoat", "kf-webgoat", 8082, 8080, "intermediate", "/WebGoat"),
    LabEnv("bwapp", "bWAPP", "Buggy Web Application with 100+ web vulnerabilities.",
           "raesene/bwapp", "kf-bwapp", 8083, 80, "beginner", "/install.php"),
    LabEnv("vampi", "VAmPI", "Vulnerable REST API for testing API security.",
           "erev0s/vampi", "kf-vampi", 5001, 5000, "intermediate"),
    LabEnv("mutillidae", "Mutillidae II", "OWASP Mutillidae II deliberately vulnerable web app.",
           "citizenstig/nowasp", "kf-mutillidae", 8084, 80, "beginner"),
]

LAB_BY_ID = {lab.id: lab for lab in LABS}


@dataclass
class LabStatus:
    running: bool = False
    container_id: str = ""
    error: str = ""


class LabManager:
    def __init__(self, audit=None):
        self.audit = audit

    @staticmethod
    def docker_available() -> bool:
        return shutil.which("docker") is not None

    @staticmethod
    def docker_running() -> bool:
        if not LabManager.docker_available():
            return False
        try:
            proc = subprocess.run(["docker", "info"], capture_output=True,
                                  timeout=8, check=False)
            return proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def status(self, lab: LabEnv) -> LabStatus:
        status = LabStatus()
        if not self.docker_available():
            status.error = "docker not installed"
            return status
        try:
            proc = subprocess.run(
                ["docker", "ps", "--filter", f"name=^{lab.container}$",
                 "--format", "{{.ID}}"],
                capture_output=True, text=True, timeout=8, check=False)
            cid = proc.stdout.strip()
            status.running = bool(cid)
            status.container_id = cid
        except (OSError, subprocess.TimeoutExpired) as exc:
            status.error = str(exc)
        return status

    def start(self, lab: LabEnv, on_line=None, on_done=None) -> ManagedProcess:
        command = lab.run_command()
        if self.audit:
            self.audit.record(source="lab", tool=lab.id, command=command, decision="start")
        proc = ManagedProcess(command, on_line=on_line, on_done=on_done, timeout=300)
        proc.start()
        return proc

    def stop(self, lab: LabEnv, on_done=None) -> ManagedProcess:
        command = lab.stop_command()
        if self.audit:
            self.audit.record(source="lab", tool=lab.id, command=command, decision="stop")
        proc = ManagedProcess(command, on_done=on_done, timeout=60)
        proc.start()
        return proc
