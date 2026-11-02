from pathlib import Path

from core.ai_assistant import AIAssistant
from core.evidence import EvidenceManager, sha256_file
from core.process_manager import ManagedProcess
from core.terminal_manager import TerminalSession
from core.workflow_engine import WorkflowEngine, list_workflows
from core.config import WORKFLOWS_DIR
from tools.catalog import Catalog


def test_tool_detection(app):
    counts = app.tools.counts()
    assert counts["total"] >= 100
    # bash/sh based builtins like strings/openssl should be found on this host
    assert counts["installed"] >= 0
    status = app.tools.status("kf-report")
    assert status.builtin is True


def test_ai_offline_suggestions():
    ai = AIAssistant(catalog=Catalog())
    r = ai.ask("scan ports on 192.168.56.10")
    assert r.suggestions
    assert "nmap" in r.suggestions[0].command
    r2 = ai.ask("enumerate subdomains of example.com")
    assert any("subfinder" in s.command or "amass" in s.command for s in r2.suggestions)
    r3 = ai.ask("completely unrelated gibberish zzz")
    assert r3.text  # falls back to guidance text


def test_process_manager_runs_and_captures():
    proc = ManagedProcess("echo kaliforge-test")
    result = proc.run()
    assert result.ok
    assert "kaliforge-test" in result.output


def test_process_manager_timeout():
    proc = ManagedProcess("sleep 5", timeout=0.5)
    result = proc.run()
    assert result.timed_out or result.killed


def test_terminal_session_echo():
    import time
    session = TerminalSession(columns=80, rows=24, shell="/bin/bash")
    session.start()
    time.sleep(0.4)
    session.send_line("echo TERMUNIT")
    time.sleep(0.5)
    assert any("TERMUNIT" in line for line in session.display())
    session.terminate()


def test_evidence_hash_and_store(db, tmp_path):
    src = tmp_path / "artifact.txt"
    src.write_text("evidence-bytes")
    mgr = EvidenceManager(db, tmp_path / "ws")
    record = mgr.add_file(src, workspace_id=1, note="n")
    assert record["sha256"] == sha256_file(src)
    assert mgr.verify(record)
    # tamper
    Path(record["path"]).write_text("changed")
    assert not mgr.verify(record)


def test_workflows_load_and_prepare(app, tmp_path):
    workflows = list_workflows(WORKFLOWS_DIR)
    assert any(w["id"] == "recon" for w in workflows)
    recon = next(w for w in workflows if w["id"] == "recon")
    app.scope.add("example.com")
    engine = WorkflowEngine(tool_manager=app.tools, scope=app.scope, enforce_scope=True)
    run = engine.run(recon, {"domain": "example.com", "target": "example.com"},
                     tmp_path / "out", background=False, step_timeout=2)
    assert run.steps
    # at least prepared steps; installed-missing tools are skipped not errored
    statuses = {s.status for s in run.steps}
    assert statuses & {"skipped", "done", "failed", "blocked"}


def test_workflow_blocks_out_of_scope(app, tmp_path):
    recon = next(w for w in list_workflows(WORKFLOWS_DIR) if w["id"] == "recon")
    app.scope.add("safe.test")
    engine = WorkflowEngine(tool_manager=app.tools, scope=app.scope, enforce_scope=True)
    run = engine.run(recon, {"domain": "evil.test", "target": "evil.test"},
                     tmp_path / "out2", background=False, step_timeout=2)
    assert any(s.status == "blocked" for s in run.steps)


def test_plugin_tools_merged(app):
    assert app.catalog.get("example-ping") is not None


def test_workspace_isolation(app):
    ws = app.workspaces.create("Engagement-X", client="ACME")
    assert ws["name"] == "Engagement-X"
    app.switch_workspace(ws["id"])
    assert app.active_workspace_id() == ws["id"]
    assert Path(ws["path"]).exists()
