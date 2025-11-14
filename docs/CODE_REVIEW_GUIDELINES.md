# Code Review Guidelines

This document provides guidance for reviewing code contributions to Board of One.

---

## What to Look For

### Security

- [ ] **No hardcoded secrets** - API keys, passwords, tokens must be in environment variables
- [ ] **User input validated** - All inputs validated with Pydantic models
- [ ] **SQL queries parameterized** - No string interpolation in SQL (prevents injection)
- [ ] **Auth required on protected endpoints** - All user-specific operations check authentication
- [ ] **RLS enforced** - Row Level Security policies prevent cross-user data access
- [ ] **No eval() or exec()** - Dynamic code execution is forbidden
- [ ] **Safe file operations** - Validate paths, prevent directory traversal
- [ ] **Rate limiting considered** - High-cost operations have rate limits

### Testing

- [ ] **New code has tests** - Unit and/or integration tests for new functionality
- [ ] **Tests cover happy path + edge cases** - Don't just test success scenarios
- [ ] **Tests are deterministic** - No flaky tests that randomly fail
- [ ] **Mocks used appropriately** - External dependencies (LLM, Redis) mocked in unit tests
- [ ] **Test names are descriptive** - `test_user_cannot_access_other_user_sessions()` not `test_sessions()`
- [ ] **Assertions are clear** - Use specific assertions, not just `assert result`

### Performance

- [ ] **No N+1 queries** - Use joins or batch loading instead of loops with queries
- [ ] **Expensive operations cached** - LLM responses, database queries cached in Redis
- [ ] **Database queries use indexes** - Check that WHERE/JOIN clauses have indexes
- [ ] **Large datasets paginated** - Don't load thousands of records at once
- [ ] **Async used correctly** - I/O-bound operations (LLM calls, DB) use async/await
- [ ] **Memory leaks avoided** - No unbounded lists, proper cleanup of resources

### Code Quality

- [ ] **Code is readable** - Clear variable names, logical structure
- [ ] **Functions are small** - <50 lines per function (exceptions for configuration)
- [ ] **No duplication** - DRY principle followed, shared logic extracted
- [ ] **Type hints present** - All functions have type annotations
- [ ] **Mypy passes** - No type errors (run `make typecheck`)
- [ ] **Docstrings for public APIs** - All public functions/classes documented
- [ ] **Error handling is robust** - Try/except blocks, clear error messages
- [ ] **Constants defined** - No magic numbers, use named constants

### Documentation

- [ ] **Complex logic explained** - Non-obvious code has comments or docstrings
- [ ] **Public APIs documented** - FastAPI auto-docs work, parameters described
- [ ] **Breaking changes noted in PR** - Clearly state if API changes break compatibility
- [ ] **README updated if needed** - New features documented in README
- [ ] **CLAUDE.md updated** - Architecture changes reflected in CLAUDE.md

### Architecture

- [ ] **Follows existing patterns** - Consistent with codebase conventions
- [ ] **Single Responsibility** - Classes/functions do one thing well
- [ ] **Dependency injection** - Don't instantiate dependencies inside functions
- [ ] **Proper abstraction** - Don't leak implementation details
- [ ] **No circular dependencies** - Clean module structure

---

## PR Template

Use this template for all pull requests:

```markdown
## Summary

[Brief description of what this PR does and why]

## Changes

- [List specific changes made]
- [Use bullet points for clarity]

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated (if applicable)
- [ ] Manual testing completed
- [ ] Pre-commit checks pass (`make pre-commit`)
- [ ] All tests pass (`make test` or `pytest -m "not requires_llm"`)

## Screenshots (if UI changes)

[Add screenshots if this affects the UI]

## Breaking Changes

[List any breaking changes, or write "None"]

## Performance Impact

[Describe any performance implications, or write "No impact"]

## Security Considerations

[List security implications, or write "No concerns"]

## Rollback Plan

[How to revert if this causes issues in production]
```

---

## Review Process

### For Authors

1. **Self-review first** - Review your own PR before requesting review
2. **Run pre-commit checks** - `make pre-commit` must pass
3. **Run tests locally** - `make test` or `pytest -m "not requires_llm"`
4. **Keep PRs small** - <500 lines of code changes (exceptions for generated code)
5. **Provide context** - Explain WHY, not just WHAT
6. **Link to issues** - Reference relevant GitHub issues or roadmap tasks

### For Reviewers

1. **Review within 24 hours** - Don't block PRs unnecessarily
2. **Be constructive** - Suggest improvements, don't just criticize
3. **Approve with minor comments** - Don't block for trivial issues
4. **Test locally if complex** - Checkout branch and verify behavior
5. **Use "Request Changes" sparingly** - Only for security, bugs, or major issues

### Review Priorities

**Block merge for**:
- Security vulnerabilities
- Breaking tests
- Data loss risks
- Performance regressions (>20% slower)
- Missing authentication/authorization

**Don't block merge for**:
- Minor style issues (pre-commit handles this)
- Suggestions for future improvements
- Non-critical documentation gaps
- Subjective code preferences

---

## Code Review Checklist

Copy this into your PR review comment:

```markdown
### Security
- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] SQL queries parameterized
- [ ] Auth checks on protected operations

### Testing
- [ ] New code has tests
- [ ] Tests cover edge cases
- [ ] Tests are deterministic

### Performance
- [ ] No N+1 queries
- [ ] Expensive operations cached
- [ ] Queries use indexes

### Code Quality
- [ ] Code is readable
- [ ] Functions are small
- [ ] No duplication
- [ ] Type hints present

### Documentation
- [ ] Complex logic explained
- [ ] Breaking changes noted
```

---

## Common Patterns in Board of One

### Persona Prompt Composition

```python
from bo1.prompts.reusable_prompts import compose_persona_prompt

# GOOD: Use composition function
system_prompt = compose_persona_prompt(
    persona_system_role=persona["system_prompt"],
    problem_statement=problem.statement,
    participant_list=", ".join(persona_codes),
    current_phase="discussion"
)

# BAD: Hardcoding prompts
system_prompt = f"You are {persona['name']}. Solve: {problem.statement}"
```

### Async LLM Calls

```python
# GOOD: Parallel async calls
contributions = await asyncio.gather(
    *[call_persona(code) for code in persona_codes]
)

# BAD: Sequential calls (slow!)
contributions = []
for code in persona_codes:
    contrib = await call_persona(code)
    contributions.append(contrib)
```

### Redis Caching

```python
# GOOD: Use RedisManager
from bo1.state.redis_manager import RedisManager
manager = RedisManager()
state = await manager.load_state(session_id)

# BAD: Direct Redis calls
import redis
r = redis.Redis()
data = r.get(f"session:{session_id}")
```

### Type Hints

```python
# GOOD: Full type annotations
def calculate_consensus(
    votes: list[Vote],
    threshold: float = 0.7
) -> tuple[bool, float]:
    """Calculate if consensus reached."""
    ...

# BAD: No type hints
def calculate_consensus(votes, threshold=0.7):
    ...
```

---

## Anti-Patterns to Avoid

### 1. Hardcoding Configuration

```python
# BAD
MAX_ROUNDS = 15
API_KEY = "sk-ant-..."

# GOOD
from bo1.config import get_settings
settings = get_settings()
MAX_ROUNDS = settings.MAX_ROUNDS
API_KEY = settings.ANTHROPIC_API_KEY
```

### 2. Ignoring Errors

```python
# BAD
try:
    result = risky_operation()
except:
    pass

# GOOD
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise
```

### 3. String SQL Queries

```python
# BAD
query = f"SELECT * FROM sessions WHERE user_id = '{user_id}'"

# GOOD
query = "SELECT * FROM sessions WHERE user_id = :user_id"
result = db.execute(query, {"user_id": user_id})
```

### 4. Mutable Default Arguments

```python
# BAD
def add_contribution(state: State, contributions: list = []):
    contributions.append(state.contribution)

# GOOD
def add_contribution(state: State, contributions: list | None = None):
    if contributions is None:
        contributions = []
    contributions.append(state.contribution)
```

---

## Tools

### Running Checks Locally

```bash
# Full pre-commit suite
make pre-commit

# Individual checks
make lint           # Ruff linter
make format         # Ruff formatter
make typecheck      # mypy type checker

# Auto-fix issues
make fix            # Fix linting + formatting
```

### Running Tests

```bash
# All tests (includes LLM calls - costs $)
make test

# Unit tests only (fast, no LLM)
pytest -m unit

# Skip LLM tests (fast)
pytest -m "not requires_llm"

# Single test file
pytest tests/test_graph_setup.py -v

# With coverage
make test-coverage
```

---

## Questions?

- Read `CLAUDE.md` for architecture overview
- Check `docs/` for specific documentation
- Ask in PR comments or team chat
- Refer to roadmap: `zzz_project/MVP_IMPLEMENTATION_ROADMAP.md`

---

**Last Updated**: 2025-11-14 (Week 4, Day 22)
