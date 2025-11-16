# Testing Guide

## Quick Reference

```bash
make test              # DEFAULT: Fast tests (no LLM calls, ~12 seconds, $0)
make test-fast         # Same as above (explicit)
make test-all          # ALL tests including LLM (15+ min, ~$1-2 in API costs)
make test-coverage     # Coverage report (fast tests only)
```

## Test Categories

### 1. Fast Tests (DEFAULT) ⚡️
**Command**: `make test` or `make test-fast`
- **Duration**: ~12 seconds
- **Cost**: $0
- **Tests**: 228 unit tests (no LLM calls)
- **Use for**: Development, pre-commit checks, CI/CD

### 2. LLM Tests 💰
**Command**: `make test-llm`
- **Duration**: ~10-15 minutes
- **Cost**: ~$1-2 in API calls
- **Tests**: Integration tests with actual LLM calls
- **Use for**: Pre-deployment validation, feature testing

### 3. All Tests (Fast + LLM) ⚠️
**Command**: `make test-all`
- **Duration**: ~15-20 minutes
- **Cost**: ~$1-2 in API calls
- **Tests**: 260+ tests (228 fast + 32+ LLM)
- **Interactive**: Prompts for confirmation before running
- **Use for**: Final validation before production deploy

## Test Markers

Tests are marked with `pytest` markers:

- `@pytest.mark.requires_llm` - Tests that make LLM API calls
- `@pytest.mark.unit` - Pure unit tests (mocked dependencies)
- `@pytest.mark.integration` - Integration tests (may or may not use LLM)

## Running Specific Tests

```bash
# Run specific test file
docker-compose run --rm bo1 pytest tests/test_graph_state.py -v

# Run specific test function
docker-compose run --rm bo1 pytest tests/test_graph_state.py::test_create_initial_state -v

# Run tests by marker
docker-compose run --rm bo1 pytest -m unit -v
docker-compose run --rm bo1 pytest -m "not requires_llm" -v

# Run with coverage
make test-coverage
```

## Pre-Commit Testing

Before committing code, always run:

```bash
make pre-commit        # Lint + format + typecheck
make test              # Fast tests (no LLM calls)
```

**Do NOT run** `make test-all` before every commit (expensive and slow).

## CI/CD Testing

For continuous integration, use:

```bash
make test-fast         # Fast tests only
```

Reserve `make test-all` for:
- Pre-production deployments
- Major feature releases
- Weekly validation runs

## Test Results (Current)

- **228 passing** ✅ (fast tests)
- **5 skipped** (fixtures, Week 5 features)
- **41 deselected** (LLM tests - marked with `requires_llm`)
- **42% code coverage**

## Troubleshooting

### "Database does not exist" errors
Run migrations first:
```bash
docker-compose run --rm bo1 alembic upgrade head
```

### "Redis connection refused" errors
Start Redis container:
```bash
make up
```

### Tests taking too long
You're probably running `make test-all` instead of `make test`:
```bash
# Fast (12 seconds)
make test

# Slow (15 minutes)
make test-all
```

## Cost Estimation

| Test Suite | Duration | API Cost | When to Use |
|------------|----------|----------|-------------|
| `make test` | ~12s | $0 | Every commit, CI/CD |
| `make test-llm` | ~10min | ~$1-2 | Feature validation |
| `make test-all` | ~15min | ~$1-2 | Pre-deploy only |

## Best Practices

1. **Default to fast tests**: `make test` for daily development
2. **LLM tests before deploy**: Run `make test-all` before production deploys
3. **Coverage matters**: Aim for >80% coverage on critical modules
4. **Mark LLM tests**: Use `@pytest.mark.requires_llm` for any test that calls the API
5. **Mock by default**: Mock LLM responses unless specifically testing LLM behavior
