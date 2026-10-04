"""Render a run as one self-contained HTML file (FR-015, FR-031, FR-032).

Standard library only - no templating engine, because FR-031 permits no new
dependency. **Zero external requests**: no CDN, no web font, no analytics, so
it renders identically offline and on a locked-down machine.

This is deliberately **not** an Allure report, and FR-032 requires it to say
so: a reader who assumes parity goes looking for a timeline and history that
do not exist and concludes the report is broken.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from ai_qa.jira.errors import redact
from ai_qa.report.summary import UNATTRIBUTED, RunSummary

_STATUS_ORDER = ("failed", "broken", "passed", "skipped", "unknown")

_CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--muted:#666;--line:#e3e3e3;--pass:#1a7f37;
--fail:#b3261e;--skip:#8a6d00;--repair:#6a3ab2;--card:#fafafa}
@media(prefers-color-scheme:dark){:root{--bg:#15161a;--fg:#e8e8ea;--muted:#9a9aa3;
--line:#2c2e35;--pass:#4ac26b;--fail:#ff7b72;--skip:#d9b43a;--repair:#c29ffa;--card:#1c1e24}}
*{box-sizing:border-box}
body{margin:0;padding:24px 16px;background:var(--bg);color:var(--fg);
font:15px/1.55 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1040px;margin:0 auto}
h1{font-size:1.5rem;margin:0 0 4px}
.scope{font-size:1.05rem;font-weight:600;padding:10px 14px;border-left:4px solid var(--fg);
background:var(--card);margin:16px 0 8px}
.prov{color:var(--muted);font-size:.86rem;background:var(--card);padding:10px 14px;
border-radius:6px;margin-bottom:18px}
.counts{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 20px;padding:0;list-style:none}
.counts li{background:var(--card);border:1px solid var(--line);border-radius:6px;
padding:8px 12px;font-variant-numeric:tabular-nums}
.empty{border-left-color:var(--fail);color:var(--fail)}
h2{font-size:1.1rem;margin:26px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--line)}
.t{width:100%;border-collapse:collapse}
.t th,.t td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);
vertical-align:top}
.t th{font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.passed{color:var(--pass);font-weight:600}
.failed,.broken{color:var(--fail);font-weight:600}
.skipped{color:var(--skip);font-weight:600}
.rep{color:var(--repair);font-weight:700}
details{margin-top:6px}
summary{cursor:pointer;color:var(--muted);font-size:.85rem}
pre{overflow-x:auto;background:var(--card);padding:10px;border-radius:6px;
font-size:.82rem;white-space:pre-wrap;word-break:break-word}
.note{color:var(--muted);font-size:.85rem;margin-top:28px;padding-top:12px;
border-top:1px solid var(--line)}
@media(max-width:560px){body{padding:16px}.t th:nth-child(3),.t td:nth-child(3){display:none}}
"""


def render(summary: RunSummary, *, artifacts_dir: Path | str = "reports/artifacts") -> str:
    """Build the whole report as one HTML string."""
    rows: list[str] = []

    for ticket, results in summary.by_ticket.items():
        heading = (
            f"Ticket {escape(ticket)}"
            if ticket != UNATTRIBUTED
            else "Unattributed (no ticket marker)"
        )
        rows.append(f"<h2>{heading} &mdash; {len(results)} test(s)</h2>")
        rows.append(
            "<table class='t'><thead><tr><th>Test</th><th>Status</th>"
            "<th>Duration</th><th>Detail</th></tr></thead><tbody>"
        )
        for r in sorted(results, key=lambda x: (_rank(x.status), x.name)):
            rows.append(_row(r, summary, Path(artifacts_dir)))
        rows.append("</tbody></table>")

    scope_cls = "scope empty" if summary.empty else "scope"
    scope_text = (
        "Scope: this run collected ZERO tests - that is a failure, not a clean run"
        if summary.empty
        else f"Scope: {escape(summary.scope)} ({summary.collected} tests)"
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI-QA run summary</title><style>{_CSS}</style></head>
<body><div class="wrap">
<h1>AI-QA run summary</h1>
<div class="{scope_cls}">{scope_text}</div>
<div class="prov"><strong>This is a project-generated summary, not an Allure
report.</strong> It has no run timeline, no historical trend and no attachment
browser. For those, install the Allure CLI and run
<code>allure serve reports/allure-results</code> over the same result data.</div>
<ul class="counts">{_counts(summary)}</ul>
{"".join(rows) or "<p>No results found.</p>"}
<p class="note">Evidence links are relative. To view them, keep
<code>{escape(str(artifacts_dir))}/</code> alongside this file &mdash; the HTML
alone is readable, but its evidence links will not resolve if it is sent on its
own.</p>
</div></body></html>
"""


def _counts(summary: RunSummary) -> str:
    items = [f"<li><strong>{summary.collected}</strong> collected</li>"]
    for status in _STATUS_ORDER:
        n = summary.counts.get(status)
        if n:
            items.append(f"<li class='{status}'><strong>{n}</strong> {status}</li>")
    if summary.repaired:
        items.append(f"<li class='rep'><strong>{len(summary.repaired)}</strong> repaired</li>")
    return "".join(items)


def _row(r, summary: RunSummary, artifacts: Path) -> str:
    repaired = r.full_name in summary.repaired
    name = escape(r.name)
    if repaired:
        # A test passing because a tool modified it is a materially different
        # claim from one passing as authored (FR-041). A reader skimming for
        # green must not miss it.
        name += " <span class='rep'>[REPAIRED]</span>"

    detail: list[str] = []
    if r.failure_message:
        detail.append(f"<div>{escape(redact(r.failure_message)[:400])}</div>")
    if r.failure_trace:
        detail.append(
            "<details><summary>traceback</summary><pre>"
            f"{escape(redact(r.failure_trace)[:6000])}</pre></details>"
        )
    evidence = r.evidence_dir(artifacts)
    if evidence.exists():
        files = sorted(p.name for p in evidence.iterdir() if p.is_file())
        links = " ".join(
            f"<a href='{escape(str(evidence).replace(chr(92), '/'))}/{escape(f)}'>{escape(f)}</a>"
            for f in files
        )
        if links:
            detail.append(f"<div>evidence: {links}</div>")
    if r.approval:
        detail.append(f"<div>approval: {escape(r.approval)}</div>")

    return (
        f"<tr><td>{name}</td><td class='{escape(r.status)}'>{escape(r.status)}</td>"
        f"<td>{r.duration_ms} ms</td><td>{''.join(detail) or '&mdash;'}</td></tr>"
    )


def _rank(status: str) -> int:
    return _STATUS_ORDER.index(status) if status in _STATUS_ORDER else len(_STATUS_ORDER)


def write(summary: RunSummary, *, out: Path | str = "reports/report.html", artifacts_dir: Path | str = "reports/artifacts") -> Path:
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(summary, artifacts_dir=artifacts_dir), encoding="utf-8")
    return path
