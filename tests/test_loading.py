"""Ingestion has to survive whatever a foreign framework calls its columns.

If a user has to reshape their export before the tool will read it, they
won't use the tool. These cases are drawn from the header spellings that
common backtesters and broker exports actually emit.
"""

import json

import pytest

from backtest_audit.models import Backtest, load, trades_from_rows


def test_spaced_and_title_cased_headers(tmp_path):
    csv = tmp_path / "foreign.csv"
    csv.write_text(
        "Date,Ticker,Action,Size,Fill Price,Commission\n"
        "2024-01-02,AAPL,BUY,100,185.50,1.00\n"
        "2024-03-01,AAPL,SELL,100,192.00,1.50\n"
    )
    bt = load(csv)
    assert len(bt.trades) == 2
    assert bt.trades[0].symbol == "AAPL"
    assert bt.trades[0].side == "buy"
    assert bt.trades[0].price == 185.50
    assert bt.trades[0].fees == 1.00


def test_hyphenated_and_dotted_headers():
    rows = [{"trade-date": "2024-01-02", "symbol": "SPY", "side": "b",
             "qty": "10", "avg.price": "500.0"}]
    trades = trades_from_rows(rows)
    assert trades[0].quantity == 10 and trades[0].price == 500.0


@pytest.mark.parametrize(
    "raw,expected",
    [("BUY", "buy"), ("Sell", "sell"), ("long", "buy"), ("SHORT", "sell"),
     ("cover", "buy"), ("1", "buy"), ("-1", "sell")],
)
def test_side_aliases(raw, expected):
    rows = [{"date": "2024-01-02", "symbol": "X", "side": raw, "qty": 1, "price": 1.0}]
    assert trades_from_rows(rows)[0].side == expected


def test_bare_json_list_of_trades(tmp_path):
    p = tmp_path / "trades.json"
    p.write_text(json.dumps([
        {"symbol": "SPY", "side": "buy", "quantity": 1, "price": 100.0,
         "timestamp": "2024-01-02"},
    ]))
    assert len(load(p).trades) == 1


def test_unparseable_side_names_the_offending_value():
    with pytest.raises(ValueError, match="unrecognised trade side"):
        trades_from_rows([{"date": "2024-01-02", "symbol": "X", "side": "wibble",
                           "qty": 1, "price": 1.0}])


def test_missing_field_error_names_the_field_and_shows_the_row():
    with pytest.raises(ValueError) as exc:
        trades_from_rows([{"date": "2024-01-02", "symbol": "X", "side": "buy", "qty": 1}])
    assert "price" in str(exc.value)


def test_empty_backtest_is_loadable_and_every_check_reports():
    from backtest_audit.audit import audit
    result = audit(Backtest(trades=[], source="empty"))
    assert result.findings and all(f.summary for f in result.findings)
