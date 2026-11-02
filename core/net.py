"""Minimal HTTP helper built on urllib so KaliForge has no hard 'requests'
dependency. Honours the environment proxy and a custom CA bundle when present
(the cloud build sets one), and always applies a timeout."""
from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "KaliForge/1.0 (+security-dashboard)"
_CA_CANDIDATES = ["/root/.ccr/ca-bundle.crt", os.environ.get("REQUESTS_CA_BUNDLE", ""),
                  os.environ.get("SSL_CERT_FILE", "")]


def _ssl_context() -> ssl.SSLContext:
    for candidate in _CA_CANDIDATES:
        if candidate and Path(candidate).exists():
            try:
                return ssl.create_default_context(cafile=candidate)
            except (ssl.SSLError, OSError):
                continue
    return ssl.create_default_context()


class HttpError(Exception):
    pass


def get(url: str, timeout: float = 20.0, headers: dict | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise HttpError(f"HTTP {exc.code} for {url}") from exc
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise HttpError(f"request failed: {exc}") from exc


def get_json(url: str, timeout: float = 20.0, headers: dict | None = None) -> dict:
    raw = get(url, timeout=timeout, headers=headers)
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except ValueError as exc:
        raise HttpError(f"invalid JSON from {url}") from exc


def get_text(url: str, timeout: float = 20.0, headers: dict | None = None) -> str:
    return get(url, timeout=timeout, headers=headers).decode("utf-8", "replace")
