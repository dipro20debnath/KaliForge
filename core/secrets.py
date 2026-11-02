"""Secret vault for API keys and other sensitive values.

Resolution order for storing/reading a secret:

1. **System keyring** (python ``keyring``) when available and functional — the
   OS keychain / Secret Service, the most secure option.
2. **Encrypted file** (``cryptography`` Fernet) under the config dir, with a
   per-install key file (``0600``). Used when no keyring backend is usable.
3. **Plaintext fallback** is never used — if neither backend works the vault
   reports unavailable and callers fall back to the environment variable.

This replaces storing API keys in ``settings.json``.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from core.config import config_dir

SERVICE = "kaliforge"

try:
    import keyring
    from keyring.errors import KeyringError
    _HAVE_KEYRING = True
except Exception:  # noqa: BLE001
    keyring = None
    KeyringError = Exception
    _HAVE_KEYRING = False

try:
    from cryptography.fernet import Fernet, InvalidToken
    _HAVE_CRYPTO = True
except Exception:  # noqa: BLE001
    Fernet = None
    InvalidToken = Exception
    _HAVE_CRYPTO = False


class SecretVault:
    def __init__(self):
        self._key_file = config_dir() / ".vault.key"
        self._store_file = config_dir() / "secrets.enc"
        self._fernet = self._init_fernet() if _HAVE_CRYPTO else None
        self._keyring_ok = self._probe_keyring()

    # ------------------------------------------------------------- backends
    def _probe_keyring(self) -> bool:
        if not _HAVE_KEYRING:
            return False
        try:
            # a no-op round-trip to confirm a real backend is present
            keyring.get_password(SERVICE, "__probe__")
            backend = keyring.get_keyring().__class__.__name__
            return "fail" not in backend.lower()
        except Exception:  # noqa: BLE001
            return False

    def _init_fernet(self):
        try:
            if self._key_file.exists():
                key = self._key_file.read_bytes()
            else:
                key = Fernet.generate_key()
                self._key_file.write_bytes(key)
                try:
                    os.chmod(self._key_file, 0o600)
                except OSError:
                    pass
            return Fernet(key)
        except Exception:  # noqa: BLE001
            return None

    @property
    def backend(self) -> str:
        if self._keyring_ok:
            return "keyring"
        if self._fernet is not None:
            return "encrypted-file"
        return "unavailable"

    @property
    def available(self) -> bool:
        return self.backend != "unavailable"

    # --------------------------------------------------------------- file io
    def _read_store(self) -> dict:
        if self._fernet is None or not self._store_file.exists():
            return {}
        try:
            raw = self._fernet.decrypt(self._store_file.read_bytes())
            return json.loads(raw.decode("utf-8"))
        except (InvalidToken, ValueError, OSError):
            return {}

    def _write_store(self, data: dict) -> None:
        if self._fernet is None:
            return
        token = self._fernet.encrypt(json.dumps(data).encode("utf-8"))
        self._store_file.write_bytes(token)
        try:
            os.chmod(self._store_file, 0o600)
        except OSError:
            pass

    # ----------------------------------------------------------------- api
    def set(self, name: str, value: str) -> bool:
        if not value:
            return self.delete(name)
        if self._keyring_ok:
            try:
                keyring.set_password(SERVICE, name, value)
                return True
            except KeyringError:
                self._keyring_ok = False
        if self._fernet is not None:
            data = self._read_store()
            data[name] = value
            self._write_store(data)
            return True
        return False

    def get(self, name: str) -> str:
        if self._keyring_ok:
            try:
                value = keyring.get_password(SERVICE, name)
                if value:
                    return value
            except KeyringError:
                self._keyring_ok = False
        if self._fernet is not None:
            return self._read_store().get(name, "")
        return ""

    def delete(self, name: str) -> bool:
        ok = False
        if self._keyring_ok:
            try:
                keyring.delete_password(SERVICE, name)
                ok = True
            except Exception:  # noqa: BLE001
                pass
        if self._fernet is not None:
            data = self._read_store()
            if name in data:
                del data[name]
                self._write_store(data)
                ok = True
        return ok

    def has(self, name: str) -> bool:
        return bool(self.get(name))

    # ---------------------------------------------------- value encryption
    def encrypt(self, text: str) -> str:
        """Encrypt an arbitrary value for storage in the app DB (e.g. a
        credential). Returns a tagged token so decryption knows the scheme."""
        if self._fernet is not None:
            return "enc:" + self._fernet.encrypt((text or "").encode()).decode()
        return "raw:" + (text or "")

    def decrypt(self, token: str) -> str:
        if not token:
            return ""
        if token.startswith("enc:") and self._fernet is not None:
            try:
                return self._fernet.decrypt(token[4:].encode()).decode("utf-8", "replace")
            except InvalidToken:
                return ""
        if token.startswith("raw:"):
            return token[4:]
        return token

    @property
    def encrypts_values(self) -> bool:
        return self._fernet is not None
