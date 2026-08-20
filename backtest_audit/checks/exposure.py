"""Is the strategy's capital deployment comparable to the benchmark's?"""

from __future__ import annotations

from backtest_audit.checks.base import Finding, Severity, skipped


class ExposureMatchCheck:
    id = "exposure-match"
    title = "Exposure comparability"

    def run(self, bt):
        avg = bt.exposure.get("avg_gross_exposure")
        if avg is None:
            return skipped(
                self.id, self.title,
                "the artifact reports no average gross exposure, so it cannot be "
                "compared like-for-like with a fully invested benchmark",
            )

        avg = float(avg)
        ev = {
            "avg_gross_exposure": round(avg, 3),
            "peak_gross_exposure": bt.exposure.get("peak_gross_exposure"),
            "benchmarks": sorted(bt.benchmarks.keys()),
        }

        if avg < 0.7:
            return Finding(
                check_id=self.id, title=self.title, severity=Severity.WARNING,
                summary=(
                    f"average gross exposure is {avg:.0%} — returns and drawdown are not "
                    "comparable to a 100%-invested benchmark"
                ),
                detail=(
                    "A book that is only partly deployed earns less and draws down less "
                    "than one that is fully invested, for reasons that have nothing to "
                    "do with signal quality. Comparing it to buy-and-hold flatters the "
                    "drawdown and understates the return; a shallow max drawdown here is "
                    "usually idle cash rather than risk control."
                ),
                remedy=(
                    "Re-run at matched exposure, or scale the comparison — report return "
                    "per unit of exposure alongside the raw number."
                ),
                evidence=ev,
            )

        return Finding(
            check_id=self.id, title=self.title, severity=Severity.PASS,
            summary=f"average gross exposure {avg:.0%} — comparable to a fully invested benchmark",
            evidence=ev,
        )
