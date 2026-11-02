"""Scan-output parsers — turn tool output (nmap XML/normal, nuclei JSON,
gobuster) into KaliForge findings and attack-surface assets.

Each parser returns a :class:`ParseResult`; the UI persists findings via
``db.upsert_finding`` and assets via ``AttackSurface.add``.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

from database.models import Finding, severity_from_cvss

_NUCLEI_SEV = {"critical": "critical", "high": "high", "medium": "medium",
               "low": "low", "info": "info", "unknown": "info"}


@dataclass
class ParseResult:
    findings: list[dict] = field(default_factory=list)   # Finding-compatible dicts
    assets: list[dict] = field(default_factory=list)     # {kind,value,parent,meta}
    source: str = ""
    error: str = ""

    def summary(self) -> str:
        if self.error:
            return f"error: {self.error}"
        return f"{len(self.findings)} finding(s), {len(self.assets)} asset(s)"

    def to_findings(self, workspace_id=None) -> list[Finding]:
        out = []
        for f in self.findings:
            out.append(Finding(
                title=f.get("title", "Untitled"), severity=f.get("severity", "info"),
                host=f.get("host", ""), port=str(f.get("port", "")),
                service=f.get("service", ""), cve=f.get("cve", ""),
                cvss=f.get("cvss"), description=f.get("description", ""),
                source=self.source, workspace_id=workspace_id))
        return out


def detect_format(text: str) -> str:
    stripped = text.lstrip()
    if stripped.startswith("<?xml") or "<nmaprun" in stripped[:200]:
        return "nmap-xml"
    if stripped.startswith("{") or stripped.startswith("["):
        return "nuclei-json"
    if "Nmap scan report" in text:
        return "nmap-normal"
    if re.search(r"\(Status:\s*\d+\)", text):
        return "gobuster"
    return "nmap-normal"


def parse(text: str, fmt: str | None = None) -> ParseResult:
    fmt = fmt or detect_format(text)
    try:
        if fmt == "nmap-xml":
            return parse_nmap_xml(text)
        if fmt == "nuclei-json":
            return parse_nuclei(text)
        if fmt == "gobuster":
            return parse_gobuster(text)
        return parse_nmap_normal(text)
    except Exception as exc:  # noqa: BLE001
        return ParseResult(source=fmt or "import", error=str(exc))


# ------------------------------------------------------------------ nmap xml
def parse_nmap_xml(text: str) -> ParseResult:
    result = ParseResult(source="nmap")
    root = ET.fromstring(text)
    for host in root.findall("host"):
        state = host.find("status")
        if state is not None and state.get("state") == "down":
            continue
        addr = ""
        for a in host.findall("address"):
            if a.get("addrtype") in ("ipv4", "ipv6"):
                addr = a.get("addr", "")
                break
        hostname = ""
        hn = host.find("hostnames/hostname")
        if hn is not None:
            hostname = hn.get("name", "")
        node = hostname or addr
        if not node:
            continue
        if addr:
            result.assets.append({"kind": "ip", "value": addr, "parent": hostname})
        if hostname:
            result.assets.append({"kind": "host", "value": hostname, "parent": ""})
        for port in host.findall("ports/port"):
            st = port.find("state")
            if st is None or st.get("state") != "open":
                continue
            portid = port.get("portid", "")
            proto = port.get("protocol", "tcp")
            svc = port.find("service")
            name = svc.get("name", "") if svc is not None else ""
            product = svc.get("product", "") if svc is not None else ""
            version = svc.get("version", "") if svc is not None else ""
            banner = " ".join(x for x in (product, version) if x)
            result.assets.append({"kind": "port", "value": f"{portid}/{proto}",
                                  "parent": node, "meta": {"service": name}})
            result.findings.append({
                "title": f"Open port {portid}/{proto} ({name or 'unknown'})",
                "severity": "info", "host": node, "port": portid, "service": name,
                "description": f"Service: {name} {banner}".strip()})
    return result


# --------------------------------------------------------------- nmap normal
_NORMAL_HOST = re.compile(r"Nmap scan report for (\S+)(?:\s+\(([\d.]+)\))?")
_NORMAL_PORT = re.compile(r"^(\d{1,5})/(tcp|udp)\s+open\s+(\S+)(?:\s+(.*))?$", re.M)


def parse_nmap_normal(text: str) -> ParseResult:
    result = ParseResult(source="nmap")
    blocks = re.split(r"(?=Nmap scan report for )", text)
    for block in blocks:
        m = _NORMAL_HOST.search(block)
        if not m:
            continue
        name, ip = m.group(1), m.group(2)
        node = name
        if ip:
            result.assets.append({"kind": "ip", "value": ip, "parent": name})
        result.assets.append({"kind": "host", "value": name, "parent": ""})
        for pm in _NORMAL_PORT.finditer(block):
            portid, proto, svc, banner = pm.group(1), pm.group(2), pm.group(3), (pm.group(4) or "")
            result.assets.append({"kind": "port", "value": f"{portid}/{proto}",
                                  "parent": node, "meta": {"service": svc}})
            result.findings.append({
                "title": f"Open port {portid}/{proto} ({svc})",
                "severity": "info", "host": node, "port": portid, "service": svc,
                "description": banner.strip()})
    return result


# ------------------------------------------------------------------- nuclei
def parse_nuclei(text: str) -> ParseResult:
    result = ParseResult(source="nuclei")
    rows = []
    text = text.strip()
    if text.startswith("["):
        rows = json.loads(text)
    else:
        for line in text.splitlines():
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    for row in rows:
        info = row.get("info", {})
        sev = _NUCLEI_SEV.get((info.get("severity") or "info").lower(), "info")
        host = row.get("host") or row.get("matched-at") or ""
        from core.scope_manager import host_of
        host_clean = host_of(host)
        cve = ""
        classification = info.get("classification") or {}
        cve_ids = classification.get("cve-id") or []
        if cve_ids:
            cve = cve_ids[0] if isinstance(cve_ids, list) else str(cve_ids)
        cvss = None
        if classification.get("cvss-score"):
            try:
                cvss = float(classification["cvss-score"])
            except (ValueError, TypeError):
                cvss = None
        result.findings.append({
            "title": info.get("name") or row.get("template-id", "nuclei finding"),
            "severity": severity_from_cvss(cvss) if cvss else sev,
            "host": host_clean, "cve": cve, "cvss": cvss,
            "description": f"{info.get('description', '')}\nMatched: {row.get('matched-at', '')}".strip()})
        if host_clean:
            result.assets.append({"kind": "host", "value": host_clean, "parent": ""})
    return result


# ----------------------------------------------------------------- gobuster
_GOBUSTER = re.compile(r"^(/\S*)\s+\(Status:\s*(\d+)\)(?:\s+\[Size:\s*(\d+)\])?", re.M)


def parse_gobuster(text: str, base_url: str = "") -> ParseResult:
    result = ParseResult(source="gobuster")
    for m in _GOBUSTER.finditer(text):
        path, status, size = m.group(1), m.group(2), m.group(3)
        value = (base_url.rstrip("/") + path) if base_url else path
        result.assets.append({"kind": "url", "value": value, "parent": base_url,
                              "meta": {"status": status, "size": size}})
        if status in ("200", "301", "302", "401", "403"):
            result.findings.append({
                "title": f"Discovered path {path} [{status}]",
                "severity": "info", "host": base_url, "description": f"HTTP {status}, size {size}"})
    return result
