# Sprint Implementation Plan - Week 2

**Continuation of 2-Week Optimization Sprint**

See `SPRINT_IMPLEMENTATION_PLAN.md` for Week 1 tasks and overall sprint structure.

---

## Week 2 Overview

**Focus:** Complex refactoring, monitoring infrastructure, and advanced caching

**Total Effort:** 18-26 hours over 5 days

**Key Deliverables:**
- Event extractor pattern refactoring (32% code reduction)
- System metrics collection infrastructure
- Persona selection semantic caching
- Sprint validation and documentation

---

## [TASK 5] Refactor Event Extractor Pattern

**Priority:** Critical (Code quality)
**Effort:** 4-6 hours
**Day:** Day 6 (Monday, Week 2)
**Dependencies:** None

### Objective

Refactor 25 event extractor functions in `backend/api/event_collector.py` to eliminate duplication and reduce file from 884 lines to ~600 lines (32% reduction).

### Success Criteria

- [ ] File size reduced by 30-40% (884 → 600 lines)
- [ ] All 25 extractors follow uniform pattern
- [ ] Extraction logic testable in isolation
- [ ] No changes to event data structure
- [ ] All existing tests passing
- [ ] New tests for extraction utilities

### Implementation Steps

#### 1. Analysis Phase (1 hour)

**Analyze existing extractors:**
```bash
cd /Users/si/projects/bo1
# Count extractor functions
grep -c "^def _extract_" backend/api/event_collector.py

# Identify common patterns
grep -A 10 "^def _extract_" backend/api/event_collector.py | head -50

# Calculate current file size
wc -l backend/api/event_collector.py
```

**Document patterns:**
- All extractors take `output: dict[str, Any]`
- All return `dict[str, Any]`
- Common operations:
  - `output.get("field")`
  - `hasattr(obj, "field")` vs `isinstance(obj, dict)`
  - `.model_dump()` conversion
  - List comprehensions for collections

#### 2. Design Generic Extraction Framework (1 hour)

Create `backend/api/event_extractors.py`:
```python
"""Generic event data extraction framework."""
from typing import Any, Callable, TypedDict


class FieldExtractor(TypedDict, total=False):
    """Configuration for extracting a field from event output.

    Attributes:
        source_field: Key in output dict to extract from
        target_field: Key in result dict to store value
        transform: Optional function to transform extracted value
        default: Default value if source field missing
        required: Whether field is required (raises error if missing)
    """
    source_field: str
    target_field: str
    transform: Callable[[Any], Any]
    default: Any
    required: bool


def extract_event_data(
    output: dict[str, Any],
    extractors: list[FieldExtractor],
) -> dict[str, Any]:
    """Extract event data using field extractor configurations.

    Args:
        output: Raw node output dictionary
        extractors: List of field extraction configs

    Returns:
        Extracted event data dictionary

    Raises:
        KeyError: If required field is missing

    Example:
        extractors = [
            {
                "source_field": "problem",
                "target_field": "sub_problems",
                "transform": extract_sub_problems,
            },
        ]
        data = extract_event_data(output, extractors)
    """
    result = {}

    for extractor in extractors:
        source = extractor["source_field"]
        target = extractor["target_field"]
        required = extractor.get("required", False)
        default = extractor.get("default")

        # Extract value
        value = output.get(source, default)

        # Check required
        if required and value is None:
            raise KeyError(f"Required field '{source}' not found in output")

        # Apply transformation if provided
        if transform := extractor.get("transform"):
            value = transform(value)

        result[target] = value

    return result


# Transformation functions for common patterns
def to_dict_list(items: list[Any]) -> list[dict[str, Any]]:
    """Convert list of Pydantic models to list of dicts."""
    return [
        item.model_dump() if hasattr(item, "model_dump") else item
        for item in items
    ]


def get_field_safe(obj: Any, field: str, default: Any = None) -> Any:
    """Safely get field from object or dict."""
    if hasattr(obj, field):
        return getattr(obj, field)
    if isinstance(obj, dict):
        return obj.get(field, default)
    return default


def extract_sub_problems(problem: Any) -> list[dict[str, Any]]:
    """Extract sub-problems from Problem object."""
    if not problem:
        return []

    sub_problems = get_field_safe(problem, "sub_problems", [])
    return to_dict_list(sub_problems)


def extract_persona_codes(personas: list[Any]) -> list[str]:
    """Extract persona codes from persona objects."""
    return [
        get_field_safe(p, "code", "unknown")
        for p in personas
    ]


def extract_metrics_dict(metrics: Any) -> dict[str, Any]:
    """Extract metrics as dictionary."""
    if not metrics:
        return {}

    if hasattr(metrics, "model_dump"):
        return metrics.model_dump()

    return dict(metrics) if isinstance(metrics, dict) else {}
```

#### 3. Define Extractor Configurations (2 hours)

Add to `backend/api/event_extractors.py`:
```python
# Extractor configurations for each event type
DECOMPOSITION_EXTRACTORS: list[FieldExtractor] = [
    {
        "source_field": "problem",
        "target_field": "sub_problems",
        "transform": extract_sub_problems,
        "default": [],
    },
]

PERSONA_SELECTION_EXTRACTORS: list[FieldExtractor] = [
    {
        "source_field": "personas",
        "target_field": "personas",
        "transform": extract_persona_codes,
        "default": [],
    },
    {
        "source_field": "personas",
        "target_field": "count",
        "transform": lambda p: len(p) if p else 0,
        "default": 0,
    },
]

FACILITATOR_DECISION_EXTRACTORS: list[FieldExtractor] = [
    {
        "source_field": "action",
        "target_field": "action",
        "transform": lambda a: get_field_safe(a, "value", "unknown"),
        "required": True,
    },
    {
        "source_field": "action",
        "target_field": "reasoning",
        "transform": lambda a: get_field_safe(a, "reasoning", ""),
        "default": "",
    },
    {
        "source_field": "next_speaker",
        "target_field": "next_speaker",
        "default": None,
    },
]

# ... Continue for all 25 event types
```

#### 4. Refactor Extractor Functions (1 hour)

Update `backend/api/event_collector.py`:
```python
from backend.api.event_extractors import (
    extract_event_data,
    DECOMPOSITION_EXTRACTORS,
    PERSONA_SELECTION_EXTRACTORS,
    # ... import all configs
)

# OLD (37 lines)
def _extract_decomposition_data(output: dict[str, Any]) -> dict[str, Any]:
    """Extract decomposition event data."""
    problem = output.get("problem")
    sub_problems_dicts = []

    if problem and hasattr(problem, "sub_problems"):
        sub_problems = problem.sub_problems
        for sp in sub_problems:
            if isinstance(sp, SubProblem):
                sp_dict = sp.model_dump()
            elif isinstance(sp, dict):
                sp_dict = sp
            else:
                continue
            sub_problems_dicts.append(sp_dict)

    return {
        "sub_problems": sub_problems_dicts,
        "count": len(sub_problems_dicts),
    }

# NEW (3 lines)
def _extract_decomposition_data(output: dict[str, Any]) -> dict[str, Any]:
    """Extract decomposition event data."""
    return extract_event_data(output, DECOMPOSITION_EXTRACTORS)
```

Refactor all 25 extractors to use this pattern.

**Expected reduction:**
- Average extractor: 20-30 lines → 3-5 lines
- Total: ~600 lines → ~200 lines
- Net savings: ~400 lines in event_collector.py
- New file event_extractors.py: ~300 lines
- **Total savings: ~100 lines + better organization**

#### 5. Testing (1.5 hours)

Create `tests/api/test_event_extractors.py`:
```python
import pytest
from backend.api.event_extractors import (
    extract_event_data,
    to_dict_list,
    get_field_safe,
    extract_sub_problems,
    DECOMPOSITION_EXTRACTORS,
)
from bo1.models.problem import Problem, SubProblem


def test_extract_event_data_basic():
    """Test basic field extraction."""
    extractors = [
        {
            "source_field": "name",
            "target_field": "extracted_name",
        },
        {
            "source_field": "age",
            "target_field": "extracted_age",
            "default": 0,
        },
    ]

    output = {"name": "test", "other": "ignored"}
    result = extract_event_data(output, extractors)

    assert result["extracted_name"] == "test"
    assert result["extracted_age"] == 0


def test_extract_event_data_with_transform():
    """Test extraction with transformation."""
    extractors = [
        {
            "source_field": "value",
            "target_field": "doubled",
            "transform": lambda x: x * 2,
        },
    ]

    output = {"value": 5}
    result = extract_event_data(output, extractors)

    assert result["doubled"] == 10


def test_extract_event_data_required_field():
    """Test required field validation."""
    extractors = [
        {
            "source_field": "required_field",
            "target_field": "output",
            "required": True,
        },
    ]

    output = {}  # Missing required field

    with pytest.raises(KeyError):
        extract_event_data(output, extractors)


def test_to_dict_list():
    """Test Pydantic model to dict conversion."""
    sub_problem = SubProblem(
        statement="Test problem",
        goal="Test goal",
        context="Test context",
        complexity_score=3,
    )

    result = to_dict_list([sub_problem])

    assert len(result) == 1
    assert result[0]["statement"] == "Test problem"
    assert isinstance(result[0], dict)


def test_get_field_safe_object():
    """Test safe field extraction from object."""
    class TestObj:
        field = "value"

    obj = TestObj()
    result = get_field_safe(obj, "field")

    assert result == "value"


def test_get_field_safe_dict():
    """Test safe field extraction from dict."""
    data = {"field": "value"}
    result = get_field_safe(data, "field")

    assert result == "value"


def test_extract_sub_problems():
    """Test sub-problem extraction."""
    problem = Problem(
        statement="Main problem",
        goal="Main goal",
        context="Context",
        sub_problems=[
            SubProblem(
                statement="Sub 1",
                goal="Goal 1",
                context="Context 1",
                complexity_score=2,
            ),
        ],
    )

    output = {"problem": problem}
    result = extract_event_data(output, DECOMPOSITION_EXTRACTORS)

    assert "sub_problems" in result
    assert len(result["sub_problems"]) == 1
    assert result["sub_problems"][0]["statement"] == "Sub 1"


@pytest.mark.parametrize("extractor_name,config", [
    ("decomposition", DECOMPOSITION_EXTRACTORS),
    ("persona_selection", PERSONA_SELECTION_EXTRACTORS),
    # ... test all 25 extractor configs
])
def test_all_extractors(extractor_name, config):
    """Smoke test all extractor configurations."""
    # Ensure config is valid
    assert isinstance(config, list)
    assert len(config) > 0

    for extractor in config:
        assert "source_field" in extractor
        assert "target_field" in extractor
```

Run tests:
```bash
pytest tests/api/test_event_extractors.py -v
```

#### 6. Update Event Collector (30 min)

Update all handler methods in `backend/api/event_collector.py`:
```python
async def _handle_decomposition(self, session_id: str, output: dict) -> None:
    """Handle decomposition node completion."""
    await self._publish_node_event(
        session_id,
        output,
        "decomposition_complete",
        _extract_decomposition_data,  # Uses new framework
    )

# Repeat for all 25 handlers
```

#### 7. Validation & Commit (1 hour)

**Validation checklist:**
```bash
# Run all tests
make test

# Check file sizes
wc -l backend/api/event_collector.py  # Should be ~600 lines
wc -l backend/api/event_extractors.py  # Should be ~300 lines

# Run pre-commit
make pre-commit

# Manual smoke test
make up
# Trigger deliberation, verify events still publish correctly
```

**Commit:**
```bash
git add backend/api/event_extractors.py backend/api/event_collector.py tests/api/test_event_extractors.py
git commit -m "refactor: extract event data extraction to generic framework

- Create event_extractors.py with generic extraction framework
- Define extractor configurations for all 25 event types
- Refactor all _extract_* functions to use framework
- Add comprehensive tests for extraction utilities

Code Reduction:
- event_collector.py: 884 → 600 lines (32% reduction)
- New event_extractors.py: 300 lines
- Net savings: 100 lines + better organization

Benefits:
- Single source of truth for extraction patterns
- Easier to test extraction logic in isolation
- Consistent error handling across all extractors
- Simple to add new event types (just add config)

Testing:
- 15 new tests for extraction framework
- All 25 extractor configs validated
- All existing tests passing"
```

### Files Modified
- `backend/api/event_extractors.py` - New extraction framework
- `backend/api/event_collector.py` - Refactored extractors
- `tests/api/test_event_extractors.py` - New tests

### Potential Issues
- **Breaking changes:** Extraction logic could change subtly
  - *Mitigation:* Comprehensive tests, manual validation
- **Import complexity:** New module adds import overhead
  - *Mitigation:* Minimal - just one import per extractor

### Acceptance Criteria
- [ ] 884 → 600 line reduction in event_collector.py
- [ ] All 25 extractors use generic framework
- [ ] 15+ new tests passing
- [ ] All existing tests passing
- [ ] `make pre-commit` passing

---

## [TASK 6] Add Metrics Collection Infrastructure

**Priority:** Medium (Enables optimization)
**Effort:** 4-6 hours
**Day:** Day 7 (Tuesday, Week 2)
**Dependencies:** None

### Objective

Implement lightweight metrics collection system to track API performance, LLM usage, cache hit rates, and system health.

### Success Criteria

- [ ] Metrics endpoint available at `/api/metrics`
- [ ] Key metrics tracked (API latency, LLM calls, cache hits)
- [ ] Minimal performance overhead (<1ms per request)
- [ ] Metrics exportable to JSON
- [ ] Ready for Prometheus integration (future)

### Implementation Steps

#### 1. Design Metrics System (1 hour)

Create `backend/api/metrics.py`:
```python
"""Lightweight metrics collection system."""
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricsCollector:
    """In-memory metrics collector with counters and histograms.

    Thread-safe for concurrent access (uses basic dict operations).
    """
    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    histograms: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter metric.

        Args:
            name: Metric name (e.g., 'api.sessions.get.success')
            value: Amount to increment (default: 1)
        """
        self.counters[name] += value

    def observe(self, name: str, value: float) -> None:
        """Record a histogram observation.

        Args:
            name: Metric name (e.g., 'api.sessions.get.duration')
            value: Observed value (e.g., request duration in seconds)
        """
        self.histograms[name].append(value)

    def get_stats(self) -> dict[str, Any]:
        """Get all metrics as dictionary.

        Returns:
            Dictionary with counters and histogram statistics
        """
        return {
            "counters": dict(self.counters),
            "histograms": {
                name: self._histogram_stats(values)
                for name, values in self.histograms.items()
            },
        }

    def _histogram_stats(self, values: list[float]) -> dict[str, float]:
        """Calculate histogram statistics."""
        if not values:
            return {
                "count": 0,
                "sum": 0.0,
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }

        sorted_values = sorted(values)
        count = len(sorted_values)

        return {
            "count": count,
            "sum": sum(sorted_values),
            "avg": sum(sorted_values) / count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "p50": sorted_values[int(count * 0.50)],
            "p95": sorted_values[int(count * 0.95)],
            "p99": sorted_values[int(count * 0.99)],
        }

    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        self.counters.clear()
        self.histograms.clear()


# Global metrics instance
metrics = MetricsCollector()


def track_api_call(endpoint: str, method: str = "GET"):
    """Context manager to track API endpoint calls.

    Usage:
        with track_api_call("sessions.get", "GET"):
            # Endpoint logic
            pass
    """
    start = time.perf_counter()
    metric_prefix = f"api.{endpoint}.{method.lower()}"

    try:
        yield
        # Success
        metrics.increment(f"{metric_prefix}.success")
    except Exception:
        # Error
        metrics.increment(f"{metric_prefix}.error")
        raise
    finally:
        # Duration
        duration = time.perf_counter() - start
        metrics.observe(f"{metric_prefix}.duration", duration)
```

#### 2. Instrument API Endpoints (2 hours)

**Add metrics to sessions endpoints:**

Update `backend/api/sessions.py`:
```python
from backend.api.metrics import metrics, track_api_call

@router.get("/{session_id}")
async def get_session(
    session_id: str,
    session_data: VerifiedSession,
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> SessionDetailResponse:
    """Get session details with metrics tracking."""
    with track_api_call("sessions.get", "GET"):
        user_id, metadata = session_data
        # ... existing logic
        return SessionDetailResponse(...)
```

**Apply to all endpoints:**
- `backend/api/sessions.py` (10 endpoints)
- `backend/api/control.py` (5 endpoints)
- `backend/api/context.py` (4 endpoints)
- `backend/api/streaming.py` (3 endpoints)

**Add LLM metrics:**

Update `bo1/llm/broker.py`:
```python
from backend.api.metrics import metrics

async def send_prompt(request: PromptRequest) -> LLMResponse:
    """Send prompt with metrics tracking."""
    start = time.perf_counter()

    try:
        # Check cache
        cache = get_llm_cache()
        cached_response = await cache.get_cached_response(request)

        if cached_response:
            metrics.increment("llm.cache.hit")
            return cached_response

        metrics.increment("llm.cache.miss")

        # Call API
        response = await client.create_message(...)

        # Track metrics
        metrics.increment("llm.api_calls")
        metrics.observe("llm.input_tokens", response.input_tokens)
        metrics.observe("llm.output_tokens", response.output_tokens)
        metrics.observe("llm.cost", response.cost_total)
        metrics.observe("llm.duration", time.perf_counter() - start)

        return response

    except Exception as e:
        metrics.increment("llm.errors")
        raise
```

#### 3. Create Metrics Endpoint (1 hour)

Create `backend/api/admin/metrics.py`:
```python
"""Metrics endpoint (admin-only)."""
from fastapi import APIRouter, Depends

from backend.api.middleware.auth import require_admin
from backend.api.metrics import metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_metrics(
    _admin: dict = Depends(require_admin),
) -> dict:
    """Get all system metrics (admin only).

    Returns counters and histogram statistics for:
    - API endpoint calls (success/error rates, latency)
    - LLM API calls (cache hits, token usage, costs)
    - Database queries (if instrumented)
    - Cache operations (hit rates)
    """
    return metrics.get_stats()


@router.post("/reset")
async def reset_metrics(
    _admin: dict = Depends(require_admin),
) -> dict:
    """Reset all metrics to zero (admin only)."""
    metrics.reset()
    return {"message": "Metrics reset successfully"}
```

Register in `backend/api/main.py`:
```python
from backend.api.admin import metrics as metrics_router

app.include_router(
    metrics_router.router,
    prefix="/api/admin",
)
```

#### 4. Testing (1 hour)

Create `tests/api/test_metrics.py`:
```python
import pytest
from backend.api.metrics import MetricsCollector, track_api_call


def test_counter_increment():
    """Test counter increments correctly."""
    collector = MetricsCollector()
    collector.increment("test.counter", 5)
    collector.increment("test.counter", 3)

    stats = collector.get_stats()
    assert stats["counters"]["test.counter"] == 8


def test_histogram_observe():
    """Test histogram records values."""
    collector = MetricsCollector()
    collector.observe("test.duration", 0.1)
    collector.observe("test.duration", 0.2)
    collector.observe("test.duration", 0.3)

    stats = collector.get_stats()
    hist = stats["histograms"]["test.duration"]

    assert hist["count"] == 3
    assert hist["avg"] == pytest.approx(0.2)
    assert hist["min"] == 0.1
    assert hist["max"] == 0.3


def test_track_api_call_success():
    """Test API call tracking on success."""
    collector = MetricsCollector()

    with track_api_call("test.endpoint", "GET"):
        pass  # Simulated successful call

    stats = collector.get_stats()
    assert stats["counters"]["api.test.endpoint.get.success"] == 1
    assert "api.test.endpoint.get.duration" in stats["histograms"]


def test_track_api_call_error():
    """Test API call tracking on error."""
    collector = MetricsCollector()

    with pytest.raises(ValueError):
        with track_api_call("test.endpoint", "POST"):
            raise ValueError("Test error")

    stats = collector.get_stats()
    assert stats["counters"]["api.test.endpoint.post.error"] == 1


@pytest.mark.asyncio
async def test_metrics_endpoint(client, admin_user):
    """Test /api/admin/metrics endpoint."""
    # Make some API calls to generate metrics
    await client.get("/api/v1/sessions")

    # Get metrics
    response = await client.get(
        "/api/admin/metrics",
        headers={"X-Admin-Key": "test-admin-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "counters" in data
    assert "histograms" in data
```

Run tests:
```bash
pytest tests/api/test_metrics.py -v
```

#### 5. Documentation (30 min)

Update `CLAUDE.md`:
```markdown
**Metrics Collection:**
- Lightweight in-memory metrics (counters + histograms)
- API endpoint performance tracking (latency, success/error rates)
- LLM usage tracking (calls, tokens, costs, cache hits)
- Admin-only metrics endpoint: GET /api/admin/metrics
- Reset metrics: POST /api/admin/metrics/reset
- Future: Prometheus export for production monitoring
```

#### 6. Commit (15 min)

```bash
git add backend/api/metrics.py backend/api/admin/metrics.py backend/api/*.py bo1/llm/broker.py tests/api/test_metrics.py CLAUDE.md
git commit -m "feat: add system-wide metrics collection infrastructure

- Create MetricsCollector with counters and histograms
- Add track_api_call context manager for endpoint instrumentation
- Instrument all API endpoints (22 total)
- Track LLM calls (cache hits, tokens, costs)
- Add admin-only /api/admin/metrics endpoint
- Add comprehensive metrics tests

Metrics Tracked:
- API endpoints: success/error counts, latency (p50/p95/p99)
- LLM: api_calls, cache hit/miss, tokens, costs
- Per-endpoint breakdown for debugging

Performance:
- <1ms overhead per request (simple dict operations)
- In-memory storage (resets on server restart)
- Future: Prometheus export support

Usage:
- View metrics: GET /api/admin/metrics (admin only)
- Reset metrics: POST /api/admin/metrics/reset (admin only)"
```

### Files Modified
- `backend/api/metrics.py` - New metrics collector
- `backend/api/admin/metrics.py` - Metrics endpoint
- `backend/api/sessions.py` - Instrumented
- `backend/api/control.py` - Instrumented
- `backend/api/context.py` - Instrumented
- `backend/api/streaming.py` - Instrumented
- `bo1/llm/broker.py` - LLM metrics
- `tests/api/test_metrics.py` - New tests
- `CLAUDE.md` - Documentation

### Acceptance Criteria
- [ ] Metrics endpoint returns data
- [ ] All API endpoints instrumented
- [ ] LLM calls tracked
- [ ] Tests passing
- [ ] `make pre-commit` passing
- [ ] <1ms overhead verified

---

## [TASK 7] Implement Persona Selection Caching

**Priority:** High (Cost savings)
**Effort:** 5-7 hours
**Day:** Day 8 (Wednesday, Week 2)
**Dependencies:** Task 2 (LLM cache infrastructure)

### Objective

Implement semantic similarity-based caching for persona selection to reduce LLM API calls for similar business problems.

### Success Criteria

- [ ] Cache hit rate 40-60% for similar problems
- [ ] Cost savings $200-400/month at 1000 deliberations
- [ ] Similarity threshold configurable (default: 0.90)
- [ ] Embeddings generated via Voyage AI
- [ ] 7-day TTL for cached selections

### Implementation Steps

#### 1. Analysis & Design (1 hour)

**Analyze persona selection patterns:**
```bash
# Review current persona selection
cat bo1/agents/selector.py | grep -A 30 "async def select_personas"

# Identify common problem types
# - Business expansion (EU, Asia, new markets)
# - Pricing strategy (raise prices, discounts, value-based)
# - Product development (new features, roadmap)
# - Financial decisions (funding, budgeting, cost reduction)
```

**Design caching strategy:**
- Generate embedding for problem goal (Voyage AI voyage-3)
- Search cache for similar embeddings (cosine similarity >0.90)
- If hit: return cached personas
- If miss: select via LLM, cache result with embedding

#### 2. Integrate Voyage AI Embeddings (1.5 hours)

Update `bo1/llm/embeddings.py`:
```python
"""Embedding generation using Voyage AI."""
import httpx
from bo1.config import get_settings


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding using Voyage AI voyage-3 model.

    Args:
        text: Text to embed (e.g., problem goal)

    Returns:
        Embedding vector (1024 dimensions)

    Raises:
        httpx.HTTPError: If API call fails
    """
    settings = get_settings()
    url = "https://api.voyageai.com/v1/embeddings"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.voyage_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "input": [text],
                "model": "voyage-3",
            },
            timeout=10.0,
        )

        response.raise_for_status()
        data = response.json()

        return data["data"][0]["embedding"]


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First embedding vector
        vec2: Second embedding vector

    Returns:
        Similarity score (0.0 to 1.0)
    """
    import math

    # Dot product
    dot_product = sum(a * b for a, b in zip(vec1, vec2))

    # Magnitudes
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot_product / (mag1 * mag2)
```

Add to `bo1/config.py`:
```python
class Settings(BaseSettings):
    # ... existing fields

    # Voyage AI
    voyage_api_key: str = Field(default="")
```

#### 3. Implement Persona Selection Cache (2 hours)

Create `bo1/agents/persona_cache.py`:
```python
"""Persona selection caching with semantic similarity."""
import json
import logging
from typing import Any

from bo1.config import get_settings
from bo1.llm.embeddings import cosine_similarity, generate_embedding
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class PersonaSelectionCache:
    """Semantic similarity-based persona selection cache."""

    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager.redis
        self.enabled = get_settings().enable_persona_selection_cache
        self.similarity_threshold = 0.90
        self.ttl_seconds = 7 * 24 * 60 * 60  # 7 days
        self._hits = 0
        self._misses = 0

    async def get_cached_personas(
        self,
        problem: Problem,
    ) -> list[PersonaProfile] | None:
        """Get cached persona selection if similar problem exists.

        Args:
            problem: Problem to get personas for

        Returns:
            Cached persona list if similar problem found, else None
        """
        if not self.enabled:
            return None

        try:
            # Generate embedding for problem goal
            query_embedding = await generate_embedding(problem.goal)

            # Search cache for similar problems
            cache_keys = self.redis.keys("personas:cache:*")

            for key in cache_keys:
                cached_data_json = self.redis.get(key)
                if not cached_data_json:
                    continue

                cached_data = json.loads(cached_data_json)
                cached_embedding = cached_data["embedding"]

                # Calculate similarity
                similarity = cosine_similarity(query_embedding, cached_embedding)

                if similarity > self.similarity_threshold:
                    self._hits += 1
                    logger.info(
                        f"Persona cache hit (similarity={similarity:.3f}, "
                        f"threshold={self.similarity_threshold})"
                    )

                    # Return cached personas
                    return [
                        PersonaProfile(**p)
                        for p in cached_data["personas"]
                    ]

            # No similar problem found
            self._misses += 1
            return None

        except Exception as e:
            logger.error(f"Persona cache read error: {e}")
            self._misses += 1
            return None

    async def cache_persona_selection(
        self,
        problem: Problem,
        personas: list[PersonaProfile],
    ) -> None:
        """Cache persona selection for problem.

        Args:
            problem: Problem personas were selected for
            personas: Selected personas to cache
        """
        if not self.enabled:
            return

        try:
            # Generate embedding
            embedding = await generate_embedding(problem.goal)

            # Create cache key (hash of problem goal)
            import hashlib
            problem_hash = hashlib.sha256(problem.goal.encode()).hexdigest()[:16]
            cache_key = f"personas:cache:{problem_hash}"

            # Store in cache
            cache_data = {
                "embedding": embedding,
                "personas": [p.model_dump() for p in personas],
                "problem_goal": problem.goal,  # For debugging
            }

            self.redis.setex(
                cache_key,
                self.ttl_seconds,
                json.dumps(cache_data),
            )

            logger.debug(f"Cached persona selection: {cache_key}")

        except Exception as e:
            logger.error(f"Persona cache write error: {e}")

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
            "similarity_threshold": self.similarity_threshold,
            "ttl_seconds": self.ttl_seconds,
        }


# Global cache instance
_persona_cache: PersonaSelectionCache | None = None


def get_persona_cache() -> PersonaSelectionCache:
    """Get or create persona cache instance."""
    global _persona_cache
    if _persona_cache is None:
        from bo1.state.redis_manager import get_redis_manager
        _persona_cache = PersonaSelectionCache(get_redis_manager())
    return _persona_cache
```

#### 4. Integrate with Selector Agent (1 hour)

Update `bo1/agents/selector.py`:
```python
from bo1.agents.persona_cache import get_persona_cache

async def select_personas(
    problem: Problem,
    num_personas: int = 5,
) -> list[PersonaProfile]:
    """Select personas with caching."""
    cache = get_persona_cache()

    # Check cache first
    cached_personas = await cache.get_cached_personas(problem)
    if cached_personas:
        return cached_personas[:num_personas]

    # Cache miss - select via LLM
    personas = await _select_personas_via_llm(problem, num_personas)

    # Store in cache
    await cache.cache_persona_selection(problem, personas)

    return personas
```

Update graph node:
```python
# bo1/graph/nodes.py
async def select_personas_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Select personas with caching."""
    v1_state = graph_state_to_deliberation_state(state)

    # This now uses cache internally
    personas = await selector.select_personas(
        v1_state.problem,
        num_personas=5,
    )

    return {"personas": personas}
```

#### 5. Testing (1.5 hours)

Create `tests/agents/test_persona_cache.py`:
```python
import pytest
from bo1.agents.persona_cache import PersonaSelectionCache, cosine_similarity
from bo1.models.problem import Problem
from bo1.models.persona import PersonaProfile


@pytest.mark.asyncio
async def test_cosine_similarity():
    """Test cosine similarity calculation."""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    vec3 = [0.0, 1.0, 0.0]

    # Identical vectors = 1.0
    assert cosine_similarity(vec1, vec2) == pytest.approx(1.0)

    # Orthogonal vectors = 0.0
    assert cosine_similarity(vec1, vec3) == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_persona_cache_hit(redis_manager):
    """Test cache returns personas for similar problem."""
    cache = PersonaSelectionCache(redis_manager)

    # Original problem
    problem1 = Problem(
        statement="Should we expand to European markets?",
        goal="Evaluate EU expansion",
        context="SaaS company",
    )

    personas = [
        PersonaProfile(code="cfo", name="CFO", ...),
        PersonaProfile(code="cmo", name="CMO", ...),
    ]

    # Cache selection
    await cache.cache_persona_selection(problem1, personas)

    # Similar problem (high similarity)
    problem2 = Problem(
        statement="Should we launch in Europe?",
        goal="Assess European market entry",
        context="SaaS business",
    )

    # Should hit cache
    cached = await cache.get_cached_personas(problem2)

    assert cached is not None
    assert len(cached) == 2
    assert cached[0].code == "cfo"
    assert cache.hit_rate > 0.0


@pytest.mark.asyncio
async def test_persona_cache_miss(redis_manager):
    """Test cache returns None for different problem."""
    cache = PersonaSelectionCache(redis_manager)

    # Original problem
    problem1 = Problem(
        statement="Should we expand to Europe?",
        goal="EU expansion",
        context="SaaS",
    )

    personas = [PersonaProfile(code="cfo", ...)]
    await cache.cache_persona_selection(problem1, personas)

    # Very different problem
    problem2 = Problem(
        statement="What tech stack for mobile app?",
        goal="Choose mobile technology",
        context="App development",
    )

    # Should miss cache (low similarity)
    cached = await cache.get_cached_personas(problem2)

    assert cached is None
    assert cache.hit_rate == 0.0
```

Run tests:
```bash
pytest tests/agents/test_persona_cache.py -v
```

#### 6. Documentation (30 min)

Update `CLAUDE.md`:
```markdown
**Persona Selection Caching:**
- Semantic similarity-based caching using Voyage AI embeddings
- Similarity threshold: 0.90 (configurable)
- Cache TTL: 7 days
- Expected hit rate: 40-60% for similar problems
- Cost savings: ~$200-400/month at 1000 deliberations
- Enable: ENABLE_PERSONA_SELECTION_CACHE=true
```

#### 7. Commit (15 min)

```bash
git add bo1/agents/persona_cache.py bo1/agents/selector.py bo1/llm/embeddings.py bo1/config.py tests/agents/test_persona_cache.py CLAUDE.md
git commit -m "feat: add semantic persona selection caching

- Implement PersonaSelectionCache with similarity matching
- Integrate Voyage AI voyage-3 for embeddings (1024 dimensions)
- Add cosine similarity calculation for vector comparison
- Cache persona selections for 7 days with semantic lookup
- Add comprehensive tests for caching and similarity

Performance:
- Similarity threshold: 0.90 (highly similar problems)
- Expected hit rate: 40-60% in production
- Cost per miss: \$0.01-0.02 (LLM call)
- Cost per hit: \$0.00006 (embedding only)
- Savings: ~\$200-400/month at 1000 deliberations

Configuration:
- ENABLE_PERSONA_SELECTION_CACHE=true (default: false)
- VOYAGE_API_KEY=<your-key>
- Similarity threshold: 0.90 (hardcoded, could be configurable)

Example Cache Hits:
- 'Should we expand to EU?' → 'Should we launch in Europe?'
- 'Raise prices by 20%?' → 'Should we increase pricing?'
- 'Hire VP of Sales?' → 'Do we need a sales leader?'"
```

### Files Modified
- `bo1/agents/persona_cache.py` - New caching system
- `bo1/agents/selector.py` - Integrate cache
- `bo1/llm/embeddings.py` - Voyage AI integration
- `bo1/config.py` - Add settings
- `bo1/graph/nodes.py` - Use cached selector
- `tests/agents/test_persona_cache.py` - New tests
- `CLAUDE.md` - Documentation

### Potential Issues
- **High similarity threshold:** 0.90 may be too strict (low hit rate)
  - *Mitigation:* Start at 0.90, can lower to 0.85 if needed
- **Embedding API costs:** Voyage AI charges per call
  - *Mitigation:* Very cheap ($0.00006 per call vs $0.01-0.02 for persona selection)
- **Wrong personas cached:** Similar problems may need different personas
  - *Mitigation:* 7-day TTL prevents long-term staleness, high threshold ensures accuracy

### Acceptance Criteria
- [ ] Cache functional with similarity matching
- [ ] Voyage AI integration working
- [ ] Tests passing
- [ ] `make pre-commit` passing
- [ ] Documentation complete

---

## [TASK 8] Sprint Validation & Documentation

**Priority:** Medium
**Effort:** 5-6 hours
**Day:** Day 9-10 (Thursday-Friday, Week 2)
**Dependencies:** All previous tasks

### Objective

Validate all sprint deliverables, run comprehensive tests, measure impact, and document results.

### Activities

#### Day 9: Integration Testing & Validation

**1. Full Test Suite (2 hours)**
```bash
# Run all tests
make test

# Check coverage
pytest --cov=bo1 --cov=backend --cov-report=html
open htmlcov/index.html

# Run integration tests
pytest -m integration -v

# Run LLM tests (if needed)
pytest -m requires_llm -v
```

**2. Performance Benchmarks (1 hour)**
```bash
# LLM cache performance
python tests/benchmarks/bench_llm_cache.py

# State conversion cache
python tests/benchmarks/bench_state_conversion.py

# Persona cache (requires embeddings)
python tests/benchmarks/bench_persona_cache.py
```

**3. Manual Testing (1 hour)**
```bash
# Start all services
make up

# Test deliberation flow
make run
# Enter test problem, verify caching works

# Check metrics endpoint
curl http://localhost:8000/api/admin/metrics \
  -H "X-Admin-Key: <admin-key>"

# Verify cache stats
# Should see cache hits in metrics
```

#### Day 10: Documentation & Retrospective

**1. Update Documentation (2 hours)**

Update `CLAUDE.md` with all new features:
```markdown
## Recent Optimizations (Sprint Jan 2025)

### Cost Reduction (60-70% savings)
- LLM Response Caching: 60%+ hit rate, $0.04-0.08 saved per hit
- Persona Selection Caching: 40-60% hit rate, $200-400/month savings
- Total monthly savings: ~$300-500 → $100-150

### Code Quality Improvements
- Event extractor refactoring: 32% code reduction (884 → 600 lines)
- Standardized error handling: 28 endpoints consistent
- Test coverage: 41% → 60%+ (28 tests unblocked)

### System Observability
- Metrics collection: API latency, LLM usage, cache hit rates
- Feature flags: Runtime configuration toggles
- Admin metrics endpoint: /api/admin/metrics

### Quick Wins Implemented
1. Response compression validation
2. Component cache eviction (bounded memory)
3. Feature flags system
4. SSE client error logging
5. Event deduplication bounds
6. State conversion cache bounds
7. Rate limiting on auth endpoints
```

**2. Create Sprint Summary Report (1 hour)**

Create `SPRINT_SUMMARY.md`:
```markdown
# Sprint Summary - Jan 2025 Optimization Sprint

## Goals Achieved

- ✅ Reduce LLM costs by 60-70% via caching
- ✅ Improve code quality (300+ lines removed)
- ✅ Enable system observability (metrics)
- ✅ Unblock 28 failing tests

## Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Monthly LLM cost | $300-500 | $100-150 | -70% |
| Test coverage | 41% | 60%+ | +19% |
| Code complexity (event_collector.py) | 884 lines | 600 lines | -32% |
| API error consistency | 60% | 95%+ | +35% |
| System observability | None | Full metrics | ✅ |

## Deliverables

1. LLM Response Caching (Task 2)
2. Persona Selection Caching (Task 7)
3. Error Handling Standardization (Task 3)
4. Event Extractor Refactoring (Task 5)
5. Metrics Collection Infrastructure (Task 6)
6. Feature Flags System (Task 4.3)
7. 7 Quick Wins (Task 4)
8. Test Fixes (Task 1)

## Total Effort

- Estimated: 40-50 hours
- Actual: [Record actual hours]
- Variance: [Calculate]

## Lessons Learned

- What went well: [Fill in retrospective]
- What could improve: [Fill in retrospective]
- Blockers encountered: [Fill in retrospective]

## Next Sprint Candidates

- SSE streaming implementation (6 days)
- Database composite indexes
- Virtual scrolling for long event lists
- API response field filtering
```

**3. Retrospective (1 hour)**

Hold retrospective meeting or document answers:

1. **What went well?**
   - High-impact optimizations delivered
   - Cost reduction achieved
   - Code quality improved

2. **What could be improved?**
   - [Document learnings]
   - [Process improvements]

3. **What blockers were encountered?**
   - [Document any issues]
   - [How resolved]

4. **Were estimates accurate?**
   - [Compare estimated vs actual time]

5. **What should we do next?**
   - [Prioritize remaining items]

**4. Commit Documentation (30 min)**

```bash
git add CLAUDE.md SPRINT_SUMMARY.md
git commit -m "docs: add sprint summary and update documentation

- Document all sprint deliverables in CLAUDE.md
- Create comprehensive sprint summary report
- Update configuration examples
- Add performance metrics and benchmarks

Sprint Achievements:
- 60-70% cost reduction via LLM caching
- 32% code complexity reduction
- 28 tests unblocked
- Full metrics collection enabled
- 7 quick wins implemented

Total effort: ~40-50 hours over 2 weeks"
```

### Acceptance Criteria
- [ ] All tests passing
- [ ] Performance benchmarks run and documented
- [ ] All documentation updated
- [ ] Sprint summary created
- [ ] Retrospective completed

---

## Sprint Completion Checklist

### Week 1
- [ ] Task 1: Test collection fixes (1-2h) ✅
- [ ] Task 2: LLM response caching (4-6h) ✅
- [ ] Task 3: Error handling standardization (3-4h) ✅
- [ ] Task 4: Quick wins batch (10-15h) ✅

### Week 2
- [ ] Task 5: Event extractor refactoring (4-6h) ✅
- [ ] Task 6: Metrics collection (4-6h) ✅
- [ ] Task 7: Persona selection caching (5-7h) ✅
- [ ] Task 8: Validation & documentation (5-6h) ✅

### Quality Gates
- [ ] All pre-commit hooks passing
- [ ] Test coverage >60%
- [ ] All new features documented
- [ ] Performance benchmarks recorded
- [ ] Sprint summary created

### Deployment Readiness
- [ ] Feature flags configured
- [ ] Environment variables documented
- [ ] Rollback plans tested
- [ ] Monitoring enabled
- [ ] Ready for staging deployment

---

**End of Sprint Implementation Plan**

**Total Pages:** 2 documents, ~25 pages combined
**Total Tasks:** 8 major tasks + 7 quick wins
**Total Effort:** 40-50 hours over 10 days
**Expected Impact:** 60-70% cost reduction, significant code quality improvement
