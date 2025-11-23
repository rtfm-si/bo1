# Board of One - Refactoring Analysis
**Date:** 2025-01-23
**Sprint:** Week 8 (Optimization Sprint Completion)
**Scope:** Priority 1 (Sprint Code) + Priority 2 (Related Core Code)

---

## Executive Summary

This analysis identifies **12 high-impact refactoring opportunities** across the Board of One codebase after completing the 2-week optimization sprint. The focus is on eliminating duplication, improving consistency, and enhancing maintainability while preserving all functionality.

**Key Findings:**
- **3 cache pattern duplications** requiring extraction to base class
- **2 database safety issues** needing standardization
- **4 consistency gaps** across error handling and metrics
- **3 performance improvements** in caching and connection management

**Estimated Impact:**
- **~300 lines of code reduction** through DRY principles
- **Type safety improvements** via better type hints
- **Reduced maintenance burden** through standardized patterns
- **Zero functional changes** - purely structural improvements

---

## High-Priority Refactorings (Must Do)

### REFACTOR #1: Extract Base Semantic Cache Class

**Category:** Code Duplication (Critical)
**Priority:** HIGH
**Impact:** -150 lines, improved maintainability, single source of truth for caching logic
**Effort:** 2-3 hours

**Problem:**

Three cache implementations share nearly identical patterns:
- `bo1/llm/cache.py` - LLMResponseCache (deterministic key-based)
- `bo1/agents/persona_cache.py` - PersonaSelectionCache (semantic similarity-based)
- `bo1/agents/researcher.py` - ResearcherAgent (semantic similarity-based with PostgreSQL)

**Code Duplication:**

All three have:
```python
# Identical statistics tracking
self._hits = 0
self._misses = 0

@property
def hit_rate(self) -> float:
    total = self._hits + self._misses
    return self._hits / total if total > 0 else 0.0

def get_stats(self) -> dict[str, Any]:
    return {
        "enabled": self.enabled,
        "hits": self._hits,
        "misses": self._misses,
        "hit_rate": self.hit_rate,
        "ttl_seconds": self.ttl_seconds,
    }
```

**Solution:**

Create `bo1/llm/base_cache.py`:

```python
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar("T")  # Cache value type
K = TypeVar("K")  # Cache key type

class BaseCache(ABC, Generic[K, T]):
    """Base class for all cache implementations.

    Provides:
    - Hit/miss tracking
    - Statistics calculation
    - Common configuration (enabled, TTL)
    - Abstract methods for get/set operations
    """

    def __init__(
        self,
        redis_manager: Any,
        enabled: bool,
        ttl_seconds: int,
    ) -> None:
        self.redis = redis_manager.redis
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

    @abstractmethod
    async def get(self, key: K) -> T | None:
        """Get cached value. Must update hit/miss counters."""
        pass

    @abstractmethod
    async def set(self, key: K, value: T) -> None:
        """Set cached value with TTL."""
        pass

    def _record_hit(self) -> None:
        """Record cache hit."""
        self._hits += 1

    def _record_miss(self) -> None:
        """Record cache miss."""
        self._misses += 1

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate (0.0-1.0)."""
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
```

Then inherit:
```python
# cache.py
class LLMResponseCache(BaseCache[PromptRequest, LLMResponse]):
    async def get(self, key: PromptRequest) -> LLMResponse | None:
        if not self.enabled:
            return None
        # ... existing logic ...
        if cached_json:
            self._record_hit()
            return LLMResponse.model_validate_json(cached_json)
        self._record_miss()
        return None

# persona_cache.py
class PersonaSelectionCache(BaseCache[SubProblem, list[PersonaProfile]]):
    # Similar pattern
```

**Files Changed:**
- NEW: `bo1/llm/base_cache.py`
- MODIFIED: `bo1/llm/cache.py`
- MODIFIED: `bo1/agents/persona_cache.py`
- MODIFIED: `bo1/agents/researcher.py`

**Tests Required:**
- Unit tests for BaseCache (abstract methods, hit/miss tracking)
- Verify existing cache tests still pass with inheritance

---

### REFACTOR #2: Standardize Database Interval Filters

**Category:** Bug Fix / Consistency
**Priority:** HIGH
**Impact:** Prevents SQL injection, eliminates duplication, safer code
**Effort:** 1-2 hours

**Problem:**

`postgres_manager.py` has **inconsistent interval filter handling**:

```python
# Line 340 - Uses SafeQueryBuilder (CORRECT)
from bo1.utils.sql_safety import SafeQueryBuilder
builder.add_interval_filter("research_date", max_age_days)

# Line 341 - Raw f-string (POTENTIAL INJECTION)
query += " AND research_date >= NOW() - (freshness_days || ' days')::interval"
```

**Solution:**

1. Always use `SafeQueryBuilder` for interval filters
2. Extract common patterns to helper functions

```python
def _build_freshness_filter(
    category: str | None,
    industry: str | None,
    max_age_days: int | None,
) -> tuple[str, list[Any]]:
    """Build safe WHERE clause for research cache freshness.

    Returns:
        (query_fragment, params) - Safe SQL with parameterized values
    """
    builder = SafeQueryBuilder("WHERE 1=1")

    if category:
        builder.add_filter("category", category)

    if industry:
        builder.add_filter("industry", industry)

    if max_age_days:
        builder.add_interval_filter("research_date", max_age_days)
    else:
        # Use database column value for freshness
        builder.query += " AND research_date >= NOW() - (freshness_days || ' days')::interval"

    return builder.build()
```

**Files Changed:**
- `bo1/state/postgres_manager.py` (find_cached_research, get_stale_research_cache_entries)

**Tests Required:**
- Test interval filters with various day values
- Verify protection against SQL injection attempts

---

### REFACTOR #3: Consolidate Cache Configuration

**Category:** DRY Violation
**Priority:** HIGH
**Impact:** Single source of truth for cache settings, easier configuration
**Effort:** 1 hour

**Problem:**

Cache configuration is scattered across three files with hardcoded values:

```python
# llm/cache.py
self.enabled = get_settings().enable_llm_response_cache
self.ttl_seconds = get_settings().llm_response_cache_ttl_seconds

# agents/persona_cache.py
self.enabled = get_settings().enable_persona_selection_cache
self.similarity_threshold = 0.90  # HARDCODED
self.ttl_seconds = 7 * 24 * 60 * 60  # HARDCODED

# agents/researcher.py
freshness_map = {  # HARDCODED
    "saas_metrics": 90,
    "pricing": 180,
    # ...
}
```

**Solution:**

Centralize in `bo1/config.py`:

```python
@dataclass
class CacheConfig:
    """Configuration for all cache implementations."""

    # LLM Response Cache
    llm_cache_enabled: bool = True
    llm_cache_ttl_seconds: int = 24 * 60 * 60  # 24 hours

    # Persona Selection Cache
    persona_cache_enabled: bool = True
    persona_cache_similarity_threshold: float = 0.90
    persona_cache_ttl_seconds: int = 7 * 24 * 60 * 60  # 7 days

    # Research Cache
    research_cache_similarity_threshold: float = 0.85
    research_cache_freshness_map: dict[str, int] = field(default_factory=lambda: {
        "saas_metrics": 90,
        "pricing": 180,
        "competitor_analysis": 30,
        "market_trends": 60,
        "regulations": 365,
    })
    research_cache_default_freshness_days: int = 90

class Settings(BaseSettings):
    # ... existing fields ...

    cache: CacheConfig = CacheConfig()
```

Then reference:
```python
# persona_cache.py
self.similarity_threshold = get_settings().cache.persona_cache_similarity_threshold
```

**Files Changed:**
- `bo1/config.py`
- `bo1/llm/cache.py`
- `bo1/agents/persona_cache.py`
- `bo1/agents/researcher.py`

---

### REFACTOR #4: Extract Event Extractor Factory Pattern

**Category:** Consistency / Maintainability
**Priority:** MEDIUM-HIGH
**Impact:** Easier to add new event types, clearer pattern
**Effort:** 1-2 hours

**Problem:**

`event_extractors.py` has scattered extractor configurations with inconsistent patterns:

```python
# Some use simple field mapping
DECOMPOSITION_EXTRACTORS: list[FieldExtractor] = [...]

# Some use factory functions
def _create_facilitator_decision_extractors() -> list[FieldExtractor]:
    # Complex logic
    pass

FACILITATOR_DECISION_EXTRACTORS = _create_facilitator_decision_extractors()
```

**Solution:**

Create a registry pattern:

```python
class EventExtractorRegistry:
    """Central registry for event data extractors."""

    def __init__(self) -> None:
        self._extractors: dict[str, list[FieldExtractor]] = {}

    def register(
        self,
        event_type: str,
        extractors: list[FieldExtractor] | Callable[[], list[FieldExtractor]]
    ) -> None:
        """Register extractors for an event type."""
        if callable(extractors):
            extractors = extractors()
        self._extractors[event_type] = extractors

    def get(self, event_type: str) -> list[FieldExtractor]:
        """Get extractors for event type."""
        return self._extractors.get(event_type, [])

    def extract(self, event_type: str, output: dict[str, Any]) -> dict[str, Any]:
        """Extract data for event type."""
        extractors = self.get(event_type)

        # Handle special __root__ extractors
        if extractors and extractors[0].get("source_field") == "__root__":
            return extract_with_root_transform(output, extractors)

        return extract_event_data(output, extractors)

# Create global registry
registry = EventExtractorRegistry()

# Register all extractors
registry.register("decomposition", DECOMPOSITION_EXTRACTORS)
registry.register("persona_selection", PERSONA_SELECTION_EXTRACTORS)
registry.register("facilitator_decision", _create_facilitator_decision_extractors)
# ... etc
```

Usage:
```python
# streaming.py
data = registry.extract("decomposition", output)
```

**Files Changed:**
- `backend/api/event_extractors.py`
- `backend/api/streaming.py` (usage)

---

## Medium-Priority Refactorings (Should Do)

### REFACTOR #5: Improve Type Safety in Metrics Collection

**Category:** Type Safety
**Priority:** MEDIUM
**Impact:** Better IDE support, catch errors at development time
**Effort:** 30 minutes

**Problem:**

`metrics.py` uses `defaultdict` which loses type information:

```python
counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
histograms: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
```

Type checkers can't verify counter increment logic.

**Solution:**

Use explicit dict with `.get()` default:

```python
from dataclasses import dataclass, field

@dataclass
class MetricsCollector:
    counters: dict[str, int] = field(default_factory=dict)
    histograms: dict[str, list[float]] = field(default_factory=dict)

    def increment(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + value

    def observe(self, name: str, value: float) -> None:
        if name not in self.histograms:
            self.histograms[name] = []
        self.histograms[name].append(value)
```

**Files Changed:**
- `backend/api/metrics.py`

**Tests Required:**
- Verify increment/observe still work correctly
- Run mypy to confirm type checking improvements

---

### REFACTOR #6: Consolidate Singleton Patterns

**Category:** Consistency
**Priority:** MEDIUM
**Impact:** Consistent pattern across codebase
**Effort:** 1 hour

**Problem:**

Multiple singleton patterns used inconsistently:

```python
# llm/cache.py - Global variable pattern
_cache_instance: LLMResponseCache | None = None

def get_llm_cache() -> LLMResponseCache:
    global _cache_instance
    if _cache_instance is None:
        from bo1.state.redis_manager import RedisManager
        _cache_instance = LLMResponseCache(RedisManager())
    return _cache_instance

# agents/persona_cache.py - Same pattern (duplicated)
_persona_cache: PersonaSelectionCache | None = None

def get_persona_cache() -> PersonaSelectionCache:
    # Identical logic
```

**Solution:**

Extract to base pattern or use functools:

```python
# utils/singleton.py
from functools import wraps
from typing import Callable, TypeVar

T = TypeVar("T")

def singleton(factory: Callable[[], T]) -> Callable[[], T]:
    """Decorator to create thread-safe singleton."""
    instance: T | None = None

    @wraps(factory)
    def get_instance() -> T:
        nonlocal instance
        if instance is None:
            instance = factory()
        return instance

    return get_instance

# Usage
@singleton
def get_llm_cache() -> LLMResponseCache:
    from bo1.state.redis_manager import RedisManager
    return LLMResponseCache(RedisManager())

@singleton
def get_persona_cache() -> PersonaSelectionCache:
    from bo1.state.redis_manager import RedisManager
    return PersonaSelectionCache(RedisManager())
```

**Files Changed:**
- NEW: `bo1/utils/singleton.py`
- `bo1/llm/cache.py`
- `bo1/agents/persona_cache.py`

---

### REFACTOR #7: Add Type Hints to db_session() Context Manager

**Category:** Type Safety
**Priority:** MEDIUM
**Impact:** Better IDE autocomplete, type checking
**Effort:** 15 minutes

**Problem:**

```python
@contextmanager
def db_session() -> Any:  # Too generic
    """Context manager for database transactions."""
    pool_instance = get_connection_pool()
    conn = pool_instance.getconn()
    # ...
```

**Solution:**

```python
from typing import Generator
from psycopg2.extensions import connection

@contextmanager
def db_session() -> Generator[connection, None, None]:
    """Context manager for database transactions.

    Yields:
        PostgreSQL connection from pool
    """
    pool_instance = get_connection_pool()
    conn: connection = pool_instance.getconn()

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool_instance.putconn(conn)
```

**Files Changed:**
- `bo1/state/postgres_manager.py`

---

### REFACTOR #8: Standardize Logging Patterns

**Category:** Consistency
**Priority:** MEDIUM
**Impact:** Easier debugging, consistent log format
**Effort:** 1-2 hours

**Problem:**

Inconsistent logging across cache implementations:

```python
# llm/cache.py
logger.info(f"LLM cache hit: {cache_key} (hit_rate={self.hit_rate:.1%})")

# persona_cache.py
logger.info(
    f"✓ Persona cache hit (similarity={best_similarity:.3f}, "
    f"threshold={self.similarity_threshold})"
)

# researcher.py
logger.info(f"✓ Cache hit for '{question[:50]}...' (age: {age_days} days, cost: ${embedding_cost:.6f})")
```

Different formats, different emoji usage, different detail levels.

**Solution:**

Create structured logging helper:

```python
# utils/logging_helpers.py
import logging
from typing import Any

def log_cache_event(
    logger: logging.Logger,
    event_type: str,
    cache_type: str,
    **kwargs: Any,
) -> None:
    """Structured logging for cache events.

    Args:
        event_type: "hit" | "miss" | "write"
        cache_type: "llm" | "persona" | "research"
        **kwargs: Additional context (hit_rate, similarity, cost, etc.)
    """
    if event_type == "hit":
        emoji = "✓"
        level = logging.INFO
    elif event_type == "miss":
        emoji = "×"
        level = logging.DEBUG
    else:  # write
        emoji = "💾"
        level = logging.DEBUG

    # Format consistent message
    details = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    message = f"{emoji} {cache_type.upper()} cache {event_type}"
    if details:
        message += f" ({details})"

    logger.log(level, message, extra={"cache_type": cache_type, "event": event_type, **kwargs})
```

Usage:
```python
# cache.py
log_cache_event(logger, "hit", "llm", hit_rate=f"{self.hit_rate:.1%}")

# persona_cache.py
log_cache_event(logger, "hit", "persona", similarity=f"{best_similarity:.3f}")
```

**Files Changed:**
- NEW: `bo1/utils/logging_helpers.py`
- `bo1/llm/cache.py`
- `bo1/agents/persona_cache.py`
- `bo1/agents/researcher.py`

---

## Low-Priority Refactorings (Nice to Have)

### REFACTOR #9: Extract Common Agent Patterns to BaseAgent

**Category:** DRY
**Priority:** LOW
**Impact:** Reduced duplication in agent implementations
**Effort:** 2-3 hours

**Problem:**

`selector.py` and other agents duplicate LLM calling patterns:

```python
# All agents do this
response = await self._create_and_call_prompt(
    system=SELECTOR_SYSTEM_PROMPT,
    user_message=user_message,
    phase="selection",
    prefill="{",
    cache_system=False,
)
```

But each agent reimplements error handling, JSON parsing, fallbacks.

**Solution:**

Enhance `BaseAgent` with common patterns:

```python
# agents/base.py
class BaseAgent:
    async def call_with_json_response(
        self,
        system: str,
        user_message: str,
        phase: str,
        fallback: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], LLMResponse]:
        """Call LLM expecting JSON response with automatic fallback.

        Returns:
            (parsed_json, llm_response)
        """
        response = await self._create_and_call_prompt(
            system=system,
            user_message=user_message,
            phase=phase,
            prefill="{",
            **kwargs,
        )

        try:
            data = json.loads(response.content)
            return data, response
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error in {phase}: {e}")
            if fallback is not None:
                response.content = json.dumps(fallback)
                return fallback, response
            raise
```

**Files Changed:**
- `bo1/agents/base.py`
- `bo1/agents/selector.py`
- Other agent implementations

---

### REFACTOR #10: Extract Common Test Fixtures

**Category:** Test Maintainability
**Priority:** LOW
**Impact:** Easier to write new tests, reduced test code duplication
**Effort:** 1-2 hours

**Problem:**

Test files likely duplicate fixture setup for:
- Mock Redis connections
- Mock database connections
- Sample SubProblems
- Sample PersonaProfiles
- Mock LLM responses

**Solution:**

Create `tests/conftest.py` with shared fixtures:

```python
# tests/conftest.py
import pytest
from bo1.models.problem import SubProblem
from bo1.models.persona import PersonaProfile

@pytest.fixture
def sample_sub_problem() -> SubProblem:
    """Sample sub-problem for testing."""
    return SubProblem(
        id="sp_test_001",
        goal="Should we invest $50K in SEO or paid ads?",
        context="Solo founder, SaaS product, $100K ARR",
        complexity_score=6,
    )

@pytest.fixture
def sample_personas() -> list[PersonaProfile]:
    """Sample persona list for testing."""
    return [
        PersonaProfile(code="finance_strategist", name="Maria Santos", ...),
        PersonaProfile(code="growth_hacker", name="Zara Morales", ...),
    ]

@pytest.fixture
def mock_redis_manager(mocker):
    """Mock RedisManager with in-memory dict."""
    # Implementation
```

**Files Changed:**
- NEW: `tests/conftest.py`
- Various test files (simplify with shared fixtures)

---

### REFACTOR #11: Add Docstring Consistency

**Category:** Documentation
**Priority:** LOW
**Impact:** Better code understanding, easier onboarding
**Effort:** 2-3 hours

**Problem:**

Docstring quality varies across files:
- Some have full examples (good)
- Some missing return type documentation
- Some missing examples
- Inconsistent format (Google style vs NumPy style)

**Solution:**

Standardize on Google-style docstrings with examples:

```python
def function_name(arg1: str, arg2: int = 5) -> dict[str, Any]:
    """Brief one-line description.

    Longer description with additional context about when to use
    this function and any important caveats.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2 (default: 5)

    Returns:
        Description of return value with structure:
        {
            "key1": value1 description,
            "key2": value2 description,
        }

    Raises:
        ValueError: When arg1 is empty
        KeyError: When required key missing

    Examples:
        >>> result = function_name("test", 10)
        >>> print(result["key1"])
        value1
    """
```

Run through all new sprint code and ensure consistency.

**Files Changed:**
- All Priority 1 files

---

### REFACTOR #12: Performance - Add @lru_cache to Pure Functions

**Category:** Performance
**Priority:** LOW
**Impact:** Minor speedup for frequently called pure functions
**Effort:** 30 minutes

**Problem:**

Some functions are called repeatedly with same inputs but don't cache:

```python
# event_extractors.py
def to_dict_list(items: list[Any]) -> list[dict[str, Any]]:
    """Convert list of Pydantic models to list of dicts."""
    return [item.model_dump() if hasattr(item, "model_dump") else item for item in items]
```

Not a pure function (modifies input), but similar patterns exist.

**Solution:**

Identify truly pure functions (no side effects, deterministic) and add caching:

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def calculate_consensus_level(avg_confidence: float) -> str:
    """Calculate consensus level from confidence.

    Pure function - safe to cache.
    """
    if avg_confidence >= 0.8:
        return "strong"
    elif avg_confidence >= 0.6:
        return "moderate"
    else:
        return "weak"
```

**Files Changed:**
- Identify candidates across codebase
- Add `@lru_cache` where appropriate

---

## Implementation Plan

### Phase 1: Critical Fixes (Day 1)
1. REFACTOR #2: Standardize database interval filters (SQL injection fix)
2. REFACTOR #1: Extract base semantic cache class (major DRY improvement)
3. Run tests after each refactoring

### Phase 2: High-Value Improvements (Day 2)
4. REFACTOR #3: Consolidate cache configuration
5. REFACTOR #4: Event extractor factory pattern
6. REFACTOR #5: Improve type safety in metrics
7. Run full test suite

### Phase 3: Consistency Improvements (Day 3)
8. REFACTOR #6: Consolidate singleton patterns
9. REFACTOR #7: Add type hints to db_session()
10. REFACTOR #8: Standardize logging patterns
11. Run pre-commit checks

### Phase 4: Nice-to-Haves (If Time Permits)
12. REFACTOR #9-12: Lower priority improvements

---

## Success Criteria

- [ ] All existing tests pass
- [ ] `make pre-commit` passes (lint + format + typecheck)
- [ ] No functional behavior changes
- [ ] Code coverage maintained or improved
- [ ] Documentation updated where needed

---

## Risk Mitigation

1. **One refactoring per commit** - Easy rollback if issues
2. **Run tests after EVERY change** - Catch regressions immediately
3. **Start with HIGH priority** - Most impact first
4. **Stop if tests fail** - Don't proceed until fixed
5. **Document all changes** - Clear commit messages

---

## Metrics

**Before Refactoring:**
- Lines of code (Priority 1): ~1,500
- Duplication: ~300 lines duplicated across caches
- Type coverage: ~85% (estimated)
- Test count: (run `pytest --collect-only`)

**After Refactoring (Target):**
- Lines of code: ~1,200 (-300 through DRY)
- Duplication: <50 lines
- Type coverage: ~95%
- Test count: Same or higher (no tests removed)

---

## Next Steps

1. Review this analysis with team
2. Get approval for high-priority refactorings
3. Create feature branch: `refactor/sprint-consolidation`
4. Begin Phase 1 implementation
5. Document each refactoring in commit messages
6. Generate final summary report after completion
