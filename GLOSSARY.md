# backtest-audit

Audits a backtest's trade log for the defects that silently inflate its headline result. It judges the artifact a backtest produced, never the strategy code that produced it.

## Language

### Input

**Backtest**:
A backtest result reduced to what every framework can export: a list of **Trades** plus optional equity curve, exposure, metrics, benchmarks and config.
_Avoid_: run, strategy, result file

**Trade**:
One fill: symbol, side, quantity, price, timestamp, and optional pnl and fees. Side is normalised to `buy` or `sell`; quantity is always positive.
_Avoid_: order, execution, transaction (these are only accepted as input key spellings)

**Trade log**:
The artifact the audit reads (JSON or CSV): the **Trades** a backtester emitted. Column and key spellings are folded to one canonical form on load.
_Avoid_: export, fills file

### Judging

**Check**:
One test of a single defect, with a stable `id` and `title`, run against a **Backtest** and returning exactly one **Finding**. All checks live in `ALL_CHECKS`; their order is the report order.
_Avoid_: rule, validator, test

**Finding**:
The result of one **Check**: severity, summary, detail, remedy and evidence.
_Avoid_: issue, error, result

**Severity**:
How much a **Finding** should change belief in the result: **Blocking**, **Warning**, **Pass**, or **Skipped**.
_Avoid_: level, status

**Blocking**:
The headline number does not measure what it claims to. Not a style opinion; it makes the CLI exit `1`.

**Warning**:
The number may be real but is not comparable or not yet significant. Fails the run only under `--strict`.

**Skipped**:
The artifact did not carry enough information to judge. Reported, never hidden, because a silent skip reads as a pass.
_Avoid_: N/A, ignored

**Audit**:
The set of **Findings** for one **Backtest**, plus its **Verdict**.
_Avoid_: report (the report is a rendering of an **Audit**)

**Verdict**:
The one-line outcome of an **Audit**: `NOT TRUSTWORTHY`, `TRUSTWORTHY WITH CAVEATS`, `TRUSTWORTHY (some checks unjudged)`, `TRUSTWORTHY`, or `NOT JUDGED`. An **Audit** in which every **Check** was **Skipped** (an empty trade log) is not judged and is not a pass.
_Avoid_: score, grade

### Position

**Book**:
The signed position per symbol, rebuilt by replaying **Trades** in order. Several **Checks** read it to see what the run held when each fill landed.
_Avoid_: portfolio, holdings

**Event**:
One **Trade** paired with the position before and after it, produced by replaying the **Book**.
_Avoid_: step, tick

**Flat**:
A position whose absolute size is below the float tolerance (1e-9), so fractional quantities that sum to zero in decimal count as closed.
