# Observability Audit Report
**Date:** 2025-12-08

## Logging Coverage Map

### Backend API (262 log statements across 20 files)

| Component | Log Count | Coverage |
|-----------|-----------|----------|
| event_collector.py | 48 | ✅ High |
| control.py | 53 | ✅ High |
| oauth_session_manager.py | 25 | ✅ Good |
| actions.py | 22 | ✅ Good |
| event_publisher.py | 21 | ✅ Good |
| business_metrics.py | 16 | ✅ Good |
| streaming.py | 16 | ✅ Good |
| supertokens_config.py | 14 | ✅ Good |
| persistence_worker.py | 11 | ⚠️ Medium |
| context/routes.py | 9 | ⚠️ Medium |

### Core Graph Components

| Component | Coverage | Notes |
|-----------|----------|-------|
| config.py | ✅ Good | Graph construction logged |
| routers.py | ✅ Good | All routing decisions logged |
| rounds.py | ✅ Good | Contribution generation logged |
| event_collector.py | ✅ Excellent | SSE events with debug prefixes |

### Logging Patterns Used

1. **Structured prefixes**: `[EVENT DEBUG]`, `[CONTRIBUTION DEBUG]`, `[CONVERGENCE DEBUG]`
2. **Context in messages**: Session ID, round number, sub_problem_index included
3. **Cost tracking**: `${cost:.4f}` format for monetary values

## Missing Observability Points

### Critical Gaps ❌

1. **No distributed tracing correlation IDs**
   - Request ID not passed through LangGraph execution
   - Cannot trace single meeting across all API calls
   - **Impact**: Debugging multi-step failures is difficult

2. **No health checks for external dependencies**
   - Redis connectivity not checked
   - PostgreSQL pool health not exposed
   - Anthropic API status not monitored

3. **No frontend error capture**
   - SSE connection failures not logged server-side
   - Client-side errors not reported back

### Medium Gaps ⚠️

4. **Checkpoint operations not logged**
   - Redis checkpoint writes/reads silent
   - Cannot track checkpoint size growth

5. **Embedding generation not observable**
   - Voyage API calls tracked in api_costs but no separate metrics
   - Semantic dedup cache hits not logged

## Health Check Assessment

### Current Health Endpoints
Based on codebase analysis:
- No dedicated `/health` endpoint found in routes
- No `/ready` or `/live` endpoints for Kubernetes

### Recommended Health Checks

| Check | Endpoint | Timeout |
|-------|----------|---------|
| API alive | `/health/live` | 1s |
| PostgreSQL | `/health/ready/db` | 5s |
| Redis | `/health/ready/redis` | 2s |
| Anthropic API | `/health/ready/llm` | 10s |

## Cost Tracking Completeness

### Tracked in `api_costs` Table ✅
- All Anthropic calls (CostTracker context manager)
- Voyage embeddings
- Brave/Tavily searches
- Attribution: session_id, node_name, phase, persona_name, round_number

### Cost Tracking Gaps
1. **Summarization costs** - Haiku calls for contribution summaries tracked
2. **Research detection** - Tracked via CostTracker
3. **Quality checks** - Tracked via `track_accumulated_cost()`

### Missing Attribution
- User-level cost aggregation exists but no alerts for high-cost users
- No cost anomaly detection (e.g., 10x normal session cost)

## Tracing Correlation ID Coverage

### Current State
- `session_id` used as primary correlation key
- Logged in most event_collector handlers
- NOT passed to LLM calls or Redis operations

### Recommended Trace Context

```
X-Request-ID: uuid-from-client
session_id: bo1_xxxxx
trace_id: derived-from-request
span_id: per-node-execution
```

## Alert Threshold Recommendations

### Cost Alerts

| Metric | Warning | Critical |
|--------|---------|----------|
| Session cost | >$0.50 | >$1.00 |
| Daily user cost | >$5.00 | >$10.00 |
| Research loop count | >2 | >3 |

### Latency Alerts

| Operation | P95 Warning | P95 Critical |
|-----------|-------------|--------------|
| SSE first event | >10s | >30s |
| Round completion | >30s | >60s |
| Meeting total | >5min | >10min |

### Error Rate Alerts

| Metric | Warning | Critical |
|--------|---------|----------|
| SSE disconnect rate | >5% | >20% |
| LLM retry rate | >10% | >30% |
| DB connection errors | Any | >5/hour |

## Recommendations

### P0 - Critical
1. **Add correlation IDs** - Generate trace ID at API entry, pass through graph execution
2. **Create health endpoint** - `/health` with db/redis/llm checks

### P1 - High Value
3. **Add cost anomaly alerts** - Flag sessions >$1.00
4. **Log checkpoint operations** - Size, latency, errors
5. **Capture SSE connection lifecycle** - Connect/disconnect events with client info

### P2 - Nice to Have
6. **Add structured JSON logging** - Replace text logs with structured format
7. **Create observability dashboard** - Grafana/DataDog metrics
8. **Add client error reporting** - Frontend → backend error bridge
