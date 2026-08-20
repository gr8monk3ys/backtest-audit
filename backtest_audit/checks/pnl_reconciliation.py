"""Does the equity curve agree with the trades that supposedly produced it?"""

from __future__ import annotations

from backtest_audit.checks.base import Finding, Severity, skipped


class PnLReconciliationCheck:
    id = "pnl-reconciliation"
    title = "P&L reconciliation"

    def run(self, bt):
        if len(bt.equity_curve) < 2:
            return skipped(
                self.id, self.title,
                "the artifact carries no equity curve to reconcile against the trade log",
            )
        realised = [t.pnl for t in bt.trades if t.pnl is not None]
        if not realised:
            return skipped(self.id, self.title, "no per-trade P&L is reported")

        total = sum(realised)
        change = bt.equity_curve[-1] - bt.equity_curve[0]
        ev = {
            "curve_change": round(change, 2),
            "realised_pnl": round(total, 2),
            "unexplained": round(change - total, 2),
        }

        # A curve that climbs far more than the trade log realises is the
        # signature of a headline resting on open positions.
        scale = max(abs(change), abs(total), 1.0)
        if abs(change - total) / scale > 0.25:
            return Finding(
                check_id=self.id, title=self.title, severity=Severity.WARNING,
                summary=(
                    f"equity moved {change:,.0f} while the trade log realises "
                    f"{total:,.0f} — {change - total:,.0f} is unexplained"
                ),
                detail=(
                    "When the curve and the closed trades disagree by this much, the "
                    "headline is largely unrealised mark-to-market on positions that "
                    "were never closed, or the two are computed on different bases. "
                    "Either way the reported return is not the money the strategy took."
                ),
                remedy=(
                    "Liquidate open positions at the end of the run so the headline is "
                    "realised, and confirm both figures are net of the same costs."
                ),
                evidence=ev,
            )

        return Finding(
            check_id=self.id, title=self.title, severity=Severity.PASS,
            summary="equity curve agrees with realised trade P&L",
            evidence=ev,
        )
