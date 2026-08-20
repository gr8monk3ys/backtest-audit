"""Fills that could not have happened, and fills counted twice."""

from __future__ import annotations

from collections import Counter

from backtest_audit.checks.base import Finding, Severity, skipped


class DataSanityCheck:
    id = "data-sanity"
    title = "Trade log sanity"

    def run(self, bt):
        if not bt.trades:
            return skipped(self.id, self.title, "the trade log is empty")

        bad_price = [t for t in bt.trades if t.price <= 0]
        bad_qty = [t for t in bt.trades if t.quantity <= 0]

        keys = Counter(
            (t.symbol, t.side, t.quantity, round(t.price, 8), t.timestamp) for t in bt.trades
        )
        dupes = sum(c - 1 for c in keys.values() if c > 1)

        ordered = all(
            a.timestamp <= b.timestamp for a, b in zip(bt.trades, bt.trades[1:], strict=False)
        )

        ev = {
            "fills": len(bt.trades),
            "non_positive_price": len(bad_price),
            "non_positive_quantity": len(bad_qty),
            "duplicate_fills": dupes,
            "chronological": ordered,
        }

        if bad_price or bad_qty:
            parts = []
            if bad_price:
                parts.append(f"{len(bad_price)} fill(s) at a price of zero or less")
            if bad_qty:
                parts.append(f"{len(bad_qty)} fill(s) with zero or negative quantity")
            return Finding(
                check_id=self.id, title=self.title, severity=Severity.BLOCKING,
                summary=" and ".join(parts),
                detail=(
                    "These fills could not have occurred. They usually mean a data gap "
                    "was filled with a default, or a sign convention leaked into a field "
                    "that should always be positive. Any statistic computed over them is "
                    "meaningless."
                ),
                remedy="Find where those rows come from and fix the source, not the report.",
                evidence=ev,
            )

        if dupes:
            return Finding(
                check_id=self.id, title=self.title, severity=Severity.WARNING,
                summary=f"{dupes} fill(s) appear more than once, identical in every field",
                detail=(
                    "Exact duplicates are occasionally real, but far more often they are "
                    "a trade recorded twice — which double counts both the position and "
                    "the P&L attributed to it."
                ),
                remedy="Deduplicate on (symbol, side, quantity, price, timestamp) and re-run.",
                evidence=ev,
            )

        if not ordered:
            return Finding(
                check_id=self.id, title=self.title, severity=Severity.WARNING,
                summary="fills are not in chronological order",
                detail=(
                    "Out-of-order fills make position reconstruction ambiguous, and can "
                    "hide a fill that was recorded against the wrong bar."
                ),
                remedy="Sort by timestamp at export time and confirm the order is stable.",
                evidence=ev,
            )

        return Finding(
            check_id=self.id, title=self.title, severity=Severity.PASS,
            summary=f"{len(bt.trades)} fills, all well-formed and in order",
            evidence=ev,
        )
