"""Command template builder — turns a catalog command template such as
``nmap -sV -sC {target}`` into a concrete command by substituting placeholders,
and reports which placeholders still need a value.
"""
from __future__ import annotations

import re
import shlex

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

# Friendly descriptions used by the Command Builder form.
PLACEHOLDER_HINTS = {
    "target": "IP, host or CIDR to test",
    "host": "Target host / IP",
    "domain": "Target domain (example.com)",
    "url": "Full URL (https://example.com)",
    "cidr": "Network range (192.168.56.0/24)",
    "interface": "Network interface (eth0, wlan0)",
    "wordlist": "Path to a wordlist",
    "userlist": "Path to a username list",
    "user": "Username",
    "port": "Port number",
    "outfile": "Output file path",
    "outdir": "Output directory path",
    "file": "Path to input file",
    "image": "Disk/memory image or container image",
    "hashfile": "File containing hashes",
    "mode": "Hash mode (hashcat -m value)",
    "query": "Search term",
    "nameserver": "DNS server to query",
    "bssid": "Target BSSID (AA:BB:CC:DD:EE:FF)",
    "cover": "Cover file (carrier)",
    "secret": "File to hide",
    "package": "Android package name",
    "rules": "YARA rules file",
    "charset": "Character set for generation",
    "min": "Minimum length",
    "max": "Maximum length",
    "path": "Filesystem path",
}

# Placeholders that denote a remote target (subject to scope checks).
TARGET_PLACEHOLDERS = {"target", "host", "domain", "url", "cidr", "nameserver", "bssid"}


def placeholders(template: str) -> list[str]:
    seen: list[str] = []
    for name in _PLACEHOLDER_RE.findall(template):
        if name not in seen:
            seen.append(name)
    return seen


def hint_for(name: str) -> str:
    return PLACEHOLDER_HINTS.get(name, name.replace("_", " ").title())


def build(template: str, values: dict[str, str]) -> tuple[str, list[str]]:
    """Return (command, missing_placeholders). Values are shell-quoted when
    they contain whitespace or shell metacharacters so the result is safe to
    display and paste."""
    missing: list[str] = []

    def _sub(match: re.Match) -> str:
        name = match.group(1)
        value = values.get(name, "").strip()
        if not value:
            missing.append(name)
            return match.group(0)
        return _quote(value)

    command = _PLACEHOLDER_RE.sub(_sub, template)
    # de-dup missing while preserving order
    seen: list[str] = []
    for name in missing:
        if name not in seen:
            seen.append(name)
    return command.strip(), seen


def _quote(value: str) -> str:
    # URLs and simple tokens stay readable; quote only when necessary.
    if value and (value[0] in "\"'"):
        return value
    if re.search(r"[\s;&|<>$`\\]", value):
        return shlex.quote(value)
    return value


def target_values(template: str, values: dict[str, str]) -> list[str]:
    """Collect the concrete values that correspond to target placeholders."""
    out: list[str] = []
    for name in placeholders(template):
        if name in TARGET_PLACEHOLDERS:
            value = values.get(name, "").strip()
            if value:
                out.append(value)
    return out
