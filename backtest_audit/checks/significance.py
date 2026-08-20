"""Is there enough evidence here to support a performance claim?"""

from __future__ import annotations

from backtest_audit.checks.base import Finding, Severity, skipped
from backtest_audit.positions import replay

# Below roughly this many round trips, Sharpe and win rate are dominated by
# sampling noise. It is a convention, not a law, but claims made under it
# should be labelled provisional.
TRADE_BAR = 50


class SignificanceCheck:
    id = "significance"
    title = "Statistical significance"

    def run(self, bt):
        if not bt.trades:
            return skipped(self.id, self.title, "the trade log is empty")

        events = replay(bt)
        closes = sum(1 for e in events if e.closes)
        ev = {"n_trades": len(bt.trades), "round_trips": closes, "bar": TRADE_BAR}

        if closes < TRADE_BAR:
            return Finding(
                check_id=self.id, title=self.title, severity=Severity.WARNING,
                summary=(
                    f"{closes} round trips is below the {TRADE_BAR}-trade bar — "
                    "Sharpe and win rate are not yet meaningful"
                ),
                detail=(
                    "With this few closed trades, performance statistics are dominated "
                    "by a handful of outcomes. The result may still be directionally "
                    "informative, but it cannot support a precise claim."
                ),
                remedy=(
                    "Extend the period or widen the universe until the run clears the "
                    "bar, and label any number quoted before then as provisional."
                ),
                evidence=ev,
            )

        return Finding(
            check_id=self.id, title=self.title, severity=Severity.PASS,
            summary=f"{closes} round trips clears the {TRADE_BAR}-trade bar",
            evidence=ev,
        )
