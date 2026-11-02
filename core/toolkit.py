"""Offline crypto/encoding toolkit — a mini CyberChef that needs no network and
no external tools. Encoders/decoders, a hash identifier and quick hashing."""
from __future__ import annotations

import base64
import binascii
import codecs
import hashlib
import html
import json
import re
import urllib.parse

# ---- encode / decode operations -------------------------------------------
# name -> (encode_fn, decode_fn|None). Functions take/return str and may raise.


def _b64_enc(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


def _b64_dec(s: str) -> str:
    pad = "=" * (-len(s.strip()) % 4)
    return base64.b64decode(s.strip() + pad).decode("utf-8", "replace")


def _b64url_dec(s: str) -> str:
    s = s.strip()
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad).decode("utf-8", "replace")


def _b32_enc(s: str) -> str:
    return base64.b32encode(s.encode()).decode()


def _b32_dec(s: str) -> str:
    return base64.b32decode(s.strip()).decode("utf-8", "replace")


def _hex_enc(s: str) -> str:
    return s.encode().hex()


def _hex_dec(s: str) -> str:
    cleaned = re.sub(r"[\s:]", "", s.strip())
    return bytes.fromhex(cleaned).decode("utf-8", "replace")


def _url_enc(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def _url_dec(s: str) -> str:
    return urllib.parse.unquote(s)


def _rot13(s: str) -> str:
    return codecs.encode(s, "rot_13")


def _html_enc(s: str) -> str:
    return html.escape(s)


def _html_dec(s: str) -> str:
    return html.unescape(s)


def _bin_enc(s: str) -> str:
    return " ".join(format(b, "08b") for b in s.encode())


def _bin_dec(s: str) -> str:
    bits = re.sub(r"\s", "", s.strip())
    if len(bits) % 8:
        raise ValueError("bit length not a multiple of 8")
    data = bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))
    return data.decode("utf-8", "replace")


def _a85_enc(s: str) -> str:
    return base64.a85encode(s.encode()).decode()


def _a85_dec(s: str) -> str:
    return base64.a85decode(s.strip()).decode("utf-8", "replace")


OPERATIONS = {
    "Base64": (_b64_enc, _b64_dec),
    "Base64 URL-safe": (lambda s: base64.urlsafe_b64encode(s.encode()).decode(), _b64url_dec),
    "Base32": (_b32_enc, _b32_dec),
    "Hex": (_hex_enc, _hex_dec),
    "URL encoding": (_url_enc, _url_dec),
    "ROT13": (_rot13, _rot13),
    "HTML entities": (_html_enc, _html_dec),
    "Binary": (_bin_enc, _bin_dec),
    "ASCII85": (_a85_enc, _a85_dec),
}


def transform(operation: str, text: str, decode: bool) -> str:
    enc, dec = OPERATIONS[operation]
    fn = dec if decode else enc
    if fn is None:
        raise ValueError(f"{operation} does not support that direction")
    return fn(text)


# ---- quick hashing ---------------------------------------------------------
def hash_text(text: str) -> dict[str, str]:
    data = text.encode()
    out = {}
    for algo in ("md5", "sha1", "sha256", "sha512"):
        out[algo] = hashlib.new(algo, data).hexdigest()
    out["crc32"] = format(binascii.crc32(data) & 0xFFFFFFFF, "08x")
    return out


# ---- hash identifier -------------------------------------------------------
# (name, compiled-regex, hashcat-mode hint)
_HASH_SIGS = [
    ("bcrypt", re.compile(r"^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$"), "3200"),
    ("Argon2", re.compile(r"^\$argon2(id|i|d)\$"), "—"),
    ("SHA-512 crypt", re.compile(r"^\$6\$"), "1800"),
    ("SHA-256 crypt", re.compile(r"^\$5\$"), "7400"),
    ("MD5 crypt", re.compile(r"^\$1\$"), "500"),
    ("MySQL 4.1+", re.compile(r"^\*[0-9A-Fa-f]{40}$"), "300"),
    ("JWT", re.compile(r"^eyJ[0-9A-Za-z_\-]+\.eyJ[0-9A-Za-z_\-]+\.[0-9A-Za-z_\-]*$"), "—"),
    ("SHA-512", re.compile(r"^[0-9a-fA-F]{128}$"), "1700"),
    ("SHA-384", re.compile(r"^[0-9a-fA-F]{96}$"), "10800"),
    ("SHA-256", re.compile(r"^[0-9a-fA-F]{64}$"), "1400"),
    ("SHA-224", re.compile(r"^[0-9a-fA-F]{56}$"), "1300"),
    ("SHA-1", re.compile(r"^[0-9a-fA-F]{40}$"), "100"),
    ("CRC-32", re.compile(r"^[0-9a-fA-F]{8}$"), "—"),
]

# ambiguous 32-hex: list all candidates
_32HEX = re.compile(r"^[0-9a-fA-F]{32}$")


def identify_hash(value: str) -> list[dict]:
    value = value.strip()
    if not value:
        return []
    results = []
    for name, rx, mode in _HASH_SIGS:
        if rx.match(value):
            results.append({"name": name, "hashcat": mode})
    if _32HEX.match(value):
        for name, mode in [("MD5", "0"), ("NTLM", "1000"), ("MD4", "900"),
                           ("LM", "3000"), ("MD2", "—")]:
            results.append({"name": name, "hashcat": mode})
    if not results:
        results.append({"name": "Unknown / not a recognised hash", "hashcat": "—"})
    return results
