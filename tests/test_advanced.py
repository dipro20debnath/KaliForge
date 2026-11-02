"""Tests for the Phase 3-5 advanced modules: attack surface, tool health,
installer, learning and lab environments."""
from core import learning
from core.attack_surface import AttackSurface
from core.installer import InstallManager
from core.lab_env import LABS, LabManager
from core.tool_health import ToolHealth
from database.models import Finding


# ------------------------------------------------------------- attack surface
def test_attack_surface_build_and_edges(app):
    ws = app.active_workspace_id()
    app.scope.add("example.com")
    app.scope.add("192.168.56.0/24")
    surface = AttackSurface(app.db, ws)
    assert surface.seed_from_scope(app.scope.entries()) == 2
    app.db.upsert_finding(Finding(title="SSH", host="192.168.56.5", port="22",
                                  service="ssh", workspace_id=ws))
    assert surface.seed_from_findings() == 1
    graph = surface.build()
    assert graph.stats()["total"] >= 4
    # the port should hang off its host via an edge
    assert any(graph.children_of(n.id) for n in graph.nodes)


def test_attack_surface_import_text(app):
    surface = AttackSurface(app.db, app.active_workspace_id())
    text = ("Nmap scan report for web.corp.test (10.0.0.9)\n"
            "22/tcp open ssh\n80/tcp open http\n")
    added = surface.import_text(text, root="corp.test")
    assert added >= 3
    labels = {n.label for n in surface.build().nodes}
    assert "10.0.0.9" in labels
    assert any("22/tcp" in lbl for lbl in labels)


def test_attack_surface_clear(app):
    surface = AttackSurface(app.db, app.active_workspace_id())
    surface.add("domain", "a.test")
    assert surface.build().nodes
    surface.clear()
    assert not surface.build().nodes


# ---------------------------------------------------------------- tool health
def test_tool_health_builtin_and_missing(app):
    health = ToolHealth(app.tools)
    builtin = health.check(app.catalog.get("kf-report"))
    assert builtin.status == "builtin"
    # a definitely-missing tool
    report = health.check(app.catalog.get("maltego"))
    assert report.status == "missing"


def test_tool_health_summary(app):
    health = ToolHealth(app.tools)
    reports = health.check_installed(app.catalog, probe_version=False)
    summary = health.summary(reports)
    assert set(summary) >= {"ok", "degraded", "builtin", "missing"}
    assert sum(summary.values()) == len(reports)


# ----------------------------------------------------------------- installer
def test_installer_missing_and_plan(app):
    installer = InstallManager(app.catalog, app.tools)
    missing = installer.missing()
    assert len(missing) > 0
    plan = installer.plan(["nmap", "amass", "mobsf"])
    assert "nmap" in plan.apt_packages
    assert any(m["name"] == "MobSF" for m in plan.manual)
    assert plan.apt_command.startswith("sudo apt")
    script = installer.script(plan)
    assert "apt install" in script and "MobSF" in script


def test_installer_groups_by_category(app):
    installer = InstallManager(app.catalog, app.tools)
    grouped = installer.missing_by_category()
    assert grouped
    assert all(isinstance(v, list) for v in grouped.values())


# ------------------------------------------------------------------ learning
def test_learning_modules_and_ids():
    ids = learning.learnable_tool_ids()
    assert "nmap" in ids
    assert learning.has_learning("nmap")
    assert learning.modules_for("nmap")
    assert not learning.modules_for("nonexistent")


def test_command_explainer():
    exp = learning.explain("nmap -sV -sC 192.168.56.101")
    assert exp.program == "nmap"
    roles = {p.token: p.role for p in exp.parts}
    assert roles["-sV"] == "flag"
    assert roles["192.168.56.101"] == "target"
    descs = {p.token: p.description for p in exp.parts}
    assert "version" in descs["-sV"].lower()


def test_command_explainer_subcommand():
    exp = learning.explain("gobuster dir -u http://t.test -w list.txt")
    roles = {p.token: p.role for p in exp.parts}
    assert roles["dir"] == "subcommand"
    assert roles["-u"] == "flag"


# ------------------------------------------------------------------ lab env
def test_lab_definitions():
    assert len(LABS) >= 5
    juice = next(l for l in LABS if l.id == "juiceshop")
    assert juice.url == "http://127.0.0.1:3000/"
    assert "docker run" in juice.run_command()
    assert juice.container in juice.stop_command()


def test_lab_manager_status_no_crash():
    mgr = LabManager()
    # should not raise even if docker is absent
    status = mgr.status(LABS[0])
    assert hasattr(status, "running")
