"""Static analysis helpers for shell commands: tokenising, target extraction
and dangerous-pattern detection. Pure functions — no side effects — so they are
easy to unit test and are reused by the permission manager, terminal and AI
assistant alike.
"""
from __future__ import annotations

import ipaddress
import re
import shlex

# Flags/values that are never targets even though they look host-ish.
_SKIP_VALUES = {"-", "localhost", "127.0.0.1", "::1", "0.0.0.0"}

# Common file extensions — a dotted token ending in one of these is a filename,
# not a domain (e.g. ``hash.txt``, ``rockyou.txt``, ``image.raw``).
_FILE_EXTS = {
    "txt", "log", "out", "csv", "json", "xml", "html", "htm", "md", "pdf",
    "png", "jpg", "jpeg", "gif", "bmp", "svg", "pcap", "pcapng", "cap",
    "raw", "img", "bin", "dd", "e01", "mem", "dmp", "vmem", "zip", "tar",
    "gz", "tgz", "bz2", "xz", "7z", "rar", "db", "sqlite", "conf", "cfg",
    "ini", "yaml", "yml", "sh", "py", "rb", "pl", "php", "js", "exe", "dll",
    "apk", "jar", "so", "elf", "dex", "list", "dic", "lst", "hash", "hccapx",
    "pem", "key", "crt", "cer", "pub", "wordlist", "rule",
}

_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_CIDR_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")

# Destructive / high-impact command signatures. Each tuple: (compiled regex,
# human explanation). These are matched against the raw command string.
_DANGEROUS = [
    (re.compile(r"\brm\s+(-[a-zA-Z]*\s+)*-[a-zA-Z]*[rf]", re.I), "Recursive/forced file deletion (rm -rf)"),
    (re.compile(r"\brm\s+-[a-zA-Z]*r", re.I), "Recursive file deletion"),
    (re.compile(r"\bmkfs(\.\w+)?\b", re.I), "Formats a filesystem"),
    (re.compile(r"\bdd\b.*\bof=/dev/", re.I), "Writes directly to a block device"),
    (re.compile(r">\s*/dev/sd[a-z]", re.I), "Overwrites a raw disk device"),
    (re.compile(r":\(\)\s*\{\s*:\|:&\s*\}\s*;", ), "Fork-bomb pattern"),
    (re.compile(r"\bshred\b", re.I), "Securely erases files"),
    (re.compile(r"\bwipefs\b", re.I), "Wipes filesystem signatures"),
    (re.compile(r"\b(shutdown|reboot|halt|poweroff|init\s+0)\b", re.I), "Shuts down or reboots the host"),
    (re.compile(r"\biptables\s+-F\b", re.I), "Flushes all firewall rules"),
    (re.compile(r"\bchmod\s+-R\s+777\b", re.I), "Recursively makes files world-writable"),
    (re.compile(r"\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(bash|sh|zsh)\b", re.I), "Pipes a remote script straight into a shell"),
    (re.compile(r"\bmv\s+[^ ]+\s+/dev/null\b", re.I), "Destroys data by moving it to /dev/null"),
    (re.compile(r">\s*/etc/(passwd|shadow|fstab)\b", re.I), "Overwrites a critical system file"),
]

_SUDO_RE = re.compile(r"(^|[|&;]\s*)sudo\b")


def tokenize(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def is_target_token(token: str) -> bool:
    token = token.strip()
    if not token or token.startswith("-") or token in _SKIP_VALUES:
        return False
    if _URL_RE.match(token) or _CIDR_RE.match(token):
        return True
    if _IP_RE.match(token):
        try:
            ipaddress.ip_address(token)
            return True
        except ValueError:
            return False
    host = token.split("@")[-1]
    if "/" in host:  # looks like a path, not a bare host
        return False
    last = host.rsplit(".", 1)[-1].lower()
    if last in _FILE_EXTS:
        return False
    return bool(_DOMAIN_RE.match(host))


def extract_targets(command: str) -> list[str]:
    """Pull out IP/CIDR/URL/domain style arguments that denote remote targets."""
    targets: list[str] = []
    for token in tokenize(command):
        # strip common proto prefixes like ssh://, smb:// for matching
        candidate = token
        if "://" in candidate and not _URL_RE.match(candidate):
            candidate = candidate.split("://", 1)[1]
        if is_target_token(token) and token not in targets:
            targets.append(token)
        elif candidate != token and is_target_token(candidate) and candidate not in targets:
            targets.append(candidate)
    return targets


def dangerous_reasons(command: str) -> list[str]:
    return [reason for pattern, reason in _DANGEROUS if pattern.search(command)]


def uses_sudo(command: str) -> bool:
    return bool(_SUDO_RE.search(command))


def program_name(command: str) -> str:
    tokens = tokenize(command)
    for token in tokens:
        if token == "sudo" or "=" in token:
            continue
        return token.split("/")[-1]
    return tokens[0] if tokens else ""
