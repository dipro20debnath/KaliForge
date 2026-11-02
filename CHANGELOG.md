# Changelog

## 1.1.0 — Advanced features (Phase 3–5)

### Added
- **Attack Surface Mapper** — visual asset graph (QGraphicsView, no external deps)
  seeded from scope, findings, manual entry or pasted tool output; imports hosts,
  IPs and open ports from nmap/recon output.
- **Tool Health Monitor** — per-tool version + runtime-dependency health with a
  dependency map and a probe-all action.
- **Installation Manager** — lists missing tools, builds a grouped `apt` install
  plan and a commented install script (still never auto-installs).
- **Learning & Practice Mode** — per-tool beginner→advanced lessons plus a live
  command explainer (per-tool flag dictionaries + generic fallback).
- **One-Click Lab Environment** — start/stop Docker vulnerable targets (OWASP
  Juice Shop, DVWA, WebGoat, bWAPP, VAmPI, Mutillidae) and add them to scope.
- New sidebar **ADVANCED** section wiring all five pages.

### Engineering
- 12 new tests (52 total); UI smoke test now covers all 18 pages.

## 1.0.0 — Initial release

First full release of **KaliForge — Cybersecurity Command Center**.

### Added
- **Dashboard** with live tool counts, quick access, real-time system monitor and recent activity.
- **Tool Arsenal** — 106 tools across 14 categories with install detection, version probing, install guides, command templates and favourites.
- **Command Center** — multi-tab PTY terminals with split view, profiles, command bar, history and output export.
- **AI Command Assistant** — offline rule engine plus optional Anthropic Messages API integration.
- **Workflows** — automated recon / web-audit / network-audit pipelines with per-step output.
- **Vulnerability Assessment** — findings dashboard, CVE intelligence (NVD + EPSS + CISA KEV) and a security news feed.
- **Reports** — Markdown / HTML / JSON / CSV / PDF export.
- **Scope Manager** — authorised-target boundary (IP / CIDR / range / domain / URL) with live testing.
- **Command Vault & Knowledge Base**, **Evidence & Lab Manager** (SHA-256 integrity), **System Monitor**.
- **Workspaces** for engagement isolation.
- **Plugins** (declarative) and **custom tool import**.
- Three themes (Kali Neon, Cyber Cyan, SOC Pro).

### Security
- Scope enforcement, command preview, destructive-command detection, sudo confirmation, runs-as-normal-user by default, full local audit log, no hidden execution.

### Engineering
- Qt-free backend with 40 headless tests (catalog, scope/permission, command builder, database, reporting, managers, UI smoke).
- Debian packaging scaffold, desktop entry and icon.
