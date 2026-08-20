"""Signed-position reconstruction shared by several checks.

Replaying fills into positions is how most of these defects become visible:
a trade log alone looks fine until you ask what the book looked like when
each fill landed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backtest_audit.models import Backtest, Trade


@dataclass
class Event:
    trade: Trade
    before: float
    after: float

    @property
    def opens(self) -> bool:
        return self.before == 0 and self.after != 0

    @property
    def closes(self) -> bool:
        return self.before != 0 and (
            self.after == 0 or (self.before > 0) != (self.after > 0)
        )

    @property
    def adds(self) -> bool:
        """Increases an existing position in the same direction."""
        return (
            self.before != 0
            and abs(self.after) > abs(self.before)
            and (self.before > 0) == (self.after > 0)
        )


def replay(bt: Backtest) -> list[Event]:
    book: dict[str, float] = {}
    events: list[Event] = []
    for tr in sorted(bt.trades, key=lambda x: x.timestamp):
        before = book.get(tr.symbol, 0.0)
        after = before + tr.signed_quantity
        events.append(Event(trade=tr, before=before, after=after))
        book[tr.symbol] = after
    return events


def final_book(bt: Backtest) -> dict[str, float]:
    book: dict[str, float] = {}
    for tr in bt.trades:
        book[tr.symbol] = book.get(tr.symbol, 0.0) + tr.signed_quantity
    return {k: v for k, v in book.items() if abs(v) > 1e-9}
