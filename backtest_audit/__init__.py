"""backtest-audit — find the defects that make a backtest lie.

    from backtest_audit import audit_file
    result = audit_file("results.json")
    print(result.verdict, result.blocking)
"""

from backtest_audit.audit import audit, audit_file
from backtest_audit.checks.base import Finding, Severity
from backtest_audit.models import Backtest, Trade, load
from backtest_audit.report import Audit

__version__ = "0.1.0"
__all__ = [
    "audit", "audit_file", "load", "Audit", "Backtest", "Trade", "Finding", "Severity",
]
