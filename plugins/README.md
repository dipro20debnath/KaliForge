# KaliForge Plugins

A plugin adds tool cards (and future integrations) to KaliForge **declaratively**
— no plugin code is executed on load, which keeps the dashboard's attack surface
small.

## Layout

```
my-plugin/
├── plugin.json      # manifest
└── tools.json       # optional: list of tool-card definitions
```

## `plugin.json`

```json
{
  "id": "my-plugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "author": "you",
  "description": "What it adds.",
  "tools": "tools.json"
}
```

`tools` may be a path to a JSON file **or** an inline array of tool definitions.

## Tool definition

Each tool card uses the same fields as the built-in catalog:

```json
{
  "id": "my-tool",
  "name": "My Tool",
  "category": "recon",
  "desc": "One-line description.",
  "binary": "mytool",
  "package": "mytool",
  "homepage": "https://example.com",
  "docs": "https://example.com/docs",
  "lab_only": false,
  "risk": "caution",
  "tags": ["custom"],
  "commands": [
    {"label": "Scan", "template": "mytool -t {target}", "scope": true}
  ]
}
```

Valid categories: `recon, web, network, vuln, password, wireless, forensics,
stego, reverse, android, exploit, crypto, cloud, reporting`. Valid risk levels:
`info, caution, dangerous`.

## Installing

Drop the plugin folder into your config plugins directory
(`~/.config/kaliforge/plugins/`), then open **Plugins → Reload plugins**. The
bundled `example_plugin/` shows a working example.
