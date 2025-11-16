# =============================================================================
# Makefile for Board of One (bo1)
# Combines local development with Docker-first workflows
# =============================================================================

.PHONY: help
help: ## Show this help message
	@echo "Board of One (bo1) - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Docker Development Commands (Primary Workflow)
# =============================================================================

.PHONY: build
build: ## Build development Docker images
	docker-compose build

.PHONY: up
up: ## Start development environment
	docker-compose up -d

.PHONY: down
down: ## Stop development environment
	docker-compose down

.PHONY: restart
restart: down up ## Restart development environment

.PHONY: logs
logs: ## Show logs from all containers
	docker-compose logs -f

.PHONY: logs-app
logs-app: ## Show logs from bo1 app only
	docker-compose logs -f bo1

.PHONY: shell
shell: ## Open interactive shell in bo1 container
	docker-compose exec bo1 /bin/bash

.PHONY: run
run: ## Run deliberation in container (interactive)
	docker-compose run --rm bo1 python -m bo1.main

.PHONY: demo
demo: ## Run complete Board of One demo (FULL pipeline validation - Weeks 1-3)
	docker-compose run --rm bo1 python bo1/demo.py

.PHONY: demo-interactive
demo-interactive: ## Run demo in interactive mode (prompts for Q&A)
	docker-compose run --rm bo1 python bo1/demo.py --interactive

.PHONY: redis-cli
redis-cli: ## Open Redis CLI
	docker-compose exec redis redis-cli

.PHONY: redis-ui
redis-ui: ## Start Redis Commander (web UI at http://localhost:8081)
	docker-compose --profile debug up -d redis-commander
	@echo "Redis Commander available at: http://localhost:8081"

# =============================================================================
# Testing Commands (In Docker)
# =============================================================================

.PHONY: test
test: test-fast ## Default: Run fast tests (alias for test-fast)

.PHONY: test-fast
test-fast: ## Run tests WITHOUT LLM calls (safe for development, no API costs) - DEFAULT
	docker-compose run --rm bo1 pytest -v -m "not requires_llm"

.PHONY: test-all
test-all: ## Run ALL tests including LLM tests (WARNING: 15+ min, incurs API costs ~$1-2)
	@echo "⚠️  WARNING: Running ALL tests including LLM tests. This will:"
	@echo "   - Take 15-20 minutes"
	@echo "   - Cost ~\$$1-2 in API calls"
	@echo "   - Use test-fast for development (10 seconds, \$$0)"
	@echo ""
	@read -p "Continue? [y/N] " -n 1 -r; echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose run --rm bo1 pytest -v; \
	else \
		echo "Cancelled. Use 'make test-fast' instead."; \
		exit 1; \
	fi

.PHONY: test-llm
test-llm: ## Run ONLY LLM tests (will incur API costs)
	docker-compose run --rm bo1 pytest -v -m "requires_llm"

.PHONY: test-unit
test-unit: ## Run unit tests only
	docker-compose run --rm bo1 pytest -v tests/unit

.PHONY: test-integration
test-integration: ## Run integration tests only
	docker-compose run --rm bo1 pytest -v tests/integration

.PHONY: test-scenario
test-scenario: ## Run scenario tests only
	docker-compose run --rm bo1 pytest -v tests/scenarios

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report (excludes LLM tests)
	docker-compose run --rm bo1 pytest --cov=bo1 --cov-report=html --cov-report=term -m "not requires_llm"

# =============================================================================
# Code Quality Commands (In Docker)
# =============================================================================

.PHONY: lint
lint: ## Run linter (ruff)
	docker-compose run --rm bo1 ruff check .

.PHONY: format
format: ## Format code (ruff)
	docker-compose run --rm bo1 ruff format .

.PHONY: format-check
format-check: ## Check code formatting without changes
	docker-compose run --rm bo1 ruff format --check .

.PHONY: typecheck
typecheck: ## Run type checker (mypy) - matches CI exactly
	docker-compose run --rm bo1 mypy bo1/ --install-types --non-interactive

.PHONY: check
check: lint format-check typecheck ## Run all code quality checks
	@echo "All checks passed!"

.PHONY: pre-commit
pre-commit: ## Run pre-commit checks (lint + format + typecheck) - MATCHES CI EXACTLY
	@echo "🔍 Running pre-commit checks (matching CI)..."
	@echo ""
	@echo "1/3 Linting..."
	@docker-compose run --rm bo1 ruff check .
	@echo "✓ Linting passed"
	@echo ""
	@echo "2/3 Formatting..."
	@docker-compose run --rm bo1 ruff format --check .
	@echo "✓ Formatting passed"
	@echo ""
	@echo "3/3 Type checking (full bo1/ directory)..."
	@docker-compose run --rm bo1 mypy bo1/ --install-types --non-interactive
	@echo "✓ Type checking passed"
	@echo ""
	@echo "✅ All pre-commit checks passed! Safe to commit and push."

.PHONY: fix
fix: ## Auto-fix linting and formatting issues
	@echo "🔧 Auto-fixing code issues..."
	docker-compose run --rm bo1 ruff check --fix .
	docker-compose run --rm bo1 ruff format .
	@echo "✅ Code fixed!"

# =============================================================================
# Production Commands
# =============================================================================

.PHONY: build-prod
build-prod: ## Build production Docker image
	docker-compose -f docker-compose.prod.yml build

.PHONY: up-prod
up-prod: ## Start production environment
	docker-compose -f docker-compose.prod.yml up -d

.PHONY: down-prod
down-prod: ## Stop production environment
	docker-compose -f docker-compose.prod.yml down

.PHONY: logs-prod
logs-prod: ## Show production logs
	docker-compose -f docker-compose.prod.yml logs -f

# =============================================================================
# Data Management Commands
# =============================================================================

.PHONY: backup-redis
backup-redis: ## Backup Redis data
	@mkdir -p backups
	docker-compose exec redis redis-cli SAVE
	docker cp bo1-redis:/data/dump.rdb ./backups/redis-$(shell date +%Y%m%d-%H%M%S).rdb
	@echo "Redis backup saved to ./backups/"

.PHONY: restore-redis
restore-redis: ## Restore Redis data (requires BACKUP_FILE variable)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Error: BACKUP_FILE not specified"; \
		echo "Usage: make restore-redis BACKUP_FILE=./backups/redis-YYYYMMDD-HHMMSS.rdb"; \
		exit 1; \
	fi
	docker-compose down
	docker cp $(BACKUP_FILE) bo1-redis:/data/dump.rdb
	docker-compose up -d

.PHONY: clean-redis
clean-redis: ## Clear Redis data (WARNING: deletes all data)
	docker-compose exec redis redis-cli FLUSHALL
	@echo "Redis data cleared"

.PHONY: clean-exports
clean-exports: ## Remove all exported files
	rm -rf ./exports/*
	@echo "Exports cleared"

# =============================================================================
# Cleanup Commands
# =============================================================================

.PHONY: clean
clean: down ## Stop containers and clean Python cache
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage 2>/dev/null || true
	@echo "Cleanup complete"

.PHONY: clean-all
clean-all: clean ## Remove containers, volumes, and images
	docker-compose down -v --rmi all
	docker-compose -f docker-compose.prod.yml down -v --rmi all

.PHONY: prune
prune: ## Remove unused Docker resources (system-wide)
	docker system prune -f
	docker volume prune -f

# =============================================================================
# Setup Commands
# =============================================================================

.PHONY: setup
setup: ## Initial project setup (Docker-first)
	@echo "Setting up Board of One (Docker-first)..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Created .env file from .env.example"; \
		echo "  → Edit .env and add your API keys"; \
	else \
		echo "✓ .env file already exists"; \
	fi
	@mkdir -p exports backups tests
	@echo "✓ Created directories: exports, backups, tests"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env and add your ANTHROPIC_API_KEY and VOYAGE_API_KEY"
	@echo "2. Run 'make build' to build Docker images"
	@echo "3. Run 'make up' to start the development environment"
	@echo "4. Run 'make run' to start a deliberation"
	@echo ""
	@echo "Optional: Run 'make redis-ui' to start Redis web UI (http://localhost:8081)"

.PHONY: install-dev
install-dev: ## Install development dependencies locally (outside Docker, optional)
	@echo "Installing local development environment (optional)..."
	@command -v uv >/dev/null 2>&1 || { echo "uv not installed. Installing..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	uv venv
	uv sync
	@echo "✓ Development environment ready"
	@echo "  Activate with: source .venv/bin/activate"
	@echo ""
	@echo "Note: You can develop entirely in Docker without this."

.PHONY: setup-dev
setup-dev: ## One-command setup for new developers (<5 min)
	@echo "🚀 Setting up Board of One development environment..."
	@echo ""
	@echo "Step 1/7: Installing uv package manager..."
	@command -v uv >/dev/null 2>&1 || { echo "Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	@echo "✓ uv installed"
	@echo ""
	@echo "Step 2/7: Installing Python dependencies..."
	@uv sync --frozen
	@echo "✓ Dependencies installed"
	@echo ""
	@echo "Step 3/7: Creating .env file..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ .env created from .env.example"; \
		echo "  → IMPORTANT: Edit .env and add your ANTHROPIC_API_KEY"; \
	else \
		echo "✓ .env already exists"; \
	fi
	@echo ""
	@echo "Step 4/7: Installing git hooks (pre-commit + pre-push)..."
	@bash scripts/install-hooks.sh
	@echo "✓ Git hooks installed"
	@echo ""
	@echo "Step 5/7: Starting Docker services..."
	@docker-compose up -d
	@echo "✓ Docker services started"
	@echo ""
	@echo "Step 6/7: Waiting for services to be ready..."
	@sleep 5
	@echo "✓ Services ready"
	@echo ""
	@echo "Step 7/7: Running database migrations..."
	@uv run alembic upgrade head
	@echo "✓ Migrations complete"
	@echo ""
	@echo "Step 8/8: Seeding personas..."
	@uv run python scripts/seed_personas.py
	@echo "✓ Personas seeded"
	@echo ""
	@echo "✅ Setup complete! You're ready to develop."
	@echo ""
	@echo "Quick start:"
	@echo "  • Run deliberation: make run"
	@echo "  • Run tests: make test"
	@echo "  • View Redis: make redis-ui (http://localhost:8081)"
	@echo "  • View docs: cat CLAUDE.md"
	@echo ""
	@echo "⏱️  Total setup time: <5 minutes"

# =============================================================================
# Cloud Deployment Helpers (for future use)
# =============================================================================

.PHONY: docker-tag
docker-tag: ## Tag production image for registry
	@if [ -z "$(REGISTRY)" ] || [ -z "$(TAG)" ]; then \
		echo "Error: REGISTRY and TAG required"; \
		echo "Usage: make docker-tag REGISTRY=your-registry.com TAG=v1.0.0"; \
		exit 1; \
	fi
	docker tag bo1-app-prod $(REGISTRY)/bo1:$(TAG)
	docker tag bo1-app-prod $(REGISTRY)/bo1:latest
	@echo "Tagged images:"
	@echo "  $(REGISTRY)/bo1:$(TAG)"
	@echo "  $(REGISTRY)/bo1:latest"

.PHONY: docker-push
docker-push: ## Push production image to registry
	@if [ -z "$(REGISTRY)" ] || [ -z "$(TAG)" ]; then \
		echo "Error: REGISTRY and TAG required"; \
		echo "Usage: make docker-push REGISTRY=your-registry.com TAG=v1.0.0"; \
		exit 1; \
	fi
	docker push $(REGISTRY)/bo1:$(TAG)
	docker push $(REGISTRY)/bo1:latest
	@echo "Pushed images to $(REGISTRY)"

# =============================================================================
# Information Commands
# =============================================================================

.PHONY: status
status: ## Show container status
	docker-compose ps

.PHONY: stats
stats: ## Show container resource usage
	docker stats bo1-app bo1-redis --no-stream

.PHONY: inspect
inspect: ## Show detailed container configuration
	docker-compose config

.PHONY: version
version: ## Show version information
	@echo "Docker version:"
	@docker --version
	@echo ""
	@echo "Docker Compose version:"
	@docker-compose --version
	@echo ""
	@echo "Python version (in container):"
	@docker-compose run --rm bo1 python --version 2>/dev/null || echo "Container not built yet. Run 'make build' first."
