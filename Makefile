.PHONY: check lint test dogfood

check: lint test dogfood

lint:
	ruff check .

test:
	pytest -q

# The tool must reject the known-bad artifact (exit 1) and accept the fixed one, as CI does.
dogfood:
	@btaudit tests/fixtures/etf_prefix_2020-2024.json --no-color >/dev/null; \
	  test $$? -eq 1 || { echo "known-bad artifact was not rejected"; exit 1; }
	btaudit tests/fixtures/etf_current_2020-2024.json --no-color >/dev/null
