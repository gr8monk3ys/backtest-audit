"""Input model: a backtest reduced to the few facts every framework can export.

The audit deliberately works on a *trade log*, not on strategy source. Any
backtester — backtrader, vectorbt, zipline, QuantConnect, a hand-rolled loop,
even a spreadsheet — can emit a list of fills. Auditing the artifact rather
than the code is what makes the checks portable, and it is also the honest
scope: the artifact is what the performance claim was computed from.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(text[: len(fmt) + 4], fmt)
            except ValueError:
                continue
    raise ValueError(f"unparseable timestamp: {value!r}")


@dataclass(frozen=True)
class Trade:
    """One fill. `side` is normalised to 'buy' or 'sell'."""

    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: datetime
    pnl: float | None = None
    fees: float | None = None

    @property
    def signed_quantity(self) -> float:
        return self.quantity if self.side == "buy" else -self.quantity

    @property
    def date(self) -> str:
        return self.timestamp.date().isoformat()


@dataclass
class Backtest:
    """A backtest result: the trade log plus whatever context was reported."""

    trades: list[Trade]
    equity_curve: list[float] = field(default_factory=list)
    exposure: dict[str, float] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    benchmarks: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    source: str = "<unknown>"

    @property
    def final_date(self) -> str | None:
        return max((t.date for t in self.trades), default=None)

    @property
    def symbols(self) -> list[str]:
        return sorted({t.symbol for t in self.trades})


_SIDE_ALIASES = {
    "buy": "buy", "b": "buy", "long": "buy", "bought": "buy", "1": "buy", "cover": "buy",
    "sell": "sell", "s": "sell", "short": "sell", "sold": "sell", "-1": "sell",
}


def _norm_side(raw: Any) -> str:
    key = str(raw).strip().lower()
    if key not in _SIDE_ALIASES:
        raise ValueError(f"unrecognised trade side: {raw!r}")
    return _SIDE_ALIASES[key]


def _normalise_key(key: Any) -> str:
    """Fold a column name to a canonical form.

    Exports in the wild use 'Fill Price', 'fill-price', 'avg.price' and
    'fill_price' for the same field; requiring one spelling would mean users
    reshaping their data before the tool would read it.
    """
    text = str(key).strip().lower()
    for ch in (" ", "-", ".", "/"):
        text = text.replace(ch, "_")
    return text.strip("_")


def _trade_from_mapping(row: dict[str, Any]) -> Trade:
    lower = {_normalise_key(k): v for k, v in row.items()}

    def pick(*names: str) -> Any:
        for n in names:
            if n in lower and lower[n] not in (None, ""):
                return lower[n]
        return None

    qty = pick("quantity", "qty", "size", "shares", "amount")
    price = pick("price", "fill_price", "filled_avg_price", "avg_price", "execution_price",
                 "avg_fill_price", "exec_price")
    ts = pick("timestamp", "date", "datetime", "time", "filled_at", "created_at",
              "trade_date", "exit_time", "entry_time")
    missing = [n for n, v in (("quantity", qty), ("price", price), ("timestamp", ts)) if v is None]
    if missing:
        raise ValueError(f"trade row missing required field(s) {missing}: {row!r}")

    pnl = pick("pnl", "profit", "realized_pnl", "p&l")
    fees = pick("fees", "commission", "fee")
    return Trade(
        symbol=str(pick("symbol", "ticker", "asset", "instrument") or "UNKNOWN"),
        side=_norm_side(pick("side", "action", "direction", "type")),
        quantity=abs(float(qty)),
        price=float(price),
        timestamp=_parse_ts(ts),
        pnl=float(pnl) if pnl not in (None, "") else None,
        fees=float(fees) if fees not in (None, "") else None,
    )


def trades_from_rows(rows: Iterable[dict[str, Any]]) -> list[Trade]:
    return [_trade_from_mapping(r) for r in rows]


def load(path: str | Path) -> Backtest:
    """Load a backtest from JSON or CSV, tolerating common key spellings."""
    p = Path(path)
    if p.suffix.lower() == ".csv":
        with p.open(newline="") as fh:
            trades = trades_from_rows(csv.DictReader(fh))
        return Backtest(trades=trades, source=str(p))

    raw = json.loads(p.read_text())
    if isinstance(raw, list):
        return Backtest(trades=trades_from_rows(raw), source=str(p))

    trade_rows = None
    for key in ("trades", "fills", "orders", "transactions"):
        if isinstance(raw.get(key), list):
            trade_rows = raw[key]
            break
    if trade_rows is None:
        raise ValueError(f"{p}: no trade list found (looked for trades/fills/orders/transactions)")

    curve = raw.get("equity_curve") or raw.get("portfolio_value") or []
    if isinstance(curve, dict):
        curve = list(curve.values())

    return Backtest(
        trades=trades_from_rows(trade_rows),
        equity_curve=[float(x) for x in curve if isinstance(x, (int, float))],
        exposure=raw.get("exposure") or {},
        metrics=raw.get("metrics") or {},
        benchmarks=raw.get("benchmarks") or {},
        config=raw.get("config") or {},
        source=str(p),
    )
