# backtest-audit

## Agent skills

### Issue tracker

GitHub Issues on `gr8monk3ys/backtest-audit`, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical roles, label string equal to role name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Checks

`make check` runs ruff, pytest and the dogfood run (the known-bad fixture must exit 1, the fixed one 0). Needs `pip install -e ".[dev]"`. The pre-commit hook (`pre-commit install`) runs ruff on staged files.
