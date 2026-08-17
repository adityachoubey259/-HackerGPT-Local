.PHONY: install dev test lint format typecheck check migrate

install:
	python -m pip install -e ".[dev]"

dev:
	python -m uvicorn backend.api.app:app --factory --reload --host 127.0.0.1 --port 8000

test:
	python -m pytest

lint:
	python -m ruff check .

format:
	python -m ruff format .

typecheck:
	python -m mypy backend tests

check: lint typecheck test

migrate:
	python -m alembic upgrade head
