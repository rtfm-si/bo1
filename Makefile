.PHONY: help install install-dev test test-unit test-integration lint format typecheck check clean docker-up docker-down docker-logs run

help:
	@echo "Board of One - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install dependencies"
	@echo "  make install-dev    Install dependencies including dev tools"
	@echo ""
	@echo "Development:"
	@echo "  make run            Run the application locally"
	@echo "  make test           Run all tests"
	@echo "  make test-unit      Run unit tests only"
	@echo "  make test-integration  Run integration tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           Run linter (ruff)"
	@echo "  make format         Format code (ruff)"
	@echo "  make typecheck      Run type checker (mypy)"
	@echo "  make check          Run all quality checks"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up      Start Docker services"
	@echo "  make docker-down    Stop Docker services"
	@echo "  make docker-logs    View Docker logs"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          Remove generated files"

install:
	uv sync --no-dev

install-dev:
	uv sync

run:
	uv run python -m bo1.main

test:
	uv run pytest

test-unit:
	uv run pytest -m unit

test-integration:
	uv run pytest -m integration

test-scenario:
	uv run pytest -m scenario

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy bo1/

check: lint typecheck
	@echo "All checks passed!"

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f bo1

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage 2>/dev/null || true
	@echo "Cleanup complete"
