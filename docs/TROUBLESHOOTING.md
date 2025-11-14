# Development Troubleshooting Guide

This guide helps resolve common issues when developing Board of One.

---

## Common Errors

### Error: "Redis connection refused"

**Symptom**: `ConnectionRefusedError: [Errno 61] Connection refused`

**Cause**: Redis container not running

**Fix**:
```bash
# Check if Redis is running
docker-compose ps

# Start Redis
make up

# Verify connection
make redis-cli
# Should see: 127.0.0.1:6379>
```

---

### Error: "Database does not exist"

**Symptom**: `psycopg2.OperationalError: database "boardofone" does not exist`

**Cause**: Database not created or migrations not run

**Fix**:
```bash
# Start database
make up

# Run migrations
alembic upgrade head

# Verify
docker-compose exec postgres psql -U bo1 -d boardofone -c '\dt'
# Should list 7 tables
```

---

### Error: "ANTHROPIC_API_KEY not set"

**Symptom**: `KeyError: 'ANTHROPIC_API_KEY'` or `ANTHROPIC_API_KEY is not set in environment`

**Cause**: Missing .env file or missing API key

**Fix**:
```bash
# Check if .env exists
ls -la .env

# If not, create from template
cp .env.example .env

# Edit and add your API key
nano .env  # or your preferred editor

# Add this line:
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# Verify
grep ANTHROPIC_API_KEY .env
```

---

### Error: "Persona not found"

**Symptom**: `PersonaNotFoundError: Persona 'maria' not found`

**Cause**: Personas not seeded to database

**Fix**:
```bash
# Seed personas
python scripts/seed_personas.py

# Verify
docker-compose exec postgres psql -U bo1 -d boardofone -c "SELECT COUNT(*) FROM personas;"
# Should return: 45
```

---

### Error: Tests fail with "No module named 'bo1'"

**Symptom**: `ModuleNotFoundError: No module named 'bo1'`

**Cause**: Wrong directory or missing uv sync

**Fix**:
```bash
# Check current directory
pwd
# Should be: /Users/si/projects/bo1

# If not, navigate there
cd /Users/si/projects/bo1

# Install dependencies
uv sync

# Verify installation
python -c "import bo1; print(bo1.__file__)"
# Should print path to bo1/__init__.py
```

---

### Error: Pre-commit hook fails

**Symptom**: `ruff....Failed` or `mypy....Failed`

**Cause**: Code doesn't pass linting or type checking

**Fix**:
```bash
# Auto-fix linting and formatting
make fix

# If mypy errors remain, review them
make typecheck

# If stuck, skip pre-commit for emergency commits
git commit --no-verify -m "Your message"
# Note: Only use --no-verify in emergencies!
```

---

### Error: "Port already in use"

**Symptom**: `Error starting userland proxy: listen tcp4 0.0.0.0:6379: bind: address already in use`

**Cause**: Port conflict with another service

**Fix**:
```bash
# Find process using port 6379 (Redis)
lsof -i :6379

# Kill the process
kill -9 <PID>

# Or change port in docker-compose.yml
# ports:
#   - "6380:6379"  # Use 6380 instead

# Restart
make restart
```

---

### Error: "Permission denied" when running scripts

**Symptom**: `bash: ./script.sh: Permission denied`

**Cause**: Script not executable

**Fix**:
```bash
# Make executable
chmod +x script.sh

# Or run with python
python script.py
```

---

### Error: Docker build fails

**Symptom**: `ERROR [builder X/Y] RUN ...` during `make build`

**Cause**: Dependency conflicts or network issues

**Fix**:
```bash
# Clean build cache
docker-compose down -v
docker system prune -f

# Rebuild
make build

# If still failing, check logs
docker-compose build --no-cache 2>&1 | tee build.log
```

---

## Performance Issues

### Issue: Deliberation very slow locally

**Cause**: Using Sonnet 4.5 (expensive, slow) instead of Haiku (fast, cheap)

**Fix**:
```bash
# Edit .env
nano .env

# Change model to Haiku for local dev
LLM_MODEL=claude-haiku-4.5

# Restart
make restart
```

---

### Issue: Tests take forever

**Cause**: Running LLM tests (expensive and slow)

**Fix**:
```bash
# Skip LLM tests
pytest -m "not requires_llm"

# Or run only unit tests
pytest -m unit

# Full test suite (when needed)
make test
```

---

### Issue: Redis eating memory

**Symptom**: Redis using >1GB memory

**Cause**: Too many cached keys, no TTL

**Fix**:
```bash
# Check memory usage
make redis-cli
> INFO memory

# Run cleanup
python scripts/redis_cleanup.py --verbose

# Or flush all (WARNING: deletes everything)
make clean-redis
```

---

## Database Issues

### Issue: Migrations out of sync

**Symptom**: `alembic current` shows different version than expected

**Cause**: Manual database changes or failed migration

**Fix**:
```bash
# Check current version
alembic current

# Check migration history
alembic history

# Downgrade to previous version
alembic downgrade -1

# Re-upgrade
alembic upgrade head

# If stuck, reset (WARNING: deletes all data)
docker-compose down -v
make up
alembic upgrade head
python scripts/seed_personas.py
```

---

### Issue: RLS policies blocking queries

**Symptom**: `SELECT` returns 0 rows when you know data exists

**Cause**: Row Level Security blocking access

**Fix**:
```bash
# Check if RLS is enabled
docker-compose exec postgres psql -U bo1 -d boardofone -c "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';"

# Disable RLS for debugging (WARNING: dev only!)
docker-compose exec postgres psql -U bo1 -d boardofone -c "ALTER TABLE sessions DISABLE ROW LEVEL SECURITY;"

# Re-enable after debugging
docker-compose exec postgres psql -U bo1 -d boardofone -c "ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;"

# For queries, set user context
docker-compose exec postgres psql -U bo1 -d boardofone -c "SET app.current_user_id = 'user-123'; SELECT * FROM sessions;"
```

---

## Docker Issues

### Issue: Container keeps restarting

**Symptom**: `docker-compose ps` shows container "Restarting"

**Cause**: Application crash on startup

**Fix**:
```bash
# View logs
make logs-app

# Check for errors
docker-compose logs bo1 --tail=100

# Shell into container
make shell

# Try running app manually
python -m bo1.main
```

---

### Issue: "No space left on device"

**Symptom**: Docker operations fail with disk space error

**Cause**: Docker images/volumes filling disk

**Fix**:
```bash
# Check disk usage
docker system df

# Remove unused containers/images
make prune

# More aggressive cleanup
docker system prune -a --volumes

# Free up space
rm -rf htmlcov .mypy_cache .pytest_cache .ruff_cache
```

---

## Environment Issues

### Issue: Wrong Python version

**Symptom**: `SyntaxError` or `ImportError` with Python-specific features

**Cause**: Using Python <3.12

**Fix**:
```bash
# Check version
python --version

# Install Python 3.12+ (macOS)
brew install python@3.12

# Or use pyenv
pyenv install 3.12
pyenv local 3.12

# Verify
python --version
# Should show: Python 3.12.x
```

---

### Issue: uv command not found

**Symptom**: `bash: uv: command not found`

**Cause**: uv not installed

**Fix**:
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (if needed)
export PATH="$HOME/.cargo/bin:$PATH"

# Verify
uv --version
```

---

## Testing Issues

### Issue: "Fixture not found"

**Symptom**: `pytest.fixture.FixtureLookupError: fixture 'redis_manager' not found`

**Cause**: Missing conftest.py or fixture not imported

**Fix**:
```bash
# Check if conftest.py exists
ls tests/conftest.py

# If exists, check imports
cat tests/conftest.py | grep -A5 "def redis_manager"

# Run tests with verbose output
pytest -v --tb=short
```

---

### Issue: Tests fail in CI but pass locally

**Cause**: Environment differences (API keys, database, Redis)

**Fix**:
- Check CI logs for specific errors
- Ensure GitHub Secrets configured (ANTHROPIC_API_KEY)
- Use mocks for external services in CI
- Run `pytest -m "not requires_llm"` in CI to skip LLM tests

---

## LLM / API Issues

### Issue: "Rate limit exceeded"

**Symptom**: `RateLimitError: Rate limit exceeded for model`

**Cause**: Too many API calls too quickly

**Fix**:
```bash
# Check rate limit status
curl https://api.anthropic.com/v1/rate-limits \
  -H "X-API-Key: $ANTHROPIC_API_KEY"

# Reduce concurrency
# Edit .env
MAX_CONCURRENT_PERSONAS=3  # Default: 5

# Add delays between calls
DELAY_BETWEEN_ROUNDS_MS=1000  # 1 second
```

---

### Issue: "Invalid API key"

**Symptom**: `AuthenticationError: Invalid API key`

**Cause**: Wrong API key or typo

**Fix**:
```bash
# Check API key format
echo $ANTHROPIC_API_KEY
# Should start with: sk-ant-api03-

# Test API key
curl https://api.anthropic.com/v1/messages \
  -H "X-API-Key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-haiku-4.5","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'

# If invalid, get new key from: https://console.anthropic.com/
```

---

## Getting More Help

### Useful Commands

```bash
# System information
make version        # Show versions
make status         # Container status
make stats          # Resource usage

# Logs
make logs           # All container logs
make logs-app       # App logs only

# Debugging
make shell          # Shell in container
make redis-cli      # Redis CLI

# Cleanup
make clean          # Clean build artifacts
make clean-redis    # Clear Redis data
make prune          # Clean Docker
```

### Log Locations

- **Application logs**: `docker-compose logs bo1`
- **Database logs**: `docker-compose logs postgres`
- **Redis logs**: `docker-compose logs redis`
- **Pre-commit logs**: `.git/hooks/pre-commit.log`
- **Test logs**: `pytest --log-cli-level=DEBUG`

### Debug Mode

```bash
# Enable debug logging
# Edit .env
LOG_LEVEL=DEBUG

# Restart
make restart

# View debug logs
make logs-app
```

---

## Still Stuck?

1. **Check documentation**:
   - `CLAUDE.md` - Architecture overview
   - `README.md` - Getting started
   - `docs/` - Detailed documentation

2. **Search issues**:
   - Check closed GitHub issues
   - Search Discord/Slack for similar problems

3. **Create detailed bug report**:
   - Include error message (full traceback)
   - Include steps to reproduce
   - Include environment info (`make version`)
   - Include relevant logs

4. **Ask for help**:
   - GitHub Issues
   - Team chat
   - Stack Overflow (tag: langgraph, fastapi, anthropic)

---

**Last Updated**: 2025-11-14 (Week 4, Day 22)
