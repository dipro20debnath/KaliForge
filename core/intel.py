"""Threat-intelligence sources: CVE lookups (NVD), exploit-prediction (EPSS),
the CISA Known-Exploited-Vulnerabilities catalog, and a simple RSS/Atom news
feed reader. All calls are network-bound and must run off the UI thread; each
degrades gracefully to a clear error string when offline."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from core import net

CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)


@dataclass
class CVEInfo:
    cve_id: str
    description: str = ""
    cvss_score: float | None = None
    cvss_severity: str = ""
    cvss_vector: str = ""
    published: str = ""
    modified: str = ""
    references: list[str] = field(default_factory=list)
    cwe: list[str] = field(default_factory=list)
    epss: float | None = None
    epss_percentile: float | None = None
    kev: bool = False
    error: str = ""

    def as_dict(self) -> dict:
        return self.__dict__.copy()


class IntelService:
    def __init__(self, settings=None, db=None):
        self.settings = settings
        self.db = db
        self._kev_cache: dict | None = None
        self._kev_time = 0.0

    def _cfg(self, key: str, default: str) -> str:
        return self.settings.get(key, default) if self.settings else default

    # ---------------------------------------------------------------- CVE
    def lookup_cve(self, cve_id: str, use_cache: bool = True) -> CVEInfo:
        cve_id = cve_id.strip().upper()
        if not CVE_RE.fullmatch(cve_id):
            return CVEInfo(cve_id=cve_id, error="not a valid CVE identifier")

        if use_cache and self.db is not None:
            cached = self.db.cached_cve(cve_id)
            if cached:
                hours = float(self._cfg("intel.cache_hours", "24"))
                if self._fresh(cached["fetched"], hours):
                    return CVEInfo(**cached["data"])

        info = CVEInfo(cve_id=cve_id)
        base = self._cfg("intel.nvd_base", "https://services.nvd.nist.gov/rest/json/cves/2.0")
        try:
            data = net.get_json(f"{base}?cveId={cve_id}", timeout=25)
            self._parse_nvd(data, info)
        except net.HttpError as exc:
            info.error = str(exc)
            return info

        # enrich with EPSS + KEV (best effort)
        try:
            info.epss, info.epss_percentile = self.lookup_epss(cve_id)
        except net.HttpError:
            pass
        try:
            info.kev = self.in_kev(cve_id)
        except net.HttpError:
            pass

        if self.db is not None:
            self.db.cache_cve(cve_id, info.as_dict())
        return info

    def _parse_nvd(self, data: dict, info: CVEInfo) -> None:
        vulns = data.get("vulnerabilities") or []
        if not vulns:
            info.error = "CVE not found"
            return
        cve = vulns[0].get("cve", {})
        for desc in cve.get("descriptions", []):
            if desc.get("lang") == "en":
                info.description = desc.get("value", "")
                break
        info.published = cve.get("published", "")
        info.modified = cve.get("lastModified", "")
        info.references = [r.get("url", "") for r in cve.get("references", [])][:15]
        for weakness in cve.get("weaknesses", []):
            for desc in weakness.get("description", []):
                val = desc.get("value", "")
                if val and val not in info.cwe:
                    info.cwe.append(val)
        metrics = cve.get("metrics", {})
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if metrics.get(key):
                data0 = metrics[key][0].get("cvssData", {})
                info.cvss_score = data0.get("baseScore")
                info.cvss_vector = data0.get("vectorString", "")
                info.cvss_severity = (data0.get("baseSeverity")
                                      or metrics[key][0].get("baseSeverity", ""))
                break

    # ---------------------------------------------------------------- EPSS
    def lookup_epss(self, cve_id: str) -> tuple[float | None, float | None]:
        base = self._cfg("intel.epss_base", "https://api.first.org/data/v1/epss")
        data = net.get_json(f"{base}?cve={cve_id}", timeout=15)
        rows = data.get("data") or []
        if not rows:
            return None, None
        row = rows[0]
        score = float(row["epss"]) if row.get("epss") else None
        pct = float(row["percentile"]) if row.get("percentile") else None
        return score, pct

    # ---------------------------------------------------------------- KEV
    def _load_kev(self) -> dict:
        if self._kev_cache is not None and (time.time() - self._kev_time) < 3600:
            return self._kev_cache
        url = self._cfg("intel.kev_url",
                        "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json")
        data = net.get_json(url, timeout=30)
        self._kev_cache = data
        self._kev_time = time.time()
        return data

    def in_kev(self, cve_id: str) -> bool:
        data = self._load_kev()
        return any(v.get("cveID", "").upper() == cve_id.upper()
                   for v in data.get("vulnerabilities", []))

    # ---------------------------------------------------------------- feeds
    def read_feed(self, url: str, limit: int = 15) -> list[dict]:
        raw = net.get_text(url, timeout=20)
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return []
        items: list[dict] = []
        # RSS 2.0
        for item in root.iter("item"):
            items.append({
                "title": _text(item, "title"),
                "link": _text(item, "link"),
                "published": _text(item, "pubDate"),
                "summary": _clean(_text(item, "description")),
            })
        # Atom
        if not items:
            ns = {"a": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//a:entry", ns):
                link_el = entry.find("a:link", ns)
                items.append({
                    "title": _text(entry, "a:title", ns),
                    "link": link_el.get("href") if link_el is not None else "",
                    "published": _text(entry, "a:updated", ns),
                    "summary": _clean(_text(entry, "a:summary", ns)),
                })
        return items[:limit]

    @staticmethod
    def _fresh(iso_ts: str, hours: float) -> bool:
        try:
            then = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
            if then.tzinfo is None:
                then = then.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - then).total_seconds() < hours * 3600
        except ValueError:
            return False


def _text(parent, tag, ns=None) -> str:
    el = parent.find(tag, ns) if ns else parent.find(tag)
    return (el.text or "").strip() if el is not None and el.text else ""


def _clean(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()
