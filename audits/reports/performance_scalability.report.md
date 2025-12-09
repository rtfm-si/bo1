# Performance Scalability Audit Report
**Date:** 2025-12-08

## Query Pattern Analysis

### Session Repository
| Query | Pattern | Concern |
|-------|---------|---------|
| `list_by_user` | 4 correlated subqueries | N+1 risk at scale; each session triggers 4 COUNT queries |
| `get_events` | Full table scan with ORDER BY | No index on `(session_id, sequence)` composite |
| `save_tasks` | Loop with multiple INSERTs | Batching would reduce round trips |

### Contribution Repository
| Query | Pattern | Concern |
|-------|---------|---------|
| `save_contribution` | Single INSERT | OK |
| `count_by_session` | COUNT with WHERE | OK - indexed on `session_id` |

### Missing Indexes (Estimated)
1. `session_events(session_id, sequence)` - Composite for event ordering
2. `contributions(session_id, round_number)` - For round filtering
3. `actions(source_session_id)` - For session-action lookups

## Parallelization Analysis

### Already Parallelized ✅
- Expert contributions in `parallel_round_node` via `asyncio.gather`
- Research detection batch processing
- Quality metric calculations
- Voting rounds
- Sub-problem batch execution

### Opportunities for Further Parallelization
1. **Contribution summarization in event_collector** - Currently awaits each summary individually
2. **Event persistence** - Could batch via `asyncio.gather` instead of sequential saves
3. **list_by_user subqueries** - Could be parallelized or joined

## Caching Gap Analysis

### Currently Cached
- Research results in `research_cache` table with HNSW vector index
- Round summaries in state (not persisted)
- LangGraph checkpoints in Redis (7-day TTL)

### Caching Opportunities
1. **Persona profiles** - Static per meeting; cache in memory during execution
2. **Problem decomposition** - Same problem statement could reuse decomposition
3. **Embedding results** - Contribution embeddings are cached, but not used for retry prevention
4. **Quality check results** - Not cached between rounds

## Scalability Limits

### Estimated Concurrent Sessions
Based on current architecture:
- **LLM bottleneck**: ~10 concurrent sessions (API rate limits)
- **Redis memory**: ~100 sessions (checkpoints ~1MB each)
- **PostgreSQL**: ~1000 sessions/minute (connection pool of 20)

### Critical Path Timing (Estimated)
| Phase | Duration | Bottleneck |
|-------|----------|------------|
| Context collection | 2-4s | LLM call |
| Decomposition | 3-5s | LLM call |
| Persona selection | 3-5s | LLM call |
| Initial round (5 experts) | 8-15s | Parallel LLM calls |
| Parallel round | 5-12s | Parallel LLM calls |
| Voting | 8-15s | Parallel LLM calls |
| Synthesis | 5-10s | LLM call |

**Total meeting time**: 60-120s for 3-round deliberation

## Priority-Ranked Recommendations

### P0 - Critical
1. Add composite index on `session_events(session_id, sequence)` for event ordering
2. Batch contribution summarization in event_collector (3-5 summaries in parallel)

### P1 - High Value
3. Refactor `list_by_user` to use JOINs instead of correlated subqueries
4. Batch event persistence using `executemany` or `asyncio.gather`
5. Add contribution embedding cache lookup before regenerating

### P2 - Nice to Have
6. In-memory persona profile cache during meeting execution
7. Remove or make configurable the 2s event verification delay
8. Pre-compute session summary counts on write (denormalization)
