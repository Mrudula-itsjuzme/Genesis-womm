.NOTPARALLEL:

UV ?= uv

.PHONY: sync test lint typecheck layers contracts verify run

sync:
	$(UV) sync

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

typecheck:
	$(UV) run mypy

layers:
	$(UV) run lint-imports

contracts:
	$(UV) run python -m scripts.export_contracts --check

# One gate: no Docker or network needed, because every dependency has a fake.
verify: lint typecheck layers test contracts

run:
	$(UV) run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8001 --reload
