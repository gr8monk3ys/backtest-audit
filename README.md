# backtest-audit

**Your backtest is probably lying to you. This finds out how.**

Most backtesting tools help you *build* a backtest. None of them tell you when
the number it produced doesn't mean what you think it means. `backtest-audit`
reads a trade log — from any framework — and checks it for the specific
defects that silently inflate results.

```console
$ btaudit results.json

  ✗ Position awareness         18 of 38 fills (47%) added to a position the run
                               already held, across only 4 genuine entries
  ✓ Exit reachability          5 of 7 exits were strategy decisions
  ✗ Short accounting           3 short position(s) are never covered: EFA, IWM, SPY
  ? Exposure comparability     not enough information to judge — the artifact
                               reports no average gross exposure
  ✓ Cost realism               fills show price dispersion — costs appear modelled
  ! Statistical significance   7 round trips is below the 50-trade bar

  VERDICT: NOT TRUSTWORTHY  (2 blocking, 1 warning, 1 unjudged)
```

Exit code is `1` when anything blocking is found, so it drops straight into CI.

## Install

```bash
pip install backtest-audit
```

## Use

```bash
btaudit results.json                 # JSON from your backtester
btaudit trades.csv                   # or a plain CSV trade log
btaudit results.json --html out.html # shareable offline report
btaudit results.json --json          # machine-readable, for CI
btaudit results.json --strict        # warnings fail too
```

### In CI

```yaml
- uses: gr8monk3ys/backtest-audit@v1
  with:
    path: results/backtest.json
    strict: true          # optional: warnings fail too
    html: audit.html      # optional: report to upload as an artifact
```

The run summary gets the full report, and the build fails on anything
blocking.

```python
from backtest_audit import audit_file

result = audit_file("results.json")
if not result.trustworthy:
    for f in result.blocking:
        print(f.title, "—", f.summary)
```

## Input

Anything with a trade log. JSON (`{"trades": [...]}` or a bare list) or CSV.
Column names are matched loosely, so `Fill Price`, `fill_price` and `avg.price`
all work, as do `BUY`/`long`/`1` for sides. The minimum is symbol, side,
quantity, price, and a timestamp.

Optional fields unlock extra checks: `exposure.avg_gross_exposure` enables the
exposure comparison, `fees` sharpens the cost check.

## What it checks, and why each one matters

| Check | Catches |
|---|---|
| **Trade log sanity** | Fills at a price or quantity of zero or less, exact duplicate fills that double count a position, and out-of-order timestamps. |
| **Position awareness** | Fills that add to a position the run already held. Usually means the strategy can't see its own book — a position lookup returning nothing — so size and exposure are accidental. |
| **Exit reachability** | Exits that only ever happen on the final bar. If the harness liquidated everything at the end, the run measured buy-and-hold, and any trailing stop or exit rule was never executed. |
| **Short accounting** | Shorts opened and never covered. If the engine credits sale proceeds without booking the borrow as a liability, that cash is invented — enough to turn a losing strategy into a spectacular one. |
| **Exposure comparability** | A book that's only partly deployed compared against a fully invested benchmark. Shallow drawdown is usually idle cash, not risk control. |
| **Cost realism** | Round trips filling at an identical price with no fees. Frictions are what kill most high-turnover edges. |
| **P&L reconciliation** | An equity curve that climbs far more than the closed trades realise — the headline resting on positions that were never closed. |
| **Statistical significance** | Sharpe and win rate quoted on too few round trips to mean anything. |

A check that can't be judged is reported as **unjudged**, never as a pass — a
silent skip reads as approval.

## Why trust these checks

They were derived from real failures, not imagined ones. Every one of them
was found the hard way in a live strategy repo, where each defect had been
quietly flattering the results for months:

- A position lookup that always returned `None` (an operator-precedence bug),
  so the strategy re-entered names it already held and could never exit them.
- Naked short sells that booked no liability, inventing about $83k of cash.
- Sizing off *remaining cash*, which left the book ~25% deployed while being
  compared to a 100%-invested benchmark — making a mediocre drawdown look
  like exceptional risk control.
- Exit logic that lived in a method the engine never called, so a five-year
  "strategy" backtest was really buy-and-hold with extra steps.

Correcting those four turned a headline of *+53% and a −7% max drawdown* into
*+16% against a benchmark's +95%*. The strategy hadn't changed. Only the
honesty of the measurement had.

`backtest-audit` finds two of those four automatically from the trade log
alone, and flags a third as unjudged when the artifact doesn't report enough
to check it. The regression suite runs against the genuine before/after
artifacts from that repo, so the checks are pinned to labelled ground truth
rather than to fixtures that merely agree with the implementation.

## What it does not do

It audits the artifact, not your source code. It can't see look-ahead bias in
your feature construction, survivorship bias in your universe, or parameters
you fit on the test set. It tells you when the trade log is internally
inconsistent with the story being told about it — which is where a
surprising share of "profitable" strategies fall over.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
