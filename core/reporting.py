"""Report generator — turns findings + metadata into Markdown, HTML, JSON and
CSV, with an optional PDF via ReportLab when available. Designed so the same
report model renders to every format."""
from __future__ import annotations

import csv
import html
import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from database.models import SEVERITIES, SEVERITY_WEIGHT

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)
    _HAVE_REPORTLAB = True
except ImportError:  # pragma: no cover
    _HAVE_REPORTLAB = False

SEVERITY_COLORS = {
    "critical": "#ff2d55", "high": "#ff8f1f", "medium": "#ffd23f",
    "low": "#38c172", "info": "#4dabf7",
}


@dataclass
class ReportModel:
    title: str = "Security Assessment Report"
    client: str = ""
    workspace: str = ""
    author: str = ""
    date: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    summary: str = ""
    scope: list[str] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    tool_versions: list[dict] = field(default_factory=list)

    def severity_counts(self) -> dict[str, int]:
        counts = {sev: 0 for sev in SEVERITIES}
        for finding in self.findings:
            sev = finding.get("severity", "info")
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    def risk_score(self) -> float:
        if not self.findings:
            return 0.0
        total = sum(SEVERITY_WEIGHT.get(f.get("severity", "info"), 0) for f in self.findings)
        return round(total / len(self.findings), 1)

    def sorted_findings(self) -> list[dict]:
        order = {sev: i for i, sev in enumerate(SEVERITIES)}
        return sorted(self.findings, key=lambda f: order.get(f.get("severity", "info"), 99))


class ReportGenerator:
    def __init__(self, model: ReportModel):
        self.model = model

    # --------------------------------------------------------------- markdown
    def to_markdown(self) -> str:
        m = self.model
        lines = [f"# {m.title}", ""]
        meta = []
        if m.client:
            meta.append(f"**Client:** {m.client}")
        if m.workspace:
            meta.append(f"**Workspace:** {m.workspace}")
        if m.author:
            meta.append(f"**Author:** {m.author}")
        meta.append(f"**Date:** {m.date}")
        lines.append("  \n".join(meta))
        lines.append("")

        lines.append("## Executive Summary")
        lines.append(m.summary or "_No summary provided._")
        lines.append("")

        counts = m.severity_counts()
        lines.append("## Findings Overview")
        lines.append("")
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        for sev in SEVERITIES:
            lines.append(f"| {sev.title()} | {counts.get(sev, 0)} |")
        lines.append(f"| **Total** | **{len(m.findings)}** |")
        lines.append("")
        lines.append(f"**Average risk weight:** {m.risk_score()} / 10")
        lines.append("")

        if m.scope:
            lines.append("## Scope")
            for item in m.scope:
                lines.append(f"- `{item}`")
            lines.append("")

        lines.append("## Detailed Findings")
        lines.append("")
        if not m.findings:
            lines.append("_No findings recorded._")
        for idx, finding in enumerate(m.sorted_findings(), 1):
            lines.append(f"### {idx}. {finding.get('title', 'Untitled')} "
                         f"[{finding.get('severity', 'info').upper()}]")
            detail = []
            if finding.get("cve"):
                detail.append(f"**CVE:** {finding['cve']}")
            if finding.get("cvss") is not None:
                detail.append(f"**CVSS:** {finding['cvss']}")
            host = finding.get("host", "")
            port = finding.get("port", "")
            if host:
                detail.append(f"**Host:** {host}" + (f":{port}" if port else ""))
            if finding.get("service"):
                detail.append(f"**Service:** {finding['service']}")
            if detail:
                lines.append("  \n".join(detail))
                lines.append("")
            if finding.get("description"):
                lines.append(f"**Description:**\n\n{finding['description']}\n")
            if finding.get("evidence"):
                lines.append(f"**Evidence:**\n\n```\n{finding['evidence']}\n```\n")
            if finding.get("remediation"):
                lines.append(f"**Remediation:**\n\n{finding['remediation']}\n")
            lines.append("")

        if m.tool_versions:
            lines.append("## Tooling")
            lines.append("")
            lines.append("| Tool | Version |")
            lines.append("|------|---------|")
            for tv in m.tool_versions:
                lines.append(f"| {tv.get('name', '')} | {tv.get('version', '')} |")
            lines.append("")
        lines.append("---")
        lines.append("_Generated by KaliForge._")
        return "\n".join(lines)

    # --------------------------------------------------------------- html
    def to_html(self) -> str:
        m = self.model
        counts = m.severity_counts()
        esc = html.escape
        chips = "".join(
            f'<span class="chip" style="--c:{SEVERITY_COLORS[sev]}">{sev.title()}: '
            f'{counts.get(sev, 0)}</span>'
            for sev in SEVERITIES
        )
        rows = []
        for idx, f in enumerate(m.sorted_findings(), 1):
            sev = f.get("severity", "info")
            rows.append(f"""
            <div class="finding">
              <div class="fhead">
                <span class="sev" style="--c:{SEVERITY_COLORS.get(sev, '#888')}">{sev.upper()}</span>
                <h3>{idx}. {esc(f.get('title', 'Untitled'))}</h3>
              </div>
              <div class="meta">
                {_meta_html(f)}
              </div>
              {_section('Description', f.get('description', ''))}
              {_section('Evidence', f.get('evidence', ''), mono=True)}
              {_section('Remediation', f.get('remediation', ''))}
            </div>""")
        findings_html = "\n".join(rows) or "<p><em>No findings recorded.</em></p>"
        scope_html = "".join(f"<code>{esc(s)}</code> " for s in m.scope) or "<em>Not specified.</em>"
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(m.title)}</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; margin:0;
          background:#0b0f10; color:#d7e0e2; line-height:1.55; }}
  .wrap {{ max-width: 960px; margin: 0 auto; padding: 32px 20px 64px; }}
  header {{ border-bottom:2px solid #1de9b6; padding-bottom:16px; margin-bottom:24px; }}
  h1 {{ color:#1de9b6; margin:0 0 6px; font-size: 1.8rem; }}
  h2 {{ color:#9ff; border-left:3px solid #1de9b6; padding-left:10px; margin-top:32px; }}
  .metaline {{ color:#8aa; font-size:.92rem; }}
  .chips {{ display:flex; flex-wrap:wrap; gap:8px; margin:16px 0; }}
  .chip {{ background:#13191b; border:1px solid var(--c); color:var(--c);
           padding:4px 12px; border-radius:20px; font-size:.82rem; font-weight:600; }}
  .finding {{ background:#11181a; border:1px solid #1f2b2e; border-radius:12px;
              padding:18px 20px; margin:16px 0; }}
  .fhead {{ display:flex; align-items:center; gap:12px; }}
  .fhead h3 {{ margin:0; font-size:1.1rem; }}
  .sev {{ background:var(--c); color:#07100f; font-weight:700; font-size:.72rem;
          padding:3px 8px; border-radius:6px; }}
  .meta code {{ background:#0b1113; border:1px solid #233; padding:1px 6px;
                border-radius:5px; margin-right:6px; font-size:.82rem; }}
  .sec h4 {{ margin:14px 0 4px; color:#7fd; font-size:.86rem; text-transform:uppercase;
             letter-spacing:.05em; }}
  pre {{ background:#0a0e0f; border:1px solid #1d2a2c; border-radius:8px; padding:12px;
         overflow:auto; font-size:.85rem; }}
  code {{ font-family: 'DejaVu Sans Mono', monospace; }}
  footer {{ margin-top:40px; color:#567; font-size:.8rem; text-align:center; }}
</style></head>
<body><div class="wrap">
<header>
  <h1>{esc(m.title)}</h1>
  <div class="metaline">{_header_meta(m)}</div>
</header>
<h2>Executive Summary</h2>
<p>{esc(m.summary) or '<em>No summary provided.</em>'}</p>
<h2>Findings Overview</h2>
<div class="chips">{chips}</div>
<p>Total findings: <strong>{len(m.findings)}</strong> &nbsp;·&nbsp;
   Average risk weight: <strong>{m.risk_score()}</strong> / 10</p>
<h2>Scope</h2><p>{scope_html}</p>
<h2>Detailed Findings</h2>
{findings_html}
<footer>Generated by KaliForge · {esc(m.date)}</footer>
</div></body></html>"""

    # --------------------------------------------------------------- json/csv
    def to_json(self) -> str:
        m = self.model
        return json.dumps({
            "title": m.title, "client": m.client, "workspace": m.workspace,
            "author": m.author, "date": m.date, "summary": m.summary,
            "scope": m.scope, "severity_counts": m.severity_counts(),
            "risk_score": m.risk_score(), "findings": m.sorted_findings(),
            "tool_versions": m.tool_versions,
        }, indent=2)

    def to_csv(self) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["#", "title", "severity", "cve", "cvss", "host", "port",
                         "service", "status", "description", "remediation"])
        for idx, f in enumerate(self.model.sorted_findings(), 1):
            writer.writerow([
                idx, f.get("title", ""), f.get("severity", ""), f.get("cve", ""),
                f.get("cvss", ""), f.get("host", ""), f.get("port", ""),
                f.get("service", ""), f.get("status", ""),
                (f.get("description", "") or "").replace("\n", " "),
                (f.get("remediation", "") or "").replace("\n", " "),
            ])
        return buffer.getvalue()

    # --------------------------------------------------------------- pdf
    @staticmethod
    def pdf_available() -> bool:
        return _HAVE_REPORTLAB

    def to_pdf(self, path: str | Path) -> Path:
        if not _HAVE_REPORTLAB:
            raise RuntimeError("ReportLab is not installed; export to HTML/PDF-print instead.")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        m = self.model
        doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle("KFTitle", parent=styles["Title"], textColor=colors.HexColor("#0b8f73")))
        styles.add(ParagraphStyle("KFH2", parent=styles["Heading2"], textColor=colors.HexColor("#0b6f7a")))
        story = [Paragraph(html.escape(m.title), styles["KFTitle"])]
        story.append(Paragraph(_header_meta(m), styles["Normal"]))
        story.append(Spacer(1, 10))
        story.append(Paragraph("Executive Summary", styles["KFH2"]))
        story.append(Paragraph(html.escape(m.summary or "No summary provided."), styles["Normal"]))
        story.append(Spacer(1, 10))

        counts = m.severity_counts()
        data = [["Severity", "Count"]] + [[s.title(), str(counts.get(s, 0))] for s in SEVERITIES]
        data.append(["Total", str(len(m.findings))])
        table = Table(data, hAlign="LEFT", colWidths=[80 * mm, 30 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b6f7a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(Paragraph("Findings Overview", styles["KFH2"]))
        story.append(table)
        story.append(Spacer(1, 10))

        story.append(Paragraph("Detailed Findings", styles["KFH2"]))
        for idx, f in enumerate(m.sorted_findings(), 1):
            story.append(Paragraph(
                f"{idx}. {html.escape(f.get('title', 'Untitled'))} "
                f"[{f.get('severity', 'info').upper()}]", styles["Heading4"]))
            if f.get("description"):
                story.append(Paragraph(html.escape(f["description"]), styles["Normal"]))
            if f.get("remediation"):
                story.append(Paragraph("<b>Remediation:</b> " + html.escape(f["remediation"]),
                                       styles["Normal"]))
            story.append(Spacer(1, 6))
        doc.build(story)
        return path

    # --------------------------------------------------------------- dispatch
    def save(self, path: str | Path, fmt: str | None = None) -> Path:
        path = Path(path)
        fmt = (fmt or path.suffix.lstrip(".")).lower()
        if fmt in ("md", "markdown"):
            path.write_text(self.to_markdown(), encoding="utf-8")
        elif fmt in ("html", "htm"):
            path.write_text(self.to_html(), encoding="utf-8")
        elif fmt == "json":
            path.write_text(self.to_json(), encoding="utf-8")
        elif fmt == "csv":
            path.write_text(self.to_csv(), encoding="utf-8")
        elif fmt == "pdf":
            self.to_pdf(path)
        else:
            raise ValueError(f"unsupported report format: {fmt}")
        return path


def _header_meta(m: ReportModel) -> str:
    bits = []
    if m.client:
        bits.append(f"Client: {html.escape(m.client)}")
    if m.workspace:
        bits.append(f"Workspace: {html.escape(m.workspace)}")
    if m.author:
        bits.append(f"Author: {html.escape(m.author)}")
    bits.append(f"Date: {html.escape(m.date)}")
    return " &nbsp;·&nbsp; ".join(bits)


def _meta_html(f: dict) -> str:
    bits = []
    if f.get("cve"):
        bits.append(f"<code>{html.escape(str(f['cve']))}</code>")
    if f.get("cvss") is not None:
        bits.append(f"<code>CVSS {html.escape(str(f['cvss']))}</code>")
    if f.get("host"):
        host = html.escape(str(f["host"]))
        port = f.get("port")
        bits.append(f"<code>{host}{':' + html.escape(str(port)) if port else ''}</code>")
    if f.get("service"):
        bits.append(f"<code>{html.escape(str(f['service']))}</code>")
    return "".join(bits)


def _section(title: str, body: str, mono: bool = False) -> str:
    if not body:
        return ""
    safe = html.escape(body)
    content = f"<pre>{safe}</pre>" if mono else f"<p>{safe}</p>"
    return f'<div class="sec"><h4>{title}</h4>{content}</div>'
