"""Run the registered checks over a backtest."""

from __future__ import annotations

from pathlib import Path

from backtest_audit.checks import ALL_CHECKS
from backtest_audit.models import Backtest, load
from backtest_audit.report import Audit


def audit(bt: Backtest) -> Audit:
    return Audit(findings=[c.run(bt) for c in ALL_CHECKS], source=bt.source)


def audit_file(path: str | Path) -> Audit:
    return audit(load(path))
