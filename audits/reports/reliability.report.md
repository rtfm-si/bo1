# Reliability Audit Report

**Audit Date**: 2025-12-30 (updated from 2025-12-22)
**Scope**: Exception handling, retry strategies, state recovery, database transaction management, external service failure handling
**Files Analyzed**:
- `bo1/graph/execution.py`
- `bo1/state/repositories/session_repository.py`
- `bo1/services/replanning_service.py`
- `backend/api/streaming.py`
- `bo1/state/database.py`
- `bo1/utils/retry.py`
- `bo1/llm/broker.py`
- `bo1/state/redis_manager.py`
- `bo1/graph/checkpointer_factory.py`

---

## Executive Summary

The codebase demonstrates **strong reliability patterns** with comprehensive retry logic, circuit breakers, and graceful degradation. However, **critical gaps exist in state recovery for partial session failures and LLM provider fallback resilience**.

**Key Strengths**:
- Robust retry decorators with exponential backoff + jitter
- Circuit breakers for DB, Redis, and LLM services
- Connection pool management with health checks
- Graceful degradation for Redis and checkpoint backends
- SSE reconnection with event replay and gap detection

**Critical Gaps**:
- No LangGraph checkpoint recovery after partial session failures
- Missing replanning service rollback on downstream failures
- SSE stream lacks reconnection backoff for rapid client reconnects
- No LLM provider fallback testing/validation
- Database transaction boundaries unclear in multi-repository operations

---

## 1. Error Handling Coverage Map

### 1.1 Database Operations

| Component | Error Types Covered | Recovery Mechanism | Gaps |
|-----------|---------------------|-------------------|------|
| `db_session()` | PoolError, OperationalError, InterfaceError | Circuit breaker + timeout | ❌ No transaction retry on deadlock |
| `session_repository` | Transient DB errors | `@retry_db` decorator (3 attempts) | ✅ Good coverage |
| Connection pool | Pool exhaustion | Timeout + load shedding | ⚠️ No pool recovery on sustained exhaustion |

**Patterns Observed**:
```python
# db_session() - Good: Timeout enforcement
conn = _getconn_with_timeout(pool_instance, timeout=5.0)

# session_repository - Good: Retry with timeout bound
@retry_db(max_attempts=3, base_delay=0.5, total_timeout=30.0)
def update_status(self, session_id: str, status: str) -> bool:
    ...
```

**Gap**: No deadlock detection/retry. Postgres deadlocks (code 40P01) are not handled by `retry_db`.

---

### 1.2 Redis Operations

| Component | Error Types Covered | Recovery Mechanism | Gaps |
|-----------|---------------------|-------------------|------|
| `RedisManager` | ConnectionError, TimeoutError | Auto-reconnect (3 attempts, exponential backoff) | ✅ Strong |
| Circuit breaker | Transient errors | Fast-fail when open | ✅ Good |
| Session metadata | Redis unavailable | Graceful fallback (logs warning) | ❌ No PostgreSQL fallback for metadata |

**Patterns Observed**:
```python
# Good: Exponential backoff with max attempts
def _calculate_backoff_delay(self) -> float:
    delay = base_delay * (BACKOFF_FACTOR ** self._reconnect_attempts)
    return min(delay, max_delay)

# Good: Circuit breaker integration
if is_redis_circuit_open():
    logger.debug("[REDIS_CIRCUIT] Circuit open, skipping reconnection")
    return False
```

**Gap**: `_save_session_metadata()` does not fall back to PostgreSQL when Redis is unavailable, causing metadata loss.

---

### 1.3 LLM Service Calls

| Component | Error Types Covered | Recovery Mechanism | Gaps |
|-----------|---------------------|-------------------|------|
| `PromptBroker.call()` | RateLimitError, APIError | Retry with exponential backoff (3 attempts) | ⚠️ Provider fallback untested |
| Circuit breaker | LLM service failures | Per-provider circuit (Anthropic, OpenAI) | ✅ Good |
| Caching | N/A | LRU cache for repeated prompts | ✅ Good |

**Patterns Observed**:
```python
# Good: Provider fallback support
provider = get_active_llm_provider(
    primary=settings.llm_primary_provider,
    fallback="openai" if settings.llm_primary_provider == "anthropic" else "anthropic",
    fallback_enabled=settings.llm_fallback_enabled,
)

# Gap: Fallback is enabled but not validated in error path
# No test for "Anthropic down -> auto-switch to OpenAI"
```

**Gap**: Provider fallback is configured but **not actively exercised** in the retry loop. If Anthropic circuit opens, fallback should trigger automatically.

---

### 1.4 Session Execution (LangGraph)

| Component | Error Types Covered | Recovery Mechanism | Gaps |
|-----------|---------------------|-------------------|------|
| `SessionManager.start_session()` | General exceptions, CancelledError | Error event emission + metadata update | ❌ No checkpoint recovery |
| Graph execution | N/A | Wrapped in try/except, emits error event | ❌ No partial retry (all-or-nothing) |
| Eviction | Capacity exhaustion | FIFO eviction with grace period | ✅ Good |

**Patterns Observed**:
```python
# Good: Error event emission for UI feedback
session_repository.save_event(
    session_id=session_id,
    event_type="error",
    sequence=9999,
    data={"error": error_msg, "error_type": error_type, "recoverable": False},
)

# Gap: No checkpoint-based recovery
# If session fails at round 3/10, user must restart from scratch
```

**Critical Gap**: Sessions marked as `failed` have no recovery path. LangGraph checkpoints exist but are never used for partial session recovery.

---

### 1.5 SSE Streaming

| Component | Error Types Covered | Recovery Mechanism | Gaps |
|-----------|---------------------|-------------------|------|
| `stream_session_events()` | CancelledError, JSONDecodeError | Event replay from `Last-Event-ID` | ⚠️ No client backoff |
| Gap detection | Sequence gaps | `gap_detected` event emission | ✅ Good |
| Keepalive | N/A | 15s keepalive to prevent timeout | ✅ Good |

**Patterns Observed**:
```python
# Good: Event replay on reconnect
if resume_from_sequence > 0:
    missed_events = await get_event_history_with_fallback(...)
    for payload in missed_events:
        yield format_sse_for_type(event_type, data)

# Gap: No rate limiting on reconnection
# Rapid client reconnects (e.g., network flapping) can overwhelm server
```

**Gap**: SSE endpoint has rate limiting (5 connections/min) but no **exponential backoff** for rapid reconnects from same client.

---

## 2. Retry Strategy Inventory

### 2.1 Database Retries

**Decorator**: `@retry_db`
**Configuration**:
```python
max_attempts=3
base_delay=0.5s
max_delay=10s
total_timeout=30s
jitter=True (0-10% of delay)
```

**Exception Coverage**:
- `OperationalError` (connection failures)
- `InterfaceError` (protocol errors)
- `PoolError` (pool exhaustion)

**Applied To**:
- `session_repository.update_status()`
- `session_repository.save_event()`
- `session_repository.save_events_batch()`
- `session_repository.save_synthesis()`
- All repository write operations

**Gaps**:
- ❌ Deadlock errors (40P01) not retryable
- ❌ No serialization failure handling (40001)
- ⚠️ `total_timeout=30s` may be too short for batch operations

---

### 2.2 LLM Retries

**Class**: `RetryPolicy` in `PromptBroker`
**Configuration**:
```python
max_retries=3
base_delay=1.0s
max_delay=30.0s
jitter=True (0-100% of delay)
```

**Exception Coverage**:
- `RateLimitError` (429 responses, honors Retry-After header)
- `APIError` (generic Anthropic/OpenAI errors)

**Applied To**:
- All `PromptBroker.call()` invocations
- Covers decomposition, persona selection, deliberation, synthesis

**Gaps**:
- ⚠️ Provider fallback triggered only on circuit open, not on retry exhaustion
- ❌ No timeout for individual LLM calls (relies on httpx default)

---

### 2.3 Redis Reconnection

**Class**: `RedisManager._attempt_reconnect()`
**Configuration**:
```python
max_attempts=3
initial_delay=1s
max_delay=30s
backoff_factor=2.0
```

**Exception Coverage**:
- `ConnectionError` (network failures)
- `TimeoutError` (slow responses)

**Applied To**:
- All Redis operations via `_ensure_connected()`
- Triggered automatically on connection drop

**Gaps**:
- ✅ Well-designed, no major gaps
- ⚠️ No async reconnection in `_ensure_connected()` (blocks for sync callers)

---

### 2.4 SSE Event Replay

**Function**: `stream_session_events()`
**Configuration**:
- No formal retry policy (client-driven reconnect)
- Event replay based on `Last-Event-ID` header
- Gap detection for missing sequences

**Applied To**:
- SSE streaming endpoint `/api/v1/sessions/{session_id}/stream`

**Gaps**:
- ❌ No server-side backoff for rapid client reconnects
- ⚠️ Event history fallback (Redis → PostgreSQL) not tested under Redis failure

---

## 3. Single Points of Failure

### 3.1 Critical Dependencies

| Dependency | Failure Mode | Impact | Mitigation | Status |
|------------|-------------|--------|-----------|--------|
| PostgreSQL | Connection failure | ❌ All writes fail, sessions cannot start | Circuit breaker + timeout | ⚠️ Partial (no query timeout) |
| Redis | Connection failure | ⚠️ SSE events lost, metadata stale | Auto-reconnect + circuit breaker | ✅ Good |
| Anthropic API | Rate limit / outage | ⚠️ LLM calls fail | Provider fallback (OpenAI) | ⚠️ Untested |
| Redis (checkpoints) | Data loss | ❌ Session resume impossible | Fallback to PostgreSQL checkpoints | ✅ Good |

**Analysis**:

1. **PostgreSQL**: No read replica support. All reads/writes hit primary. Under load, connection pool exhaustion (10 max) can cascade to full service outage.
   - **Risk**: Connection pool exhaustion → all requests fail → circuit opens → service unavailable
   - **Mitigation**: Pool degradation manager exists but load shedding is aggressive (90% threshold)

2. **Redis**: Non-critical for core functionality. SSE events are logged to PostgreSQL as backup. Metadata loss on Redis failure is acceptable (short-lived).
   - **Risk**: Redis down → SSE streams fail → users see stale data
   - **Mitigation**: Auto-reconnect + fallback to PostgreSQL event history

3. **Anthropic API**: Critical for all LLM operations. Fallback to OpenAI configured but not validated.
   - **Risk**: Anthropic outage → fallback not triggered → all sessions fail
   - **Mitigation**: Provider fallback exists but needs integration testing

4. **Redis Checkpoints**: Replaced by PostgreSQL checkpoints (CHECKPOINT_BACKEND=postgres). Fallback to in-memory checkpoints exists but loses state on restart.
   - **Risk**: Redis down + fallback disabled → checkpoint writes fail → sessions cannot resume
   - **Mitigation**: PostgreSQL checkpoints preferred in production

---

### 3.2 Cascading Failure Scenarios

**Scenario 1: PostgreSQL Pool Exhaustion**
```
High load (100 concurrent sessions)
  → All 10 pool connections in use
  → New session requests timeout after 5s
  → Circuit breaker opens after 5 consecutive failures
  → Service rejects all new sessions for 60s
  → Existing sessions continue but cannot save events
```

**Mitigation**: Load shedding at 90% utilization (9/10 connections). But this is **too aggressive** - sheds load too early.

**Recommendation**: Increase pool size to 20, adjust load shedding threshold to 95%.

---

**Scenario 2: Anthropic API Outage**
```
Anthropic API returns 500 errors
  → PromptBroker retries 3 times (max_retries=3)
  → Circuit breaker opens after 5 failures
  → Provider fallback to OpenAI SHOULD trigger
  → [UNTESTED] Does fallback work?
  → If not, all sessions fail immediately
```

**Mitigation**: Provider fallback configured but **not validated** in chaos tests.

**Recommendation**: Add chaos test: `test_anthropic_outage_triggers_openai_fallback`.

---

**Scenario 3: Redis Unavailable at Session Start**
```
Redis connection fails
  → RedisManager._available = False
  → Checkpoint backend falls back to in-memory (MemorySaver)
  → Session metadata writes succeed (PostgreSQL)
  → SSE events written to PostgreSQL only
  → [PARTIAL FAILURE] SSE clients get events from PostgreSQL fallback
  → [EDGE CASE] If PostgreSQL also fails, events lost entirely
```

**Mitigation**: PostgreSQL event fallback via `get_event_history_with_fallback()`.

**Recommendation**: Add monitoring alert: "Redis down + PostgreSQL event writes slow".

---

## 4. State Recovery Capability Assessment

### 4.1 Database Transactions

**Patterns Observed**:
```python
# Good: Automatic commit/rollback in db_session()
@contextmanager
def db_session(user_id: str | None = None, timeout: float = 5.0):
    conn = _getconn_with_timeout(pool_instance, timeout)
    try:
        yield conn
        conn.commit()  # Success path
    except Exception:
        conn.rollback()  # Failure path
        raise
    finally:
        pool_instance.putconn(conn)
```

**Transaction Boundaries**:
- ✅ Repository methods use `with db_session()` consistently
- ✅ Rollback on exception prevents partial writes
- ⚠️ Multi-repository operations (e.g., `save_tasks()`) use single transaction (good)

**Gaps**:
- ❌ No SAVEPOINT support for nested transactions
- ❌ Long-running transactions (e.g., `save_events_batch()` with 100+ events) may hold locks too long

**Example Gap**:
```python
# session_repository.save_tasks() - 100 tasks in single transaction
# If task 99 fails, entire batch rolls back (all-or-nothing)
# Better: Batch into chunks of 10-20 tasks with individual commits
```

---

### 4.2 LangGraph Checkpoint Recovery

**Current State**:
- Checkpoints saved to Redis or PostgreSQL (configurable)
- Checkpoints contain full graph state at each node transition
- **No recovery logic implemented**

**Patterns Observed**:
```python
# Checkpoints are created automatically by LangGraph
# But never loaded for recovery:
checkpointer = create_checkpointer("postgres")
graph = create_deliberation_graph(checkpointer=checkpointer)

# On failure:
session_repository.update_status(session_id, "failed", error=error_msg)
# User sees failed session, cannot resume from checkpoint
```

**Gaps**:
- ❌ **Critical**: No `resume_from_checkpoint()` function
- ❌ Failed sessions marked as unrecoverable (`"recoverable": False` in error event)
- ❌ No UI affordance to retry failed sessions

**Recommendation**: Implement checkpoint recovery:
```python
def resume_session_from_checkpoint(session_id: str) -> bool:
    """Resume failed session from last successful checkpoint."""
    # 1. Load session metadata (verify status='failed')
    # 2. Get latest checkpoint from LangGraph
    # 3. Resume graph execution from checkpoint
    # 4. Update status to 'running'
    return True
```

---

### 4.3 Replanning Service Rollback

**Current State**:
```python
def create_replan_session(self, action_id: str, user_id: str) -> dict:
    # 1. Create session in Redis + PostgreSQL ✅
    # 2. Link session to project ⚠️ (logs warning on failure)
    # 3. Update action with replan_session_id ⚠️ (logs warning on failure)
    # No rollback if step 2 or 3 fails
```

**Gaps**:
- ❌ Partial failure leaves orphaned session (created but not linked)
- ❌ Redis cleanup not called on PostgreSQL failure
- ⚠️ Error handling logs warnings but returns success response

**Example**:
```python
# Step 1 succeeds: session created in Redis + PostgreSQL
session_id = self.redis_manager.create_session()
session_repository.create(session_id=session_id, ...)

# Step 2 fails: project link fails (e.g., project_id invalid)
try:
    project_repository.link_session(project_id=project_id, session_id=session_id)
except Exception as e:
    logger.warning(f"Failed to link: {e}. Session created but not linked.")
    # [BUG] Should delete session here, but doesn't

# Step 3 fails: action update fails
try:
    self._update_action_replan_fields(...)
except Exception as e:
    logger.warning(f"Failed to update action: {e}. Session created but action not updated.")
    # [BUG] Returns success response anyway
```

**Recommendation**: Add rollback logic:
```python
except Exception as e:
    # Rollback: delete session from Redis + PostgreSQL
    try:
        self.redis_manager.delete_state(session_id)
        session_repository.delete(session_id)  # Need to add this method
    except Exception as cleanup_error:
        logger.error(f"Rollback failed: {cleanup_error}")
    raise RuntimeError("Failed to create replanning session") from e
```

---

### 4.4 SSE Stream Recovery

**Current State**:
- Client sends `Last-Event-ID` header on reconnect
- Server replays missed events from Redis or PostgreSQL
- Gap detection alerts client to missing events

**Patterns Observed**:
```python
# Good: Event replay from last known position
if resume_from_sequence > 0:
    missed_events = await get_event_history_with_fallback(
        redis_client=redis_client,
        session_id=session_id,
        last_event_id=last_event_id,
    )
    for payload in missed_events:
        yield format_sse_for_type(event_type, data)

# Good: Gap detection
if first_seq > expected_seq:
    missed_count = first_seq - expected_seq
    yield gap_detected_event(session_id, expected_seq, first_seq, missed_count)
```

**Gaps**:
- ⚠️ `get_event_history_with_fallback()` not covered by tests (Redis failure → PostgreSQL fallback)
- ❌ No client-side backoff for rapid reconnects (can spam server)

---

## 5. Graceful Degradation Recommendations

### 5.1 Database Pool Exhaustion

**Current**: Load shedding at 90% utilization (9/10 connections)
**Recommendation**:
1. Increase pool size to 20 connections (safer headroom)
2. Adjust load shedding threshold to 95% (19/20)
3. Add `queue_depth` metric to track queued requests

**Impact**: Reduce false-positive load shedding during normal load spikes.

---

### 5.2 LLM Provider Fallback

**Current**: Fallback configured but not actively exercised
**Recommendation**:
1. Add chaos test: `test_anthropic_circuit_open_triggers_openai_fallback`
2. Modify `PromptBroker.call()` to switch providers on retry exhaustion:
   ```python
   except APIError as e:
       if attempt == max_retries and fallback_enabled:
           logger.warning(f"Primary provider failed, switching to {fallback_provider}")
           provider = fallback_provider
           circuit_breaker = self._get_circuit_breaker(provider)
           # Retry with fallback provider
   ```

**Impact**: Automatic failover to secondary LLM provider on primary outage.

---

### 5.3 Redis Metadata Fallback

**Current**: Metadata lost when Redis unavailable
**Recommendation**:
1. Add `session_repository.save_metadata()` to write metadata to PostgreSQL as backup
2. Modify `SessionManager._save_session_metadata()` to dual-write:
   ```python
   def _save_session_metadata(self, session_id: str, metadata: dict) -> None:
       # Try Redis first (fast path)
       if self.redis_manager.is_available:
           self.redis_manager.save_metadata(session_id, metadata)
       # Always write to PostgreSQL (backup)
       session_repository.save_metadata(session_id, metadata)
   ```

**Impact**: Session metadata survives Redis failures.

---

### 5.4 Checkpoint Recovery UI

**Current**: Failed sessions show error message, no recovery option
**Recommendation**:
1. Add "Retry Session" button to failed session UI
2. Implement `POST /api/v1/sessions/{session_id}/retry` endpoint:
   ```python
   async def retry_session(session_id: str) -> dict:
       # Load latest checkpoint
       checkpoint = await checkpointer.aget(session_id)
       if not checkpoint:
           raise HTTPException(404, "No checkpoint found")
       # Resume graph from checkpoint
       await session_manager.resume_session(session_id, checkpoint)
       return {"status": "resumed"}
   ```

**Impact**: Users can recover from transient failures (e.g., LLM rate limit) without restarting.

---

### 5.5 SSE Reconnection Backoff

**Current**: No backoff for rapid client reconnects
**Recommendation**:
1. Track reconnection attempts in session metadata
2. Return `Retry-After` header on rapid reconnects:
   ```python
   reconnect_count = metadata.get("reconnect_count", 0)
   if reconnect_count > 3:
       backoff_seconds = min(2 ** reconnect_count, 60)
       return Response(
           status_code=429,
           headers={"Retry-After": str(backoff_seconds)},
           content="Too many reconnection attempts"
       )
   ```

**Impact**: Prevent client reconnection storms from overwhelming server.

---

## 6. Priority Action Items

### High Priority (P0 - Critical Gaps)

1. **Add LangGraph checkpoint recovery**
   - Implement `resume_session_from_checkpoint()` function
   - Add "Retry Session" UI affordance
   - **Impact**: Users can recover from transient failures

2. **Fix replanning service rollback**
   - Add session cleanup on link/update failures
   - Return error on partial failure (not success)
   - **Impact**: Prevent orphaned sessions

3. **Validate LLM provider fallback**
   - Add chaos test: Anthropic outage → OpenAI fallback
   - Modify retry loop to switch providers on exhaustion
   - **Impact**: Automatic failover on primary LLM outage

### Medium Priority (P1 - Reliability Improvements)

4. **Add Redis metadata fallback to PostgreSQL**
   - Dual-write session metadata to Redis + PostgreSQL
   - **Impact**: Metadata survives Redis failures

5. **Increase database pool size**
   - Change from 10 → 20 connections
   - Adjust load shedding threshold from 90% → 95%
   - **Impact**: Reduce false-positive load shedding

6. **Add SSE reconnection backoff**
   - Track reconnect attempts, return `Retry-After` header
   - **Impact**: Prevent client reconnection storms

### Low Priority (P2 - Monitoring/Observability)

7. **Add deadlock retry to @retry_db**
   - Handle 40P01 errors with retry
   - **Impact**: Automatic recovery from transient deadlocks

8. **Add query timeout to database operations**
   - Set `statement_timeout` on long-running queries
   - **Impact**: Prevent runaway queries from holding locks

9. **Test PostgreSQL event fallback under Redis failure**
   - Chaos test: Redis down → SSE clients get events from PostgreSQL
   - **Impact**: Validate fallback path

---

## Conclusion

The codebase demonstrates **strong foundational reliability** with comprehensive retry logic, circuit breakers, and connection management. However, **critical gaps in state recovery** (LangGraph checkpoints, replanning rollback) and **untested fallback paths** (LLM provider fallback, Redis → PostgreSQL) pose risks to production reliability.

**Overall Grade**: **B+** (Strong patterns, needs recovery implementation)

**Top Risks**:
1. Failed sessions cannot resume (no checkpoint recovery)
2. Replanning service creates orphaned sessions on partial failure
3. LLM provider fallback untested (may not work in production)

**Recommended Next Steps**:
1. Implement checkpoint recovery (P0)
2. Fix replanning rollback (P0)
3. Validate LLM provider fallback with chaos tests (P0)
