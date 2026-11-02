<div align="center">

# ⚒ KaliForge

### Cybersecurity Command Center

**One Interface. Every Security Workflow.**

A full **Cybersecurity Operations Workstation** for Kali Linux — not just a tool
launcher. KaliForge centralises 100+ security tools, an integrated terminal,
reconnaissance, vulnerability assessment, reporting and workflow automation into
one dark, modern dashboard, with authorisation guard-rails built into its core.

<img src="docs/screenshots/01-dashboard.png" alt="KaliForge Dashboard" width="880">

</div>

---

> ⚠️ **Authorised use only.** KaliForge is for ethical hacking, penetration
> testing and security research **on systems you own or are explicitly
> authorised to test.** Lab-only and high-impact tools refuse to run against any
> target that is not in your defined engagement scope.

## Highlights

| | |
|---|---|
| **100+ tools** | 106 built-in integrations across 14 security domains |
| **12+ categories** | Recon, Web, Network, Vuln, Password, Wireless, Forensics, Stego, Reversing, Android, Exploitation, Crypto, Cloud, Reporting |
| **Unified terminal** | Real PTY terminals with tabs, split view, profiles and output export |
| **Scope-aware** | Every guarded command is checked against your authorised scope |

### Feature overview

- **Dashboard** — live tool counts, quick access, real-time CPU/RAM/disk monitor and recent activity.
- **Tool Arsenal** — searchable, category-filtered cards with install status, version probing, command templates and favourites.
- **Command Center** — multi-tab PTY terminal (tabs, split, profiles, history, export) with a scope-aware command bar.
- **AI Command Assistant** — natural language → real command suggestions. Works **fully offline**; optionally uses the Anthropic API when a key is supplied.
- **Workflows** — chain tools into automated recon / web-audit / network-audit runs that write output to the workspace.
- **Vulnerability Assessment** — findings dashboard with severity scoring, CVE intelligence (NVD + EPSS + CISA KEV) and a live security feed.
- **Reports** — export Markdown / HTML / JSON / CSV / PDF from your findings.
- **Scope Manager** — define and test the authorised engagement boundary (IP, CIDR, range, domain, URL).
- **Command Vault & Knowledge Base** — save, tag and search commands; keep pentest notes.
- **Evidence & Lab Manager** — register artefacts with SHA-256 integrity; track lab/VM targets.
- **System Monitor** — live resource meters and top-process table.
- **Plugins & Custom Tools** — extend the arsenal with declarative plugins or import your own scripts.
- **Workspaces** — isolate each engagement (scope, findings, evidence, output, reports).

### Advanced (Phase 3–5)

- **Attack Surface Mapper** — a visual asset graph (domains → subdomains → hosts → ports) seeded from scope, findings or pasted tool output.
- **Tool Health Monitor** — version + runtime-dependency health for every installed tool.
- **Installation Manager** — select missing tools and generate a safe bulk `apt` install plan / script (never auto-installs).
- **Learning & Practice Mode** — per-tool beginner→advanced lessons and a live command explainer that breaks any command into explained parts.
- **One-Click Lab Environment** — start/stop Docker-based vulnerable targets (OWASP Juice Shop, DVWA, WebGoat, bWAPP, VAmPI, Mutillidae) for authorised practice, and add them to scope.

### Utilities & analysis

- **Crypto Toolkit** — an offline mini-CyberChef: encode/decode Base64/32, Hex, URL, ROT13, HTML, Binary, ASCII85; identify hash types (MD5/NTLM/SHA/bcrypt/…) and hash text. No network, no external tools.
- **Payload Generator** — reverse/bind shell one-liners (bash, nc, Python, PHP, Perl, Ruby, PowerShell, socat, …) with matching listeners, plus URL-encode / Base64 / PowerShell `-enc` variants.
- **Scan Import** — parse nmap (XML & normal), nuclei JSON and gobuster output into **findings + attack-surface assets** automatically.
- **Hosts** — a host-centric view aggregating every host's open ports/services and findings in one place.

### Tracking & workspaces

- **Dashboard charts** — a findings-by-severity donut and a tool-status bar chart drawn natively (no plotting libraries).
- **Methodology Checklist** — track progress through OWASP WSTG and PTES per engagement, with a live progress bar.
- **Credentials Manager** — store discovered credentials per workspace, encrypted at rest (reveal/hide, copy).
- **Global search** — the `Ctrl+K` palette also searches findings, notes and hosts, not just pages and tools.
- **Workspaces** — create/switch/delete engagements from the UI, and **export/import** a whole workspace as a portable `.kfw` backup.

## 📸 Screenshots

### Core

| Tool Arsenal | Command Center (PTY terminal) |
|---|---|
| ![Arsenal](docs/screenshots/02-arsenal.png) | ![Terminal](docs/screenshots/03-command-center.png) |
| **Tool details & command templates** | **AI Command Assistant** |
| ![Tool detail](docs/screenshots/04-tool-detail.png) | ![AI assistant](docs/screenshots/08-ai-assistant.png) |

### Assessment & reporting

| Vulnerability Assessment | Attack Surface Mapper |
|---|---|
| ![Vulnerability](docs/screenshots/05-vulnerability.png) | ![Attack surface](docs/screenshots/06-attack-surface.png) |
| **Workflows** | **Reports** |
| ![Workflows](docs/screenshots/07-workflows.png) | ![Reports](docs/screenshots/18-reports.png) |
| **Scope Manager** | **System Monitor** |
| ![Scope](docs/screenshots/09-scope.png) | ![Monitor](docs/screenshots/10-monitor.png) |

### Advanced (Phase 3–5)

| Tool Health Monitor | Installation Manager |
|---|---|
| ![Tool health](docs/screenshots/11-tool-health.png) | ![Installer](docs/screenshots/12-installer.png) |
| **Learning & Practice Mode** | **One-Click Lab Environments** |
| ![Learning](docs/screenshots/13-learning.png) | ![Lab env](docs/screenshots/14-lab-env.png) |

### Manage & navigate

| Command Vault & Notes | Evidence & Lab Manager |
|---|---|
| ![Vault](docs/screenshots/15-vault.png) | ![Evidence](docs/screenshots/16-evidence.png) |
| **Plugins & Custom Tools** | **Settings** |
| ![Plugins](docs/screenshots/17-plugins.png) | ![Settings](docs/screenshots/19-settings.png) |
| **Command Palette (Ctrl+K)** | |
| ![Command palette](docs/screenshots/20-command-palette.png) | |

### Utilities & analysis

| Crypto Toolkit (offline) | Payload Generator |
|---|---|
| ![Crypto toolkit](docs/screenshots/21-crypto-toolkit.png) | ![Payloads](docs/screenshots/22-payloads.png) |
| **Scan Import (nmap / nuclei / gobuster)** | **Hosts (aggregated view)** |
| ![Scan import](docs/screenshots/23-scan-import.png) | ![Hosts](docs/screenshots/24-hosts.png) |

### Tracking & workspaces

| Methodology Checklist (WSTG / PTES) | Credentials Manager (encrypted) |
|---|---|
| ![Methodology](docs/screenshots/25-methodology.png) | ![Credentials](docs/screenshots/26-credentials.png) |
| **Workspaces (export / import)** | *(the dashboard above carries the charts)* |
| ![Workspaces](docs/screenshots/27-workspaces.png) | |

> Screenshots rendered from the running app (Kali Neon theme) with sample
> engagement data.

## Install

### From source

```bash
git clone https://github.com/dipro20debnath/KaliForge.git
cd KaliForge
pip install -r requirements.txt      # PySide6, psutil, pyte, reportlab
python3 main.py
```

### As a Debian package

```bash
bash packaging/deb/build_deb.sh 1.0.0
sudo dpkg -i kaliforge_1.0.0_all.deb   # then launch 'kaliforge'
```

> KaliForge runs as a **normal user** by default — it is designed never to start
> as root. Individual commands request `sudo` only when needed, after a
> confirmation prompt.

## Security model

KaliForge manages offensive tools, so its own guard-rails matter:

- **Scope enforcement** — out-of-scope targets are blocked (lab-only tools) or confirmed (warn mode).
- **Command preview** — the exact command is shown, and editable, before it runs.
- **Destructive-command detection** — `rm -rf`, `mkfs`, `dd of=/dev/…`, remote-pipe-to-shell and more trigger an explicit confirmation.
- **Audit log** — every command decision is written to `~/.local/share/kaliforge/logs/audit.jsonl` and the database.
- **No hidden execution** — nothing runs without passing the permission flow.
- **Encrypted API-key vault** — AI keys are stored in the system keyring or an AES-encrypted file (`cryptography` Fernet, `0600`), never in plaintext, and only ever sent to the chosen provider.

See [`SECURITY.md`](SECURITY.md) for the full model.

## Tech stack

Python 3 · PySide6 (Qt) · SQLite · psutil · pyte (terminal emulation) · ReportLab.

The UI uses a persistent header bar (page icon/title, active workspace, quick
search), gradient surfaces with hover elevation, fade-in page transitions,
animated stat tiles and meters, and pointing-hand cursors throughout — themed
across four colour schemes (Kali Neon, Cyber Cyan, SOC Pro and a Light theme).

<img src="docs/screenshots/28-light-theme.png" alt="KaliForge light theme" width="820">

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the design,
[`docs/USAGE.md`](docs/USAGE.md) for a walkthrough, and
[`docs/TESTING.md`](docs/TESTING.md) for a step-by-step real-Kali
integration-testing guide.

## Tests

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest
```

59 headless tests cover the catalog, scope/permission engine, command builder,
database, reporting (with evidence embedding), managers, the advanced Phase 3–5
modules, the encrypted vault, and a full UI smoke test. CI runs them on Python
3.11 and 3.12 and builds a wheel.

### Keyboard shortcuts

`Ctrl+K` / `Ctrl+P` command palette · `Ctrl+T` terminal · `Ctrl+D` dashboard ·
`Ctrl+L` arsenal · `Ctrl+R` reports · `Ctrl+Shift+S` scope.

## License

[MIT](LICENSE) © dipro20debnath
