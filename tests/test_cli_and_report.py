"""Exit codes are the contract CI depends on; the HTML is what gets shared."""

import json
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
    html = out.read_text()
    assert html.startswith("<!doctype html>")
    assert "NOT TRUSTWORTHY" in html
    # No external requests: the report must render offline.
    assert "http://" not in html and "https://" not in html


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
