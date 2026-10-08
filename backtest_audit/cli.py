"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from backtest_audit.audit import audit_file
from backtest_audit.report import render_html, render_text


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="btaudit",
        description=(
            "Audit a backtest result for the defects that silently inflate it. "
            "Reads a trade log (JSON or CSV) from any backtesting framework."
        ),
    )
    p.add_argument("path", help="backtest result: .json or .csv trade log")
    p.add_argument("--html", metavar="FILE", help="also write an HTML report")
    p.add_argument("--json", action="store_true", dest="as_json",
                   help="emit machine-readable JSON instead of text")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="show detail for passing checks too")
    p.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    p.add_argument("--strict", action="store_true",
                   help="exit non-zero on warnings as well as blocking findings")
    return p


def _stdout_can_encode(text: str) -> bool:
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        text.encode(enc)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def _make_stdout_safe() -> None:
    """Never let a console encoding (cp1252 on Windows) turn a report into a crash."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(errors="replace")
    except (ValueError, OSError):
        pass


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _run(args)
    except Exception as exc:
        # Exit 1 means "blocking finding"; a crash must never be mistaken for one.
        print(f"btaudit: internal error auditing {args.path}: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


def _run(args: argparse.Namespace) -> int:
    try:
        result = audit_file(args.path)
    except (OSError, ValueError) as exc:
        print(f"btaudit: cannot audit {args.path}: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        _make_stdout_safe()
        color = not args.no_color and sys.stdout.isatty()
        unicode_marks = _stdout_can_encode("✓✗→")
        print(render_text(result, color=color, verbose=args.verbose,
                          unicode_marks=unicode_marks))

    if args.html:
        Path(args.html).write_text(render_html(result), encoding="utf-8")
        if not args.as_json:
            print(f"  HTML report: {args.html}\n")

    if result.blocking:
        return 1
    if args.strict and result.warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
