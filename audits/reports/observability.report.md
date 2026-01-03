# Observability Audit Report
**Date:** 2026-01-03 (Re-audit - no new issues since 2025-12-30)
**Scope:** Logging patterns, error handling, health checks, cost tracking, event stream observability
**Status:** ⚠️ Moderate gaps identified

---

## Executive Summary

Bo1 has a **solid observability foundation** with structured logging, correlation IDs, Prometheus metrics, and comprehensive health endpoints. However, several critical gaps exist in error context propagation, missing observability points, and incomplete health coverage that could hinder production troubleshooting.

**Key Findings:**
- ✅ **Strong:** Structured logging (JSON), correlation IDs, centralized error codes, Prometheus metrics
- ✅ **Strong:** Comprehensive health endpoints (11 distinct checks), cost tracking with batching
- ⚠️ **Moderate:** Missing correlation ID propagation in graph execution
- ⚠️ **Moderate:** Event persistence has limited visibility into batching/retry metrics
- ⚠️ **Moderate:** No structured logging for critical graph node errors (exceptions swallowed)
- ⚠️ **Critical:** No Redis connection pool health metrics (only ping check)
- ⚠️ **Critical:** LLM provider circuit breaker state not exposed in metrics (only health endpoint)

---

## 1. Logging Coverage Map

### Components with Structured Logging

| Component | Logger Name | Log Levels Used | Correlation ID | Error Codes |
|-----------|-------------|-----------------|----------------|-------------|
| **API Layer** |
| main.py | `__name__` | INFO, WARNING, ERROR | ✅ | ⚠️ (manual) |
| health.py | `backend.api.health` | INFO, WARNING, ERROR | ✅ | ❌ |
| event_collector.py | `backend.api.event_collector` | DEBUG, INFO, WARNING, ERROR | ✅ | ⚠️ (partial) |
| event_publisher.py | `backend.api.event_publisher` | DEBUG, INFO, WARNING, ERROR | ✅ | ⚠️ (partial) |
| streaming.py | `backend.api.streaming` | INFO, WARNING, ERROR | ✅ | ❌ |
| control.py | `backend.api.control` | INFO, WARNING, ERROR | ✅ | ❌ |
| **Cost Tracking** |
| cost_tracker.py | `bo1.llm.cost_tracker` | DEBUG, INFO, WARNING, CRITICAL | ⚠️ (session only) | ✅ |
| **Graph Execution** |
| nodes/*.py | `bo1.graph.nodes.*` | INFO, WARNING, ERROR | ❌ | ⚠️ (inconsistent) |
| checkpointer.py | `bo1.graph.checkpointer` | WARNING, ERROR | ❌ | ✅ |
| routers.py | `bo1.graph.routers` | INFO, WARNING | ❌ | ✅ |
| **LLM Layer** |
| broker.py | `bo1.llm.broker` | INFO, WARNING, ERROR | ❌ | ✅ |
| circuit_breaker.py | `bo1.llm.circuit_breaker` | WARNING, ERROR | ❌ | ❌ |

### Logging Configuration

**Format:** Dual mode support (text for dev, JSON for prod)
```python
# Text: "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
# JSON: {"timestamp":"...","level":"...","logger":"...","message":"..."}
```

**Log Levels:** Configurable via `LOG_LEVEL` env var (default: INFO)

**Suppressed Loggers:** uvicorn.access, httpx, httpcore, asyncpg, aiobotocore, botocore, urllib3 (WARNING+ only)

**Structured Error Codes:** Defined in `bo1.logging.errors.ErrorCode` (28 codes across 8 categories)

---

## 2. Missing Observability Points

### Critical Gaps

#### 2.1 Graph Node Error Context Loss
**Issue:** Graph node exceptions are caught but not logged with full context
- **Location:** `bo1/graph/nodes/*.py` (8 files, 125 log calls)
- **Problem:** Try-catch blocks in nodes log errors but don't include:
  - Session ID for correlation
  - Sub-problem index
  - Round number
  - Persona context
- **Impact:** Cannot trace which session/problem caused node failure
- **Example:**
```python
# Current (insufficient context):
logger.error(f"Failed to synthesize: {e}")

# Should be:
log_error(
    logger,
    ErrorCode.GRAPH_NODE_ERROR,
    f"Synthesis failed for session {session_id}",
    exc_info=True,
    session_id=session_id,
    sub_problem_index=state.sub_problem_index,
    round_number=state.round_number
)
```

#### 2.2 Correlation ID Not Propagated Through Graph
**Issue:** Request ID set in API layer but not available in graph nodes
- **Location:** `backend/api/middleware/correlation_id.py` sets ID, but `bo1/graph/` doesn't access it
- **Problem:** Graph execution logs lack correlation to originating API request
- **Impact:** Cannot trace API request → graph execution → node failure
- **Current State:**
  - ✅ API middleware sets `request.state.request_id`
  - ✅ `EventCollector.collect_and_publish()` accepts `request_id` param
  - ❌ `request_id` not stored in graph state
  - ❌ Nodes don't log with `request_id`

#### 2.3 Event Persistence Batch Metrics Gap
**Issue:** No Prometheus metrics for event batching/persistence health
- **Location:** `backend/api/event_publisher.py`
- **Missing Metrics:**
  - Batch flush latency (p50, p95, p99)
  - Batch size distribution
  - Retry queue depth trend over time
  - Persistence failure rate
  - Events dropped due to buffer overflow
- **Current State:**
  - ✅ Logs batch flush success/failure
  - ❌ No metrics exposed for Grafana dashboards
  - ❌ Cannot alert on persistence degradation

#### 2.4 Redis Connection Pool Metrics
**Issue:** Redis health check only pings, no pool metrics
- **Location:** `backend/api/health.py::health_check_redis()`
- **Missing:**
  - Active connections count
  - Pool utilization %
  - Connection acquisition latency
  - Connection errors/timeouts
- **Current State:**
  - ✅ Basic ping test
  - ❌ No visibility into connection exhaustion

#### 2.5 Circuit Breaker Metrics Not Exposed
**Issue:** Circuit breaker state available via health endpoint but not Prometheus
- **Location:** `bo1/llm/circuit_breaker.py`
- **Missing:**
  - Per-provider circuit state (closed/open/half_open) as gauge
  - State transition events
  - Failure count trends
  - Recovery success rate
- **Current State:**
  - ✅ `/health/circuit-breakers` returns JSON state
  - ❌ No `circuit_breaker_state{provider="anthropic"}` metric
  - ❌ Cannot alert on circuit opens

---

## 3. Health Check Completeness

### Available Health Endpoints (11 total)

| Endpoint | Coverage | Response Time | Dependencies |
|----------|----------|---------------|--------------|
| `/health` | ✅ Liveness (process alive) | <10ms | None |
| `/ready` | ✅ Readiness (Postgres + Redis) | <100ms | Postgres, Redis |
| `/health/db` | ✅ Postgres connectivity | <50ms | Postgres |
| `/health/db/pool` | ✅ Pool health + utilization | <100ms | Postgres |
| `/health/redis` | ✅ Redis ping | <50ms | Redis |
| `/health/anthropic` | ⚠️ Config check only (no API call) | <10ms | None |
| `/health/voyage` | ⚠️ API key format check | <10ms | None |
| `/health/brave` | ⚠️ API key format check | <10ms | None |
| `/health/persistence` | ✅ Event persistence integrity | <500ms | Redis, Postgres |
| `/health/circuit-breakers` | ✅ Circuit state summary | <10ms | None |
| `/health/checkpoint` | ✅ LangGraph checkpointer | <100ms | Redis/Postgres |
| `/health/detailed` | ✅ Event queue + circuits | <50ms | Batcher, Circuits |

### Health Check Gaps

#### 3.1 External API Checks Don't Validate Connectivity
**Issue:** `/health/anthropic`, `/health/voyage`, `/health/brave` only check if API key is configured
- **Missing:** Actual test API call to validate credentials and connectivity
- **Rationale (per code comment):** "This endpoint does NOT make actual API calls to avoid costs"
- **Impact:** False positive if API key is revoked or provider is down
- **Recommendation:** Implement periodic background probe (e.g., every 5 min) with cached result

#### 3.2 No Unified Degraded Mode Indicator
**Issue:** Multiple health endpoints but no single "can accept traffic" status
- **Current:** `/ready` checks Postgres + Redis only
- **Missing:** Should also check:
  - At least one LLM provider circuit is closed
  - Event persistence queue depth < threshold
  - DB pool utilization < critical threshold
- **Impact:** K8s may route traffic to instance that can't execute deliberations

#### 3.3 No Health History/Trend Data
**Issue:** All health checks are point-in-time snapshots
- **Missing:**
  - Last 5 health check results with timestamps
  - Flap detection (e.g., Postgres up/down/up within 1 min)
  - Degradation trend (e.g., pool utilization increasing 5% per hour)
- **Impact:** Cannot diagnose intermittent issues or detect gradual degradation

---

## 4. Cost Tracking Observability

### Strengths

✅ **Comprehensive tracking:** Input/output/cache tokens, cost breakdown by provider, phase, sub-problem
✅ **Batched persistence:** Reduces DB overhead (flush at 100 records or 30s interval)
✅ **Retry queue:** Failed cost flushes pushed to Redis for recovery
✅ **Idempotency:** `ON CONFLICT (request_id, created_at) DO NOTHING` prevents duplicates
✅ **Budget checks:** Session cost warnings at 80%, exceeded alerts at 100%
✅ **Prometheus metrics:** `record_tokens()`, `record_cost()`, `observe_llm_request()`

### Gaps

#### 4.1 Retry Queue Metrics Not Exposed
**Issue:** Retry queue depth logged but not exposed as metric
- **Location:** `bo1/llm/cost_tracker.py::_push_to_retry_queue()`
- **Current:** Logs warning if queue depth > 100
- **Missing:**
  - `cost_retry_queue_depth` gauge
  - `cost_retry_attempts_total` counter
  - `cost_retry_success_rate` ratio

#### 4.2 Buffer Flush Latency Not Tracked
**Issue:** No metrics for cost flush performance
- **Missing:**
  - `cost_flush_duration_seconds` histogram
  - `cost_flush_batch_size` histogram
  - `cost_flush_failures_total` counter

#### 4.3 Cost Anomaly Detection Silent
**Issue:** `_check_cost_anomaly()` emits event but no persistent alert
- **Current:** Logs warning + emits `cost_anomaly` event (ephemeral)
- **Missing:**
  - Alert sent to ntfy topic
  - Metric for anomaly count per user
  - Anomaly threshold configurable per environment

---

## 5. Event Stream Observability

### Current State

**Architecture:** SSE stream → Redis PubSub → EventPublisher → Batcher → PostgreSQL

**Components:**
1. **EventCollector:** Wraps LangGraph execution, dispatches node events
2. **EventPublisher:** Publishes to Redis, batches for Postgres
3. **EventBatcher:** Priority-based batching (completion events first)
4. **Persistence Worker:** Retries failed persistence jobs

### Coverage

| Aspect | Status | Notes |
|--------|--------|-------|
| Event emission | ✅ | All node completions mapped to events |
| Redis publish | ✅ | Logged per event with session ID |
| Batch formation | ⚠️ | Logged but no metrics |
| Postgres insert | ✅ | Logged with retry on failure |
| Persistence verification | ✅ | Compares Redis vs Postgres counts at completion |
| Retry queue | ⚠️ | Exists but depth not tracked in metrics |

### Gaps

#### 5.1 Event Publish Latency Not Measured
**Issue:** No visibility into SSE stream lag
- **Missing:**
  - Time from node completion to Redis publish
  - Time from Redis publish to client receive (SSE)
  - Batch flush wait time (time event spent in buffer)

#### 5.2 Event Type Distribution Not Tracked
**Issue:** Cannot see which event types dominate traffic
- **Missing:** `events_published_total{event_type="contribution"}` counter
- **Impact:** Cannot optimize batching strategy by event frequency

#### 5.3 Batch Priority Queue Metrics
**Issue:** EventBatcher uses priority queue but no visibility
- **Missing:**
  - Current queue depth per priority level
  - Priority inversion events (low priority delayed >30s)
  - Flush trigger breakdown (size vs timeout)

---

## 6. Error Handling and Exception Propagation

### Current State

**Error Code Registry:** 28 codes across 8 categories (LLM, DB, Redis, Parse, Service, Graph, Auth, API)

**Structured Logging:** `log_error(logger, ErrorCode.*, message, exc_info=True, **context)`

**Exception Handling Patterns:**
- ✅ API layer: Global exception handler in `main.py`
- ✅ Cost tracker: Errors logged with `ErrorCode.COST_*`
- ✅ LLM broker: Circuit breaker logs with `ErrorCode.LLM_CIRCUIT_OPEN`
- ⚠️ Graph nodes: Inconsistent use of `log_error()` vs plain `logger.error()`
- ⚠️ Event collector: Some exceptions swallowed without context

### Gaps

#### 6.1 Inconsistent Error Code Usage
**Issue:** Some components log errors without using `ErrorCode` enum
- **Files with errors logged without codes:**
  - `backend/api/streaming.py` (18 log calls)
  - `backend/api/sessions.py` (55 log calls)
  - `backend/api/health.py` (2 log calls)
- **Impact:** Cannot filter/aggregate errors by category in Loki

#### 6.2 Missing Exception Context in Graph Nodes
**Issue:** Graph node exceptions don't include session/state context
- **Example:** `bo1/graph/nodes/synthesis.py` catches exceptions but logs generic message
- **Missing Context:**
  - Session ID
  - Sub-problem index
  - Round number
  - Current phase
- **Impact:** Cannot correlate errors to specific deliberations

#### 6.3 No Error Rate Metrics by Component
**Issue:** Prometheus alerts configured but base metrics not exposed
- **Alert:** `bo1_graph_node_total{status="error"}` (alert_rules.yml:18)
- **Problem:** Metric not emitted by graph nodes
- **Current:** Only HTTP error rates tracked via Prometheus instrumentator

---

## 7. Alert Threshold Recommendations

### Database Pool

| Metric | Warning | Critical | Current |
|--------|---------|----------|---------|
| Utilization % | >80% for 5m | >95% for 2m | ✅ Configured |
| Queue Depth | >10 for 2m | >50 for 1m | ⚠️ Only >10 configured |
| Degraded Mode | Active for 1m | Active for 5m | ⚠️ Warning only |

**Recommended Addition:**
```yaml
- alert: DBPoolQueueCritical
  expr: bo1_db_pool_queue_depth > 50
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "CRITICAL: DB pool queue severely backlogged"
```

### Event Persistence

| Metric | Warning | Critical | Current |
|--------|---------|----------|---------|
| Retry Queue Depth | >100 | >500 | ❌ Not configured |
| Persistence Rate | <99% | <95% | ❌ Not tracked |
| Batch Flush Failures | >5/min | >20/min | ❌ Not tracked |

**Recommended Additions:**
```yaml
- alert: EventPersistenceRetryBacklog
  expr: event_retry_queue_depth > 100
  for: 5m
  labels:
    severity: warning

- alert: EventPersistenceFailureRate
  expr: rate(event_persistence_failures_total[5m]) > 5
  for: 2m
  labels:
    severity: warning
```

### Circuit Breakers

| Metric | Warning | Critical | Current |
|--------|---------|----------|---------|
| Circuit Open | Any circuit | Anthropic circuit | ❌ Not configured |
| Half-Open Duration | >5 min | >15 min | ❌ Not tracked |
| Recovery Failures | >3 in 10m | >10 in 10m | ❌ Not tracked |

**Recommended Additions:**
```yaml
- alert: LLMProviderCircuitOpen
  expr: circuit_breaker_state{provider="anthropic"} == 1
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "CRITICAL: Anthropic circuit breaker open"

- alert: CircuitRecoveryStuck
  expr: circuit_breaker_state{state="half_open"} > 0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Circuit stuck in half-open for >5 min"
```

### Cost Tracking

| Metric | Warning | Critical | Current |
|--------|---------|----------|---------|
| Session Cost | >$0.50 | >$1.00 | ⚠️ Logged only |
| Retry Queue | >100 | >500 | ⚠️ Ntfy only |
| Flush Failures | >5/hour | >20/hour | ❌ Not tracked |

**Recommended Additions:**
```yaml
- alert: CostTrackingRetryBacklog
  expr: cost_retry_queue_depth > 100
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Cost tracking retry queue backlog"
```

---

## 8. Tracing and Correlation ID Coverage

### Current Coverage

| Layer | Correlation ID | Propagation | Logged |
|-------|----------------|-------------|--------|
| **Incoming HTTP Request** | ✅ X-Request-ID | - | ✅ |
| **API Middleware** | ✅ request.state | → | ✅ |
| **EventCollector** | ✅ Param accepted | ⚠️ Not stored | ⚠️ |
| **Graph Execution** | ❌ | - | ❌ |
| **Graph Nodes** | ❌ | - | ❌ |
| **LLM Broker** | ❌ | - | ❌ |
| **Cost Tracker** | ❌ | - | ❌ |
| **EventPublisher** | ❌ | - | ⚠️ Session ID only |

### Propagation Flow

```
HTTP Request (X-Request-ID: abc-123)
  ↓ CorrelationIdMiddleware
  → request.state.request_id = "abc-123"
  → set_correlation_id("abc-123")  # contextvars
  ↓ /api/sessions/{id}/execute
  → collector.collect_and_publish(request_id="abc-123")
  ↓ Graph Execution
  ❌ request_id NOT in state
  ❌ Nodes log without request_id
  ❌ LLM calls lack correlation
```

### Gap Analysis

#### 8.1 Graph State Lacks request_id Field
**Issue:** Request ID not stored in `DeliberationGraphState`
- **Location:** `bo1/graph/state.py`
- **Impact:** Cannot correlate graph logs to originating API request
- **Fix Required:**
```python
@dataclass
class DeliberationGraphState:
    # ... existing fields
    request_id: str | None = None  # Add correlation ID
```

#### 8.2 Nodes Don't Access Correlation ID
**Issue:** Even if request_id in state, nodes don't log with it
- **Current Pattern:**
```python
logger.error(f"Synthesis failed: {e}")
```
- **Should Be:**
```python
log_error(
    logger,
    ErrorCode.GRAPH_NODE_ERROR,
    f"Synthesis failed",
    exc_info=True,
    request_id=state.request_id,
    session_id=state.session_id,
)
```

#### 8.3 LLM Broker Lacks Tracing
**Issue:** LLM API calls don't include request_id in logs
- **Impact:** Cannot trace "which API request triggered this LLM call?"
- **Current:** Logs session_id, node_name, but not request_id

---

## 9. Summary of Critical Recommendations

### Priority 1 (Critical - Impairs Production Troubleshooting)

1. **Add correlation ID to graph state and node logs**
   - Store `request_id` in `DeliberationGraphState`
   - Update all graph nodes to log with `request_id`
   - Propagate through LLM broker calls

2. **Expose circuit breaker state as Prometheus metrics**
   - `circuit_breaker_state{provider, state}` gauge
   - Configure alerts for circuit opens

3. **Add event persistence metrics**
   - `event_persistence_batch_size` histogram
   - `event_persistence_duration_seconds` histogram
   - `event_retry_queue_depth` gauge

4. **Add Redis connection pool metrics**
   - Active connections count
   - Pool utilization %
   - Connection acquisition latency

### Priority 2 (High - Improves Operational Visibility)

5. **Standardize error code usage across all components**
   - Audit `backend/api/*.py` for plain `logger.error()` calls
   - Replace with `log_error(logger, ErrorCode.*, ...)`

6. **Add cost tracking metrics**
   - `cost_flush_duration_seconds` histogram
   - `cost_retry_queue_depth` gauge
   - `cost_anomaly_total` counter

7. **Enhance health check probes**
   - Add background LLM provider health probe (cached result)
   - Add unified degraded mode check to `/ready`
   - Add health check history (last 5 results)

8. **Configure missing Prometheus alerts**
   - Event persistence retry backlog
   - Circuit breaker opens
   - Cost tracking failures

### Priority 3 (Medium - Operational Improvements)

9. **Add structured context to graph node errors**
   - Include session_id, sub_problem_index, round_number in exceptions

10. **Add event stream metrics**
    - Event publish latency
    - Event type distribution
    - Batch priority queue depth

11. **Add error rate metrics by component**
    - `graph_node_errors_total{node_name}` counter
    - `api_endpoint_errors_total{endpoint, status}` counter

---

## Appendix A: Logging Component Inventory

### Backend API (34 files with logging)
- event_collector.py (64 calls)
- control.py (68 calls)
- sessions.py (55 calls)
- event_publisher.py (46 calls)
- actions.py (43 calls)
- supertokens_config.py (33 calls)
- billing.py (33 calls)
- datasets.py (32 calls)
- oauth_session_manager.py (25 calls)
- user.py (23 calls)
- streaming.py (18 calls)
- business_metrics.py (16 calls)
- auth.py (14 calls)
- persistence_worker.py (11 calls)
- email.py (11 calls)
- contribution_summarizer.py (10 calls)
- main.py (7 calls)
- industry_insights.py (5 calls)
- tags.py (5 calls)
- competitors.py (4 calls)
- ntfy.py (4 calls)
- feedback.py (3 calls)
- onboarding.py (3 calls)
- analysis.py (2 calls)
- client_errors.py (2 calls)
- csp_reports.py (2 calls)
- event_bridge.py (2 calls)
- health.py (2 calls)
- mentor.py (2 calls)
- page_analytics.py (2 calls)
- client_metrics.py (2 calls)
- logging_config.py (1 call)
- projects.py (1 call)
- waitlist.py (1 call)

### Core Library (11 files with logging)
- bo1/graph/nodes/context.py (35 calls)
- bo1/graph/nodes/rounds.py (27 calls)
- bo1/graph/nodes/synthesis.py (16 calls)
- bo1/graph/nodes/subproblems.py (16 calls)
- bo1/graph/nodes/research.py (13 calls)
- bo1/llm/broker.py (11 calls)
- bo1/graph/checkpointer.py (11 calls)
- bo1/graph/routers.py (11 calls)
- bo1/llm/cost_tracker.py (10 calls)
- bo1/graph/nodes/moderation.py (8 calls)
- bo1/graph/nodes/data_analysis.py (6 calls)

### Total Logging Coverage
- **Backend:** 552 log calls across 34 files
- **Core:** 125 log calls across 11 files
- **Total:** 677+ structured log calls

---

## Appendix B: Health Endpoint Details

### /health (Liveness Probe)
- **Purpose:** K8s liveness probe
- **Checks:** Process alive
- **Response Time:** <10ms
- **Failure Condition:** Never (always returns 200)

### /ready (Readiness Probe)
- **Purpose:** K8s readiness probe
- **Checks:** Postgres (SELECT 1), Redis (PING)
- **Response Time:** <100ms
- **Failure Condition:** Any check fails → 503
- **Gap:** Doesn't check if LLM providers available

### /health/db/pool
- **Purpose:** Pool health monitoring
- **Checks:** Pool initialized, checkout test, SELECT 1
- **Metrics Returned:**
  - `used_connections`
  - `free_connections`
  - `pool_utilization_pct`
  - `pool_degraded` (boolean)
  - `queue_depth`
- **Updates Prometheus:** ✅ via `prom_metrics.update_pool_metrics()`

### /health/persistence
- **Purpose:** Verify event persistence integrity
- **Checks:** Compares Redis event count vs Postgres for last 20 sessions
- **Thresholds:**
  - Healthy: 100% persistence rate
  - Warning: 95-99% or minor discrepancies
  - Critical: <95% or sessions with zero Postgres events
- **Response Time:** <500ms (queries both Redis and Postgres)
- **Gap:** No metrics exposed, only logged

### /health/circuit-breakers
- **Purpose:** Monitor circuit breaker state
- **Returns:**
  - Per-service state (closed/open/half_open)
  - Failure/success counts
  - Uptime since last state change
- **Gap:** Not exposed as Prometheus metrics

### /health/detailed
- **Purpose:** Operational health dashboard
- **Combines:**
  - Event queue depth (batcher)
  - Circuit breaker state summary
- **Thresholds:**
  - Queue warning: >50 events
  - Queue critical: >100 events
- **Response:** 200 if healthy, 503 if critical
