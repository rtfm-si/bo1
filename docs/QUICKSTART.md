# Board of One - Quick Start Guide (Docker-First)

Get started with Board of One in Docker in under 5 minutes.

---

## Prerequisites

- Docker Desktop installed ([download](https://www.docker.com/products/docker-desktop))
- Docker Compose available (included with Docker Desktop)
- API keys:
  - Anthropic API key ([get one](https://console.anthropic.com))
  - Voyage AI API key ([get one](https://www.voyageai.com))

---

## 5-Minute Setup

```bash
# 1. Clone and enter project
cd /Users/si/projects/bo1

# 2. Setup (creates .env and directories)
make setup

# 3. Edit .env with your API keys
nano .env
# Add:
# ANTHROPIC_API_KEY=sk-ant-...
# VOYAGE_API_KEY=pa-...
# Save and exit (Ctrl+X, Y, Enter)

# 4. Build Docker images (~2-3 minutes)
make build

# 5. Start development environment
make up

# 6. Verify everything works
make status    # Should show bo1-app and bo1-redis running
```

**That's it!** Your development environment is ready. 🎉

---

## Your First Deliberation

```bash
# Run interactive deliberation
make run
```

You'll be prompted to describe a problem. Try:

> "I have $50K and 12 months runway. Should I build a B2B SaaS dashboard, a consumer mobile app, or a freelance marketplace?"

Board of One will:
1. ✅ Decompose your problem into sub-problems
2. ✅ Select 3-5 expert personas
3. ✅ Run multi-round debate
4. ✅ Vote and synthesize recommendations
5. ✅ Export final report to `./exports/`

---

## Essential Commands

```bash
# Daily Development
make run          # Run deliberation (interactive)
make shell        # Open bash in container
make logs-app     # View application logs

# Testing
make test         # Run all tests
make test-unit    # Unit tests only

# Code Quality
make lint         # Lint code
make format       # Format code
make check        # All quality checks

# Debugging
make redis-cli    # Open Redis CLI
make redis-ui     # Redis web UI (http://localhost:8081)
make logs         # All container logs

# Cleanup
make down         # Stop containers
make restart      # Restart everything
make clean        # Stop + remove volumes
```

---

## Development Workflow

### Edit Code (Hot Reload)

```bash
# 1. Start containers
make up

# 2. Edit code in your favorite editor
# Changes are immediately available (no rebuild!)

# 3. Run with updated code
make run

# 4. View logs in real-time
make logs-app
```

### When to Rebuild

Only rebuild when:
- `pyproject.toml` changes (new dependencies)
- `Dockerfile` changes
- First-time setup

```bash
make restart  # Stops, rebuilds, starts
```

### Testing Your Changes

```bash
# Run tests in container
make test

# Run specific test file
docker-compose run --rm bo1 pytest tests/unit/test_models.py -v

# Run with coverage
make test-coverage
```

---

## File Organization

```
bo1/
├── bo1/                        # Python package (your code)
│   ├── agents/                # Agent classes (personas, facilitator, etc.)
│   ├── models/                # Pydantic models
│   ├── prompts/               # Prompt templates
│   ├── orchestration/         # Deliberation engine
│   ├── state/                 # Redis state management
│   └── ui/                    # Console UI (Rich)
├── exports/                   # Generated reports (volume mount)
├── zzz_important/             # Design docs (personas, prompts)
├── zzz_project/               # Project management (tasks, PRD)
├── tests/                     # Test files
├── docker-compose.yml         # Development config
├── docker-compose.prod.yml    # Production config
├── Dockerfile                 # Multi-stage build
├── Makefile                   # Easy commands
└── .env                       # Your API keys (gitignored)
```

---

## Common Issues & Fixes

### "Cannot connect to Redis"

```bash
# Check Redis is running
make status

# Restart Redis
make restart

# Check Redis logs
docker-compose logs redis
```

### "Permission denied" errors

```bash
# Development runs as root (OK)
# If you see permission errors:
make clean
make build
make up
```

### "Container won't start"

```bash
# Check logs
make logs-app

# Nuclear option: clean and rebuild
make clean-all
make build
make up
```

### "Out of memory"

```bash
# Check resource usage
make stats

# Increase Docker Desktop memory:
# Docker Desktop → Settings → Resources → Memory
# Set to at least 4GB
```

---

## Where's My Data?

- **Redis state**: Inside `redis-data` volume (persists across restarts)
- **Exports**: In `./exports/` (on your host machine)
- **Source code**: Volume-mounted (edits reflected immediately)
- **Logs**: `docker-compose logs` or `make logs-app`

---

## Redis Web UI (Optional)

```bash
# Start Redis Commander
make redis-ui

# Open browser
open http://localhost:8081

# You can now:
# - Browse Redis keys
# - View session state
# - Inspect cached prompts
# - Monitor in real-time
```

---

## Production Deployment (Future)

When ready to deploy to cloud:

```bash
# Build production image
make build-prod

# Tag for your registry
make docker-tag REGISTRY=your-registry.com TAG=v1.0.0

# Push to registry
make docker-push REGISTRY=your-registry.com TAG=v1.0.0

# Deploy to AWS ECS / Google Cloud Run / Azure
# (See DOCKER.md for platform-specific instructions)
```

---

## Getting Help

1. **Commands**: Run `make help` to see all available commands
2. **Docker Guide**: See `DOCKER.md` for comprehensive Docker documentation
3. **Tasks**: See `zzz_project/TASKS.md` for development roadmap
4. **Design**: See `zzz_project/PRD.md` for product requirements

---

## Next Steps

✅ **You're ready to start coding!**

1. Open `zzz_project/TASKS.md` and start with Day 1-2 tasks
2. Work inside Docker: `make shell` for interactive development
3. Test frequently: `make test`
4. Commit often: Git works normally (Docker doesn't affect it)

Happy coding! 🚀
