"""Credentials manager — stores discovered credentials per workspace with the
secret encrypted at rest via the secret vault's Fernet key."""
from __future__ import annotations

from dataclasses import dataclass

from database.database import Database
from core.secrets import SecretVault


@dataclass
class Credential:
    host: str = ""
    service: str = ""
    username: str = ""
    password: str = ""
    note: str = ""
    id: int | None = None
    workspace_id: int | None = None
    created: str = ""


class CredentialStore:
    def __init__(self, db: Database, vault: SecretVault):
        self.db = db
        self.vault = vault

    @property
    def encrypted(self) -> bool:
        return self.vault.encrypts_values

    def add(self, cred: Credential, workspace_id: int | None) -> int:
        record = {
            "workspace_id": workspace_id,
            "host": cred.host, "service": cred.service, "username": cred.username,
            "secret": self.vault.encrypt(cred.password), "note": cred.note,
        }
        return self.db.add_credential(record)

    def list(self, workspace_id: int | None, reveal: bool = False) -> list[dict]:
        out = []
        for row in self.db.credentials(workspace_id):
            item = dict(row)
            item["password"] = self.vault.decrypt(row["secret"]) if reveal else "••••••••"
            out.append(item)
        return out

    def reveal(self, row: dict) -> str:
        return self.vault.decrypt(row.get("secret", ""))

    def delete(self, cred_id: int) -> None:
        self.db.delete_credential(cred_id)
