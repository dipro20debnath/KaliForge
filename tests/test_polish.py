"""Tests for the hardening/polish features: secret vault, report evidence embed,
extra workflows, command-palette scoring."""
import base64
from pathlib import Path

from core.reporting import ReportGenerator, ReportModel
from core.secrets import SecretVault
from core.workflow_engine import list_workflows
from core.config import WORKFLOWS_DIR


# ------------------------------------------------------------------- vault
def test_secret_vault_roundtrip(kf_home):
    vault = SecretVault()
    assert vault.available
    assert vault.set("anthropic_api_key", "sk-ant-SECRET-1")
    assert vault.get("anthropic_api_key") == "sk-ant-SECRET-1"
    assert vault.has("anthropic_api_key")
    assert vault.delete("anthropic_api_key")
    assert not vault.has("anthropic_api_key")


def test_secret_vault_no_plaintext_on_disk(kf_home):
    vault = SecretVault()
    vault.set("anthropic_api_key", "sk-ant-PLAINTEXT-CHECK")
    if vault.backend == "encrypted-file":
        from core.config import config_dir
        blob = (config_dir() / "secrets.enc").read_bytes()
        assert b"sk-ant-PLAINTEXT-CHECK" not in blob
    vault.delete("anthropic_api_key")


def test_api_key_migrates_to_vault(app):
    # simulate a legacy plaintext key in settings
    app.settings.set("ai.api_key", "sk-ant-LEGACY")
    app._migrate_api_key()
    if app.vault.available:
        assert app.vault.get("anthropic_api_key") == "sk-ant-LEGACY"
        assert app.settings.get("ai.api_key", "") == ""
        assert app.ai.api_key() == "sk-ant-LEGACY"


# -------------------------------------------------------------- report embed
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


def test_report_embeds_evidence(tmp_path):
    img = tmp_path / "shot.png"
    img.write_bytes(_PNG)
    evidence = [{"path": str(img), "original_path": str(img), "sha256": "a" * 64,
                 "kind": "screenshot", "note": "login"}]
    model = ReportModel(title="T", findings=[], evidence=evidence,
                        embed_evidence=True, summary="s")
    gen = ReportGenerator(model)
    html = gen.to_html()
    assert "data:image/png;base64" in html
    assert "<h2>Evidence</h2>" in html
    md = gen.to_markdown()
    assert "## Evidence" in md and "login" in md


def test_report_evidence_can_be_disabled(tmp_path):
    img = tmp_path / "shot.png"
    img.write_bytes(_PNG)
    evidence = [{"path": str(img), "original_path": str(img), "sha256": "a" * 64,
                 "kind": "screenshot", "note": "x"}]
    gen = ReportGenerator(ReportModel(title="T", evidence=evidence, embed_evidence=False))
    assert "data:image" not in gen.to_html()


# ----------------------------------------------------------------- workflows
def test_six_workflows_present():
    ids = {w["id"] for w in list_workflows(WORKFLOWS_DIR)}
    assert {"recon", "web_audit", "network_audit",
            "password_audit", "wireless_survey", "forensics_triage"} <= ids


# ------------------------------------------------------------------ palette
def test_palette_fuzzy_score():
    from ui.widgets.command_palette import _score
    assert _score("", "anything") == 0
    assert _score("nmap", "nmap network scanner") == 0        # exact substring at 0
    assert _score("hc", "hashcat") >= 0                        # subsequence match
    assert _score("zzz", "hashcat") == -1                      # no match
