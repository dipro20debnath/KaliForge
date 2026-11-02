"""Methodology checklist templates (OWASP WSTG subset and PTES phases).

Each template: {id, name, sections: [{name, items: [{id, text}]}]}. Item ids are
stable so progress survives edits.
"""
from __future__ import annotations

TEMPLATES = [
    {
        "id": "wstg",
        "name": "OWASP WSTG (Web)",
        "sections": [
            {"name": "Information Gathering", "items": [
                {"id": "wstg-info-01", "text": "Fingerprint web server & technologies"},
                {"id": "wstg-info-02", "text": "Enumerate applications on the webserver"},
                {"id": "wstg-info-03", "text": "Review webpage content / comments for leaks"},
                {"id": "wstg-info-04", "text": "Identify entry points (params, headers, cookies)"},
                {"id": "wstg-info-05", "text": "Map the application (spider/crawl)"},
            ]},
            {"name": "Configuration & Deployment", "items": [
                {"id": "wstg-conf-01", "text": "Test TLS/SSL configuration & ciphers"},
                {"id": "wstg-conf-02", "text": "Check for default/admin interfaces"},
                {"id": "wstg-conf-03", "text": "Review HTTP security headers"},
                {"id": "wstg-conf-04", "text": "Look for backup/old/exposed files"},
            ]},
            {"name": "Authentication & Session", "items": [
                {"id": "wstg-auth-01", "text": "Test for weak/default credentials"},
                {"id": "wstg-auth-02", "text": "Test account lockout / brute-force protection"},
                {"id": "wstg-auth-03", "text": "Review session token randomness & flags"},
                {"id": "wstg-auth-04", "text": "Test logout and session timeout"},
            ]},
            {"name": "Input Validation", "items": [
                {"id": "wstg-inpv-01", "text": "Test for SQL injection"},
                {"id": "wstg-inpv-02", "text": "Test for reflected/stored/DOM XSS"},
                {"id": "wstg-inpv-03", "text": "Test for command injection"},
                {"id": "wstg-inpv-04", "text": "Test for SSRF / open redirect"},
                {"id": "wstg-inpv-05", "text": "Test for file upload flaws"},
            ]},
            {"name": "Authorization & Business Logic", "items": [
                {"id": "wstg-athz-01", "text": "Test for IDOR / broken object-level auth"},
                {"id": "wstg-athz-02", "text": "Test privilege escalation paths"},
                {"id": "wstg-busl-01", "text": "Test business-logic / workflow bypasses"},
            ]},
        ],
    },
    {
        "id": "ptes",
        "name": "PTES (Engagement)",
        "sections": [
            {"name": "Pre-engagement", "items": [
                {"id": "ptes-pre-01", "text": "Scope & rules of engagement agreed in writing"},
                {"id": "ptes-pre-02", "text": "Authorisation / get-out-of-jail documented"},
                {"id": "ptes-pre-03", "text": "Emergency contacts & test windows set"},
            ]},
            {"name": "Intelligence Gathering", "items": [
                {"id": "ptes-intel-01", "text": "Passive OSINT on target"},
                {"id": "ptes-intel-02", "text": "Active host/service discovery"},
                {"id": "ptes-intel-03", "text": "Map the attack surface"},
            ]},
            {"name": "Threat Modeling & Vuln Analysis", "items": [
                {"id": "ptes-vuln-01", "text": "Identify likely attack vectors"},
                {"id": "ptes-vuln-02", "text": "Run vulnerability scans"},
                {"id": "ptes-vuln-03", "text": "Validate findings (reduce false positives)"},
            ]},
            {"name": "Exploitation & Post-Exploitation", "items": [
                {"id": "ptes-expl-01", "text": "Exploit validated vulnerabilities (authorised)"},
                {"id": "ptes-post-01", "text": "Assess impact / data access"},
                {"id": "ptes-post-02", "text": "Test lateral movement / persistence (if in scope)"},
                {"id": "ptes-post-03", "text": "Clean up artefacts & restore state"},
            ]},
            {"name": "Reporting", "items": [
                {"id": "ptes-rep-01", "text": "Document findings with evidence & severity"},
                {"id": "ptes-rep-02", "text": "Provide remediation guidance"},
                {"id": "ptes-rep-03", "text": "Deliver & walk through the report"},
            ]},
        ],
    },
]

TEMPLATE_BY_ID = {t["id"]: t for t in TEMPLATES}


def total_items(template_id: str) -> int:
    t = TEMPLATE_BY_ID.get(template_id)
    if not t:
        return 0
    return sum(len(s["items"]) for s in t["sections"])
