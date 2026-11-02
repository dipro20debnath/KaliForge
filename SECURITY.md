# KaliForge — Security Model & Responsible Use

KaliForge is a dashboard for **authorised** security testing. It drives powerful
offensive tools, so it is built with guard-rails that make authorised, auditable
use the default path.

## Responsible use

- Use KaliForge **only** against systems you own or are explicitly authorised, in
  writing, to test.
- Wireless, exploitation, password-attack and MITM tools are flagged **lab-only**
  and will not run against targets outside your defined scope.
- You are responsible for complying with all applicable laws and the rules of
  your engagement.

## Built-in guard-rails

| Control | What it does |
|---|---|
| **Scope Manager** | Defines the authorised boundary (IP, CIDR, range, domain, URL). Every command's targets are checked against it. |
| **Scope modes** | *Enforce* blocks any out-of-scope target; *Warn* requires confirmation; *Off* disables checks (not recommended). |
| **Lab-only enforcement** | High-impact tools require an in-scope target regardless of mode. |
| **Command preview** | The exact command is shown and is editable before execution. |
| **Destructive detection** | Recognises `rm -rf`, `mkfs`, `dd of=/dev/…`, `shred`, fork bombs, remote-pipe-to-shell, firewall flushes and more, and forces confirmation. |
| **Sudo confirmation** | Privileged commands require an explicit confirmation. |
| **Runs as normal user** | KaliForge refuses to start as root by default. |
| **Audit log** | Every decision (launched / blocked / cancelled) is appended to `audit.jsonl` and the database with user, time, command, targets and risk. |
| **No hidden execution** | No tool or script runs without passing the permission flow. |
| **Declarative plugins** | Plugins add tool cards via JSON manifests; no plugin code is executed on load. |

## Data & privacy

- All data (workspaces, findings, evidence, audit log, settings) is stored
  **locally** under the XDG config/data directories.
- API keys for the optional AI assistant are stored in the user config file with
  `0600` permissions and are only ever sent to the configured provider.
- The CVE intelligence and security-feed features make outbound requests to the
  configured public sources (NVD, FIRST EPSS, CISA KEV, RSS feeds) only when you
  invoke them.

## Reporting a vulnerability

If you find a security issue in KaliForge itself, please open a private report to
the maintainer rather than a public issue.
