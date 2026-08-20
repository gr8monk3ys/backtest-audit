"""Each check is asserted against real artifacts with independently known bugs.

The two ETF fixtures are genuine output from a real strategy, before and
after a documented fix. Their defects were confirmed by hand in the source
repo, so they function as labelled ground truth rather than as mocks that
merely agree with the implementation.
"""

from backtest_audit.checks import ALL_CHECKS, Severity
from backtest_audit.checks.costs import CostRealismCheck
from backtest_audit.checks.exit_reachability import ExitReachabilityCheck
from backtest_audit.checks.exposure import ExposureMatchCheck
from backtest_audit.checks.position_integrity import PositionIntegrityCheck
from backtest_audit.checks.short_liability import ShortLiabilityCheck
from backtest_audit.checks.significance import SignificanceCheck


def _run(check, bt):
    return check.run(bt)


class TestPositionIntegrity:
    def test_flags_repeated_entries_into_held_symbols(self, real_prefix_backtest):
        # 38 fills but only 4 opens: the run kept adding to positions it held.
        f = _run(PositionIntegrityCheck(), real_prefix_backtest)
        assert f.severity is Severity.BLOCKING
        # Measured from the artifact: 4 opens + 7 closes + 18 adds + 9 partial
        # reductions = 38 fills. Every one of the four symbols was re-entered.
        assert f.evidence["adds_to_open_positions"] == 18
        assert f.evidence["symbols_added_to"] == ["EFA", "IWM", "QQQ", "SPY"]

    def test_balanced_round_trips_pass(self, real_current_backtest):
        f = _run(PositionIntegrityCheck(), real_current_backtest)
        assert f.severity is Severity.PASS

    def test_clean_backtest_passes(self, clean_backtest):
        assert _run(PositionIntegrityCheck(), clean_backtest).severity is Severity.PASS


class TestExitReachability:
    def test_all_exits_on_final_bar_is_blocking(self, clean_backtest):
        # Hold-to-the-end: every close happens on the last bar, so the run
        # measures buy-and-hold no matter what the signal did.
        from datetime import datetime

        from backtest_audit.models import Backtest, Trade
        trades = []
        for sym in ["SPY", "QQQ", "IWM", "EFA"]:
            trades.append(Trade(sym, "buy", 10, 100.0, datetime(2020, 6, 12)))
            trades.append(Trade(sym, "sell", 10, 150.0, datetime(2024, 12, 30), pnl=500.0))
        f = _run(ExitReachabilityCheck(), Backtest(trades=trades))
        assert f.severity is Severity.BLOCKING
        assert f.evidence["forced_exit_share"] == 1.0

    def test_real_run_with_working_exits_is_not_blocking(self, real_current_backtest):
        f = _run(ExitReachabilityCheck(), real_current_backtest)
        assert f.severity is not Severity.BLOCKING
        assert 0.0 < f.evidence["forced_exit_share"] < 0.5

    def test_spread_out_exits_pass(self, clean_backtest):
        assert _run(ExitReachabilityCheck(), clean_backtest).severity is Severity.PASS


class TestShortLiability:
    def test_short_without_position_is_detected(self):
        from datetime import datetime

        from backtest_audit.models import Backtest, Trade
        # Sell 100 never held, then never covered: a naked short that many
        # engines book as free cash with no liability.
        bt = Backtest(trades=[Trade("IWM", "sell", 100, 50.0, datetime(2022, 5, 5))])
        f = _run(ShortLiabilityCheck(), bt)
        assert f.severity in (Severity.BLOCKING, Severity.WARNING)
        assert f.evidence["uncovered_short_symbols"] == ["IWM"]

    def test_long_only_run_passes(self, clean_backtest):
        assert _run(ShortLiabilityCheck(), clean_backtest).severity is Severity.PASS


class TestExposureMatch:
    def test_missing_exposure_is_skipped_not_passed(self, real_prefix_backtest):
        # The June artifact never reported exposure, so comparability to a
        # 100%-invested benchmark cannot be judged.
        f = _run(ExposureMatchCheck(), real_prefix_backtest)
        assert f.severity is Severity.SKIPPED

    def test_low_exposure_vs_benchmark_warns(self, real_current_backtest):
        f = _run(ExposureMatchCheck(), real_current_backtest)
        assert f.severity is Severity.WARNING
        assert f.evidence["avg_gross_exposure"] < 0.7


class TestCostRealism:
    def test_zero_cost_backtest_warns(self):
        from datetime import datetime

        from backtest_audit.models import Backtest, Trade
        # Every round trip fills at exactly the same price: no spread, no slippage.
        trades = []
        for d in range(1, 21):
            trades.append(Trade("SPY", "buy", 10, 100.0, datetime(2024, 1, d)))
            trades.append(Trade("SPY", "sell", 10, 100.0, datetime(2024, 1, d)))
        f = _run(CostRealismCheck(), Backtest(trades=trades))
        assert f.severity is Severity.WARNING


class TestSignificance:
    def test_below_trade_bar_warns(self, real_current_backtest):
        f = _run(SignificanceCheck(), real_current_backtest)
        assert f.severity is Severity.WARNING
        assert f.evidence["n_trades"] == 26

    def test_sixty_round_trips_passes(self, clean_backtest):
        assert _run(SignificanceCheck(), clean_backtest).severity is Severity.PASS


def test_every_registered_check_runs_on_every_fixture(
    clean_backtest, real_prefix_backtest, real_current_backtest
):
    for bt in (clean_backtest, real_prefix_backtest, real_current_backtest):
        for check in ALL_CHECKS:
            f = check.run(bt)
            assert f.check_id and f.title and f.summary
            assert isinstance(f.severity, Severity)
