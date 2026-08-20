from datetime import datetime
from pathlib import Path

import pytest

from backtest_audit.models import Backtest, Trade

FIXTURES = Path(__file__).parent / "fixtures"


def t(symbol, side, qty, price, day, pnl=None):
    return Trade(
        symbol=symbol, side=side, quantity=qty, price=price,
        timestamp=datetime.fromisoformat(f"2024-01-{day:02d}"), pnl=pnl,
    )


@pytest.fixture
def clean_backtest():
    """60 balanced round trips, exits spread through the run, costs modelled."""
    trades = []
    for i in range(60):
        day = (i % 27) + 1
        trades.append(t("SPY", "buy", 10, 100.0 + i, day))
        trades.append(t("SPY", "sell", 10, 103.0 + i, day, pnl=30.0))
    return Backtest(trades=trades, exposure={"avg_gross_exposure": 0.95},
                    benchmarks={"spy_buy_hold": {"total_return": 0.5}})


@pytest.fixture
def real_prefix_backtest():
    """The June 2026 ETF run: 38 fills, only 4 opens / 7 closes.

    Ground truth (confirmed by hand in the source repo): a position-detection
    bug made the strategy blind to its own book, so it kept re-entering
    symbols it already held.
    """
    from backtest_audit.models import load
    return load(FIXTURES / "etf_prefix_2020-2024.json")


@pytest.fixture
def real_current_backtest():
    """The same universe after the exit fix: 13 opens / 13 closes."""
    from backtest_audit.models import load
    return load(FIXTURES / "etf_current_2020-2024.json")
