import json

from core.reporting import ReportGenerator, ReportModel
from database.models import Finding, severity_from_cvss


def test_severity_from_cvss():
    assert severity_from_cvss(9.8) == "critical"
    assert severity_from_cvss(7.5) == "high"
    assert severity_from_cvss(5.0) == "medium"
    assert severity_from_cvss(2.0) == "low"
    assert severity_from_cvss(0) == "info"
    assert severity_from_cvss(None) == "info"


def test_findings_crud_and_dedup(db):
    f = Finding(title="Open port", severity="high", host="10.0.0.1", port="22", workspace_id=1)
    fid = db.upsert_finding(f)
    # same fingerprint updates, not duplicates
    again = db.upsert_finding(Finding(title="Open port", severity="critical",
                                      host="10.0.0.1", port="22", workspace_id=1))
    assert fid == again
    rows = db.findings(1)
    assert len(rows) == 1
    assert rows[0]["severity"] == "critical"
    db.set_finding_status(fid, "remediated")
    assert db.findings(1)[0]["status"] == "remediated"


def test_severity_counts(db):
    for i, sev in enumerate(("critical", "high", "high", "low")):
        db.upsert_finding(Finding(title=f"t-{i}", severity=sev,
                                  host="h", port=str(i), workspace_id=2))
    counts = db.severity_counts(2)
    assert counts.get("high") == 2
    assert counts.get("critical") == 1
    assert counts.get("low") == 1


def test_favorites_toggle(db):
    assert db.toggle_favorite("nmap") is True
    assert "nmap" in db.favorites()
    assert db.toggle_favorite("nmap") is False


def test_vault_and_history(db):
    vid = db.add_vault("Quick scan", "nmap -F {target}", "recon", "fast")
    assert db.vault("fast")[0]["id"] == vid
    db.bump_vault(vid)
    assert db.vault()[0]["uses"] == 1
    db.add_history("nmap -sV 10.0.0.1", "nmap", 1)
    assert db.history()[0]["command"].startswith("nmap")


def test_report_renders_all_formats():
    findings = [
        {"title": "RCE", "severity": "critical", "host": "10.0.0.1", "port": "8080",
         "cve": "CVE-2021-1", "cvss": 9.8, "description": "bad", "remediation": "patch",
         "status": "open", "evidence": "poc"},
        {"title": "Info leak", "severity": "low", "host": "10.0.0.2", "port": "",
         "cve": "", "cvss": None, "description": "", "remediation": "", "status": "open",
         "evidence": ""},
    ]
    model = ReportModel(title="T", findings=findings, scope=["10.0.0.0/24"], summary="s")
    gen = ReportGenerator(model)
    md = gen.to_markdown()
    assert "RCE" in md and "Critical" in md
    html = gen.to_html()
    assert "<html" in html and "RCE" in html
    data = json.loads(gen.to_json())
    assert data["severity_counts"]["critical"] == 1
    csv = gen.to_csv()
    assert "RCE" in csv
    # ordering: critical before low
    assert md.index("RCE") < md.index("Info leak")


def test_report_pdf_if_available(tmp_path):
    model = ReportModel(title="PDF", findings=[], summary="x")
    gen = ReportGenerator(model)
    if gen.pdf_available():
        out = gen.save(tmp_path / "r.pdf")
        assert out.exists() and out.stat().st_size > 0
