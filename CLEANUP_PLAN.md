# Codebase Cleanup Plan

**Generated**: 2025-11-27
**Status**: No live customers - can make breaking changes
**Principle**: 95% quality in 5 minutes beats 100% quality in 2 hours

---

## Executive Summary

| Category | Issues Found | Est. Code Removal | Priority Items |
|----------|--------------|-------------------|----------------|
| Legacy/Fallback Code | ~1,000 lines | Remove completely | Serial architecture, v1 state conversion |
| Persistence Gaps | 8 major outputs | Add ~500 lines | Contributions, recommendations, sub-problems |
| Optimizations | 12 opportunities | Refactor ~200 lines | dict() conversions, batch inserts |
| Dependency Conflicts | 4 packages | Remove 4 deps | asyncpg, supabase, langchain-anthropic |
| Frontend/Backend Issues | 25 issues | Various | Auth bypass, race conditions, memory leaks |

---

## Phase 1: Quick Wins (1-2 hours)

### 1.1 Remove Unused Dependencies
**Files**: `pyproject.toml`
```bash
# Remove these lines:
- supabase>=2.0.0,<3.0       # Line 37 - deprecated, no usage
- asyncpg>=0.29.0            # Line 24 - never imported
- langchain-anthropic>=1.1.0 # Line 15 - bypassed for raw SDK
```

### 1.2 Remove Deprecated Functions (Zero Callers)
| Function | File | Lines | Action |
|----------|------|-------|--------|
| `parse_vote_decision()` | `bo1/utils/vote_parsing.py` | 8-49 | Delete |
| `get_cached_personas()` | `bo1/agents/persona_cache.py` | 202-208 | Delete |
| `cache_persona_selection()` | `bo1/agents/persona_cache.py` | 210-216 | Delete |
| `get_cached_response()` | `bo1/llm/cache.py` | 174-180 | Delete |
| `cache_response()` | `bo1/llm/cache.py` | 182-187 | Delete |
| Test file | `tests/utils/test_vote_parsing.py` | All | Delete entire file |
| `redis_manager_or_skip()` | `tests/conftest.py` | 265-273 | Delete |
| `redis_manager_or_none()` | `tests/conftest.py` | 275-282 | Delete |

### 1.3 Remove Unnecessary dict() Conversions
**File**: `bo1/state/postgres_manager.py`
**Issue**: 17 locations with `dict(row)` when `RealDictCursor` already returns dicts
```python
# Replace pattern:
return [dict(row) for row in rows]
# With:
return list(rows)
```
**Lines**: 130, 179, 255, 280, 403, 467, 551, 629, 683, 711, 768, 797, 913, 1014, 1110, 1164, 1210

### 1.4 Convert FacilitatorDecision to Pydantic
**File**: `bo1/graph/nodes.py:454`
**Issue**: Using `asdict()` on dataclass every round
**Fix**: Change from `@dataclass` to Pydantic `BaseModel`, use `.model_dump()`

---

## Phase 2: Remove Serial Architecture (2-3 hours)

### 2.1 Delete Serial Persona Node
**File**: `bo1/graph/nodes.py`
- Delete `persona_contribute_node()` function (lines 463-666)
- Delete legacy subproblem fallback (lines 2615-2624)

### 2.2 Remove Feature Flag
**File**: `bo1/feature_flags/features.py`
- Delete `ENABLE_PARALLEL_ROUNDS` flag and checking code (lines 13, 33-42)

### 2.3 Simplify Routing
**File**: `bo1/graph/routers.py`
- Remove serial routing logic (lines 50, 84-85, 102, 182-208)
- Keep only parallel routing

### 2.4 Update Event Handlers
**Files**:
- `backend/api/event_collector.py` - Remove serial event type handling (lines 176, 365)
- `bo1/console/interface.py` - Remove serial display code (line 260)

---

## Phase 3: Fix Persistence Gaps (3-4 hours)

### 3.1 Persist Contributions (HIGH PRIORITY)
**Schema exists but unused**: `contributions` table in migrations

**Add to** `bo1/state/postgres_manager.py`:
```python
def save_contribution(session_id: str, persona_code: str, content: str,
                     round_number: int, phase: str, cost: float, tokens: int, model: str):
    # INSERT INTO contributions ...
```

**Call from** `backend/api/event_collector.py:_publish_contribution()` (after line 352)

### 3.2 Persist Recommendations (HIGH PRIORITY)
**Current**: `votes` table exists but schema outdated

**Migration needed**: Add `recommendations` table
```sql
CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    sub_problem_index INTEGER,
    persona_code VARCHAR(50) NOT NULL,
    recommendation TEXT NOT NULL,
    reasoning TEXT,
    confidence DECIMAL(3,2),
    conditions JSONB,
    weight DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);
```

**Call from** `backend/api/event_collector.py:_handle_voting()` (line 447)

### 3.3 Persist Sub-Problem Results (MEDIUM PRIORITY)
**Currently**: Only final synthesis stored

**Migration needed**: Add `sub_problem_results` table
```sql
CREATE TABLE sub_problem_results (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    sub_problem_index INTEGER NOT NULL,
    goal TEXT NOT NULL,
    synthesis TEXT,
    expert_summaries JSONB,
    cost DECIMAL(10,4),
    duration_seconds INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);
```

### 3.4 Persist Facilitator Decisions (MEDIUM PRIORITY)
**Currently**: Only in Redis events, not queryable

**Migration needed**: Add `facilitator_decisions` table
```sql
CREATE TABLE facilitator_decisions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    round_number INTEGER NOT NULL,
    sub_problem_index INTEGER,
    action VARCHAR(50) NOT NULL,
    reasoning TEXT,
    next_speaker VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);
```

---

## Phase 4: Security & Critical Fixes (2-3 hours)

### 4.1 Fix Auth Bypass Risk
**File**: `backend/api/middleware/auth.py:82-91`
**Issue**: MVP fallback returns `test_user_1` when auth disabled
**Fix**:
- Remove fallback in production builds
- Force `ENABLE_SUPERTOKENS_AUTH=true` in non-debug mode

### 4.2 Fix Session Race Condition
**File**: `backend/api/control.py:116-128`
**Issue**: Non-atomic check between "is running" and "start"
**Fix**: Use atomic check-and-set in `SessionManager.start_session()`

### 4.3 Propagate PostgreSQL Errors
**File**: `backend/api/sessions.py:144-146`
**Issue**: PostgreSQL failures silently logged, session continues
**Fix**: Raise `HTTPException(500)` if primary storage fails

### 4.4 Add Frontend Cleanup
**File**: `frontend/src/routes/(app)/meeting/[id]/+page.svelte`
**Issue**: No `onDestroy()` cleanup for SSE client
**Fix**:
```svelte
onDestroy(() => {
    sseClient?.disconnect();
});
```

### 4.5 Bound Event Array
**File**: `frontend/src/routes/(app)/meeting/[id]/lib/sessionStore.svelte.ts:93`
**Issue**: Events array grows unbounded
**Fix**: Add max size (5000) with pruning of oldest events

---

## Phase 5: Optimizations (2-3 hours)

### 5.1 Batch Database Inserts
**File**: `bo1/state/postgres_manager.py:408-468`
**Issue**: Research results saved one at a time
**Fix**: Create `save_research_results_batch()` with multi-row INSERT

### 5.2 Pre-build Shared Memory Context
**File**: `bo1/graph/nodes.py:2105-2131`
**Issue**: Same `dependency_context` and `subproblem_context` rebuilt per expert
**Fix**: Build once outside loop, pass to all tasks

### 5.3 Parallelize Research Questions
**File**: `bo1/agents/researcher.py:122-146`
**Issue**: Sequential batch processing
**Fix**: Use `asyncio.gather(*all_tasks)` for all questions at once

---

## Phase 6: Remove v1-v2 State Conversion (4-6 hours)

**This is the largest refactor - do after above phases are stable**

### 6.1 Current State
- `DeliberationState` (v1) - old model
- `DeliberationGraphState` (v2) - LangGraph model
- `deliberation_state_to_graph_state()` - v1 → v2
- `graph_state_to_deliberation_state()` - v2 → v1 (with caching)

### 6.2 Migration Strategy
1. Update all agents to accept `DeliberationGraphState` directly
2. Remove conversion functions from `bo1/graph/state.py:240-431`
3. Remove v1 state model from `bo1/models/state.py`
4. Update all node implementations to work with v2 state only

### 6.3 Files to Modify
| File | Changes |
|------|---------|
| `bo1/graph/nodes.py` | Remove all `graph_state_to_deliberation_state()` calls |
| `bo1/graph/state.py` | Remove conversion functions (lines 240-431) |
| `bo1/models/state.py` | Remove `DeliberationState` class |
| `bo1/agents/*.py` | Update to accept v2 state |

---

## Code Debt: TODO Comments

| File | Line | TODO | Priority |
|------|------|------|----------|
| `bo1/agents/facilitator.py` | 225 | Undercontribution check | Low |
| `bo1/agents/researcher.py` | 435 | Detect API tier | Low |
| `bo1/agents/researcher.py` | 562 | Detect API tier | Low |
| `backend/api/control.py` | 151 | Load personas from metadata | Medium |
| `backend/api/middleware/auth.py` | 100 | Fetch user data from DB | Medium |
| `backend/tests/test_sse_*.py` | 277, 302 | Integration tests | Low |

---

## Dependency Cleanup Summary

### Remove (unused)
- `supabase` - deprecated, SuperTokens used instead
- `asyncpg` - never imported
- `langchain-anthropic` - code uses raw Anthropic SDK

### Move to Dev Dependencies
- `sqlalchemy` - only used by Alembic migrations

### Keep (actively used)
- `anthropic` - primary LLM client
- `langchain-core` - required by LangGraph
- `httpx` - HTTP client for external APIs
- `psycopg2-binary` - sync PostgreSQL driver
- `pydantic` / `pydantic-settings` - validation

---

## Tracking Checklist

### Phase 1: Quick Wins ✅
- [x] Remove unused dependencies from pyproject.toml
- [x] Delete deprecated functions (6 functions, 1 test file)
- [x] Remove dict() wrapper calls (kept for type safety - RealDictRow issue)
- [ ] Convert FacilitatorDecision to Pydantic (deferred - working fine)

### Phase 2: Serial Architecture ✅
- [x] Delete persona_contribute_node()
- [x] Delete legacy subproblem fallback
- [x] Remove ENABLE_PARALLEL_ROUNDS flag
- [x] Simplify routing logic
- [x] Update event handlers

### Phase 3: Persistence ✅
- [x] Create save_contribution() function
- [x] Create recommendations table + save function
- [x] Create sub_problem_results table + save function
- [x] Create facilitator_decisions table + save function

### Phase 4: Security ✅
- [x] Add DEBUG mode check for auth bypass
- [ ] Fix session race condition (low priority - single-threaded async)
- [x] Propagate PostgreSQL errors
- [x] Frontend SSE cleanup (already implemented)
- [x] Bound event array size (MAX_EVENTS = 5000)

### Phase 5: Optimizations ✅
- [x] Batch database inserts (save_research_results_batch)
- [x] Pre-build shared memory context (already optimized)
- [x] Parallelize research questions (asyncio.gather)

### Phase 6: State Refactor (DEFERRED)
- [ ] Update agents to accept v2 state
- [ ] Remove conversion functions
- [ ] Remove v1 state model
- [ ] Update all nodes
*Large refactor - do after above phases are stable*

---

## Notes

- **Test after each phase** - run `make test` and `make pre-commit`
- **Deploy incrementally** - don't bundle all changes into one deploy
- **No live customers** - we can make breaking changes without migration paths
- **Migrations** - create Alembic migrations for all schema changes

---

*Generated by codebase analysis - verify before implementing*
