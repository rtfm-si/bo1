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

.PHONY: logs-api
logs-api: ## Show logs from API only
	docker-compose logs -f api

.PHONY: logs-frontend
logs-frontend: ## Show logs from frontend only
	docker-compose logs -f frontend

.PHONY: shell
shell: ## Open interactive shell in bo1 container
	docker-compose exec bo1 /bin/bash

.PHONY: shell-frontend
shell-frontend: ## Open interactive shell in frontend container
	docker-compose exec frontend /bin/sh

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
test-unit: ## Run unit tests only (using pytest markers)
	docker-compose run --rm bo1 pytest -v -m "unit and not requires_llm"

.PHONY: test-integration
test-integration: ## Run integration tests only (using pytest markers)
	docker-compose run --rm bo1 pytest -v -m "integration and not requires_llm"

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report (excludes LLM tests)
	docker-compose run --rm bo1 pytest --cov=bo1 --cov-report=html --cov-report=term -m "not requires_llm"

.PHONY: test-chaos
test-chaos: ## Run chaos/fault injection tests (validates recovery paths)
	docker-compose run --rm bo1 pytest tests/chaos -m "chaos" -v --timeout=300

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
	@echo "Backend checks:"
	@echo "1/5 Linting backend..."
	@docker-compose run --rm bo1 ruff check .
	@echo "✓ Backend linting passed"
	@echo ""
	@echo "2/5 Checking backend formatting..."
	@docker-compose run --rm bo1 ruff format --check .
	@echo "✓ Backend formatting passed"
	@echo ""
	@echo "3/5 Type checking backend (full bo1/ directory)..."
	@docker-compose run --rm bo1 mypy bo1/ --install-types --non-interactive
	@echo "✓ Backend type checking passed"
	@echo ""
	@echo "Frontend checks:"
	@echo "4/5 Checking frontend package-lock.json sync..."
	@cd frontend && npm ci --dry-run >/dev/null 2>&1 && echo "✓ package-lock.json in sync" || (echo "❌ package-lock.json out of sync! Run: cd frontend && npm install" && exit 1)
	@echo ""
	@echo "5/5 Type checking frontend..."
	@cd frontend && npm run check
	@echo "✓ Frontend type checking passed"
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

.PHONY: backup-db
backup-db: ## Backup PostgreSQL database
	@mkdir -p backups/postgres
	@echo "Creating PostgreSQL backup..."
	docker-compose exec -T postgres pg_dump -U bo1 -d boardofone | gzip > ./backups/postgres/boardofone-$$(date +%Y%m%d-%H%M%S).sql.gz
	@echo "Backup saved to ./backups/postgres/"
	@ls -lh ./backups/postgres/*.sql.gz | tail -1

.PHONY: restore-db
restore-db: ## Restore PostgreSQL database (requires BACKUP_FILE variable)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Error: BACKUP_FILE not specified"; \
		echo "Usage: make restore-db BACKUP_FILE=./backups/postgres/boardofone-YYYYMMDD-HHMMSS.sql.gz"; \
		exit 1; \
	fi
	@echo "WARNING: This will overwrite the current database!"
	@read -p "Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ] || (echo "Cancelled" && exit 1)
	gunzip -c $(BACKUP_FILE) | docker-compose exec -T postgres psql -U bo1 -d boardofone
	@echo "Database restored from $(BACKUP_FILE)"

.PHONY: verify-backup
verify-backup: ## Verify most recent PostgreSQL backup
	@echo "Verifying most recent backup..."
	@BACKUP_FILE=$$(ls -t ./backups/postgres/*.sql.gz 2>/dev/null | head -1); \
	if [ -z "$$BACKUP_FILE" ]; then \
		echo "No backup files found in ./backups/postgres/"; \
		exit 1; \
	fi; \
	echo "Testing backup: $$BACKUP_FILE"; \
	gunzip -t "$$BACKUP_FILE" && echo "Compression OK" || (echo "Compression FAILED" && exit 1); \
	echo "Backup verification passed"

.PHONY: backup-db-encrypted
backup-db-encrypted: ## Backup PostgreSQL database with encryption (requires BACKUP_AGE_RECIPIENT)
	@if [ -z "$${BACKUP_AGE_RECIPIENT:-}" ]; then \
		echo "Error: BACKUP_AGE_RECIPIENT not set"; \
		echo "Usage: BACKUP_AGE_RECIPIENT=age1... make backup-db-encrypted"; \
		echo "Generate a key with: make generate-backup-key"; \
		exit 1; \
	fi
	@mkdir -p backups/postgres
	@echo "Creating encrypted PostgreSQL backup..."
	POSTGRES_HOST=localhost POSTGRES_PASSWORD=$${POSTGRES_PASSWORD:-postgres} \
		BACKUP_DIR=./backups/postgres BACKUP_AGE_RECIPIENT=$${BACKUP_AGE_RECIPIENT} \
		./scripts/backup_postgres.sh
	@echo "Encrypted backup saved to ./backups/postgres/"
	@ls -lh ./backups/postgres/*.sql.gz.age 2>/dev/null | tail -1 || echo "No encrypted backups found"

.PHONY: generate-backup-key
generate-backup-key: ## Generate age encryption keypair for backups
	@if ! command -v age-keygen &> /dev/null; then \
		echo "Error: age not installed. Install with: brew install age"; \
		exit 1; \
	fi
	@mkdir -p backups/keys
	@echo "Generating age keypair for backup encryption..."
	@age-keygen -o backups/keys/backup.key 2>&1 | tee backups/keys/backup.pub
	@echo ""
	@echo "Key files created:"
	@echo "  Private key: backups/keys/backup.key (KEEP SECURE - store separately from backups)"
	@echo "  Public key:  backups/keys/backup.pub"
	@echo ""
	@echo "To encrypt backups, set:"
	@echo "  export BACKUP_AGE_RECIPIENT=$$(grep 'public key' backups/keys/backup.pub | awk '{print $$NF}')"
	@echo ""
	@echo "To decrypt backups, set:"
	@echo "  export BACKUP_AGE_KEY_FILE=./backups/keys/backup.key"

.PHONY: backup-redis
backup-redis: ## Backup Redis data
	@mkdir -p backups/redis
	REDISCLI_AUTH="$${REDIS_PASSWORD}" docker-compose exec redis redis-cli SAVE
	docker cp $$(docker-compose ps -q redis):/data/dump.rdb ./backups/redis/redis-$$(date +%Y%m%d-%H%M%S).rdb
	@echo "Redis backup saved to ./backups/redis/"

.PHONY: restore-redis
restore-redis: ## Restore Redis data (requires BACKUP_FILE variable)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Error: BACKUP_FILE not specified"; \
		echo "Usage: make restore-redis BACKUP_FILE=./backups/redis/redis-YYYYMMDD-HHMMSS.rdb"; \
		exit 1; \
	fi
	docker-compose stop redis
	docker cp $(BACKUP_FILE) $$(docker-compose ps -q redis):/data/dump.rdb
	docker-compose start redis

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
# Production Deployment Commands
# =============================================================================

.PHONY: prod-build
prod-build: ## Build production images
	docker-compose -f docker-compose.prod.yml build

.PHONY: prod-up
prod-up: ## Start production environment
	docker-compose -f docker-compose.prod.yml up -d

.PHONY: prod-down
prod-down: ## Stop production environment
	docker-compose -f docker-compose.prod.yml down

.PHONY: prod-logs
prod-logs: ## Show production logs
	docker-compose -f docker-compose.prod.yml logs -f

.PHONY: prod-status
prod-status: ## Show production service status
	docker-compose -f docker-compose.prod.yml ps

.PHONY: prod-restart
prod-restart: prod-down prod-up ## Restart production environment

.PHONY: deploy
deploy: ## Full production deployment (automated script)
	@bash scripts/deploy-production.sh

.PHONY: generate-ssl
generate-ssl: ## Generate self-signed SSL certificate (dev/testing only)
	@bash scripts/generate-ssl-cert.sh

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
# Load Testing Commands
# =============================================================================

.PHONY: load-test-normal
load-test-normal: ## Run normal load test (10 users, 5 min)
	@echo "Starting normal load test..."
	@echo "Make sure the API is running (make up)"
	@mkdir -p reports
	docker-compose run --rm bo1 locust -f tests/load/scenarios/normal.py --headless -u 10 -r 1 -t 5m --html reports/load-test-normal.html

.PHONY: load-test-peak
load-test-peak: ## Run peak load test (50 users, 2 min)
	@echo "Starting peak load test..."
	@echo "Make sure the API is running (make up)"
	@mkdir -p reports
	docker-compose run --rm bo1 locust -f tests/load/scenarios/peak.py --headless -u 50 -r 10 -t 2m --html reports/load-test-peak.html

.PHONY: load-test-sustained
load-test-sustained: ## Run sustained load test (25 users, 30 min)
	@echo "Starting sustained load test..."
	@echo "Make sure the API is running (make up)"
	@mkdir -p reports
	docker-compose run --rm bo1 locust -f tests/load/scenarios/sustained.py --headless -u 25 -r 2 -t 30m --html reports/load-test-sustained.html

.PHONY: load-test-ui
load-test-ui: ## Start Locust web UI for interactive testing (http://localhost:8089)
	@echo "Starting Locust web UI at http://localhost:8089"
	@echo "Make sure the API is running (make up)"
	docker-compose run --rm -p 8089:8089 bo1 locust -f tests/load/locustfile.py --web-host 0.0.0.0

.PHONY: load-test-report
load-test-report: ## Open latest load test report
	@if [ -f reports/load-test-normal.html ]; then \
		open reports/load-test-normal.html 2>/dev/null || xdg-open reports/load-test-normal.html 2>/dev/null || echo "Report at: reports/load-test-normal.html"; \
	else \
		echo "No load test reports found. Run a load test first."; \
	fi

# =============================================================================
# E2E Testing Commands (Playwright)
# =============================================================================

.PHONY: e2e-install
e2e-install: ## Install Playwright browsers
	cd frontend && npx playwright install --with-deps chromium firefox

.PHONY: e2e-test
e2e-test: ## Run Playwright E2E tests (requires services running)
	@echo "Running E2E tests..."
	@echo "Make sure docker-compose services are running (make up)"
	cd frontend && npm run test:e2e

.PHONY: e2e-test-ui
e2e-test-ui: ## Run Playwright tests with interactive UI
	cd frontend && npm run test:e2e:ui

.PHONY: e2e-test-headed
e2e-test-headed: ## Run E2E tests in headed mode (visible browser)
	cd frontend && npx playwright test --headed

.PHONY: e2e-test-debug
e2e-test-debug: ## Run E2E tests in debug mode
	cd frontend && npx playwright test --debug

.PHONY: e2e-report
e2e-report: ## Open Playwright HTML report
	cd frontend && npx playwright show-report

# =============================================================================
# Security Audit Commands
# =============================================================================

.PHONY: audit-python
audit-python: ## Scan Python dependencies for vulnerabilities
	@echo "🔍 Scanning Python dependencies for vulnerabilities..."
	@mkdir -p audits/reports
	docker-compose run --rm bo1 pip-audit --format markdown > audits/reports/python-deps.report.md 2>&1 || true
	docker-compose run --rm bo1 pip-audit
	@echo "✓ Python audit complete. Report: audits/reports/python-deps.report.md"

.PHONY: audit-npm
audit-npm: ## Scan npm dependencies for vulnerabilities
	@echo "🔍 Scanning npm dependencies for vulnerabilities..."
	@mkdir -p audits/reports
	cd frontend && npm audit --json > ../audits/reports/npm-deps.report.json 2>&1 || true
	cd frontend && npm audit
	@echo "✓ npm audit complete. Report: audits/reports/npm-deps.report.json"

.PHONY: audit-deps
audit-deps: audit-python audit-npm ## Scan all dependencies for vulnerabilities
	@echo "✅ All dependency audits complete!"

.PHONY: osv-scan
osv-scan: ## Run OSV scanner for malware/typosquatting detection
	@echo "🔍 Running OSV scanner (malware + vulnerability detection)..."
	@command -v osv-scanner >/dev/null 2>&1 || { echo "❌ osv-scanner not installed. Install with: brew install osv-scanner"; exit 1; }
	osv-scanner --lockfile=uv.lock --lockfile=frontend/package-lock.json --config=.osv-scanner.toml
	@echo "✓ OSV scan complete"

.PHONY: audit-schema
audit-schema: ## Audit Pydantic models against PostgreSQL schema (detects migration gaps)
	@echo "🔍 Auditing Pydantic models vs database schema..."
	@mkdir -p audits/reports
	docker-compose run --rm bo1 python scripts/audit_model_schema.py --output audits/reports/schema-audit.report.md
	@echo "✓ Schema audit complete. Report: audits/reports/schema-audit.report.md"

.PHONY: audit-schema-ci
audit-schema-ci: ## Schema audit for CI (exits 1 on issues)
	docker-compose run --rm bo1 python scripts/audit_model_schema.py --ci

# =============================================================================
# Email Deliverability Testing
# =============================================================================

.PHONY: test-email-deliverability
test-email-deliverability: ## Send all test emails to RECIPIENT (requires RECIPIENT=email@example.com)
	@if [ -z "$(RECIPIENT)" ]; then \
		echo "Error: RECIPIENT not specified"; \
		echo "Usage: make test-email-deliverability RECIPIENT=test@gmail.com"; \
		exit 1; \
	fi
	docker-compose run --rm bo1 python -m backend.scripts.test_email_deliverability --recipient $(RECIPIENT)

.PHONY: test-email-template
test-email-template: ## Send specific test email (requires RECIPIENT and TEMPLATE)
	@if [ -z "$(RECIPIENT)" ]; then \
		echo "Error: RECIPIENT not specified"; \
		echo "Usage: make test-email-template RECIPIENT=test@gmail.com TEMPLATE=welcome"; \
		exit 1; \
	fi
	@if [ -z "$(TEMPLATE)" ]; then \
		echo "Error: TEMPLATE not specified"; \
		echo "Available templates: welcome, meeting_completed, action_reminder, action_reminder_overdue, weekly_digest, workspace_invitation"; \
		exit 1; \
	fi
	docker-compose run --rm bo1 python -m backend.scripts.test_email_deliverability --recipient $(RECIPIENT) --template $(TEMPLATE)

.PHONY: list-email-templates
list-email-templates: ## List available email templates for testing
	docker-compose run --rm bo1 python -m backend.scripts.test_email_deliverability --list-templates

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

# =============================================================================
# OpenAPI / Type Generation Commands
# =============================================================================

.PHONY: openapi-export
openapi-export: ## Export OpenAPI spec to openapi.json (for frontend type generation)
	@docker-compose run --rm bo1 python scripts/export_openapi.py --stdout 2>/dev/null > openapi.json
	@echo "✓ OpenAPI spec exported to openapi.json"

.PHONY: generate-types
generate-types: openapi-export ## Generate TypeScript types from OpenAPI spec
	@echo "Generating TypeScript types..."
	@cd frontend && npm run generate:types
	@echo "✓ Types generated at frontend/src/lib/api/generated-types.ts"

.PHONY: check-types-fresh
check-types-fresh: ## Check if generated types are up-to-date with OpenAPI spec
	@cd frontend && npm run check:types-fresh

.PHONY: openapi-public
openapi-public: openapi-export ## Generate filtered public OpenAPI spec (excludes admin endpoints)
	@docker-compose run --rm bo1 python scripts/filter_openapi_spec.py openapi.json openapi-public.json
	@echo "✓ Public OpenAPI spec generated at openapi-public.json"

# =============================================================================
# Datetime Linting Commands
# =============================================================================

.PHONY: lint-datetime
lint-datetime: ## Lint for raw .isoformat() calls in API response code
	@docker-compose run --rm bo1 python scripts/lint_datetime.py --base /app
