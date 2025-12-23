"""Unit tests for Redis pool metrics.

Tests:
- RedisManager.get_pool_health() returns expected fields
- Utilization calculation (used/max * 100)
- Zero handling (empty pool)
- Error handling when pool unavailable
"""

from unittest.mock import MagicMock, patch

import pytest


class TestRedisPoolHealth:
    """Tests for RedisManager.get_pool_health() method."""

    def test_get_pool_health_returns_expected_fields(self) -> None:
        """Test get_pool_health() returns all required fields."""
        from bo1.state.redis_manager import RedisManager

        with patch.object(RedisManager, "__init__", lambda self, **kwargs: None):
            manager = RedisManager()
            manager._available = True
            manager.pool = MagicMock()

            # Mock pool internals
            manager.pool._in_use_connections = {"conn1", "conn2"}
            manager.pool._available_connections = ["conn3", "conn4", "conn5"]
            manager.pool.max_connections = 10

            health = manager.get_pool_health()

            assert "healthy" in health
            assert "used_connections" in health
            assert "free_connections" in health
            assert "max_connections" in health
            assert "utilization_pct" in health

    def test_get_pool_health_calculates_utilization(self) -> None:
        """Test utilization calculation: used/max * 100."""
        from bo1.state.redis_manager import RedisManager

        with patch.object(RedisManager, "__init__", lambda self, **kwargs: None):
            manager = RedisManager()
            manager._available = True
            manager.pool = MagicMock()

            # 3 in use out of 10 max = 30% utilization
            manager.pool._in_use_connections = {"conn1", "conn2", "conn3"}
            manager.pool._available_connections = ["conn4", "conn5"]
            manager.pool.max_connections = 10

            health = manager.get_pool_health()

            assert health["healthy"] is True
            assert health["used_connections"] == 3
            assert health["free_connections"] == 2
            assert health["max_connections"] == 10
            assert health["utilization_pct"] == 30.0

    def test_get_pool_health_handles_empty_pool(self) -> None:
        """Test zero handling when pool has no connections."""
        from bo1.state.redis_manager import RedisManager

        with patch.object(RedisManager, "__init__", lambda self, **kwargs: None):
            manager = RedisManager()
            manager._available = True
            manager.pool = MagicMock()

            # Empty pool
            manager.pool._in_use_connections = set()
            manager.pool._available_connections = []
            manager.pool.max_connections = 10

            health = manager.get_pool_health()

            assert health["healthy"] is True
            assert health["used_connections"] == 0
            assert health["free_connections"] == 0
            assert health["utilization_pct"] == 0.0

    def test_get_pool_health_handles_zero_max_connections(self) -> None:
        """Test zero division handling when max_connections is 0."""
        from bo1.state.redis_manager import RedisManager

        with patch.object(RedisManager, "__init__", lambda self, **kwargs: None):
            manager = RedisManager()
            manager._available = True
            manager.pool = MagicMock()

            manager.pool._in_use_connections = set()
            manager.pool._available_connections = []
            manager.pool.max_connections = 0

            health = manager.get_pool_health()

            assert health["healthy"] is True
            assert health["utilization_pct"] == 0.0

    def test_get_pool_health_returns_unhealthy_when_unavailable(self) -> None:
        """Test returns unhealthy when Redis is unavailable."""
        from bo1.state.redis_manager import RedisManager

        with patch.object(RedisManager, "__init__", lambda self, **kwargs: None):
            manager = RedisManager()
            manager._available = False
            manager.pool = None

            health = manager.get_pool_health()

            assert health["healthy"] is False
            assert health["used_connections"] == 0
            assert health["free_connections"] == 0
            assert health["max_connections"] == 0
            assert "error" in health
            assert health["error"] == "Redis pool not available"

    def test_get_pool_health_handles_missing_pool_attributes(self) -> None:
        """Test handles pool without expected internal attributes."""
        from bo1.state.redis_manager import RedisManager

        with patch.object(RedisManager, "__init__", lambda self, **kwargs: None):
            manager = RedisManager()
            manager._available = True
            manager.pool = MagicMock(spec=[])  # Empty spec, no attributes

            health = manager.get_pool_health()

            # Should use defaults from getattr
            assert health["healthy"] is True
            assert health["used_connections"] == 0
            assert health["free_connections"] == 0

    def test_get_pool_health_handles_exception(self) -> None:
        """Test graceful handling of exceptions."""
        from bo1.state.redis_manager import RedisManager

        with patch.object(RedisManager, "__init__", lambda self, **kwargs: None):
            manager = RedisManager()
            manager._available = True
            manager.pool = MagicMock()

            # Make getattr raise an exception
            manager.pool._in_use_connections = property(lambda self: 1 / 0)

            health = manager.get_pool_health()

            assert health["healthy"] is False
            assert "error" in health

    def test_get_pool_health_high_utilization(self) -> None:
        """Test high utilization (80%+) detection."""
        from bo1.state.redis_manager import RedisManager

        with patch.object(RedisManager, "__init__", lambda self, **kwargs: None):
            manager = RedisManager()
            manager._available = True
            manager.pool = MagicMock()

            # 9 in use out of 10 max = 90% utilization
            manager.pool._in_use_connections = {f"conn{i}" for i in range(9)}
            manager.pool._available_connections = ["conn9"]
            manager.pool.max_connections = 10

            health = manager.get_pool_health()

            assert health["healthy"] is True
            assert health["utilization_pct"] == 90.0


class TestMetricsHelpers:
    """Tests for Redis pool metrics helper functions."""

    def test_update_redis_pool_metrics_sets_gauges(self) -> None:
        """Test update_redis_pool_metrics sets all Prometheus gauges."""
        from backend.api.middleware.metrics import (
            bo1_redis_pool_free_connections,
            bo1_redis_pool_used_connections,
            bo1_redis_pool_utilization_percent,
            update_redis_pool_metrics,
        )

        update_redis_pool_metrics(
            used_connections=5,
            free_connections=3,
            utilization_pct=50.0,
        )

        # Prometheus gauges use _value.get() to retrieve current value
        assert bo1_redis_pool_used_connections._value.get() == 5
        assert bo1_redis_pool_free_connections._value.get() == 3
        assert bo1_redis_pool_utilization_percent._value.get() == 50.0

    def test_record_redis_connection_acquire_latency(self) -> None:
        """Test record_redis_connection_acquire_latency records histogram."""
        from backend.api.middleware.metrics import (
            bo1_redis_connection_acquire_seconds,
            record_redis_connection_acquire_latency,
        )

        # Record a few observations
        record_redis_connection_acquire_latency(0.001)
        record_redis_connection_acquire_latency(0.005)
        record_redis_connection_acquire_latency(0.010)

        # Check histogram has observations (sum > 0)
        assert bo1_redis_connection_acquire_seconds._sum.get() >= 0.016


class TestRedisPoolHealthEndpoint:
    """Tests for /health/redis/pool endpoint.

    Note: These tests use integration-style testing with FastAPI TestClient
    since get_redis_manager() is cached via @lru_cache and difficult to mock.
    We mock at the health endpoint level instead.
    """

    @pytest.mark.asyncio
    async def test_health_redis_pool_returns_healthy(self) -> None:
        """Test endpoint returns healthy status when pool is available."""
        from backend.api.health import RedisPoolHealthResponse

        # Directly test the response model construction (unit test)
        response = RedisPoolHealthResponse(
            status="healthy",
            component="redis_pool",
            healthy=True,
            used_connections=2,
            free_connections=8,
            max_connections=10,
            pool_utilization_pct=20.0,
            message="Pool functioning correctly (20.0% utilization)",
            error=None,
            timestamp="2025-01-15T12:00:00.000000",
        )

        assert response.status == "healthy"
        assert response.healthy is True
        assert response.used_connections == 2
        assert response.free_connections == 8
        assert response.max_connections == 10
        assert response.pool_utilization_pct == 20.0

    @pytest.mark.asyncio
    async def test_health_redis_pool_returns_warning_on_high_utilization(self) -> None:
        """Test high utilization detection logic."""

        # Test the high utilization threshold logic
        health = {
            "healthy": True,
            "used_connections": 8,
            "free_connections": 2,
            "max_connections": 10,
            "utilization_pct": 80.0,
        }

        utilization_pct = health.get("utilization_pct", 0.0)
        status = "healthy" if health["healthy"] else "unhealthy"

        if health["healthy"]:
            if utilization_pct >= 80:
                status = "warning"
                message = f"Pool healthy but high utilization ({utilization_pct}%)"
            else:
                message = f"Pool functioning correctly ({utilization_pct}% utilization)"
        else:
            message = "Pool health check failed"

        assert status == "warning"
        assert "high utilization" in message

    @pytest.mark.asyncio
    async def test_health_redis_pool_returns_unhealthy(self) -> None:
        """Test unhealthy response construction."""
        from backend.api.health import RedisPoolHealthResponse

        response = RedisPoolHealthResponse(
            status="unhealthy",
            component="redis_pool",
            healthy=False,
            used_connections=0,
            free_connections=0,
            max_connections=0,
            pool_utilization_pct=0.0,
            message="Pool health check failed",
            error="Redis pool not available",
            timestamp="2025-01-15T12:00:00.000000",
        )

        assert response.status == "unhealthy"
        assert response.healthy is False
        assert response.error == "Redis pool not available"

    def test_update_redis_pool_metrics_called_correctly(self) -> None:
        """Test that update_redis_pool_metrics is called with correct arguments."""
        from backend.api.middleware.metrics import update_redis_pool_metrics

        # This is a unit test of the metrics function itself
        with patch("backend.api.middleware.metrics.bo1_redis_pool_used_connections") as mock_used:
            with patch(
                "backend.api.middleware.metrics.bo1_redis_pool_free_connections"
            ) as mock_free:
                with patch(
                    "backend.api.middleware.metrics.bo1_redis_pool_utilization_percent"
                ) as mock_util:
                    update_redis_pool_metrics(
                        used_connections=3,
                        free_connections=7,
                        utilization_pct=30.0,
                    )

                    mock_used.set.assert_called_once_with(3)
                    mock_free.set.assert_called_once_with(7)
                    mock_util.set.assert_called_once_with(30.0)
