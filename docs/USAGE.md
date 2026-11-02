# KaliForge — Usage Guide

## First run

```bash
python3 main.py
```

You land on the **Dashboard**: tool counts, quick access, a live system monitor
and recent activity. The sidebar groups everything into Overview, Domains,
Operate and Manage.

## 1. Define your scope first

Open **Scope Manager** and add every target you are authorised to test:

- `192.168.56.0/24` (CIDR)
- `10.0.0.10-10.0.0.20` (range)
- `example.com` (domain — matches subdomains too)
- `https://app.example.com` (URL)

Use the **Check** box to test whether a target is in scope. Lab-only tools will
refuse to run against anything not listed here.

## 2. Browse the Tool Arsenal

- Search by name, tag or description; filter by category with the chips.
- Each card shows **Installed / Missing / Built-in** status.
- **Details** opens description, version probe, command templates and an
  **Install Guide** (KaliForge shows the apt command — it never auto-installs).
- Click **Build & Run** on a command template to fill placeholders and launch it.

## 3. Run commands safely

Any guarded command goes through the confirmation flow:

1. The **exact command** is shown (and is editable).
2. Out-of-scope targets and destructive patterns are highlighted.
3. For high-impact actions you must tick *"I am authorised…"*.
4. On confirm, it runs in the **Command Center** and is written to the audit log.

## 4. Command Center (terminal)

Real terminals with **tabs**, **split view**, **profiles**, a **command bar**
and **export**. The command bar sends to the focused terminal.

## 5. Automate with Workflows

**Workflows** → pick *Reconnaissance*, *Web Application Audit* or *Network Audit*,
fill the inputs, and run. Each step's output is written to the workspace output
directory; missing tools are skipped and out-of-scope targets are blocked.

## 6. Track findings & CVEs

**Vulnerability** →
- *Findings* — add findings with severity, host, CVE, CVSS, remediation.
- *CVE Intelligence* — look up a CVE (NVD + EPSS exploit-prediction + CISA KEV);
  results with a CVSS score are saved as findings automatically.
- *Security Feed* — load advisories from CISA, Exploit-DB, Kali and more.

## 7. Report

**Reports** → set the title/client/summary, pick a format (Markdown, HTML, JSON,
CSV, PDF) and export. The report is built from the active workspace's findings,
scope and detected tool versions.

## 8. The AI Command Assistant

**AI Assistant** → type a request like *"find live hosts on 192.168.56.0/24"* or
*"enumerate subdomains of example.com"*. It returns real command suggestions with
a rationale. It works **fully offline**; add an Anthropic API key in **Settings →
AI Assistant** to use the Claude API instead. Suggestions always pass the normal
confirmation flow before running.

## 9. Organise your work

- **Vault & Notes** — save/tag/search commands and keep cheat-sheets.
- **Evidence & Labs** — register files with SHA-256 integrity; track VM targets.
- **Workspaces** — each engagement has its own scope, findings, evidence and reports.
- **Plugins** — enable/disable plugins or import your own scripts as tool cards.

## Settings

- **Appearance** — three themes (Kali Neon, Cyber Cyan, SOC Pro), font size.
- **Security** — scope mode, lab-only enforcement, destructive/sudo confirmation, audit logging.
- **AI Assistant** — provider, API key, model.
- **Terminal** — scrollback, close confirmation, session recording.
