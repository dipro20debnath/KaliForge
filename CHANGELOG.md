# Changelog

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
