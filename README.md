<div align="center">

# ⚒ KaliForge

### Cybersecurity Command Center

**One Interface. Every Security Workflow.**

A full **Cybersecurity Operations Workstation** for Kali Linux — not just a tool
launcher. KaliForge centralises 100+ security tools, an integrated terminal,
reconnaissance, vulnerability assessment, reporting and workflow automation into
one dark, modern dashboard, with authorisation guard-rails built into its core.

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
- **Local API-key storage** — AI keys are stored in your user config (`chmod 600`), never transmitted anywhere except the chosen provider.

See [`SECURITY.md`](SECURITY.md) for the full model.

## Tech stack

Python 3 · PySide6 (Qt) · SQLite · psutil · pyte (terminal emulation) · ReportLab.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the design and
[`docs/USAGE.md`](docs/USAGE.md) for a walkthrough.

## Tests

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest
```

40 headless tests cover the catalog, scope/permission engine, command builder,
database, reporting, managers and a full UI smoke test.

## License

[MIT](LICENSE) © dipro20debnath
