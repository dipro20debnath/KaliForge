# KaliForge Architecture

KaliForge is a modular PySide6 desktop application with a strict separation
between a **Qt-free backend** (`core/`, `database/`, `tools/`) and the **UI**
(`ui/`). The backend can be constructed and fully exercised headless, which is
why the test-suite covers it without a display server.

```
┌──────────────────────────────────────────────────────────────┐
│                         ui/  (PySide6)                         │
│  MainWindow · Sidebar · Pages (dashboard, arsenal, terminal,   │
│  vulnerability, workflows, assistant, scope, monitor, reports, │
│  vault, evidence, plugins, settings) · Widgets · RunController │
└───────────────┬────────────────────────────────────────────── ┘
                │ constructs + calls
┌───────────────▼──────────────────────────────────────────────┐
│                     core/AppManager  (root)                    │
│  Settings · AuditLog · Catalog · ToolManager · WorkspaceMgr ·  │
│  ScopeManager · PermissionManager · WorkflowEngine ·           │
│  SystemMonitor · AIAssistant · IntelService · PluginManager    │
└───────────────┬──────────────────────────────────────────────┘
                │
┌───────────────▼───────────────┐   ┌──────────────────────────┐
│       database/ (SQLite)       │   │   Kali Linux / the host   │
│  workspaces, scope, findings,  │   │  PTY shell · installed    │
│  assets, evidence, vault,      │   │  tools · subprocess ·     │
│  notes, labs, audit, cve cache │   │  psutil · filesystem      │
└────────────────────────────────┘   └──────────────────────────┘
```

## Components

### `core/`
- **config.py** — layered settings (`config.json` defaults + user overrides) and XDG paths. `KALIFORGE_HOME` relocates all runtime data (used by tests).
- **app_manager.py** — the composition root; owns one instance of every manager.
- **categories.py** — the 14 security domains.
- **tool_manager.py** — installation detection (`shutil.which`), version probing, install guidance, favourites.
- **command_utils.py** — target extraction, destructive-pattern and sudo detection (pure functions).
- **command_builder.py** — template placeholder substitution with shell-safe quoting.
- **scope_manager.py** — authorised-target matching (IP/CIDR/range/domain/URL).
- **permission_manager.py** — turns a command + scope + settings into a `Decision`.
- **terminal_manager.py** — a real PTY + `pyte` screen (no Qt).
- **process_manager.py** — non-interactive command runner with capture, timeout and kill.
- **workflow_engine.py** — runs ordered tool steps, enforcing scope and skipping missing tools.
- **system_monitor.py** — psutil sampling.
- **ai_assistant.py** — offline rule engine + optional Anthropic Messages API (raw HTTPS).
- **intel.py** — CVE (NVD) + EPSS + CISA KEV + RSS feeds.
- **reporting.py** — Markdown / HTML / JSON / CSV / PDF generation.
- **evidence.py** — SHA-256 evidence registration.
- **workspace.py** — per-engagement isolation.
- **plugins.py** — declarative plugin discovery.
- **audit.py** — JSONL + DB audit trail.
- **attack_surface.py** — asset relationship graph model (seed + build).
- **tool_health.py** — version + dependency health checks.
- **installer.py** — bulk install-plan / script generation.
- **learning.py** — learning modules + command explainer.
- **lab_env.py** — Docker vulnerable-target lifecycle.

### `tools/`
- **catalog_data_a.py / _b.py** — the 106-tool catalog data (segments 1–7 / 8–14).
- **catalog.py** — loader, validation, search, and custom-tool merging.

### `database/`
- **models.py** — schema + dataclasses + CVSS→severity mapping.
- **database.py** — thread-safe SQLite wrapper (WAL mode).

### `ui/`
- **main_window.py** — stacked pages + sidebar + cross-page signal wiring.
- **run_controller.py** — the single gate for interactive command launches (evaluate → confirm → terminal → audit).
- **theme.py** — three colour schemes + a shared QSS stylesheet.
- **pages/**, **widgets/** — the screens and reusable components.

## Key design decisions

- **Backend is Qt-free** so it is testable and reusable; the UI only orchestrates.
- **One permission gate** (`RunController` + `PermissionManager`) — no page can bypass scope/confirmation.
- **Real PTY terminals** via `pty.fork` + `pyte`, rendered by a custom Qt widget that coalesces repaints.
- **Everything local** — SQLite + files under XDG dirs; no telemetry.
- **Extensible** — declarative plugins and DB-stored custom tools merge into the catalog at startup.
