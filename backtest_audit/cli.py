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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        result = audit_file(args.path)
    except (OSError, ValueError) as exc:
        print(f"btaudit: cannot audit {args.path}: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        color = not args.no_color and sys.stdout.isatty()
        print(render_text(result, color=color, verbose=args.verbose))

    if args.html:
        Path(args.html).write_text(render_html(result))
        if not args.as_json:
            print(f"  HTML report: {args.html}\n")

    if result.blocking:
        return 1
    if args.strict and result.warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
