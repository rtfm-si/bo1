"""Chaos testing fixtures for fault injection.

Provides reusable fixtures for injecting failures into external services:
- LLM API (Anthropic)
- Redis (checkpointing)
- PostgreSQL (session storage)
- Voyage AI (embeddings)
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================================
# Markers
# ============================================================================


def pytest_configure(config: Any) -> None:
    """Register chaos test marker."""
    config.addinivalue_line("markers", "chaos: mark test as chaos/fault injection test")


# ============================================================================
# LLM Failure Injection
# ============================================================================


class LLMFailureInjector:
    """Inject failures into LLM API calls."""

    def __init__(self) -> None:
        self.failure_count = 0
        self.max_failures = 0
        self.failure_type: type[Exception] = Exception
        self.failure_message = "Injected failure"

    def configure(
        self,
        max_failures: int,
        failure_type: type[Exception] | None = None,
        message: str = "Injected failure",
    ) -> None:
        """Configure failure injection.

        Args:
            max_failures: Number of failures before succeeding (0 = always fail)
            failure_type: Exception type to raise
            message: Error message
        """
        self.failure_count = 0
        self.max_failures = max_failures
        self.failure_type = failure_type or Exception
        self.failure_message = message

    def maybe_fail(self) -> None:
        """Raise exception if within failure count, otherwise succeed."""
        if self.max_failures == 0 or self.failure_count < self.max_failures:
            self.failure_count += 1
            raise self.failure_type(self.failure_message)

    def reset(self) -> None:
        """Reset failure counter."""
        self.failure_count = 0


@pytest.fixture
def llm_failure_injector() -> LLMFailureInjector:
    """Create LLM failure injector."""
    return LLMFailureInjector()


@pytest.fixture
def inject_anthropic_api_error() -> Generator[MagicMock, None, None]:
    """Inject Anthropic APIError on LLM calls.

    Usage:
        def test_circuit_opens(inject_anthropic_api_error):
            inject_anthropic_api_error.side_effect = APIError("Service unavailable")
            # ... test code
    """
    with patch("bo1.llm.client.ClaudeClient.call") as mock:
        yield mock


@pytest.fixture
def inject_anthropic_rate_limit() -> Generator[MagicMock, None, None]:
    """Inject Anthropic RateLimitError (429) on LLM calls."""
    with patch("bo1.llm.client.ClaudeClient.call") as mock:
        yield mock


# ============================================================================
# Redis Failure Injection
# ============================================================================


class RedisFailureInjector:
    """Inject failures into Redis operations."""

    def __init__(self) -> None:
        self.should_fail = False
        self.failure_type: type[Exception] = ConnectionError

    def enable(self, failure_type: type[Exception] | None = None) -> None:
        """Enable failure injection."""
        self.should_fail = True
        self.failure_type = failure_type or ConnectionError

    def disable(self) -> None:
        """Disable failure injection."""
        self.should_fail = False

    def maybe_fail(self) -> None:
        """Raise if failure is enabled."""
        if self.should_fail:
            raise self.failure_type("Redis connection refused (injected)")


@pytest.fixture
def redis_failure_injector() -> RedisFailureInjector:
    """Create Redis failure injector."""
    return RedisFailureInjector()


@pytest.fixture
def inject_redis_connection_error() -> Generator[MagicMock, None, None]:
    """Inject ConnectionError on Redis operations."""
    with patch("redis.asyncio.Redis.execute_command") as mock:
        yield mock


# ============================================================================
# PostgreSQL Failure Injection
# ============================================================================


class PostgresFailureInjector:
    """Inject failures into PostgreSQL operations."""

    def __init__(self) -> None:
        self.should_fail = False
        self.failure_on_commit = False
        self.pool_exhausted = False

    def enable_connection_failure(self) -> None:
        """Fail on connection attempts."""
        self.should_fail = True

    def enable_commit_failure(self) -> None:
        """Fail on transaction commit."""
        self.failure_on_commit = True

    def enable_pool_exhaustion(self) -> None:
        """Simulate pool exhaustion."""
        self.pool_exhausted = True

    def disable_all(self) -> None:
        """Disable all failure modes."""
        self.should_fail = False
        self.failure_on_commit = False
        self.pool_exhausted = False


@pytest.fixture
def postgres_failure_injector() -> PostgresFailureInjector:
    """Create PostgreSQL failure injector."""
    return PostgresFailureInjector()


@pytest.fixture
def inject_postgres_operational_error() -> Generator[MagicMock, None, None]:
    """Inject OperationalError on PostgreSQL operations."""
    with patch("sqlalchemy.ext.asyncio.AsyncSession.execute") as mock:
        yield mock


# ============================================================================
# Embedding Service Failure Injection
# ============================================================================


class EmbeddingFailureInjector:
    """Inject failures into Voyage AI embedding calls."""

    def __init__(self) -> None:
        self.failure_count = 0
        self.max_failures = 0
        self.should_timeout = False

    def configure_failures(self, max_failures: int) -> None:
        """Configure transient failures."""
        self.failure_count = 0
        self.max_failures = max_failures

    def enable_timeout(self) -> None:
        """Enable timeout simulation."""
        self.should_timeout = True

    def disable(self) -> None:
        """Disable all failure modes."""
        self.failure_count = 0
        self.max_failures = 0
        self.should_timeout = False


@pytest.fixture
def embedding_failure_injector() -> EmbeddingFailureInjector:
    """Create embedding failure injector."""
    return EmbeddingFailureInjector()


@pytest.fixture
def inject_voyage_error() -> Generator[MagicMock, None, None]:
    """Inject errors on Voyage AI embedding calls."""
    with patch("bo1.llm.embeddings.get_embeddings") as mock:
        yield mock


# ============================================================================
# SSE Connection Failure Injection
# ============================================================================


class SSEFailureInjector:
    """Inject failures into SSE connections."""

    def __init__(self) -> None:
        self.drop_after_events = 0
        self.events_sent = 0
        self.should_timeout = False

    def configure_drop(self, after_events: int) -> None:
        """Drop connection after N events."""
        self.drop_after_events = after_events
        self.events_sent = 0

    def enable_timeout(self) -> None:
        """Enable connection timeout."""
        self.should_timeout = True

    def disable(self) -> None:
        """Disable all failure modes."""
        self.drop_after_events = 0
        self.events_sent = 0
        self.should_timeout = False

    def should_drop(self) -> bool:
        """Check if connection should be dropped."""
        if self.drop_after_events > 0:
            self.events_sent += 1
            return self.events_sent >= self.drop_after_events
        return False


@pytest.fixture
def sse_failure_injector() -> SSEFailureInjector:
    """Create SSE failure injector."""
    return SSEFailureInjector()


# ============================================================================
# Circuit Breaker Reset
# ============================================================================


@pytest.fixture(autouse=True)
def reset_circuit_breakers() -> Generator[None, None, None]:
    """Reset all circuit breakers before/after each chaos test."""
    from bo1.llm.circuit_breaker import _circuit_breakers

    _circuit_breakers.clear()
    yield
    _circuit_breakers.clear()


# ============================================================================
# Time Control (for circuit breaker recovery testing)
# ============================================================================


@contextmanager
def freeze_time(frozen_time: float) -> Generator[MagicMock, None, None]:
    """Freeze time.time() to a specific value."""
    with patch("time.time", return_value=frozen_time) as mock:
        yield mock


@contextmanager
def advance_time(seconds: float) -> Generator[None, None, None]:
    """Context manager that advances time after yield."""
    import time

    original_time = time.time

    class TimeAdvancer:
        def __init__(self) -> None:
            self.offset = 0.0

        def __call__(self) -> float:
            return original_time() + self.offset

    advancer = TimeAdvancer()

    with patch("time.time", advancer):
        yield
        advancer.offset += seconds


@pytest.fixture
def time_controller() -> Generator[MagicMock, None, None]:
    """Fixture for controlling time in tests."""
    with patch("time.time") as mock:
        mock.return_value = 1000.0  # Start at a known time
        yield mock


# ============================================================================
# Async Helpers
# ============================================================================


@asynccontextmanager
async def async_timeout(seconds: float) -> AsyncGenerator[None, None]:
    """Async context manager with timeout."""
    try:
        async with asyncio.timeout(seconds):
            yield
    except TimeoutError as err:
        raise TimeoutError(f"Operation timed out after {seconds}s") from err


@pytest.fixture
def mock_async_sleep() -> Generator[AsyncMock, None, None]:
    """Mock asyncio.sleep to speed up tests. Use explicitly where needed."""
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock:
        yield mock
