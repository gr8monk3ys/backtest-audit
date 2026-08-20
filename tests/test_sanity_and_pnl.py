"""Data sanity and P&L reconciliation.

Both catch a class of problem that is invisible in a summary table: the
artifact can look perfectly well-formed while describing fills that could
not have happened, or while reporting a headline that its own trade log
does not support.
"""

from datetime import datetime

import pytest

from backtest_audit.checks.base import Severity
from backtest_audit.checks.data_sanity import DataSanityCheck
from backtest_audit.checks.pnl_reconciliation import PnLReconciliationCheck
from backtest_audit.models import Backtest, Trade


def tr(sym="SPY", side="buy", qty=10, price=100.0, day=2, pnl=None):
    return Trade(sym, side, qty, price, datetime(2024, 1, day), pnl=pnl)


class TestDataSanity:
    def test_non_positive_price_is_blocking(self):
        bt = Backtest(trades=[tr(), tr(price=0.0), tr(price=-5.0)])
        f = DataSanityCheck().run(bt)
        assert f.severity is Severity.BLOCKING
        assert f.evidence["non_positive_price"] == 2

    def test_zero_quantity_is_blocking(self):
        f = DataSanityCheck().run(Backtest(trades=[tr(), tr(qty=0)]))
        assert f.severity is Severity.BLOCKING
        assert f.evidence["non_positive_quantity"] == 1

    def test_exact_duplicate_fills_warn(self):
        dup = tr(day=5)
        bt = Backtest(trades=[dup, dup, tr(day=6), tr(day=7)])
        f = DataSanityCheck().run(bt)
        assert f.severity is Severity.WARNING
        assert f.evidence["duplicate_fills"] == 1

    def test_clean_log_passes(self):
        bt = Backtest(trades=[tr(day=2), tr(day=3, price=101.0), tr(day=4, price=99.0)])
        assert DataSanityCheck().run(bt).severity is Severity.PASS

    def test_real_artifacts_are_sane(self, real_prefix_backtest, real_current_backtest):
        for bt in (real_prefix_backtest, real_current_backtest):
            assert DataSanityCheck().run(bt).severity is Severity.PASS


class TestPnLReconciliation:
    def test_skipped_without_an_equity_curve(self, real_current_backtest):
        # The ETF artifacts report only a curve summary, so this cannot be
        # judged — and must say so rather than quietly passing.
        f = PnLReconciliationCheck().run(real_current_backtest)
        assert f.severity is Severity.SKIPPED

    def test_matching_pnl_and_curve_passes(self):
        bt = Backtest(
            trades=[tr(pnl=50.0, day=2), tr(side="sell", pnl=50.0, day=3)],
            equity_curve=[1000.0, 1100.0],
        )
        assert PnLReconciliationCheck().run(bt).severity is Severity.PASS

    def test_curve_gain_far_exceeding_realised_pnl_warns(self):
        # Equity climbs 500 while the trade log realises 20: the headline is
        # mostly unrealised mark-to-market on positions never closed.
        bt = Backtest(
            trades=[tr(pnl=10.0, day=2), tr(side="sell", pnl=10.0, day=3)],
            equity_curve=[1000.0, 1500.0],
        )
        f = PnLReconciliationCheck().run(bt)
        assert f.severity is Severity.WARNING
        assert f.evidence["curve_change"] == pytest.approx(500.0)
        assert f.evidence["realised_pnl"] == pytest.approx(20.0)


def test_new_checks_are_registered():
    from backtest_audit.checks import ALL_CHECKS

    ids = {c.id for c in ALL_CHECKS}
    assert {"data-sanity", "pnl-reconciliation"} <= ids
