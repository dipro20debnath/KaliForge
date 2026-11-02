# Changelog

## 1.2.0 — Hardening & polish

### Added
- **Encrypted API-key vault** — keys now live in the system keyring, or an
  AES-encrypted file (`cryptography` Fernet, `0600`) instead of `settings.json`;
  legacy plaintext keys are migrated automatically.
- **Terminal session save/restore + recording** — record terminals to session
  logs, save/restore the tab layout, and an optional restore-on-launch setting.
- **Report evidence embedding** — workspace screenshots/evidence are embedded in
  HTML (base64) and PDF reports, listed with SHA-256 in Markdown/JSON (toggle).
- **Three more workflows** — Password Audit, Wireless Survey, Forensics Triage
  (6 total).
- **Attack Surface graph** — draggable nodes with live edge updates and PNG export.
- **Command palette (Ctrl+K / Ctrl+P)** — fuzzy jump across pages, tools and
  saved vault commands, plus global shortcuts (Ctrl+T/D/L/R, Ctrl+Shift+S).
- **CI + packaging** — GitHub Actions (headless pytest on 3.11/3.12 + wheel
  build) and a `pyproject.toml` with a `kaliforge` console entry point.
- **Hicolor PNG icons** (16–256px) rasterised from the SVG, installed by the
  Debian package.

### Engineering
- 7 new tests (59 total).

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
