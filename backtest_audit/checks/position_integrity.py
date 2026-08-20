"""Does the run appear to know what it already holds?"""

from __future__ import annotations

from backtest_audit.checks.base import Finding, Severity, skipped
from backtest_audit.positions import replay


class PositionIntegrityCheck:
    id = "position-integrity"
    title = "Position awareness"

    def run(self, bt):
        if not bt.trades:
            return skipped(self.id, self.title, "the trade log is empty")

        events = replay(bt)
        adds = [e for e in events if e.adds]
        opens = [e for e in events if e.opens]
        share = len(adds) / len(events)

        ev = {
            "fills": len(events),
            "opens": len(opens),
            "adds_to_open_positions": len(adds),
            "add_share": round(share, 3),
            "symbols_added_to": sorted({e.trade.symbol for e in adds}),
        }

        # Pyramiding is a legitimate design, but it is rare for a majority of
        # fills to be adds. When it happens alongside very few opens, the
        # usual cause is a position lookup that silently returns nothing, so
        # the strategy re-enters names it already holds.
        if share >= 0.4 and len(adds) >= 5:
            return Finding(
                check_id=self.id, title=self.title, severity=Severity.BLOCKING,
                summary=(
                    f"{len(adds)} of {len(events)} fills ({share:.0%}) added to a position "
                    f"the run already held, across only {len(opens)} genuine entries"
                ),
                detail=(
                    "A strategy that re-enters names it already holds is usually blind to "
                    "its own book — a position lookup returning nothing rather than a "
                    "deliberate pyramiding rule. Size and exposure are then unintentional, "
                    "and any per-trade statistic is counting the same idea many times."
                ),
                remedy=(
                    "Log the position the strategy sees at each entry decision and confirm "
                    "it matches the broker's book. If pyramiding is intended, say so "
                    "explicitly and cap the number of adds per symbol."
                ),
                evidence=ev,
            )

        if share >= 0.2 and len(adds) >= 3:
            return Finding(
                check_id=self.id, title=self.title, severity=Severity.WARNING,
                summary=f"{len(adds)} of {len(events)} fills ({share:.0%}) added to open positions",
                detail="Legitimate if pyramiding is intended; suspicious otherwise.",
                remedy="Confirm the strategy is meant to add to winners.",
                evidence=ev,
            )

        return Finding(
            check_id=self.id, title=self.title, severity=Severity.PASS,
            summary=f"{len(opens)} entries, no unexplained adds to open positions",
            evidence=ev,
        )
