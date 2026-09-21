PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin
COV_FAIL_UNDER ?= 90

.PHONY: venv install lint typecheck test test-fast property scenario contract agent e2e soak coverage check clean site

venv:
	uv venv $(VENV) --python $(PYTHON) --seed --quiet || $(PYTHON) -m venv $(VENV)

install: venv
	uv pip install --python $(BIN)/python -e ".[dev]" --quiet || $(BIN)/pip install -e ".[dev]"

lint:
	$(BIN)/ruff check certarig tests

typecheck:
	$(BIN)/mypy certarig

test-fast:
	$(BIN)/pytest tests/unit tests/contract tests/agent -q

property:
	$(BIN)/pytest tests/property -q

scenario:
	$(BIN)/pytest tests/scenario -q

soak:
	$(BIN)/pytest tests/scenario -q -m slow

test:
	$(BIN)/pytest tests -q -m "not hil and not live_llm"

coverage:
	$(BIN)/pytest tests -q -m "not hil and not live_llm and not slow" \
		--cov=certarig --cov-report=term-missing --cov-report=xml \
		--cov-fail-under=$(COV_FAIL_UNDER)

e2e:
	cd studio && npx playwright test

check: lint typecheck coverage

site:
	cd site && npm ci && npm run build

clean:
	rm -rf .venv .mypy_cache .ruff_cache coverage.xml htmlcov dist build *.egg-info site/dist
