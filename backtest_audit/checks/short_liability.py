"""Are short positions carried as liabilities, or booked as free cash?"""

from __future__ import annotations

from backtest_audit.checks.base import Finding, Severity, skipped
from backtest_audit.positions import final_book, replay


class ShortLiabilityCheck:
    id = "short-liability"
    title = "Short accounting"

    def run(self, bt):
        if not bt.trades:
            return skipped(self.id, self.title, "the trade log is empty")

        events = replay(bt)
        short_opens = [e for e in events if e.opens and e.after < 0]
        if not short_opens:
            return Finding(
                check_id=self.id, title=self.title, severity=Severity.PASS,
                summary="long-only run — no short accounting to verify",
                evidence={"short_entries": 0},
            )

        book = final_book(bt)
        uncovered = sorted(s for s, q in book.items() if q < 0)
        ev = {
            "short_entries": len(short_opens),
            "uncovered_short_symbols": uncovered,
            "open_short_quantity": {s: book[s] for s in uncovered},
        }

        if uncovered:
            return Finding(
                check_id=self.id, title=self.title, severity=Severity.BLOCKING,
                summary=(
                    f"{len(uncovered)} short position(s) are never covered: "
                    f"{', '.join(uncovered)}"
                ),
                detail=(
                    "A short that is opened and never closed credits the sale proceeds "
                    "to cash. If the engine does not also record the borrow as a "
                    "liability, that cash is invented and inflates equity for the rest "
                    "of the run — a defect that can turn a losing strategy into a "
                    "spectacular one."
                ),
                remedy=(
                    "Confirm the broker model creates a negative position on a sell that "
                    "exceeds holdings, and that end-of-run liquidation covers shorts. "
                    "Then reconcile final equity against cash plus signed positions."
                ),
                evidence=ev,
            )

        return Finding(
            check_id=self.id, title=self.title, severity=Severity.PASS,
            summary=f"{len(short_opens)} short entries, all covered by the end of the run",
            evidence=ev,
        )
