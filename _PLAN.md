# Plan: [COST][P3] Batch Research Queries

## Summary

- Parallelize Brave/Tavily API calls in `industry_benchmark_researcher.py` (2 Brave + 1 Tavily run concurrently instead of sequentially)
- Add parallel competitor intelligence batching in `competitor_intelligence.py` for bulk operations
- Estimated latency reduction: ~40-60% for benchmark research, cost unchanged per call but improved throughput

## Implementation Steps

1. **Parallelize benchmark research queries** (`backend/services/industry_benchmark_researcher.py:340-356`)
   - Replace sequential `for query in queries[:2]` loop with `asyncio.gather(*[_brave_search(q, industry) for q in queries[:2]])`
   - Run Tavily search in same gather (all 3 concurrent)
   - Flatten results after gather, maintain dedup logic

2. **Add batch competitor intelligence method** (`backend/services/competitor_intelligence.py`)
   - Add `gather_intelligence_batch(competitors: list[str])` method
   - Use `asyncio.gather()` with `return_exceptions=True` for all competitors
   - Respect rate limiter by chunking if >3 competitors (Tavily rate limits)

3. **Update competitor enrich endpoint** (`backend/api/context/competitors.py`)
   - Modify bulk enrich endpoint to use batch method when >1 competitor
   - Add concurrency limit parameter (default: 3)

## Tests

- Unit tests:
  - `tests/services/test_industry_benchmark_researcher.py`: Test parallel execution via mock timing
  - `tests/services/test_competitor_intelligence.py`: Test batch method with multiple competitors
- Integration tests:
  - Verify rate limiter respected in batch scenarios
- Manual validation:
  - Run benchmark research, confirm 3 API calls fire concurrently in logs

## Dependencies & Risks

- Dependencies:
  - Existing rate limiter (`bo1/agents/research_rate_limiter.py`) must handle concurrent acquire
- Risks/edge cases:
  - Rate limiter bottleneck if all calls fire simultaneously (mitigated by token bucket)
  - Circuit breaker state shared across parallel calls (existing behavior, acceptable)
