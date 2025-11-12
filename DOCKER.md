# Docker Development Guide for Board of One

This guide explains how to develop and deploy Board of One entirely within Docker containers for maximum portability and cloud readiness.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────────────┐      ┌────────────────────┐     │
│  │   bo1-app          │      │   redis             │     │
│  │   (Python 3.12)    │◄────►│   (7-alpine)        │     │
│  │                    │      │                     │     │
│  │ - Claude API       │      │ - Session state     │     │
│  │ - Voyage AI        │      │ - LLM caching       │     │
│  │ - Rich console     │      │ - Prompt cache      │     │
│  └────────────────────┘      └────────────────────┘     │
│           │                                               │
│           │ (volume mount)                                │
│           ▼                                               │
│  ┌────────────────────┐                                  │
│  │   ./exports/       │                                  │
│  │   (host machine)   │                                  │
│  └────────────────────┘                                  │
└─────────────────────────────────────────────────────────┘
```

---

## Multi-Stage Dockerfile Strategy

The `Dockerfile` uses multi-stage builds for different environments:

### 1. **base** - Foundation
- Python 3.12-slim
- System dependencies (curl, git)
- uv package manager

### 2. **dependencies** - Cached Dependencies Layer
- Virtual environment
- Core dependencies installed
- **This layer is cached** - only rebuilds when `pyproject.toml` changes

### 3. **development** - Dev Environment (default)
- Dev dependencies (pytest, ruff, mypy)
- Source code mounted as volume (hot reload)
- Interactive shell by default
- Used by `docker-compose.yml`

### 4. **production** - Production Environment
- Minimal dependencies only
- Non-root user for security
- Optimized for size
- Used by `docker-compose.prod.yml`

### 5. **testing** - CI/CD Environment
- Test dependencies
- Runs pytest automatically
- Used for automated testing

---

## Development Workflow (Docker-First)

### Quick Start

```bash
# 1. Setup (one-time)
make setup

# 2. Edit .env and add your API keys
nano .env

# 3. Build Docker images
make build

# 4. Start development environment
make up

# 5. Run a deliberation (interactive)
make run

# 6. View logs (in another terminal)
make logs-app
```

### Common Development Commands

```bash
# Development
make shell          # Open bash shell in container
make run            # Run deliberation interactively
make logs           # Show all logs
make logs-app       # Show app logs only
make restart        # Restart all containers

# Testing
make test           # Run all tests
make test-unit      # Unit tests only
make test-coverage  # With coverage report

# Code Quality
make lint           # Run ruff linter
make format         # Format code with ruff
make typecheck      # Run mypy
make check          # All quality checks

# Redis
make redis-cli      # Open Redis CLI
make redis-ui       # Start Redis web UI (http://localhost:8081)
make backup-redis   # Backup Redis data
make clean-redis    # Clear all Redis data

# Cleanup
make down           # Stop containers
make clean          # Stop + remove volumes
make clean-all      # Nuclear option (removes images too)
```

---

## Docker Compose Files

### `docker-compose.yml` (Development)

**Use for**: Local development, testing, debugging

**Features**:
- Development stage of Dockerfile
- Source code mounted as volumes (hot reload)
- Debug logging enabled
- Redis Commander available (with `--profile debug`)
- All environment variables exposed

**Start**: `make up` or `docker-compose up`

### `docker-compose.prod.yml` (Production)

**Use for**: Production deployments, cloud environments

**Features**:
- Production stage of Dockerfile (minimal, non-root)
- No source code mounts (immutable)
- Redis password authentication
- Resource limits (CPU, memory)
- Health checks
- Always restart policy

**Start**: `make up-prod` or `docker-compose -f docker-compose.prod.yml up`

---

## Environment Variables

All configuration is through environment variables (loaded from `.env`):

### Required

```bash
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
```

### Optional (with defaults)

```bash
# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=           # Production only

# Application
DEBUG=true                # false in production
LOG_LEVEL=DEBUG           # INFO in production
MAX_COST_PER_SESSION=1.00
MAX_COST_PER_SUBPROBLEM=0.15

# Models
DEFAULT_MODEL_PERSONA=claude-sonnet-4-5-20250929
DEFAULT_MODEL_FACILITATOR=claude-sonnet-4-5-20250929
DEFAULT_MODEL_SUMMARIZER=claude-haiku-4-5-20250929
DEFAULT_MODEL_DECOMPOSER=claude-sonnet-4-5-20250929
DEFAULT_MODEL_MODERATOR=claude-haiku-4-5-20250929

# Feature Flags
ENABLE_PROMPT_CACHING=true
ENABLE_CONVERGENCE_DETECTION=true
ENABLE_DRIFT_DETECTION=true
ENABLE_EARLY_STOPPING=true
```

---

## Volume Mounts

### Development (`docker-compose.yml`)

```yaml
volumes:
  # Source code (hot reload)
  - ./bo1:/app/bo1
  - ./zzz_important:/app/zzz_important
  - ./zzz_project:/app/zzz_project
  - ./tests:/app/tests

  # Persistent data
  - ./exports:/app/exports

  # Redis data (named volume)
  - redis-data:/data
```

**Why**: Changes to source code are immediately available in container (no rebuild)

### Production (`docker-compose.prod.yml`)

```yaml
volumes:
  # Only persistent data
  - ./exports:/app/exports

  # Redis data (named volume)
  - redis-data:/data
```

**Why**: Immutable deployment - source code baked into image

---

## Cloud Deployment Strategy

The Docker-first approach makes cloud deployment straightforward:

### 1. Build Production Image

```bash
make build-prod
```

### 2. Tag for Registry

```bash
# Example: AWS ECR
make docker-tag REGISTRY=123456789.dkr.ecr.us-east-1.amazonaws.com TAG=v1.0.0

# Example: Docker Hub
make docker-tag REGISTRY=yourname/bo1 TAG=v1.0.0

# Example: Google Artifact Registry
make docker-tag REGISTRY=us-docker.pkg.dev/project-id/bo1 TAG=v1.0.0
```

### 3. Push to Registry

```bash
make docker-push REGISTRY=123456789.dkr.ecr.us-east-1.amazonaws.com TAG=v1.0.0
```

### 4. Deploy to Cloud Platform

#### AWS ECS (Fargate)

```bash
# Create ECS task definition (example)
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Create ECS service
aws ecs create-service \
  --cluster bo1-cluster \
  --service-name bo1-service \
  --task-definition bo1-task \
  --desired-count 1 \
  --launch-type FARGATE
```

#### Google Cloud Run

```bash
# Deploy (automatically builds from Dockerfile)
gcloud run deploy bo1 \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Azure Container Instances

```bash
# Create container instance
az container create \
  --resource-group bo1-rg \
  --name bo1-app \
  --image yourregistry/bo1:v1.0.0 \
  --cpu 2 \
  --memory 2 \
  --environment-variables \
    ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
    VOYAGE_API_KEY=$VOYAGE_API_KEY
```

---

## Redis in Docker

### Development

Redis runs in Docker with:
- Appendonly persistence (AOF)
- 256MB memory limit
- LRU eviction policy
- Health checks

**Access**:
```bash
# CLI
make redis-cli

# Web UI (Redis Commander)
make redis-ui
# Visit: http://localhost:8081
```

### Production

Redis runs with:
- Password authentication
- 512MB memory limit
- Persistence to volume
- Resource limits

**Configuration**:
```bash
# Set in .env
REDIS_PASSWORD=your-secure-password-here
```

---

## Debugging in Docker

### View Logs

```bash
# All containers
make logs

# Just bo1 app
make logs-app

# Just redis
docker-compose logs -f redis
```

### Interactive Shell

```bash
# Bash in running container
make shell

# Run one-off command
docker-compose run --rm bo1 python -c "print('hello')"

# Run Python REPL
docker-compose run --rm bo1 python
```

### Inspect State

```bash
# Container status
make status

# Resource usage
make stats

# Configuration (rendered docker-compose)
make inspect
```

### Redis Debugging

```bash
# Redis CLI
make redis-cli

# Inside CLI:
# > KEYS *                    # List all keys
# > GET session:123           # Get value
# > FLUSHALL                  # Clear everything (careful!)
# > INFO                      # Redis stats
# > MONITOR                   # Watch commands in real-time
```

---

## Testing in Docker

### Run Tests

```bash
# All tests
make test

# Specific test types
make test-unit
make test-integration
make test-scenario

# With coverage
make test-coverage
```

### Test File Structure

```
tests/
├── unit/              # Fast, isolated tests
│   ├── test_models.py
│   ├── test_prompts.py
│   └── test_utils.py
├── integration/       # Tests with Redis, LLM mocks
│   ├── test_state.py
│   ├── test_agents.py
│   └── test_orchestration.py
└── scenarios/         # End-to-end scenario tests
    ├── test_simple_problem.py
    ├── test_complex_problem.py
    └── test_real_world_scenarios.py
```

---

## Hot Reload Development

With volume mounts, changes to Python files are immediately available:

```bash
# 1. Start containers
make up

# 2. Edit code in your editor
# (changes are automatically available in container)

# 3. Run with updated code
make run

# No rebuild needed! ✅
```

**When to rebuild**:
- `pyproject.toml` changes (new dependencies)
- `Dockerfile` changes
- System dependency changes

```bash
make restart  # Stop + rebuild + start
```

---

## Production Best Practices

### 1. Use Production Docker Compose

```bash
make up-prod
```

### 2. Set Strong Redis Password

```bash
# In .env
REDIS_PASSWORD=$(openssl rand -base64 32)
```

### 3. Use Secrets Management

For cloud deployments, use platform-native secrets:

**AWS ECS**:
```json
{
  "secrets": [
    {
      "name": "ANTHROPIC_API_KEY",
      "valueFrom": "arn:aws:secretsmanager:region:account:secret:bo1/anthropic"
    }
  ]
}
```

**Google Cloud Run**:
```bash
gcloud run deploy bo1 \
  --update-secrets ANTHROPIC_API_KEY=anthropic-key:latest
```

### 4. Monitor Resource Usage

```bash
# Check limits
make stats

# Adjust in docker-compose.prod.yml:
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
```

### 5. Health Checks

Production image includes health check:
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import sys; sys.exit(0)"
```

Cloud platforms will use this to determine container health.

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
make logs-app

# Check Redis health
docker-compose exec redis redis-cli ping

# Rebuild from scratch
make clean-all
make build
make up
```

### Redis Connection Issues

```bash
# Test Redis connection
make redis-cli

# Inside CLI, run: PING
# Expected: PONG

# Check network
docker network inspect bo1-network
```

### Out of Memory

```bash
# Check usage
make stats

# Increase memory in docker-compose.yml:
deploy:
  resources:
    limits:
      memory: 4G  # Increase from 2G
```

### Permissions Issues

```bash
# Development: runs as root (OK)
# Production: runs as bo1user (non-root)

# If you get permission errors in production:
docker-compose -f docker-compose.prod.yml run --rm --user root bo1 bash
# Inside container: chown -R bo1user:bo1user /app
```

---

## FAQ

**Q: Do I need to install Python locally?**
A: No! Everything runs in Docker. You can edit code in your editor and run in containers.

**Q: Can I use VS Code with Docker?**
A: Yes! Use the "Dev Containers" extension. Open the project folder, and VS Code will detect the Dockerfile.

**Q: How do I debug Python code in Docker?**
A: Add `breakpoint()` in code, then run with `make shell` and execute Python script manually.

**Q: Can I run without Docker?**
A: Yes, but Docker is recommended. If needed: `make install-dev` to install locally.

**Q: How much does Redis cost in production?**
A: Depends on platform. AWS ElastiCache, Google Memorystore, Azure Cache for Redis all have pricing tiers. For low usage, container-based Redis (as we're using) is cheapest.

**Q: Is this production-ready?**
A: v1 is console-based. For production web API, wait for v2 (adds FastAPI, proper health endpoints, etc.).

---

## Next Steps

1. **Week 1**: Develop core models entirely in Docker (`make shell`, edit, test)
2. **Week 2**: Run deliberations in containers (`make run`)
3. **Week 3**: Optimize with Redis caching
4. **Week 4**: Deploy to cloud platform

Your entire development workflow is portable and cloud-ready from day 1! 🚀
