# Backend Fixes Migration Guide

Quick reference for developers on the updated patterns and how to use the new utilities.

---

## Updated Import Patterns

### ❌ OLD (Don't use)
```python
from bo1.state.redis_manager import RedisManager
redis_manager = RedisManager()

from bo1.graph.execution import SessionManager
session_manager = SessionManager(redis_manager, admin_user_ids=set())
```

### ✅ NEW (Use this)
```python
from backend.api.dependencies import get_redis_manager, get_session_manager

redis_manager = get_redis_manager()  # Singleton, cached
session_manager = get_session_manager()  # Singleton, cached, with admin IDs from env
```

---

## Input Validation

### Session IDs - ALWAYS validate
```python
from backend.api.utils.validation import validate_session_id

@router.get("/{session_id}")
async def my_endpoint(session_id: str):
    # ALWAYS validate first (prevents injection)
    session_id = validate_session_id(session_id)

    # Now safe to use
    metadata = redis_manager.load_metadata(session_id)
```

### User IDs - ALWAYS validate
```python
from backend.api.utils.validation import validate_user_id

def _get_user_id_from_header() -> str:
    user_id = "test_user_1"  # Or extract from JWT
    return validate_user_id(user_id)  # Always validate
```

---

## Database Operations

### ❌ OLD (Don't use - no pooling)
```python
from bo1.state.postgres_manager import get_connection

conn = get_connection()
try:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM ...")
        result = cur.fetchone()
    conn.commit()
finally:
    conn.close()
```

### ✅ NEW (Use this - with pooling & auto-cleanup)
```python
from bo1.state.postgres_manager import db_session

with db_session() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM ...")
        result = cur.fetchone()
# Auto-commit on success, auto-rollback on error, connection returned to pool
```

---

## Text Utilities

### ❌ OLD (Don't duplicate)
```python
def _truncate_text(text: str, max_length: int = 100) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
```

### ✅ NEW (Use shared utility)
```python
from backend.api.utils.text import truncate_text

truncated = truncate_text(long_text, max_length=100)
```

---

## Constants

### ❌ OLD (Don't use magic numbers)
```python
@router.get("/sessions")
async def list_sessions(
    limit: int = Query(10, ge=1, le=100),
):
    ...
```

### ✅ NEW (Use constants)
```python
from backend.api.constants import DEFAULT_PAGE_SIZE, MIN_PAGE_SIZE, MAX_PAGE_SIZE

@router.get("/sessions")
async def list_sessions(
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE),
):
    ...
```

---

## Environment Variables

### Admin User IDs
```bash
# In .env
ADMIN_USER_IDS=admin,user123,jane@example.com
```

The `get_session_manager()` automatically parses this and creates the SessionManager with these admin users.

---

## Security Best Practices

### 1. ALWAYS Validate Inputs
- Session IDs: `validate_session_id()`
- User IDs: `validate_user_id()`
- Cache IDs: `validate_cache_id()`

### 2. NEVER Log Sensitive Data
```python
# ❌ BAD
logger.warning(f"Invalid API key: {api_key[:8]}...")

# ✅ GOOD
logger.warning("Invalid API key attempted")
```

### 3. ALWAYS Use Parameterized Queries
```python
# ❌ BAD (SQL injection risk)
cur.execute(f"SELECT * FROM users WHERE id = '{user_id}'")

# ✅ GOOD (safe)
cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

### 4. Validate Integers Before SQL Interpolation
```python
# If you MUST use f-strings (e.g., INTERVAL), validate first:
if not isinstance(days, int) or days < 0:
    raise ValueError("days must be a positive integer")
# Now safe to use in SQL
query = f"... WHERE date > NOW() - INTERVAL '{days} days'"
```

---

## Testing Your Changes

### Run Security Tests
```bash
pytest tests/backend/test_security_fixes.py -v
```

### Run Unit Tests
```bash
pytest -m "not requires_llm" -k "not integration"
```

### Run Code Quality Checks
```bash
make pre-commit  # or:
ruff check . && ruff format --check . && mypy backend/api/
```

---

## Common Errors & Solutions

### Error: "Undefined name `_create_redis_manager`"
**Solution**: Import from dependencies instead
```python
# ❌ Remove this
def _create_redis_manager() -> RedisManager:
    return RedisManager()

# ✅ Use this
from backend.api.dependencies import get_redis_manager
```

### Error: "Invalid session ID format"
**Solution**: Your session ID doesn't match UUID format
```python
# Valid formats:
"550e8400-e29b-41d4-a716-446655440000"  # Standard UUID
"bo1_550e8400-e29b-41d4-a716-446655440000"  # With prefix
```

### Error: "DATABASE_URL environment variable is required"
**Solution**: Connection pooling requires DATABASE_URL to be set in your environment.

---

## Questions?

- See `BACKEND_FIXES_SUMMARY.md` for detailed documentation
- See `tests/backend/test_security_fixes.py` for usage examples
- Check `backend/api/utils/validation.py` for validation patterns
