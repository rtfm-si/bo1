"""Chaos testing suite for Bo1 recovery path validation.

Tests fault injection scenarios for:
- LLM API failures (circuit breaker behavior)
- Redis checkpoint failures (graceful degradation)
- PostgreSQL connection pool issues (retry/backoff)
- Embedding service outages (Voyage circuit breaker)
- SSE connection drops (client reconnection)

Run with: pytest tests/chaos -m chaos
"""
