"""Pytest configuration and fixtures."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env file for test environment
load_dotenv()


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "requires_llm: mark test as requiring LLM API keys (deselect with '-m \"not requires_llm\"')",
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test",
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test",
    )
    config.addinivalue_line(
        "markers",
        "requires_redis: mark test as requiring Redis connection",
    )


@pytest.fixture
def personas_path() -> Path:
    """Get path to personas.json file."""
    bo1_dir = Path(__file__).parent.parent / "bo1"
    return bo1_dir / "data" / "personas.json"


@pytest.fixture
def redis_url() -> str:
    """Get Redis URL from environment, with localhost fallback for local dev."""
    # Use Redis container in Docker, localhost for local dev
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture
def redis_manager_or_skip(redis_url: str):
    """Provide Redis manager or skip test if Redis unavailable.

    This fixture allows tests to gracefully skip when Redis is not available
    (e.g., in CI without Redis, or local dev without Docker).

    Usage:
        def test_something(redis_manager_or_skip):
            manager = redis_manager_or_skip
            # Use manager...
    """
    from bo1.state.redis_manager import RedisManager

    try:
        manager = RedisManager(redis_url=redis_url)
        # Test connection
        manager.client.ping()
        yield manager
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")


@pytest.fixture
def redis_manager_or_none(redis_url: str):
    """Provide Redis manager or None if unavailable (no skip).

    This fixture returns None when Redis is unavailable, allowing tests
    to validate fallback behavior without skipping.

    Usage:
        def test_graceful_degradation(redis_manager_or_none):
            if redis_manager_or_none is None:
                # Test fallback behavior
            else:
                # Test with Redis
    """
    from bo1.state.redis_manager import RedisManager

    try:
        manager = RedisManager(redis_url=redis_url)
        manager.client.ping()
        return manager
    except Exception:
        return None
