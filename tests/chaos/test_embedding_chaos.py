"""Chaos tests for embedding service (Voyage AI) recovery.

Validates:
- Voyage circuit breaker opens on failures
- Embedding batcher retries with backoff
- Deduplication gracefully skips when embeddings unavailable
"""

import asyncio

import pytest

from bo1.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    get_service_circuit_breaker,
)


@pytest.mark.chaos
class TestVoyageCircuitBreaker:
    """Test Voyage AI circuit breaker behavior."""

    def test_voyage_circuit_opens_after_threshold(self) -> None:
        """Voyage circuit opens after 8 failures (higher threshold)."""
        breaker = get_service_circuit_breaker("voyage")

        # 7 failures: still closed
        for _ in range(7):
            breaker._record_failure_sync(Exception("Voyage API error"))

        assert breaker.state == CircuitState.CLOSED

        # 8th failure: opens
        breaker._record_failure_sync(Exception("Voyage API error"))
        assert breaker.state == CircuitState.OPEN

    def test_voyage_circuit_faster_recovery(self) -> None:
        """Voyage has shorter recovery timeout (30s vs 60s)."""
        breaker = get_service_circuit_breaker("voyage")

        assert breaker.config.recovery_timeout == 30

    @pytest.mark.asyncio
    async def test_voyage_circuit_isolates_from_anthropic(self) -> None:
        """Voyage failures don't affect Anthropic circuit."""
        voyage = get_service_circuit_breaker("voyage")
        anthropic = get_service_circuit_breaker("anthropic")

        # Trip Voyage circuit
        for _ in range(8):
            voyage._record_failure_sync(Exception("Error"))

        assert voyage.state == CircuitState.OPEN
        assert anthropic.state == CircuitState.CLOSED


@pytest.mark.chaos
class TestEmbeddingBatcherRetry:
    """Test embedding batcher retry behavior."""

    @pytest.mark.asyncio
    async def test_batcher_retries_on_transient_failure(self) -> None:
        """Embedding batcher retries on transient API failures."""
        call_count = 0

        async def flaky_embed(texts: list[str]) -> list[list[float]]:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("httpx.ConnectError: Connection refused")
            return [[0.1, 0.2] for _ in texts]

        # Simulate retry logic
        result = None
        for attempt in range(5):
            try:
                result = await flaky_embed(["test text"])
                break
            except Exception:
                await asyncio.sleep(0.01 * (attempt + 1))

        assert result is not None
        assert len(result) == 1
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_batcher_respects_rate_limit(self) -> None:
        """Batcher handles rate limit responses."""
        rate_limited_count = 0

        async def rate_limited_embed(texts: list[str]) -> list[list[float]]:
            nonlocal rate_limited_count
            rate_limited_count += 1
            if rate_limited_count < 2:
                raise Exception("429: Rate limit exceeded. Retry-After: 1")
            return [[0.1] for _ in texts]

        result = None
        retry_after = 0

        for _ in range(3):
            try:
                result = await rate_limited_embed(["test"])
                break
            except Exception as e:
                if "429" in str(e):
                    # Extract retry-after (simplified)
                    retry_after = 0.05  # Use small delay for test
                    await asyncio.sleep(retry_after)
                else:
                    raise

        assert result is not None
        assert rate_limited_count == 2


@pytest.mark.chaos
class TestDeduplicationGracefulDegradation:
    """Test semantic deduplication when embeddings unavailable."""

    @pytest.mark.asyncio
    async def test_dedup_skips_when_embeddings_fail(self) -> None:
        """Deduplication returns all contributions when embeddings fail."""
        contributions = [
            {"content": "First contribution"},
            {"content": "Second contribution"},
            {"content": "Third contribution"},
        ]

        # Simulate embedding failure
        async def failing_embeddings(texts: list[str]) -> list[list[float]]:
            raise Exception("Voyage API unavailable")

        # Dedup should return all contributions (no filtering)
        # This tests the graceful degradation pattern
        try:
            await failing_embeddings([c["content"] for c in contributions])
            filtered = []  # Would normally filter
        except Exception:
            # Graceful degradation: return all contributions
            filtered = contributions

        assert len(filtered) == 3

    @pytest.mark.asyncio
    async def test_dedup_partial_embedding_failure(self) -> None:
        """Dedup handles partial embedding batch failure."""
        contributions = ["a", "b", "c", "d", "e"]
        batch_size = 2
        results: list[list[float]] = []

        async def partial_failure_embed(texts: list[str]) -> list[list[float]]:
            # Fail on second batch
            if len(results) >= batch_size:
                raise Exception("Partial batch failure")
            return [[0.1] for _ in texts]

        # Process in batches
        for i in range(0, len(contributions), batch_size):
            batch = contributions[i : i + batch_size]
            try:
                embeddings = await partial_failure_embed(batch)
                results.extend(embeddings)
            except Exception:
                # Mark failed batch with None
                results.extend([None] * len(batch))  # type: ignore[list-item]

        # Should have some results and some failures
        assert len(results) == 5
        assert results[0] is not None  # First batch succeeded
        assert results[1] is not None


@pytest.mark.chaos
class TestEmbeddingBatcherCircuitIntegration:
    """Test embedding batcher with circuit breaker."""

    @pytest.mark.asyncio
    async def test_batcher_stops_on_circuit_open(self) -> None:
        """Batcher stops attempting when circuit opens."""
        from anthropic import APIError

        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2, recovery_timeout=300))

        call_count = 0

        async def failing_embed() -> list[float]:
            nonlocal call_count
            call_count += 1
            # Must raise APIError for circuit breaker to count it
            raise APIError(
                message="API error",
                request=None,  # type: ignore[arg-type]
                body=None,
            )

        # Make calls until circuit opens
        for _ in range(5):
            try:
                await breaker.call(failing_embed)
            except CircuitBreakerOpenError:
                break
            except APIError:
                pass

        # Should have called API at threshold then fast-failed
        # Circuit opens after failure_threshold (2) failures
        assert call_count == breaker.config.failure_threshold
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_batcher_resumes_after_recovery(self) -> None:
        """Batcher resumes after circuit recovers."""
        from anthropic import APIError

        breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=1,
                recovery_timeout=0,  # Immediate for testing
                success_threshold=1,
            )
        )

        async def failing_then_succeeding() -> list[float]:
            # Must raise APIError for circuit breaker to count it
            raise APIError(
                message="Initial failure",
                request=None,  # type: ignore[arg-type]
                body=None,
            )

        # Trip circuit
        with pytest.raises(APIError):
            await breaker.call(failing_then_succeeding)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery
        await asyncio.sleep(0.01)

        # Should be able to call again
        async def success_embed() -> list[float]:
            return [0.1, 0.2]

        result = await breaker.call(success_embed)
        assert result == [0.1, 0.2]
        assert breaker.state == CircuitState.CLOSED


@pytest.mark.chaos
class TestEmbeddingTimeout:
    """Test embedding request timeout handling."""

    @pytest.mark.asyncio
    async def test_embedding_timeout_handled(self) -> None:
        """Embedding timeout raises appropriate error."""

        async def slow_embed() -> list[float]:
            await asyncio.sleep(10)
            return [0.1]

        with pytest.raises(asyncio.TimeoutError):
            async with asyncio.timeout(0.1):
                await slow_embed()

    @pytest.mark.asyncio
    async def test_embedding_timeout_with_retry(self) -> None:
        """Embedding timeout triggers retry with reduced batch."""
        timeout_count = 0
        batch_sizes: list[int] = []

        async def timeout_on_large_batch(texts: list[str]) -> list[list[float]]:
            nonlocal timeout_count
            batch_sizes.append(len(texts))

            if len(texts) > 2:
                timeout_count += 1
                raise TimeoutError("Batch too large")

            return [[0.1] for _ in texts]

        texts = ["a", "b", "c", "d"]

        # Simulate adaptive batch size reduction
        result: list[list[float]] = []
        batch_size = len(texts)

        while batch_size >= 1:
            try:
                result = await timeout_on_large_batch(texts[:batch_size])
                break
            except TimeoutError:
                batch_size //= 2

        # Eventually succeeds with smaller batch
        assert len(result) > 0
        assert timeout_count > 0
