# Datetime Handling in API Responses

## Principle

**All datetime fields in API responses MUST use Pydantic model serialization.**

Never use raw `.isoformat()` calls in API layer code. Pydantic handles serialization automatically with consistent ISO 8601 format.

## Why?

1. **Consistency**: Pydantic uses a single format across all endpoints
2. **Validation**: Response models validate data before returning
3. **Type Safety**: dict building bypasses type checking (dict is `Any`)
4. **Maintainability**: Less verbose, fewer edge cases for null handling

## Approved Patterns

### Good: Pydantic Model

```python
class SessionResponse(BaseModel):
    id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

@router.get("/sessions/{id}")
async def get_session(id: str) -> SessionResponse:
    row = await fetch_session(id)
    return SessionResponse(
        id=row["id"],
        created_at=row["created_at"],  # Pydantic serializes automatically
        updated_at=row["updated_at"],
    )
```

### Bad: Manual isoformat()

```python
# DON'T DO THIS
@router.get("/sessions/{id}")
async def get_session(id: str):
    row = await fetch_session(id)
    return {
        "id": row["id"],
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }
```

## Exceptions

`.isoformat()` is acceptable in these contexts:

1. **Repository layer**: Redis cache keys, serialization for storage
2. **Internal utilities**: Logging, debugging
3. **Non-API code**: Scripts, background tasks

The linter (`make lint-datetime`) only checks `backend/api/` files.

## Linting

```bash
# Run the datetime linter
make lint-datetime

# View allowlist (known violations pending migration)
cat scripts/lint_datetime_allowlist.txt
```

## Migration Guide

To fix a violation:

1. Create or reuse a Pydantic response model in `backend/api/models.py`
2. Add `datetime` typed fields to the model
3. Replace dict building with model instantiation
4. Add the model as the endpoint's `response_model`

Example migration:

```python
# Before
return {"expires_at": token.expires_at.isoformat()}

# After (in models.py)
class TokenResponse(BaseModel):
    expires_at: datetime

# After (in endpoint)
return TokenResponse(expires_at=token.expires_at)
```

## Reference

- Pydantic datetime serialization: https://docs.pydantic.dev/latest/concepts/serialization/
- ISO 8601 format used: `YYYY-MM-DDTHH:MM:SS.ffffff+HH:MM`
