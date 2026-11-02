"""Tests for dashboard-data, methodology checklist, credentials vault
encryption and workspace export/import."""
from pathlib import Path

from core import backup
from core.credentials import Credential, CredentialStore
from core.secrets import SecretVault
from database.models import Finding
from tools.methodology_data import TEMPLATE_BY_ID, TEMPLATES, total_items


# --------------------------------------------------------------- methodology
def test_methodology_templates_well_formed():
    assert len(TEMPLATES) >= 2
    for t in TEMPLATES:
        assert t["sections"]
        ids = [i["id"] for s in t["sections"] for i in s["items"]]
        assert len(ids) == len(set(ids))          # unique item ids
        assert total_items(t["id"]) == len(ids)


def test_checklist_state_persist(db):
    wstg = TEMPLATE_BY_ID["wstg"]
    item = wstg["sections"][0]["items"][0]["id"]
    db.set_checklist_item(1, "wstg", item, True, "done")
    state = db.checklist_state(1, "wstg")
    assert state[item]["checked"] is True
    assert state[item]["note"] == "done"
    db.set_checklist_item(1, "wstg", item, False)
    assert db.checklist_state(1, "wstg")[item]["checked"] is False


# --------------------------------------------------------------- credentials
def test_vault_value_encryption(kf_home):
    vault = SecretVault()
    token = vault.encrypt("s3cr3t")
    assert "s3cr3t" not in token
    assert vault.decrypt(token) == "s3cr3t"
    assert vault.decrypt(vault.encrypt("")) == ""


def test_credentials_store_encrypted(db, kf_home):
    vault = SecretVault()
    store = CredentialStore(db, vault)
    store.add(Credential(host="10.0.0.5", service="ssh", username="root",
                         password="toor"), workspace_id=1)
    masked = store.list(1, reveal=False)
    assert masked[0]["password"] == "••••••••"
    revealed = store.list(1, reveal=True)
    assert revealed[0]["password"] == "toor"
    # raw DB column must not contain the plaintext when crypto is available
    raw = db.credentials(1)[0]["secret"]
    if store.encrypted:
        assert "toor" not in raw
    store.delete(revealed[0]["id"])
    assert store.list(1) == []


# ----------------------------------------------------------------- backup
def test_workspace_export_import(app, tmp_path):
    ws = app.active_workspace_id()
    app.scope.add("10.0.0.0/24")
    app.db.upsert_finding(Finding(title="RCE", severity="critical", host="10.0.0.5",
                                  port="8080", workspace_id=ws))
    app.db.add_note("notes", "body", workspace_id=ws)
    from core.credentials import CredentialStore
    CredentialStore(app.db, app.vault).add(
        Credential(host="10.0.0.5", username="root", password="toor"), ws)

    out = tmp_path / "ws.kfw"
    backup.export_workspace(app, ws, out)
    assert out.exists()

    result = backup.import_workspace(app, out)
    new_id = result["id"]
    assert new_id != ws
    assert sum(app.db.severity_counts(new_id).values()) == 1
    assert len(app.db.notes(new_id)) == 1
    assert len(app.db.credentials(new_id)) == 1
    # imported credential still decrypts (same vault key)
    revealed = CredentialStore(app.db, app.vault).list(new_id, reveal=True)
    assert revealed[0]["password"] == "toor"


def test_export_unknown_workspace_raises(app, tmp_path):
    import pytest
    with pytest.raises(ValueError):
        backup.export_workspace(app, 99999, tmp_path / "x.kfw")
