"""Category definitions — the 14 segments plus the sidebar navigation map."""
from __future__ import annotations

# id -> (display name, short label, emoji/icon hint)
CATEGORIES = [
    {"id": "recon", "name": "Information Gathering & Reconnaissance", "label": "Recon", "icon": "🛰"},
    {"id": "web", "name": "Web Application Security", "label": "Web", "icon": "🌐"},
    {"id": "network", "name": "Network Analysis", "label": "Network", "icon": "🔌"},
    {"id": "vuln", "name": "Vulnerability Assessment", "label": "Vulnerability", "icon": "🛡"},
    {"id": "password", "name": "Password Security & Auditing", "label": "Password", "icon": "🔑"},
    {"id": "wireless", "name": "Wireless Security", "label": "Wireless", "icon": "📶"},
    {"id": "forensics", "name": "Digital Forensics", "label": "Forensics", "icon": "🔬"},
    {"id": "stego", "name": "Steganography", "label": "Stego", "icon": "🖼"},
    {"id": "reverse", "name": "Reverse Engineering & Malware Analysis", "label": "Reversing", "icon": "⚙"},
    {"id": "android", "name": "Android Security Testing", "label": "Android", "icon": "🤖"},
    {"id": "exploit", "name": "Exploitation & Security Validation", "label": "Exploitation", "icon": "💥"},
    {"id": "crypto", "name": "Cryptography & Encoding", "label": "Crypto", "icon": "🔐"},
    {"id": "cloud", "name": "Cloud & Container Security", "label": "Cloud", "icon": "☁"},
    {"id": "reporting", "name": "Reporting & Documentation", "label": "Reporting", "icon": "📄"},
]

CATEGORY_BY_ID = {c["id"]: c for c in CATEGORIES}


def category_name(cat_id: str) -> str:
    cat = CATEGORY_BY_ID.get(cat_id)
    return cat["name"] if cat else cat_id.title()


def category_label(cat_id: str) -> str:
    cat = CATEGORY_BY_ID.get(cat_id)
    return cat["label"] if cat else cat_id.title()
