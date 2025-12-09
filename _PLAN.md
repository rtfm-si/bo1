# Plan: Chaos Testing – Validate Recovery Paths with Fault Injection

## Summary

- Add fault injection framework for testing circuit breaker, retry, and checkpoint recovery
- Create chaos test suite covering LLM API failures, Redis/Postgres outages, and network partitions
- Validate graceful degradation and automatic recovery across all external dependencies
- Tests run in isolation (not in CI by default) to avoid flakiness

## Implementation Steps

1. **Create chaos testing infrastructure** (`tests/chaos/conftest.py`)
   - Fault injection fixtures: `inject_llm_failure`, `inject_redis_failure`, `inject_postgres_failure`
   - Configurable failure modes: timeout, connection refused, rate limit (429), server error (500)
   - Cleanup hooks to restore normal behavior after tests

2. **Add LLM circuit breaker chaos tests** (`tests/chaos/test_llm_chaos.py`)
   - Test circuit opens after N consecutive failures
   - Test circuit half-open recovery after timeout
   - Test fast-fail when circuit is open (no API calls made)
   - Test concurrent requests during circuit state transitions
   - Inject: `anthropic.APIError`, `anthropic.RateLimitError`, timeout

3. **Add Redis checkpoint chaos tests** (`tests/chaos/test_redis_chaos.py`)
   - Test checkpoint save fails gracefully when Redis down
   - Test checkpoint restore returns None (not exception) on Redis error
   - Test session resume after Redis reconnect
   - Inject: `redis.ConnectionError`, timeout

4. **Add Postgres connection pool chaos tests** (`tests/chaos/test_postgres_chaos.py`)
   - Test pool exhaustion triggers backoff retry
   - Test query failure doesn't corrupt session state
   - Test transaction rollback on partial write failure
   - Inject: `psycopg.OperationalError`, pool timeout

5. **Add embedding service chaos tests** (`tests/chaos/test_embedding_chaos.py`)
   - Test Voyage circuit breaker opens on failures
   - Test embedding batcher retries with backoff
   - Test deduplication gracefully skips when embeddings unavailable
   - Inject: `httpx.ConnectError`, rate limit response

6. **Add SSE connection chaos tests** (`tests/chaos/test_sse_chaos.py`)
   - Test client reconnection after server restart
   - Test event replay from checkpoint on reconnect
   - Test connection timeout handling
   - Inject: connection drop mid-stream

7. **Create chaos test runner script** (`scripts/run_chaos_tests.sh`)
   - Runs chaos tests in isolation
   - Sets appropriate timeouts (longer than unit tests)
   - Generates coverage report for recovery code paths

## Tests

- Unit tests:
  - Each chaos test file validates specific failure/recovery scenarios
  - Use `pytest.mark.chaos` marker to isolate from regular test runs
  - Mock external services at transport layer (no real API calls)

- Integration/flow tests:
  - Full session flow with injected mid-stream failures
  - Verify state consistency after recovery

- Manual validation:
  - Run `make chaos-test` to execute full chaos suite
  - Review logs for expected circuit breaker state transitions

## Dependencies & Risks

- Dependencies:
  - `pytest-timeout` for test timeouts
  - Existing circuit breaker implementation (`bo1/llm/circuit_breaker.py`)
  - Existing retry logic (`bo1/llm/broker.py`)

- Risks/edge cases:
  - Tests may be slow (use aggressive timeouts in CI skip)
  - Real circuit breaker state persists across tests (reset in fixtures)
  - Async timing can cause flakiness (use deterministic time mocking)
