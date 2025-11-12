# Contributing to Board of One

## Pre-Commit Workflow

**IMPORTANT**: Always run checks before committing to avoid CI/CD failures.

### Option 1: Using Git Pre-Commit Hook (Automatic)

The repository includes a pre-commit hook that automatically runs linting, formatting, and type checking on staged files.

The hook is already set up at `.git/hooks/pre-commit` and will run automatically when you commit.

### Option 2: Manual Pre-Commit Checks

Run this command before every commit:

```bash
make pre-commit
```

This will run:
- ✅ Linting (ruff check) - **BLOCKING**
- ✅ Formatting check (ruff format --check) - **BLOCKING**
- ✅ Type checking (mypy) - **BLOCKING**

All checks must pass before you can commit.

### Option 3: Auto-Fix Issues

If you have linting or formatting issues, auto-fix them:

```bash
make fix
```

This will:
- Fix linting issues automatically
- Format code according to project standards

Then run `make pre-commit` again to verify.

## Workflow Example

```bash
# 1. Make your changes
vim bo1/agents/my_agent.py

# 2. Run pre-commit checks
make pre-commit

# 3. If there are issues, auto-fix them
make fix

# 4. Verify fixes
make pre-commit

# 5. Commit (pre-commit hook will run automatically)
git add .
git commit -m "Add new agent"

# 6. Push
git push
```

## Code Quality Standards

### Linting (Ruff)
- All Python code must pass `ruff check .`
- No unused imports
- Type hints required for function signatures (including `__init__` → `None`)
- No f-strings without placeholders

### Formatting (Ruff)
- All Python code must be formatted with `ruff format .`
- 100 character line length
- Consistent quote style

### Type Checking (Mypy)
- All Python code should pass `mypy bo1/`
- Use type hints for function parameters and return values
- Use `| None` for optional types (Python 3.10+ syntax)

## Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests (requires API keys)
make test-integration

# With coverage
make test-coverage
```

## Makefile Commands

```bash
make help              # Show all available commands
make pre-commit        # Run all pre-commit checks
make fix              # Auto-fix linting and formatting
make check            # Run all code quality checks
make lint             # Run linter only
make format           # Format code
make typecheck        # Run type checker only
```

## CI/CD Pipeline

The GitHub Actions CI/CD pipeline runs:
1. Linting (ruff check)
2. Formatting check (ruff format --check)
3. Type checking (mypy)
4. Tests (pytest)

**All checks must pass before merging to main.**

## Common Issues

### Issue: Linting fails on commit
**Solution**: Run `make fix` then `make pre-commit`

### Issue: Type hints missing
**Solution**: Add return type annotations to all functions:
```python
def __init__(self, client: Client | None = None) -> None:  # Add -> None
    ...

def process(self, data: str) -> dict[str, Any]:  # Add -> dict[str, Any]
    ...
```

### Issue: Unused imports
**Solution**: Remove unused imports or use them. Ruff will show which ones.

### Issue: f-string without placeholders
**Solution**: Remove the `f` prefix:
```python
# Bad
logger.info(f"Processing complete")

# Good
logger.info("Processing complete")
```

## Questions?

Open an issue or ask in discussions!
