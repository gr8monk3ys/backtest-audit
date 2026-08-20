"""Check registry. Import order defines report order."""

from backtest_audit.checks.base import Check, Finding, Severity, skipped
from backtest_audit.checks.costs import CostRealismCheck
from backtest_audit.checks.data_sanity import DataSanityCheck
from backtest_audit.checks.exit_reachability import ExitReachabilityCheck
from backtest_audit.checks.exposure import ExposureMatchCheck
from backtest_audit.checks.pnl_reconciliation import PnLReconciliationCheck
from backtest_audit.checks.position_integrity import PositionIntegrityCheck
from backtest_audit.checks.short_liability import ShortLiabilityCheck
from backtest_audit.checks.significance import SignificanceCheck

ALL_CHECKS: list[Check] = [
    DataSanityCheck(),
    PositionIntegrityCheck(),
    ExitReachabilityCheck(),
    ShortLiabilityCheck(),
    ExposureMatchCheck(),
    CostRealismCheck(),
    PnLReconciliationCheck(),
    SignificanceCheck(),
]

__all__ = ["ALL_CHECKS", "Check", "Finding", "Severity", "skipped"]
