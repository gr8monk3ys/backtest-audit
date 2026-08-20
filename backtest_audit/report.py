"""Rendering: terminal first, HTML for sharing."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass

from backtest_audit.checks.base import Finding, Severity

_MARK = {
    Severity.BLOCKING: "✗",
    Severity.WARNING: "!",
    Severity.PASS: "✓",
    Severity.SKIPPED: "?",
}
_ANSI = {
    Severity.BLOCKING: "\033[31m",
    Severity.WARNING: "\033[33m",
    Severity.PASS: "\033[32m",
    Severity.SKIPPED: "\033[90m",
}
_RESET = "\033[0m"


@dataclass
class Audit:
    findings: list[Finding]
    source: str

    @property
    def blocking(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.BLOCKING]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.WARNING]

    @property
    def skipped(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.SKIPPED]

    @property
    def trustworthy(self) -> bool:
        return not self.blocking

    @property
    def verdict(self) -> str:
        if self.blocking:
            return "NOT TRUSTWORTHY"
        if self.warnings:
            return "TRUSTWORTHY WITH CAVEATS"
        if self.skipped:
            return "TRUSTWORTHY (some checks unjudged)"
        return "TRUSTWORTHY"

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "verdict": self.verdict,
            "trustworthy": self.trustworthy,
            "findings": [
                {
                    "id": f.check_id, "title": f.title, "severity": f.severity.value,
                    "summary": f.summary, "detail": f.detail, "remedy": f.remedy,
                    "evidence": f.evidence,
                }
                for f in self.findings
            ],
        }


def render_text(audit: Audit, color: bool = True, verbose: bool = False) -> str:
    def paint(sev: Severity, text: str) -> str:
        return f"{_ANSI[sev]}{text}{_RESET}" if color else text

    out = [f"\nbacktest-audit  {audit.source}", "=" * 72, ""]
    for f in audit.findings:
        mark = paint(f.severity, _MARK[f.severity])
        out.append(f"  {mark} {f.title:<26} {f.summary}")
        if verbose or f.severity in (Severity.BLOCKING, Severity.WARNING):
            if f.detail:
                for line in _wrap(f.detail, 66):
                    out.append(f"      {line}")
            if f.remedy:
                out.append(f"      → {_wrap(f.remedy, 64)[0]}")
                for line in _wrap(f.remedy, 64)[1:]:
                    out.append(f"        {line}")
            out.append("")
    out.append("-" * 72)
    counts = (
        f"{len(audit.blocking)} blocking, {len(audit.warnings)} warning, "
        f"{len(audit.skipped)} unjudged"
    )
    sev = Severity.BLOCKING if audit.blocking else (
        Severity.WARNING if audit.warnings else Severity.PASS
    )
    out.append(f"  VERDICT: {paint(sev, audit.verdict)}  ({counts})")
    out.append("")
    return "\n".join(out)


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines or [""]


def render_html(audit: Audit) -> str:
    rows = []
    for f in audit.findings:
        ev = html.escape(json.dumps(f.evidence, indent=2, default=str))
        rows.append(f"""
    <article class="f {f.severity.value}">
      <h3><span class="mark">{_MARK[f.severity]}</span> {html.escape(f.title)}</h3>
      <p class="sum">{html.escape(f.summary)}</p>
      {f'<p class="detail">{html.escape(f.detail)}</p>' if f.detail else ''}
      {f'<p class="remedy"><strong>What to do:</strong> {html.escape(f.remedy)}</p>' if f.remedy else ''}
      <details><summary>Evidence</summary><pre>{ev}</pre></details>
    </article>""")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Backtest audit — {html.escape(audit.source)}</title>
<style>
  :root {{ color-scheme: light dark;
    --bg:#fff; --fg:#111; --muted:#666; --line:#e5e5e5; --card:#fafafa;
    --block:#c0392b; --warn:#b7791f; --pass:#2f855a; --skip:#888; }}
  @media (prefers-color-scheme: dark) {{ :root {{
    --bg:#131315; --fg:#eaeaea; --muted:#9a9a9a; --line:#2a2a2e; --card:#1b1b1e;
    --block:#ff6b5e; --warn:#e8b339; --pass:#54c98a; --skip:#888; }} }}
  body {{ background:var(--bg); color:var(--fg); margin:0; padding:2rem 1.25rem;
    font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }}
  main {{ max-width:52rem; margin:0 auto; }}
  h1 {{ font-size:1.5rem; margin:0 0 .25rem; }}
  .src {{ color:var(--muted); font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
    font-size:.85rem; margin-bottom:1.5rem; word-break:break-all; }}
  .verdict {{ font-weight:700; padding:.85rem 1rem; border-radius:.5rem;
    border:1px solid var(--line); background:var(--card); margin-bottom:1.5rem; }}
  .verdict.bad {{ color:var(--block); border-color:var(--block); }}
  .verdict.ok {{ color:var(--pass); border-color:var(--pass); }}
  .f {{ border:1px solid var(--line); border-left-width:4px; border-radius:.4rem;
    background:var(--card); padding:.9rem 1.1rem; margin-bottom:.9rem; }}
  .f.blocking {{ border-left-color:var(--block); }}
  .f.warning  {{ border-left-color:var(--warn); }}
  .f.pass     {{ border-left-color:var(--pass); }}
  .f.skipped  {{ border-left-color:var(--skip); }}
  .f h3 {{ margin:0 0 .3rem; font-size:1rem; }}
  .mark {{ font-family:ui-monospace,monospace; margin-right:.4rem; }}
  .blocking .mark {{ color:var(--block); }} .warning .mark {{ color:var(--warn); }}
  .pass .mark {{ color:var(--pass); }} .skipped .mark {{ color:var(--skip); }}
  .sum {{ margin:.2rem 0; }}
  .detail, .remedy {{ color:var(--muted); font-size:.92rem; margin:.5rem 0 0; }}
  details {{ margin-top:.6rem; }} summary {{ cursor:pointer; color:var(--muted);
    font-size:.85rem; }}
  pre {{ overflow-x:auto; background:var(--bg); border:1px solid var(--line);
    border-radius:.35rem; padding:.7rem; font-size:.8rem; }}
</style></head><body><main>
  <h1>Backtest audit</h1>
  <p class="src">{html.escape(audit.source)}</p>
  <p class="verdict {'bad' if audit.blocking else 'ok'}">{audit.verdict}
    <span style="font-weight:400;color:var(--muted)"> — {len(audit.blocking)} blocking,
    {len(audit.warnings)} warning, {len(audit.skipped)} unjudged</span></p>
  {''.join(rows)}
</main></body></html>"""
