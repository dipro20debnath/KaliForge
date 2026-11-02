"""Live system-resource sampling via psutil. Pure data; the UI polls ``sample()``
on a timer. Degrades gracefully if psutil is missing."""
from __future__ import annotations

from dataclasses import dataclass, field

try:
    import psutil
    _HAVE_PSUTIL = True
except ImportError:  # pragma: no cover
    psutil = None
    _HAVE_PSUTIL = False


@dataclass
class Sample:
    cpu_percent: float = 0.0
    per_cpu: list[float] = field(default_factory=list)
    mem_percent: float = 0.0
    mem_used: int = 0
    mem_total: int = 0
    swap_percent: float = 0.0
    disk_percent: float = 0.0
    disk_used: int = 0
    disk_total: int = 0
    net_sent: int = 0
    net_recv: int = 0
    process_count: int = 0
    load_avg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    available: bool = True


class SystemMonitor:
    def __init__(self):
        self.available = _HAVE_PSUTIL
        if _HAVE_PSUTIL:
            try:
                psutil.cpu_percent(interval=None)  # prime the counter
            except Exception:
                pass

    def sample(self) -> Sample:
        if not _HAVE_PSUTIL:
            return Sample(available=False)
        s = Sample()
        try:
            s.cpu_percent = psutil.cpu_percent(interval=None)
            s.per_cpu = psutil.cpu_percent(interval=None, percpu=True)
            vm = psutil.virtual_memory()
            s.mem_percent, s.mem_used, s.mem_total = vm.percent, vm.used, vm.total
            sw = psutil.swap_memory()
            s.swap_percent = sw.percent
            disk = psutil.disk_usage("/")
            s.disk_percent, s.disk_used, s.disk_total = disk.percent, disk.used, disk.total
            net = psutil.net_io_counters()
            s.net_sent, s.net_recv = net.bytes_sent, net.bytes_recv
            s.process_count = len(psutil.pids())
            try:
                import os
                s.load_avg = tuple(os.getloadavg())
            except (OSError, AttributeError):
                pass
        except Exception:
            s.available = False
        return s

    def top_processes(self, limit: int = 8, by: str = "cpu") -> list[dict]:
        if not _HAVE_PSUTIL:
            return []
        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "username"]):
            try:
                info = proc.info
                procs.append({
                    "pid": info.get("pid"),
                    "name": info.get("name") or "",
                    "cpu": info.get("cpu_percent") or 0.0,
                    "mem": info.get("memory_percent") or 0.0,
                    "user": info.get("username") or "",
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        key = "cpu" if by == "cpu" else "mem"
        procs.sort(key=lambda p: p[key], reverse=True)
        return procs[:limit]


def human_bytes(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(num) < 1024.0:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} EB"
