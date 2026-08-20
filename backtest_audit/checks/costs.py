"""Were trading frictions modelled at all?"""

from __future__ import annotations

from collections import defaultdict

from backtest_audit.checks.base import Finding, Severity, skipped
from backtest_audit.positions import replay


class CostRealismCheck:
    id = "cost-realism"
    title = "Cost realism"

    def run(self, bt):
        if len(bt.trades) < 4:
            return skipped(self.id, self.title, "too few fills to infer a cost model")

        events = replay(bt)
        # Same symbol, same bar, opposite sides: an in-and-out round trip. If
        # those consistently fill at an identical price, no spread or slippage
        # is being applied.
        by_key: dict[tuple[str, str], list] = defaultdict(list)
        for e in events:
            by_key[(e.trade.symbol, e.trade.date)].append(e.trade)

        same_bar_pairs = 0
        frictionless = 0
        for fills in by_key.values():
            sides = {f.side for f in fills}
            if len(fills) >= 2 and sides == {"buy", "sell"}:
                same_bar_pairs += 1
                prices = {round(f.price, 6) for f in fills}
                if len(prices) == 1:
                    frictionless += 1

        fees_reported = any(t.fees for t in bt.trades)
        ev = {
            "same_bar_round_trips": same_bar_pairs,
            "frictionless_round_trips": frictionless,
            "fees_reported": fees_reported,
        }

        if same_bar_pairs >= 3 and frictionless == same_bar_pairs and not fees_reported:
            return Finding(
                check_id=self.id, title=self.title, severity=Severity.WARNING,
                summary=(
                    f"all {same_bar_pairs} same-bar round trips filled at an identical "
                    "price with no fees recorded — frictions look unmodelled"
                ),
                detail=(
                    "Buying and selling at exactly the same price means no spread, no "
                    "slippage and no commission were charged. Frictions are what kill "
                    "most high-turnover edges, so a frictionless backtest is optimistic "
                    "in exactly the place that decides whether a strategy is viable."
                ),
                remedy=(
                    "Apply a spread and a slippage model sized to the instrument's "
                    "liquidity, then re-run. If the edge does not survive plausible "
                    "costs, it was never an edge."
                ),
                evidence=ev,
            )

        return Finding(
            check_id=self.id, title=self.title, severity=Severity.PASS,
            summary="fills show price dispersion or explicit fees — costs appear modelled",
            evidence=ev,
        )
