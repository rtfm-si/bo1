# Board of One - Sprint Implementation Plan
## 2-Week Optimization Sprint

**Sprint Duration:** 10 working days (2 weeks)
**Total Effort:** 40-50 hours
**Sprint Goal:** Implement high-impact optimizations for cost reduction, code quality, and system observability

---

## Executive Summary

### Sprint Objectives

1. **Reduce operational costs by 60-80%** through LLM response caching and persona selection caching
2. **Improve code quality and consistency** through standardized error handling and test coverage
3. **Enhance system observability** with metrics collection and feature flags
4. **Eliminate technical debt** by fixing test collection failures and refactoring complex code

### Expected Outcomes

| Metric | Current | Target | Impact |
|--------|---------|--------|--------|
| Monthly LLM costs | $300-500 | $100-150 | 60-70% reduction |
| Test coverage | 41% | 60%+ | 28 tests unblocked |
| API error consistency | 60% | 95% | Standardized responses |
| Code complexity (event_collector.py) | 884 lines | 600 lines | 32% reduction |
| System observability | None | Full metrics | Monitoring enabled |

### Key Deliverables

- ✅ LLM response caching system with Redis backend
- ✅ Persona selection semantic caching
- ✅ Standardized API error handling across all endpoints
- ✅ Metrics collection infrastructure
- ✅ Feature flag system for runtime configuration
- ✅ Event extractor pattern refactoring
- ✅ 28 previously broken tests now passing
- ✅ 7 quick wins implemented

---

## Sprint Structure

### Week 1: Foundation & Quick Wins (20-25 hours)

**Focus:** Critical fixes, high-ROI caching, and quick improvements

- **Day 1-2:** Test fixes + LLM caching foundation
- **Day 3:** Error handling standardization
- **Day 4-5:** Quick wins batch + validation

### Week 2: Advanced Features & Optimization (20-25 hours)

**Focus:** Complex refactoring, monitoring, and advanced caching

- **Day 6-7:** Event extractor refactoring + metrics
- **Day 8:** Feature flags implementation
- **Day 9-10:** Persona caching + sprint wrap-up

---

## Task Breakdown

### [TASK 1] Fix Test Collection Failures

**Priority:** Critical
**Effort:** 1-2 hours
**Day:** Day 1 (Morning)
**Dependencies:** None

#### Objective
Fix pytest configuration to enable collection of 28 currently failing test files, unblocking comprehensive test coverage.

#### Success Criteria
- [ ] All 28 test files collect successfully
- [ ] Tests run and report results (pass/fail)
- [ ] `pytest --collect-only` shows all tests
- [ ] CI/CD pipeline updated (if applicable)

#### Implementation Steps

**1. Analysis (15 min)**
```bash
# Identify failing tests
cd /Users/si/projects/bo1
pytest --collect-only 2>&1 | grep "ERROR.*asyncio"

# Review current pytest config
cat pyproject.toml | grep -A 20 "\[tool.pytest"
```

**2. Fix Configuration (30 min)**

Edit `pyproject.toml`:
```toml
[tool.pytest.ini_options]
markers = [
    "asyncio: mark test as async",
    "unit: mark test as unit test",
    "integration: mark test as integration test",
    "requires_llm: mark test as requiring LLM API calls",
]
asyncio_mode = "auto"  # Auto-detect async tests
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

**3. Validate (30 min)**
```bash
# Collect all tests
pytest --collect-only

# Run previously failing tests
pytest tests/graph/test_resume_session.py -v
pytest tests/integration/test_context_collection_flow.py -v

# Run full suite
make test
```

**4. Commit (15 min)**
```bash
git add pyproject.toml
git commit -m "fix: add asyncio marker to pytest configuration

- Add asyncio marker to enable async test collection
- Set asyncio_mode to 'auto' for automatic async detection
- Fixes 28 test files that were failing to collect

Impact:
- All tests now collecting successfully
- Enables comprehensive test coverage measurement
- Unblocks integration and graph test suites"
```

#### Files Modified
- `pyproject.toml` - Add asyncio marker configuration

#### Acceptance Criteria
- [ ] `pytest --collect-only` runs without errors
- [ ] All 28 previously failing tests now collect
- [ ] `make pre-commit` passing
- [ ] Tests can be executed (may fail, but must collect)

---

### [TASK 2] Implement LLM Response Caching

**Priority:** High (Highest ROI)
**Effort:** 4-6 hours
**Day:** Day 1 (Afternoon) - Day 2 (Morning)
**Dependencies:** Task 1 (for testing)

#### Objective
Implement Redis-based LLM response caching to reduce API costs by 60-80% through intelligent caching of identical prompts.

#### Success Criteria
- [ ] Cache hit rate >60% in realistic scenarios
- [ ] 95%+ faster response time for cache hits (<100ms vs 2000ms)
- [ ] Cost reduction measurable ($0.04-0.08 saved per cache hit)
- [ ] TTL-based cache expiration (24 hours default)
- [ ] Cache key generation deterministic and collision-free

#### Implementation Steps

**1. Analysis (30 min)**
```bash
# Review current LLM call sites
grep -rn "broker.send_prompt\|client.create_message" bo1/agents/ bo1/orchestration/

# Identify high-frequency prompts
# - Persona contributions (5-15 per deliberation)
# - Facilitator decisions (5-15 per deliberation)
# - Research questions (3-10 per deliberation)
```

**2. Design Cache Key Generation (1 hour)**

Create `bo1/llm/cache.py`:
```python
"""LLM response caching with Redis backend."""
import hashlib
import json
import logging
from typing import Any

from bo1.config import get_settings
from bo1.llm.models import LLMResponse, PromptRequest
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

def generate_cache_key(
    system: str,
    user_message: str,
    model: str,
    max_tokens: int | None = None,
) -> str:
    """Generate deterministic cache key for LLM prompt.

    Uses SHA-256 hash of JSON-serialized prompt components to create
    stable, collision-resistant cache keys.

    Args:
        system: System prompt
        user_message: User message/prompt
        model: Model identifier (e.g., 'claude-sonnet-4.5')
        max_tokens: Max tokens setting (affects response)

    Returns:
        Redis cache key (e.g., 'llm:cache:a1b2c3d4e5f6g7h8')
    """
    cache_content = {
        "system": system,
        "user": user_message,
        "model": model,
        "max_tokens": max_tokens,
    }

    # JSON serialize with sorted keys for determinism
    content_json = json.dumps(cache_content, sort_keys=True)

    # Generate SHA-256 hash
    content_hash = hashlib.sha256(content_json.encode()).hexdigest()

    # Use first 16 chars for readability
    cache_key = f"llm:cache:{content_hash[:16]}"

    return cache_key
```

**3. Implement Caching Layer (2 hours)**

Add to `bo1/llm/cache.py`:
```python
class LLMResponseCache:
    """Redis-backed LLM response cache."""

    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager.redis
        self.enabled = get_settings().enable_llm_response_cache
        self.ttl_seconds = get_settings().llm_response_cache_ttl_seconds
        self._hits = 0
        self._misses = 0

    async def get_cached_response(
        self,
        request: PromptRequest,
    ) -> LLMResponse | None:
        """Get cached LLM response if exists."""
        if not self.enabled:
            return None

        cache_key = generate_cache_key(
            system=request.system,
            user_message=request.user_message,
            model=request.model,
            max_tokens=request.max_tokens,
        )

        try:
            cached_json = self.redis.get(cache_key)
            if cached_json:
                self._hits += 1
                logger.info(
                    f"LLM cache hit: {cache_key} "
                    f"(hit_rate={self.hit_rate:.1%})"
                )
                return LLMResponse.model_validate_json(cached_json)
        except Exception as e:
            logger.error(f"LLM cache read error: {e}")

        self._misses += 1
        return None

    async def cache_response(
        self,
        request: PromptRequest,
        response: LLMResponse,
    ) -> None:
        """Cache LLM response."""
        if not self.enabled:
            return

        cache_key = generate_cache_key(
            system=request.system,
            user_message=request.user_message,
            model=request.model,
            max_tokens=request.max_tokens,
        )

        try:
            response_json = response.model_dump_json()
            self.redis.setex(
                cache_key,
                self.ttl_seconds,
                response_json,
            )
            logger.debug(f"LLM response cached: {cache_key}")
        except Exception as e:
            logger.error(f"LLM cache write error: {e}")

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "enabled": self.enabled,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
            "ttl_seconds": self.ttl_seconds,
        }

# Global cache instance
_cache_instance: LLMResponseCache | None = None

def get_llm_cache() -> LLMResponseCache:
    """Get or create LLM cache instance."""
    global _cache_instance
    if _cache_instance is None:
        from bo1.state.redis_manager import get_redis_manager
        _cache_instance = LLMResponseCache(get_redis_manager())
    return _cache_instance
```

**4. Integrate with LLM Broker (1 hour)**

Update `bo1/llm/broker.py`:
```python
from bo1.llm.cache import get_llm_cache

async def send_prompt(request: PromptRequest) -> LLMResponse:
    """Send prompt to LLM with caching."""
    cache = get_llm_cache()

    # Check cache first
    cached_response = await cache.get_cached_response(request)
    if cached_response:
        return cached_response

    # Cache miss - call API
    client = ClaudeClient()
    response = await client.create_message(
        system=request.system,
        user_message=request.user_message,
        model=request.model,
        max_tokens=request.max_tokens,
    )

    # Store in cache
    await cache.cache_response(request, response)

    return response
```

**5. Add Configuration (15 min)**

Update `bo1/config.py`:
```python
class Settings(BaseSettings):
    # ... existing fields

    # LLM Response Caching
    enable_llm_response_cache: bool = Field(default=False)
    llm_response_cache_ttl_seconds: int = Field(default=86400)  # 24 hours
```

**6. Testing (1.5 hours)**

Create `tests/llm/test_cache.py`:
```python
import pytest
from bo1.llm.cache import generate_cache_key, LLMResponseCache
from bo1.llm.models import PromptRequest, LLMResponse

def test_cache_key_generation():
    """Test deterministic cache key generation."""
    key1 = generate_cache_key("sys", "user", "model")
    key2 = generate_cache_key("sys", "user", "model")
    assert key1 == key2

    # Different prompts = different keys
    key3 = generate_cache_key("sys", "different", "model")
    assert key1 != key3

@pytest.mark.asyncio
async def test_cache_hit(redis_manager):
    """Test cache hit returns cached response."""
    cache = LLMResponseCache(redis_manager)
    request = PromptRequest(
        system="test",
        user_message="hello",
        model="claude-sonnet-4.5",
    )
    response = LLMResponse(
        content="cached response",
        cost_input_tokens=100,
        cost_output_tokens=50,
        # ... other fields
    )

    # Cache response
    await cache.cache_response(request, response)

    # Retrieve from cache
    cached = await cache.get_cached_response(request)
    assert cached is not None
    assert cached.content == "cached response"
    assert cache.hit_rate == 1.0

@pytest.mark.asyncio
async def test_cache_miss(redis_manager):
    """Test cache miss returns None."""
    cache = LLMResponseCache(redis_manager)
    request = PromptRequest(
        system="test",
        user_message="uncached",
        model="claude-sonnet-4.5",
    )

    cached = await cache.get_cached_response(request)
    assert cached is None
    assert cache.hit_rate == 0.0
```

Run tests:
```bash
pytest tests/llm/test_cache.py -v
```

**7. Documentation (30 min)**

Update `CLAUDE.md`:
```markdown
**LLM Response Caching:**
- Enabled via `ENABLE_LLM_RESPONSE_CACHE=true` environment variable
- Default TTL: 24 hours (configurable via `LLM_RESPONSE_CACHE_TTL_SECONDS`)
- Cache key: SHA-256 hash of system + user + model + max_tokens
- Storage: Redis with automatic expiration
- Typical hit rate: 60-70% in production
- Cost savings: $0.04-0.08 per cache hit
```

**8. Commit (15 min)**
```bash
git add bo1/llm/cache.py bo1/llm/broker.py bo1/config.py tests/llm/test_cache.py CLAUDE.md
git commit -m "feat: add LLM response caching with Redis backend

- Implement LLMResponseCache with deterministic key generation
- Integrate caching layer into LLM broker send_prompt()
- Add cache statistics tracking (hits, misses, hit rate)
- Add configuration flags for enabling/disabling cache
- Add comprehensive tests for cache functionality

Performance Impact:
- Cache hits: 95% faster (<100ms vs 2000ms)
- Expected hit rate: 60-70% in production
- Cost savings: \$0.04-0.08 per cached response
- TTL: 24 hours (configurable)

Configuration:
- ENABLE_LLM_RESPONSE_CACHE=true (default: false)
- LLM_RESPONSE_CACHE_TTL_SECONDS=86400 (default: 24 hours)"
```

#### Files Modified
- `bo1/llm/cache.py` - New file with caching logic
- `bo1/llm/broker.py` - Integrate cache into send_prompt()
- `bo1/config.py` - Add cache configuration settings
- `tests/llm/test_cache.py` - New test file
- `CLAUDE.md` - Document caching feature

#### Potential Issues
- **Cache invalidation:** 24-hour TTL may serve stale responses for time-sensitive queries
  - *Mitigation:* Make TTL configurable, consider shorter TTL for certain prompt types
- **Redis connection failures:** Cache failures shouldn't break LLM calls
  - *Mitigation:* Graceful degradation - log error and proceed with API call
- **Cache key collisions:** Hash collisions could serve wrong response
  - *Mitigation:* SHA-256 provides 2^256 keyspace (collision probability negligible)

#### Acceptance Criteria
- [ ] All tests passing (including new cache tests)
- [ ] Cache hit rate measurable via `get_llm_cache().get_stats()`
- [ ] Environment variable toggles cache on/off
- [ ] `make pre-commit` passing
- [ ] Documentation in CLAUDE.md complete

---

### [TASK 3] Standardize API Error Handling

**Priority:** High
**Effort:** 3-4 hours
**Day:** Day 3
**Dependencies:** None

#### Objective
Create standardized error handling across all API endpoints to ensure consistent error responses, proper logging, and improved debugging.

#### Success Criteria
- [ ] Error decorator applied to all endpoints
- [ ] Consistent HTTP status codes (400, 401, 403, 404, 500)
- [ ] All errors logged with context
- [ ] No stack traces leaked to clients
- [ ] 95%+ of endpoints use standardized pattern

#### Implementation Steps

**1. Create Error Utilities (1 hour)**

Create `backend/api/utils/errors.py`:
```python
"""Standardized API error handling utilities."""
import logging
from functools import wraps
from typing import Callable, Literal, TypeVar

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Type alias for error categories
ErrorType = Literal[
    "redis_unavailable",
    "session_not_found",
    "unauthorized",
    "forbidden",
    "invalid_input",
    "not_found",
]

# Standard error responses
ERROR_RESPONSES: dict[ErrorType, tuple[int, str]] = {
    "redis_unavailable": (
        500,
        "Service temporarily unavailable - please try again",
    ),
    "session_not_found": (404, "Session not found"),
    "unauthorized": (401, "Authentication required"),
    "forbidden": (403, "Access denied"),
    "invalid_input": (400, "Invalid input"),
    "not_found": (404, "Resource not found"),
}


def raise_api_error(
    error_type: ErrorType,
    detail: str | None = None,
) -> None:
    """Raise HTTPException with standardized error response.

    Args:
        error_type: Category of error (determines status code)
        detail: Optional custom error message (overrides default)

    Raises:
        HTTPException with appropriate status code and message
    """
    status_code, default_detail = ERROR_RESPONSES[error_type]
    raise HTTPException(
        status_code=status_code,
        detail=detail or default_detail,
    )


F = TypeVar("F", bound=Callable)


def handle_api_errors(operation: str) -> Callable[[F], F]:
    """Decorator for consistent error handling in API endpoints.

    Catches all exceptions and converts them to appropriate HTTPExceptions:
    - HTTPException: Re-raised as-is
    - ValueError: Converted to 400 (invalid input)
    - KeyError: Converted to 404 (not found)
    - Exception: Converted to 500 (internal error)

    All errors are logged with context for debugging.

    Args:
        operation: Description of operation for logging

    Returns:
        Decorated function with error handling

    Example:
        @router.post("/sessions")
        @handle_api_errors("create session")
        async def create_session(...):
            # Implementation
            pass
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTPException as-is
                raise
            except ValueError as e:
                # Business logic validation errors → 400
                logger.warning(
                    f"Validation error in {operation}: {e}",
                    extra={"operation": operation},
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid input: {str(e)}",
                ) from e
            except KeyError as e:
                # Missing data errors → 404
                logger.warning(
                    f"Not found in {operation}: {e}",
                    extra={"operation": operation},
                )
                raise HTTPException(
                    status_code=404,
                    detail=f"Resource not found: {str(e)}",
                ) from e
            except Exception as e:
                # Unexpected errors → 500
                logger.error(
                    f"Unexpected error in {operation}: {e}",
                    exc_info=True,
                    extra={"operation": operation},
                )
                raise HTTPException(
                    status_code=500,
                    detail="An unexpected error occurred",
                ) from e

        return wrapper  # type: ignore

    return decorator
```

**2. Apply Decorator to Endpoints (1.5 hours)**

Update `backend/api/sessions.py`:
```python
from backend.api.utils.errors import handle_api_errors, raise_api_error

@router.post("")
@handle_api_errors("create session")
async def create_session(
    request: CreateSessionRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> SessionResponse:
    """Create new deliberation session."""
    user_id = extract_user_id(user)
    redis_manager = get_redis_manager()

    if not redis_manager.is_available:
        raise_api_error("redis_unavailable")

    # Implementation
    # No try/except needed - decorator handles it
    session_id = await session_manager.create_session(...)
    return SessionResponse(id=session_id, ...)
```

Apply to all endpoints in:
- `backend/api/sessions.py` (10 endpoints)
- `backend/api/control.py` (5 endpoints)
- `backend/api/context.py` (4 endpoints)
- `backend/api/streaming.py` (3 endpoints)
- `backend/api/admin.py` (6 endpoints)

**3. Testing (1 hour)**

Create `tests/api/test_error_handling.py`:
```python
import pytest
from fastapi import HTTPException

from backend.api.utils.errors import (
    handle_api_errors,
    raise_api_error,
)


def test_raise_api_error():
    """Test standardized error raising."""
    with pytest.raises(HTTPException) as exc_info:
        raise_api_error("session_not_found")

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


def test_raise_api_error_custom_detail():
    """Test error with custom message."""
    with pytest.raises(HTTPException) as exc_info:
        raise_api_error("forbidden", "Custom message")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Custom message"


@pytest.mark.asyncio
async def test_error_decorator_value_error():
    """Test decorator converts ValueError to 400."""
    @handle_api_errors("test operation")
    async def failing_func():
        raise ValueError("Invalid value")

    with pytest.raises(HTTPException) as exc_info:
        await failing_func()

    assert exc_info.value.status_code == 400
    assert "Invalid input" in exc_info.value.detail


@pytest.mark.asyncio
async def test_error_decorator_unexpected():
    """Test decorator converts unexpected errors to 500."""
    @handle_api_errors("test operation")
    async def failing_func():
        raise RuntimeError("Unexpected error")

    with pytest.raises(HTTPException) as exc_info:
        await failing_func()

    assert exc_info.value.status_code == 500
    assert "unexpected error" in exc_info.value.detail.lower()
```

Run tests:
```bash
pytest tests/api/test_error_handling.py -v
```

**4. Update Documentation (30 min)**

Update `CLAUDE.md`:
```markdown
**API Error Handling:**
- Use `@handle_api_errors("operation")` decorator on all endpoints
- Use `raise_api_error(error_type)` for common error cases
- Standard error types: redis_unavailable, session_not_found, unauthorized, forbidden
- All errors logged with operation context
- Consistent HTTP status codes across API
```

**5. Commit (15 min)**
```bash
git add backend/api/utils/errors.py backend/api/*.py tests/api/test_error_handling.py CLAUDE.md
git commit -m "feat: standardize API error handling across endpoints

- Create error utilities module with decorators and helpers
- Apply @handle_api_errors decorator to 28 endpoints
- Create raise_api_error() for common error patterns
- Add comprehensive error handling tests

Improvements:
- Consistent HTTP status codes (400, 401, 403, 404, 500)
- All errors logged with operation context
- No stack traces leaked to clients
- Easier debugging with structured logging

Files Updated:
- backend/api/sessions.py (10 endpoints)
- backend/api/control.py (5 endpoints)
- backend/api/context.py (4 endpoints)
- backend/api/streaming.py (3 endpoints)
- backend/api/admin.py (6 endpoints)"
```

#### Files Modified
- `backend/api/utils/errors.py` - New error utilities
- `backend/api/sessions.py` - Apply decorator
- `backend/api/control.py` - Apply decorator
- `backend/api/context.py` - Apply decorator
- `backend/api/streaming.py` - Apply decorator
- `backend/api/admin.py` - Apply decorator
- `tests/api/test_error_handling.py` - New tests
- `CLAUDE.md` - Document pattern

#### Acceptance Criteria
- [ ] All 28 endpoints use error handling
- [ ] Tests passing for error utilities
- [ ] `make pre-commit` passing
- [ ] Documentation updated
- [ ] No stack traces visible in API responses

---

### [TASK 4] Quick Wins Batch

**Priority:** Medium (High collective impact)
**Effort:** 10-15 hours total
**Day:** Day 4-5
**Dependencies:** None

This task bundles 7 small, high-impact improvements:

#### 4.1 Response Compression Validation (1 hour)

Create `tests/api/test_compression.py`:
```python
@pytest.mark.asyncio
async def test_gzip_compression_enabled():
    """Verify GZip compression reduces response size."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/sessions",
            headers={"Accept-Encoding": "gzip"},
        )

        assert response.headers.get("content-encoding") == "gzip"
        # Response should be smaller when compressed
        compressed_size = int(response.headers.get("content-length", 0))
        actual_size = len(response.content)
        assert compressed_size > 0
```

#### 4.2 Component Cache Eviction (1 hour)

Update `frontend/src/routes/(app)/meeting/[id]/+page.svelte`:
```typescript
const MAX_CACHED_COMPONENTS = 20;
const componentCache = new Map<string, SvelteComponent>();

async function getComponentForEvent(eventType: string): Promise<SvelteComponent> {
    // Check cache (LRU behavior)
    if (componentCache.has(eventType)) {
        const component = componentCache.get(eventType)!;
        // Move to end (most recently used)
        componentCache.delete(eventType);
        componentCache.set(eventType, component);
        return component;
    }

    // Load component
    const loader = componentLoaders[eventType];
    if (!loader) return GenericEvent;

    const module = await loader();

    // Enforce max size (evict oldest)
    if (componentCache.size >= MAX_CACHED_COMPONENTS) {
        const firstKey = componentCache.keys().next().value;
        if (firstKey) componentCache.delete(firstKey);
    }

    componentCache.set(eventType, module.default);
    return module.default;
}
```

#### 4.3 Feature Flags System (2-3 hours)

Update `bo1/config.py`:
```python
class Settings(BaseSettings):
    # ... existing fields

    # Feature Flags
    enable_context_collection: bool = Field(default=True)
    enable_llm_response_cache: bool = Field(default=False)
    enable_persona_selection_cache: bool = Field(default=False)
    enable_sse_streaming: bool = Field(default=False)  # vs polling
```

Update code to use flags:
```python
from bo1.config import get_settings

settings = get_settings()

if settings.enable_context_collection:
    context = await collect_context(user_id, problem)
```

#### 4.4 SSE Client Error Logging (30 min)

Update `frontend/src/lib/utils/sse.ts`:
```typescript
private cleanup(): void {
    if (this.reader) {
        this.reader.cancel().catch((error) => {
            console.warn('SSE reader cancellation failed:', error);
        });
        this.reader = null;
    }

    if (this.abortController) {
        try {
            this.abortController.abort();
        } catch (error) {
            console.warn('SSE abort controller error:', error);
        }
        this.abortController = null;
    }
}
```

#### 4.5 Event Deduplication Set Bounds (30 min)

Update `frontend/src/routes/(app)/meeting/[id]/+page.svelte`:
```typescript
const MAX_SEEN_EVENTS = 500;

function addEventKey(key: string) {
    seenEventKeys.add(key);

    // Prune if too large
    if (seenEventKeys.size > MAX_SEEN_EVENTS) {
        const keys = Array.from(seenEventKeys);
        seenEventKeys = new Set(keys.slice(-MAX_SEEN_EVENTS));
    }
}
```

#### 4.6 State Conversion Cache Bounds (2-3 hours)

Update `bo1/graph/state.py`:
```python
import time
from collections import OrderedDict

MAX_CACHE_ENTRIES = 100
CACHE_TTL_SECONDS = 300  # 5 minutes

_state_cache: OrderedDict[int, tuple[DeliberationState, float]] = OrderedDict()

def graph_state_to_deliberation_state(
    graph_state: DeliberationGraphState,
) -> DeliberationState:
    """Convert graph state with bounded LRU cache."""
    state_id = id(graph_state)
    now = time.time()

    # Check cache with TTL
    if state_id in _state_cache:
        cached_state, timestamp = _state_cache[state_id]
        if now - timestamp < CACHE_TTL_SECONDS:
            _cache_hits += 1
            # Move to end (LRU)
            _state_cache.move_to_end(state_id)
            return cached_state

    # Convert state
    v1_state = _convert_state_internal(graph_state)

    # Store with timestamp
    _state_cache[state_id] = (v1_state, now)

    # Evict oldest if over limit
    if len(_state_cache) > MAX_CACHE_ENTRIES:
        _state_cache.popitem(last=False)

    _cache_misses += 1
    return v1_state
```

Add tests:
```python
def test_cache_eviction():
    """Test cache respects max size limit."""
    # Fill cache beyond limit
    for i in range(MAX_CACHE_ENTRIES + 10):
        state = create_test_state(i)
        graph_state_to_deliberation_state(state)

    # Cache should not exceed max size
    assert len(_state_cache) <= MAX_CACHE_ENTRIES
```

#### 4.7 Rate Limiting on Auth Endpoints (3-4 hours)

Create `backend/api/middleware/rate_limit.py`:
```python
from fastapi import Request, HTTPException
from time import time
from collections import defaultdict

class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, requests_per_minute: int = 10):
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[float]] = defaultdict(list)

    def check_rate_limit(self, key: str) -> None:
        """Check if key exceeds rate limit."""
        now = time()
        window_start = now - 60

        # Remove old requests
        self.requests[key] = [
            ts for ts in self.requests[key]
            if ts > window_start
        ]

        # Check limit
        if len(self.requests[key]) >= self.requests_per_minute:
            retry_after = 60 - (now - self.requests[key][0])
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {retry_after:.0f} seconds.",
                headers={"Retry-After": str(int(retry_after))},
            )

        self.requests[key].append(now)

auth_rate_limiter = RateLimiter(requests_per_minute=5)
```

Apply to auth endpoints:
```python
@router.post("/auth/signin")
async def signin(request: Request, ...):
    client_ip = request.client.host
    auth_rate_limiter.check_rate_limit(f"auth:{client_ip}")
    # ... rest of endpoint
```

#### Testing & Commit (2 hours)

Test each quick win individually, then commit all together:
```bash
git add -A
git commit -m "feat: implement 7 quick wins for stability and performance

1. Response compression validation - ensure GZip working
2. Component cache eviction - LRU with max 20 components
3. Feature flags system - runtime configuration toggles
4. SSE client error logging - better debugging
5. Event deduplication bounds - max 500 seen events
6. State conversion cache bounds - LRU with TTL
7. Rate limiting on auth - prevent brute force (5 req/min)

Impact:
- Bounded memory usage (prevents leaks)
- Better observability (logging + metrics)
- Security improvement (rate limiting)
- Runtime configuration (feature flags)

Total effort: ~10-15 hours
Total impact: High (collectively addresses multiple pain points)"
```

#### Acceptance Criteria
- [ ] All 7 quick wins implemented
- [ ] Tests added for each feature
- [ ] `make pre-commit` passing
- [ ] No regressions in existing tests
- [ ] Documentation updated for feature flags

---

## Continued in SPRINT_IMPLEMENTATION_PLAN_WEEK2.md...

(Due to length, Week 2 tasks will be in a separate document)

---

## Daily Schedule Summary

### Week 1

| Day | Focus | Hours | Tasks |
|-----|-------|-------|-------|
| 1 (Mon) | Foundation | 4-5h | Test fixes (1-2h) + LLM cache start (2-3h) |
| 2 (Tue) | Caching | 4-5h | LLM cache finish (2-3h) + Error handling start (2h) |
| 3 (Wed) | Standardization | 4h | Error handling complete (3-4h) |
| 4 (Thu) | Quick Wins Batch 1 | 5h | Items 4.1-4.4 |
| 5 (Fri) | Quick Wins Batch 2 | 5-6h | Items 4.5-4.7 + testing |
| **Total** | **Week 1** | **22-25h** | **4 major tasks** |

### Week 2

| Day | Focus | Hours | Tasks |
|-----|-------|-------|-------|
| 6 (Mon) | Refactoring | 4-6h | Event extractor pattern |
| 7 (Tue) | Observability | 4-6h | Metrics collection |
| 8 (Wed) | Advanced Caching | 5-7h | Persona selection cache |
| 9 (Thu) | Integration | 3-4h | Testing + validation |
| 10 (Fri) | Polish | 2-3h | Documentation + retrospective |
| **Total** | **Week 2** | **18-26h** | **4 major tasks** |

**Grand Total:** 40-51 hours over 10 days

---

## Risk Management

### High-Risk Items

1. **LLM Response Caching**
   - Risk: Serving stale responses
   - Mitigation: 24-hour TTL, feature flag to disable
   - Rollback: Set `ENABLE_LLM_RESPONSE_CACHE=false`

2. **Persona Selection Caching**
   - Risk: Wrong personas selected due to high similarity threshold
   - Mitigation: Start with 0.90 threshold, monitor accuracy
   - Rollback: Set `ENABLE_PERSONA_SELECTION_CACHE=false`

3. **Event Extractor Refactoring**
   - Risk: Breaking event processing
   - Mitigation: Comprehensive tests before/after
   - Rollback: Git revert commit

### Medium-Risk Items

1. **Error Handling Decorator**
   - Risk: Changing API error responses (breaking clients)
   - Mitigation: Maintain same status codes, only standardize messages
   - Rollback: Revert decorator, restore try/except blocks

2. **Metrics Collection**
   - Risk: Performance overhead from metrics tracking
   - Mitigation: Lightweight counters/histograms only
   - Rollback: Remove metrics calls

### Communication Plan

- **Daily standups:** 15 min review of progress + blockers
- **Blocker escalation:** Immediate notification if >2 hours stuck
- **Code reviews:** All tasks reviewed before merge
- **Sprint demos:** Friday Week 1 + Friday Week 2

---

## Success Metrics

### Quantitative Targets

- [ ] Test coverage: 41% → 60%+
- [ ] LLM cost reduction: 60-70% (via caching)
- [ ] API error consistency: 95%+ endpoints standardized
- [ ] Code reduction: 300+ lines removed
- [ ] Cache hit rates: LLM 60%+, Personas 40%+

### Qualitative Targets

- [ ] Code maintainability improved (developer feedback)
- [ ] System observability enabled (metrics available)
- [ ] Configuration flexibility improved (feature flags)
- [ ] Error debugging easier (consistent logging)

---

## Post-Sprint Activities

### Retrospective (1 hour)

**Questions:**
1. What went well?
2. What could be improved?
3. What blockers were encountered?
4. Were estimates accurate?
5. What should we do next sprint?

### Follow-up Tasks

**High Priority:**
- Remaining medium-priority items from analysis
- SSE streaming implementation (6 days)
- Database composite indexes

**Future Considerations:**
- Virtual scrolling for long event lists
- Database read replicas
- OpenAPI client generation

### Deployment Plan

**Staging Deployment (End of Week 1):**
- Deploy LLM caching + error handling
- Monitor metrics for 2-3 days
- Validate cost reduction

**Production Deployment (End of Week 2):**
- Full sprint features deployed
- Blue-green deployment strategy
- Monitor for 24 hours
- Rollback plan ready

---

## Appendix: Tool Commands Reference

### Testing
```bash
# Run all tests
make test

# Run specific test file
pytest tests/llm/test_cache.py -v

# Run with coverage
pytest --cov=bo1 --cov=backend --cov-report=html

# Check test collection
pytest --collect-only
```

### Quality Checks
```bash
# Pre-commit all checks
make pre-commit

# Individual checks
ruff check .
ruff format .
mypy bo1/ backend/
```

### Development
```bash
# Start services
make up

# View logs
make logs-api
make logs-frontend

# Shell access
make shell
make shell-frontend
```

### Git Workflow
```bash
# Create feature branch
git checkout -b sprint-optimizations

# Commit with conventional commits
git commit -m "feat: add LLM response caching"

# Push and create PR
git push origin sprint-optimizations
```

---

**End of Week 1 Plan**

**See SPRINT_IMPLEMENTATION_PLAN_WEEK2.md for Week 2 detailed breakdown**
