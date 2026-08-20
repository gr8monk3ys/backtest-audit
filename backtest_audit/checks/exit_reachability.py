"""Did the strategy ever choose to exit, or did the backtest end for it?"""

from __future__ import annotations

from backtest_audit.checks.base import Finding, Severity, skipped
from backtest_audit.positions import replay


class ExitReachabilityCheck:
    id = "exit-reachability"
    title = "Exit reachability"

    def run(self, bt):
        events = replay(bt)
        closes = [e for e in events if e.closes]
        if not closes:
            if not bt.trades:
                return skipped(self.id, self.title, "the trade log is empty")
            return Finding(
                check_id=self.id, title=self.title, severity=Severity.BLOCKING,
                summary="no position was ever closed",
                detail=(
                    "Every position opened stays open to the end of the record. The "
                    "headline is unrealised mark-to-market, not a traded result."
                ),
                remedy="Close positions at the end of the run and re-read the number.",
                evidence={"closes": 0, "forced_exit_share": 1.0},
            )

        final = bt.final_date
        forced = [e for e in closes if e.trade.date == final]
        share = len(forced) / len(closes)
        ev = {
            "closes": len(closes),
            "closes_on_final_bar": len(forced),
            "forced_exit_share": round(share, 3),
            "final_bar": final,
        }

        if share >= 0.9:
            return Finding(
                check_id=self.id, title=self.title, severity=Severity.BLOCKING,
                summary=(
                    f"{len(forced)} of {len(closes)} exits ({share:.0%}) happen on the final "
                    "bar — the strategy never chose to exit"
                ),
                detail=(
                    "When essentially every close lands on the last bar, positions were "
                    "held to the end and liquidated by the harness. Whatever the entry "
                    "signal is worth, this run measures buy-and-hold of what it bought: "
                    "market exposure, not strategy timing. Trailing stops and exit rules "
                    "that were never executed cannot be credited."
                ),
                remedy=(
                    "Verify the exit path is reachable — that the signal generator can "
                    "emit an exit at all, and that the engine calls the code that "
                    "evaluates exits. Then re-run and compare."
                ),
                evidence=ev,
            )

        if share >= 0.5:
            return Finding(
                check_id=self.id, title=self.title, severity=Severity.WARNING,
                summary=f"{share:.0%} of exits happen on the final bar",
                detail="A large share of the result comes from end-of-run liquidation.",
                remedy="Check whether exit conditions fire as often as intended.",
                evidence=ev,
            )

        return Finding(
            check_id=self.id, title=self.title, severity=Severity.PASS,
            summary=f"{len(closes) - len(forced)} of {len(closes)} exits were strategy decisions",
            evidence=ev,
        )
