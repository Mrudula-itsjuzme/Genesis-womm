.NOTPARALLEL:

UV ?= uv

.PHONY: sync test integration lint typecheck layers contracts verify verify-fast run demo-seed

sync:
	$(UV) sync

test:
	$(UV) run pytest -m "not integration"

integration:
	$(UV) run pytest -m integration

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

typecheck:
	$(UV) run mypy

layers:
	$(UV) run lint-imports

contracts:
	$(UV) run python -m scripts.export_contracts --check

# Fast gate: no Docker needed.
verify-fast: lint typecheck layers test contracts

# Full gate: also runs the PostgreSQL integration tests (needs Docker).
verify: verify-fast integration

run:
	$(UV) run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload

demo-seed:
	$(UV) run python -m scripts.seed_demo
