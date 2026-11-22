---
status: accepted
date: 2026-11-22
---

# Audit the trade log, not the strategy source

`backtest-audit` reads a **Trade log** (JSON or CSV of fills, with an optional equity curve and context) instead of hooking into a backtesting framework or reading strategy code.

Why: every backtester, from backtrader and vectorbt to a spreadsheet, can emit fills, so the checks stay portable. The artifact is also what the performance claim was computed from, so it is the honest scope of the audit.

## Consequences

- The package has no runtime dependencies (`dependencies = []`) and no framework adapters; users export a log instead.
- Input is tolerant of key and column spellings (`models._normalise_key`) so users do not reshape their data first.
- A **Check** that needs a field the artifact lacks returns **Skipped**, not **Pass**, so missing information is never read as a clean result.
- Defects that exist only in strategy source (look-ahead in indicator code, for example) are out of scope.
