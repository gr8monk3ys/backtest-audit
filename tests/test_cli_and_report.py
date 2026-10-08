"""Exit codes are the contract CI depends on; the HTML is what gets shared."""

import io
import json
import sys
from pathlib import Path

from backtest_audit.audit import audit_file
from backtest_audit.cli import main
from backtest_audit.report import render_html, render_text

FIXTURES = Path(__file__).parent / "fixtures"
BAD = FIXTURES / "etf_prefix_2020-2024.json"
OK = FIXTURES / "etf_current_2020-2024.json"


def test_blocking_findings_exit_nonzero(capsys):
    assert main([str(BAD), "--no-color"]) == 1
    assert "NOT TRUSTWORTHY" in capsys.readouterr().out


def test_clean_enough_result_exits_zero(capsys):
    assert main([str(OK), "--no-color"]) == 0
    assert "TRUSTWORTHY WITH CAVEATS" in capsys.readouterr().out


def test_strict_mode_fails_on_warnings(capsys):
    # Same artifact that exits 0 normally must exit 1 under --strict.
    assert main([str(OK), "--no-color"]) == 0
    capsys.readouterr()
    assert main([str(OK), "--no-color", "--strict"]) == 1


def test_missing_file_exits_two_without_traceback(capsys):
    assert main(["does-not-exist.json"]) == 2
    assert "cannot audit" in capsys.readouterr().err


def test_json_output_is_machine_readable(capsys):
    main([str(BAD), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["trustworthy"] is False
    ids = {f["id"] for f in payload["findings"] if f["severity"] == "blocking"}
    assert {"position-integrity", "short-liability"} <= ids


def test_html_report_is_written_and_self_contained(tmp_path, capsys):
    out = tmp_path / "report.html"
    main([str(BAD), "--no-color", "--html", str(out)])
    html = out.read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert "NOT TRUSTWORTHY" in html
    # No external requests: the report must render offline.
    assert "http://" not in html and "https://" not in html


def test_text_report_survives_a_cp1252_console(monkeypatch):
    # Windows consoles and pipes often default to cp1252, which cannot
    # encode the ✓/✗ marks. The run must still complete and stay legible.
    buf = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(buf, encoding="cp1252"))
    code = main([str(BAD), "--no-color"])
    sys.stdout.flush()
    out = buf.getvalue().decode("cp1252")
    assert code == 1
    assert "NOT TRUSTWORTHY" in out
    assert "x Position awareness" in out and "->" in out


def test_scalar_json_top_level_exits_two_without_traceback(tmp_path, capsys):
    p = tmp_path / "scalar.json"
    p.write_text("42", encoding="utf-8")
    assert main([str(p)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("btaudit:") and "Traceback" not in err


def test_mixed_timezone_timestamps_exit_two_without_traceback(tmp_path, capsys):
    # A tz-aware fill next to a naive one makes the ordering check raise
    # TypeError; that is a crash, not a blocking finding, so it must not exit 1.
    p = tmp_path / "mixed_tz.json"
    p.write_text(json.dumps([
        {"symbol": "SPY", "side": "buy", "quantity": 1, "price": 100.0,
         "timestamp": "2024-01-02T10:00:00Z"},
        {"symbol": "SPY", "side": "sell", "quantity": 1, "price": 101.0,
         "timestamp": "2024-01-03 10:00:00"},
    ]), encoding="utf-8")
    assert main([str(p)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("btaudit:") and "Traceback" not in err


def test_html_escapes_untrusted_symbol_text(tmp_path):
    from datetime import datetime

    from backtest_audit.audit import audit
    from backtest_audit.models import Backtest, Trade

    evil = '<script>alert(1)</script>'
    bt = Backtest(trades=[Trade(evil, "sell", 5, 10.0, datetime(2024, 1, 2))], source="x")
    html = render_html(audit(bt))
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_text_report_has_no_ansi_when_color_disabled():
    text = render_text(audit_file(BAD), color=False)
    assert "\033[" not in text
