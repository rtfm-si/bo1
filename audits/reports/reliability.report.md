# Reliability Audit Report
**Date:** 2025-12-08

## Error Handling Coverage

### Exception Patterns (56 try/except blocks across 20 files)

| Component | Exceptions Caught | Severity |
|-----------|-------------------|----------|
| redis_manager.py | 15 | ✅ Comprehensive |
| researcher.py | 6 | ✅ Good |
| replanning_service.py | 4 | ✅ Good |
| console.py | 4 | ✅ Good |
| user_repository.py | 3 | ⚠️ Medium |
| research_metrics.py | 3 | ⚠️ Medium |
| database.py | 3 | ⚠️ Medium |

### Critical Path Error Handling

| Path | Wrapped | Recovery Action |
|------|---------|-----------------|
| Graph execution | ✅ | Status update + error event |
| LLM API calls | ✅ | Retry with backoff |
| Redis operations | ✅ | Fallback to PostgreSQL |
| DB writes | ⚠️ | Transaction rollback only |
| SSE publishing | ✅ | Log and continue |

## Retry Strategy Inventory

### Implemented Retries

| Component | Strategy | Max Retries | Backoff |
|-----------|----------|-------------|---------|
| `researcher.py` | Exponential | 3 | 2^n seconds |
| `redis_manager.py` | Immediate retry | 2 | None |
| `rounds.py` parallel_round | Retry failed experts | 1 | None |
| `persistence_worker.py` | Background retry | 3 | 60s intervals |

### Missing Retry Patterns ❌

1. **Database connection failures** - No retry on pool exhaustion
2. **Anthropic rate limits** - Caught but not retried
3. **Embedding API failures** - Single attempt only
4. **SSE reconnection** - Client-side only

## Single Points of Failure

### Critical SPOFs ❌

1. **PostgreSQL**
   - No read replica failover
   - Connection pool exhaustion = full outage
   - **Impact**: Session creation blocked, no event persistence

2. **Redis**
   - Checkpoint storage single instance
   - **Mitigation**: Fallback to in-memory state exists
   - **Impact**: Session resume fails if Redis down

3. **Anthropic API**
   - All LLM calls go to single provider
   - **Impact**: Full deliberation stall on outage

### Partial SPOFs ⚠️

4. **Voyage AI** - Embedding failures cause semantic dedup to skip
5. **Brave/Tavily** - Research fails but deliberation continues

## State Recovery Capability

### Session Recovery Flow

```
Session Created → Redis Checkpoint → PostgreSQL Events
                         ↓
                  (On Redis Failure)
                         ↓
              Load from PostgreSQL events
              Reconstruct state via event replay
```

### Recovery Capabilities

| Scenario | Recovery Method | Data Loss |
|----------|-----------------|-----------|
| Redis restart | Checkpoint restore | None (if TTL not expired) |
| API pod restart | Redis checkpoint | None |
| Mid-round crash | Resume from checkpoint | Current round only |
| PostgreSQL restart | Events persisted | None |
| Full Redis loss | Event replay | Checkpoint state |

### Recovery Gaps

1. **No automatic session resume** - User must manually reconnect
2. **Checkpoint TTL (7 days)** - Old sessions unrecoverable
3. **Event ordering** - Sequence gaps possible if persistence fails

## Transaction Boundaries

### Database Transactions

| Operation | Transaction | Isolation |
|-----------|-------------|-----------|
| Session create | ✅ Atomic | READ COMMITTED |
| Event batch save | ✅ Atomic | READ COMMITTED |
| Contribution save | ✅ Single row | READ COMMITTED |
| Session update | ✅ Optimistic | READ COMMITTED |

### Transaction Issues

1. **No distributed transactions** - Redis + PostgreSQL not atomic
2. **Event persistence retry** - Could create duplicates (sequence-based dedup exists)
3. **Session status race** - Optimistic locking not enforced

## Graceful Degradation

### Current Degradation Paths

| Failure | Degradation Behavior |
|---------|---------------------|
| Redis unavailable | Use in-memory state, warn user |
| Research API failure | Skip research, continue with experts only |
| Embedding failure | Skip semantic dedup, allow potential duplicates |
| Moderator failure | Continue without moderation |
| Cost tracking failure | Log error, continue deliberation |

### Missing Degradation ❌

1. **No LLM fallback** - Single provider dependency
2. **No circuit breaker** - Repeated failures not rate-limited
3. **No partial result return** - All-or-nothing synthesis

## Recommendations

### P0 - Critical
1. **Add PostgreSQL connection retry** - Implement retry with exponential backoff on pool exhaustion
2. **Add LLM rate limit handling** - Retry with backoff on 429 responses

### P1 - High Value
3. **Implement circuit breaker** - For external APIs (Anthropic, Voyage, Brave)
4. **Add automatic session resume** - Reconnect SSE clients to in-progress sessions
5. **Add distributed locking** - For session status updates via Redis SETNX

### P2 - Nice to Have
6. **Add LLM fallback provider** - OpenAI as backup for Anthropic outages
7. **Extend checkpoint TTL** - Or add PostgreSQL-based checkpointing
8. **Add chaos testing** - Validate recovery paths with fault injection
