"""Interop with a foreign framework, proven rather than asserted.

`backtrader_sma_cross.csv` is genuine output from backtrader 1.9.78.123
running an SMA-crossover strategy with commission enabled — exported the
way a user would, with backtrader's own column names and no reshaping.
Committing it keeps the "works with any framework" claim honest: if
ingestion regresses, this test fails.
"""

from pathlib import Path

from backtest_audit.audit import audit_file
from backtest_audit.checks.base import Severity
from backtest_audit.models import load

FIXTURE = Path(__file__).parent / "fixtures" / "backtrader_sma_cross.csv"


def test_backtrader_export_loads_without_reshaping():
    bt = load(FIXTURE)
    assert len(bt.trades) == 12
    first = bt.trades[0]
    # backtrader calls it `size`, not `quantity`, and `datetime`, not `timestamp`.
    assert first.quantity == 100
    assert first.side == "buy"
    assert first.symbol == "SYNTH"
    assert first.fees is not None  # commission column picked up


def test_backtrader_run_audits_clean():
    result = audit_file(FIXTURE)
    assert result.trustworthy
    assert not result.blocking

    by_id = {f.check_id: f for f in result.findings}
    # Alternating buy/close pairs: balanced round trips, real exits.
    assert by_id["position-integrity"].severity is Severity.PASS
    assert by_id["exit-reachability"].severity is Severity.PASS
    assert by_id["exit-reachability"].evidence["closes"] == 6
    # Commission is charged on every fill, so frictions are modelled.
    assert by_id["cost-realism"].severity is Severity.PASS
    # Long-only strategy: nothing to verify on the short side.
    assert by_id["short-liability"].severity is Severity.PASS
    # Six round trips is honest but under the bar.
    assert by_id["significance"].severity is Severity.WARNING
