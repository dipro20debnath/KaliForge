"""AI Command Assistant.

Two back-ends behind one interface:

* **offline** (default, always available) — a deterministic rule engine that
  maps a natural-language request to real, scope-aware command suggestions
  drawn from the tool catalog. No network, no key, no surprises.
* **claude** (optional) — calls the Anthropic Messages API over raw HTTPS
  (urllib, no SDK) when the user supplies a key. The model only *suggests*
  commands as text; nothing is executed without the normal permission flow.

Every suggestion carries a short rationale so the output is informative, which
matches the user's preference for real, explained information.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from core import net
from tools.catalog import Catalog

# -------- intent -> (tool_id, template, phrasing) rules for the offline engine
_RULES = [
    (r"\b(find|discover|enumerate).*(host|alive|up|active)\b",
     "nmap", "nmap -sn {cidr}", "Ping-sweep the range to list live hosts."),
    (r"\b(port|service).*(scan|open)\b|\bscan.*port",
     "nmap", "nmap -sV -sC {target}", "Service/version scan with default scripts."),
    (r"\bfull.*(port|scan)\b|\ball ports\b",
     "nmap", "nmap -p- -T4 {target}", "Scan every TCP port, then fingerprint services."),
    (r"\b(subdomain|sub-domain)s?\b",
     "subfinder", "subfinder -d {domain} -silent", "Passive subdomain enumeration."),
    (r"\b(dns|zone|record)s?\b",
     "dig", "dig {domain} ANY", "Query all DNS records for the domain."),
    (r"\bwhois|registration|owner\b",
     "whois", "whois {domain}", "Look up domain registration details."),
    (r"\b(directory|dir|content|path).*(brute|fuzz|discover)\b|\bgobuster\b",
     "gobuster", "gobuster dir -u {url} -w {wordlist}", "Brute-force web content paths."),
    (r"\b(fuzz|ffuf)\b",
     "ffuf", "ffuf -u {url}/FUZZ -w {wordlist}", "Fuzz the URL path for hidden endpoints."),
    (r"\b(sql|sqli|injection).*(test|scan|exploit)\b|\bsqlmap\b",
     "sqlmap", "sqlmap -u \"{url}\" --batch", "Test the URL for SQL injection (lab only)."),
    (r"\bwordpress|wp\b",
     "wpscan", "wpscan --url {url}", "Scan the WordPress site for known issues."),
    (r"\b(vuln|cve|template).*(scan)\b|\bnuclei\b",
     "nuclei", "nuclei -u {url}", "Run template-based vulnerability checks."),
    (r"\b(fingerprint|technology|tech|stack)\b|\bwhatweb\b",
     "whatweb", "whatweb {url}", "Fingerprint the web technologies in use."),
    (r"\b(ssl|tls|cipher|certificate)\b",
     "sslscan", "sslscan {host}", "Enumerate SSL/TLS configuration and ciphers."),
    (r"\b(crack|brute).*(ssh)\b|\bhydra\b",
     "hydra", "hydra -l {user} -P {wordlist} ssh://{target}", "Brute-force SSH logins (lab only)."),
    (r"\b(crack|recover).*(hash|password)\b|\bhashcat\b",
     "hashcat", "hashcat -m {mode} {hashfile} {wordlist}", "Crack password hashes with a wordlist."),
    (r"\bjohn\b|john the ripper",
     "john", "john --wordlist={wordlist} {hashfile}", "Crack hashes with John the Ripper."),
    (r"\b(capture|sniff).*(packet|traffic)\b|\btcpdump\b",
     "tcpdump", "tcpdump -i {interface} -w {outfile}", "Capture network traffic to a file."),
    (r"\b(metadata|exif)\b",
     "exiftool", "exiftool {file}", "Read embedded file metadata."),
    (r"\b(steg|hidden data|hide)\b",
     "steghide", "steghide extract -sf {file}", "Attempt to extract steganographic data."),
    (r"\b(firmware|extract|carve)\b|\bbinwalk\b",
     "binwalk", "binwalk -e {file}", "Analyse and extract firmware contents."),
    (r"\b(memory|ram).*(forensic|analy)\b|\bvolatility\b",
     "volatility", "vol -f {image} windows.pslist", "Analyse a memory image."),
    (r"\b(container|image|docker).*(scan|vuln)\b|\btrivy\b",
     "trivy", "trivy image {image}", "Scan a container image for vulnerabilities."),
    (r"\b(exploit|searchsploit|exploit-db)\b",
     "searchsploit", "searchsploit {query}", "Search Exploit-DB for matching exploits."),
]

_SYSTEM_PROMPT = (
    "You are the command assistant inside KaliForge, a dashboard for authorised "
    "penetration testing on Kali Linux. Given a request, reply with the single most "
    "appropriate command-line invocation and a one-sentence rationale. Only ever "
    "suggest testing against targets the operator is authorised to test; prefer "
    "non-destructive options. Format every answer as:\nCOMMAND: <command>\nWHY: <reason>\n"
    "Keep placeholders like <target> or <url> when the user did not give a concrete value."
)


@dataclass
class Suggestion:
    command: str
    rationale: str
    tool_id: str = ""
    source: str = "offline"
    confidence: float = 0.0


@dataclass
class AIResponse:
    suggestions: list[Suggestion] = field(default_factory=list)
    text: str = ""
    source: str = "offline"
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error and (bool(self.suggestions) or bool(self.text))


class AIAssistant:
    def __init__(self, settings=None, catalog: Catalog | None = None):
        self.settings = settings
        self.catalog = catalog or Catalog()

    # ------------------------------------------------------------------ keys
    def provider(self) -> str:
        return (self.settings.get("ai.provider", "offline") if self.settings else "offline")

    def api_key(self) -> str:
        if self.settings:
            key = self.settings.get("ai.api_key", "")
            if key:
                return key
        return os.environ.get("ANTHROPIC_API_KEY", "")

    def has_key(self) -> bool:
        return bool(self.api_key())

    # --------------------------------------------------------------- dispatch
    def ask(self, prompt: str, scope_hint: str = "") -> AIResponse:
        prompt = (prompt or "").strip()
        if not prompt:
            return AIResponse(error="empty prompt")
        if self.provider() == "claude" and self.has_key():
            response = self._ask_claude(prompt, scope_hint)
            if response.ok:
                return response
            # fall through to offline on API failure, but keep the error note
            offline = self._ask_offline(prompt)
            offline.error = response.error
            return offline
        return self._ask_offline(prompt)

    # --------------------------------------------------------------- offline
    def _ask_offline(self, prompt: str) -> AIResponse:
        text = prompt.lower()
        values = self._extract_values(prompt)
        matches: list[Suggestion] = []
        for pattern, tool_id, template, why in _RULES:
            if re.search(pattern, text):
                command = self._fill(template, values)
                tool = self.catalog.get(tool_id)
                rationale = why
                if tool and tool.get("lab_only"):
                    rationale += " Only run against an authorised, in-scope target."
                matches.append(Suggestion(command=command, rationale=rationale,
                                          tool_id=tool_id, source="offline", confidence=0.8))
        # de-duplicate by command
        seen, unique = set(), []
        for s in matches:
            if s.command not in seen:
                seen.add(s.command)
                unique.append(s)
        if not unique:
            return AIResponse(
                text=("No direct match. Try naming a tool or task — e.g. "
                      "'scan ports on 10.0.0.5', 'enumerate subdomains of example.com', "
                      "or 'crack this hash file'."),
                source="offline",
            )
        return AIResponse(suggestions=unique[:5], source="offline")

    def _extract_values(self, prompt: str) -> dict[str, str]:
        values: dict[str, str] = {}
        url = re.search(r"https?://[^\s'\"]+", prompt)
        if url:
            values["url"] = url.group(0)
        cidr = re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}\b", prompt)
        if cidr:
            values["cidr"] = cidr.group(0)
        ip = re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", prompt)
        if ip:
            values["target"] = ip.group(0)
            values.setdefault("host", ip.group(0))
        domain = re.search(r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b", prompt)
        if domain and "url" not in values:
            values["domain"] = domain.group(0)
            values.setdefault("target", domain.group(0))
            values.setdefault("host", domain.group(0))
        if "url" in values and "domain" not in values:
            from core.scope_manager import host_of
            values["domain"] = host_of(values["url"])
        return values

    @staticmethod
    def _fill(template: str, values: dict[str, str]) -> str:
        def repl(match: re.Match) -> str:
            name = match.group(1)
            return values.get(name, f"<{name}>")
        return re.sub(r"\{([a-zA-Z_]+)\}", repl, template)

    # ---------------------------------------------------------------- claude
    def _ask_claude(self, prompt: str, scope_hint: str) -> AIResponse:
        key = self.api_key()
        model = self.settings.get("ai.model", "claude-opus-5-5") if self.settings else "claude-opus-5-5"
        effort = self.settings.get("ai.effort", "low") if self.settings else "low"
        max_tokens = int(self.settings.get("ai.max_tokens", 1024) if self.settings else 1024)
        user = prompt
        if scope_hint:
            user += f"\n\nAuthorised scope for this engagement: {scope_hint}"
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "system": _SYSTEM_PROMPT,
            "output_config": {"effort": effort},
            "messages": [{"role": "user", "content": user}],
        }
        try:
            raw = self._post_claude(key, body)
        except net.HttpError as exc:
            return AIResponse(error=str(exc), source="claude")
        return self._parse_claude(raw)

    @staticmethod
    def _post_claude(key: str, body: dict) -> dict:
        import urllib.request
        from core.net import HttpError, _ssl_context, USER_AGENT
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=data, method="POST",
            headers={
                "User-Agent": USER_AGENT,
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60, context=_ssl_context()) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:  # type: ignore[name-defined]
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            raise HttpError(f"Anthropic API HTTP {exc.code}: {detail}") from exc
        except Exception as exc:  # noqa: BLE001
            raise HttpError(f"Anthropic API request failed: {exc}") from exc

    def _parse_claude(self, payload: dict) -> AIResponse:
        if payload.get("stop_reason") == "refusal":
            return AIResponse(error="The model declined this request.", source="claude")
        parts = []
        for block in payload.get("content", []):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
        text = "\n".join(parts).strip()
        if not text:
            return AIResponse(error="empty response from model", source="claude")
        suggestions = self._suggestions_from_text(text)
        return AIResponse(suggestions=suggestions, text=text, source="claude")

    @staticmethod
    def _suggestions_from_text(text: str) -> list[Suggestion]:
        suggestions: list[Suggestion] = []
        command = ""
        for line in text.splitlines():
            stripped = line.strip()
            cmd_match = re.match(r"(?i)^COMMAND:\s*(.+)$", stripped)
            why_match = re.match(r"(?i)^WHY:\s*(.+)$", stripped)
            if cmd_match:
                command = cmd_match.group(1).strip().strip("`")
            elif why_match and command:
                suggestions.append(Suggestion(command=command, rationale=why_match.group(1).strip(),
                                              source="claude", confidence=0.9))
                command = ""
        if command and not suggestions:
            suggestions.append(Suggestion(command=command, rationale="", source="claude"))
        return suggestions

import urllib.error  # noqa: E402  (used in _post_claude error branch)
