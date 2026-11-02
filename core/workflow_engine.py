"""Workflow engine — runs an ordered list of tool steps against one target,
writing each step's output to the run directory and honouring scope + skipping
steps whose tool is not installed.

A workflow is JSON:

    {
      "name": "Reconnaissance",
      "description": "...",
      "steps": [
        {"tool": "whois", "template": "whois {domain}", "optional": true},
        {"tool": "nmap",  "template": "nmap -sV -sC {target}"}
      ]
    }

Execution runs on a background thread; the caller supplies callbacks. No Qt.
"""
from __future__ import annotations

import json
import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from core import command_builder
from core.process_manager import ManagedProcess
from core.scope_manager import ScopeManager


@dataclass
class StepResult:
    index: int
    tool: str
    command: str
    status: str = "pending"   # pending|running|done|failed|skipped|blocked
    returncode: int | None = None
    output_file: str = ""
    duration: float = 0.0
    note: str = ""


@dataclass
class WorkflowRun:
    name: str
    target: str
    outdir: str
    steps: list[StepResult] = field(default_factory=list)
    status: str = "running"
    started: str = ""
    finished: str = ""


def load_workflow(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def list_workflows(directory: str | Path) -> list[dict]:
    directory = Path(directory)
    out = []
    if not directory.exists():
        return out
    for file in sorted(directory.glob("*.json")):
        try:
            data = load_workflow(file)
            data["_path"] = str(file)
            out.append(data)
        except (OSError, ValueError):
            continue
    return out


class WorkflowEngine:
    def __init__(self, tool_manager=None, scope: ScopeManager | None = None,
                 audit=None, enforce_scope: bool = True):
        self.tool_manager = tool_manager
        self.scope = scope
        self.audit = audit
        self.enforce_scope = enforce_scope
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None
        self._current: ManagedProcess | None = None

    def cancel(self) -> None:
        self._cancel.set()
        if self._current:
            self._current.stop()

    def run(self, workflow: dict, target_values: dict[str, str], outdir: str | Path,
            on_step: Callable[[StepResult], None] | None = None,
            on_done: Callable[[WorkflowRun], None] | None = None,
            step_timeout: float | None = 600.0, background: bool = True) -> WorkflowRun:
        outdir = Path(outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        primary = (target_values.get("target") or target_values.get("domain")
                   or target_values.get("url") or target_values.get("host") or "")
        run = WorkflowRun(
            name=workflow.get("name", "workflow"), target=primary, outdir=str(outdir),
            started=datetime.now(timezone.utc).isoformat(),
        )

        def _execute():
            for index, raw_step in enumerate(workflow.get("steps", [])):
                if self._cancel.is_set():
                    break
                step = self._prepare_step(index, raw_step, target_values)
                run.steps.append(step)
                if step.status in ("skipped", "blocked"):
                    if on_step:
                        on_step(step)
                    continue
                self._run_step(step, outdir, step_timeout)
                if on_step:
                    on_step(step)
            run.status = "cancelled" if self._cancel.is_set() else "completed"
            run.finished = datetime.now(timezone.utc).isoformat()
            self._write_summary(run)
            if on_done:
                on_done(run)

        self._cancel.clear()
        if background:
            self._thread = threading.Thread(target=_execute, daemon=True)
            self._thread.start()
        else:
            _execute()
        return run

    # ------------------------------------------------------------------ steps
    def _prepare_step(self, index: int, raw_step: dict, values: dict) -> StepResult:
        tool = raw_step.get("tool", "")
        template = raw_step.get("template", "")
        command, missing = command_builder.build(template, values)
        step = StepResult(index=index, tool=tool, command=command)

        if missing:
            step.status = "skipped"
            step.note = "missing values: " + ", ".join(missing)
            return step

        # Scope is checked *before* installation status: an out-of-scope target
        # must be surfaced as blocked regardless of whether the tool is present.
        if self.scope is not None and self.enforce_scope:
            targets = command_builder.target_values(template, values)
            if targets:
                _, denied = self.scope.check_targets(targets)
                if denied and not self.scope.is_empty():
                    step.status = "blocked"
                    step.note = "target not in scope: " + ", ".join(denied)
                    return step
                if denied and self.scope.is_empty():
                    step.status = "blocked"
                    step.note = "no scope defined — define an authorised scope first"
                    return step

        if self.tool_manager is not None and tool:
            status = self.tool_manager.status(tool)
            if status is not None and not status.installed:
                step.status = "skipped"
                step.note = f"{tool} is not installed"
                return step
        return step

    def _run_step(self, step: StepResult, outdir: Path, timeout: float | None) -> None:
        step.status = "running"
        out_file = outdir / f"{step.index:02d}_{step.tool or 'step'}.txt"
        step.output_file = str(out_file)
        proc = ManagedProcess(step.command, timeout=timeout)
        self._current = proc
        result = proc.run()
        self._current = None
        try:
            out_file.write_text(
                f"$ {step.command}\n\n{result.output}\n", encoding="utf-8",
            )
        except OSError:
            pass
        step.returncode = result.returncode
        step.duration = result.duration
        if result.timed_out:
            step.status = "failed"
            step.note = "timed out"
        elif result.ok:
            step.status = "done"
        else:
            step.status = "failed"
            step.note = result.error or f"exit code {result.returncode}"
        if self.audit is not None:
            self.audit.record(source="workflow", tool=step.tool, command=step.command,
                              decision=step.status, detail=step.note)

    def _write_summary(self, run: WorkflowRun) -> None:
        summary = {
            "name": run.name, "target": run.target, "status": run.status,
            "started": run.started, "finished": run.finished,
            "steps": [
                {"tool": s.tool, "command": s.command, "status": s.status,
                 "returncode": s.returncode, "output_file": s.output_file,
                 "duration": round(s.duration, 2), "note": s.note}
                for s in run.steps
            ],
        }
        try:
            (Path(run.outdir) / "summary.json").write_text(
                json.dumps(summary, indent=2), encoding="utf-8")
        except OSError:
            pass
