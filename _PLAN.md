# Plan: [OBS][P1] Redis Pool Metrics

## Summary

- Add Prometheus metrics for Redis connection pool: active connections, utilization %, acquisition latency
- Wire metrics into RedisManager for automatic tracking
- Expose via /health/redis/pool endpoint
- Add tests for new metrics

## Implementation Steps

1. **Add Redis pool metrics to `backend/api/middleware/metrics.py`**
   - `bo1_redis_pool_used_connections` Gauge
   - `bo1_redis_pool_free_connections` Gauge
   - `bo1_redis_pool_utilization_percent` Gauge
   - `bo1_redis_connection_acquire_seconds` Histogram (for acquisition latency)
   - Add `update_redis_pool_metrics()` helper (mirrors existing `update_pool_metrics()`)

2. **Add pool health method to `bo1/state/redis_manager.py`**
   - `get_pool_health() -> dict` - returns used/free connections, utilization %
   - Use `redis.connection_pool.connection_kwargs` or pool internals to get counts
   - Note: redis-py uses `ConnectionPool` with `_in_use_connections` and `_available_connections`

3. **Add latency tracking wrapper in `bo1/state/redis_manager.py`**
   - Wrap `getconn()` or equivalent to track acquisition latency
   - Observe into `bo1_redis_connection_acquire_seconds` histogram

4. **Add `/health/redis/pool` endpoint to `backend/api/health.py`**
   - Return `RedisPoolHealthResponse` with used/free/utilization fields
   - Call `update_redis_pool_metrics()` on each health check

5. **Wire metrics update in health check loop**
   - Update Redis pool metrics in existing periodic health checks

## Tests

- Unit tests in `tests/state/test_redis_pool_metrics.py`:
  - Test `get_pool_health()` returns expected fields
  - Test utilization calculation (used/total * 100)
  - Test zero handling (empty pool)
- Integration test:
  - Test `/health/redis/pool` endpoint returns metrics
  - Test Prometheus gauges are set correctly

## Dependencies & Risks

- Dependencies: redis-py ConnectionPool internals (may vary by version)
- Risks:
  - redis-py pool internals are not public API - need to verify attribute names
  - Connection pool may be lazily initialized - handle None case
