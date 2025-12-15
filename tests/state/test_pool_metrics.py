"""Tests for database connection pool metrics."""

from unittest.mock import MagicMock, patch

import pytest


class TestGetPoolHealthUtilization:
    """Test pool utilization metrics in get_pool_health()."""

    def test_get_pool_health_includes_utilization_fields(self) -> None:
        """Verify get_pool_health returns utilization metrics."""
        from bo1.state.database import get_pool_health

        with patch("bo1.state.database.get_connection_pool") as mock_get_pool:
            # Mock pool with utilization data
            mock_pool = MagicMock()
            mock_pool._lock = MagicMock()
            mock_pool._lock.__enter__ = MagicMock(return_value=None)
            mock_pool._lock.__exit__ = MagicMock(return_value=False)
            mock_pool._used = {"conn1": MagicMock(), "conn2": MagicMock()}  # 2 used
            mock_pool._pool = [MagicMock(), MagicMock(), MagicMock()]  # 3 free
            mock_conn = MagicMock()
            mock_pool.getconn.return_value = mock_conn
            mock_get_pool.return_value = mock_pool

            health = get_pool_health()

            # Verify new fields exist
            assert "used_connections" in health
            assert "free_connections" in health
            assert "pool_utilization_pct" in health

            # Verify values
            assert health["used_connections"] == 2
            assert health["free_connections"] == 3

    def test_pool_utilization_calculation(self) -> None:
        """Verify pool utilization percentage is calculated correctly."""
        from bo1.state.database import get_pool_health

        with patch("bo1.state.database.get_connection_pool") as mock_get_pool:
            mock_pool = MagicMock()
            mock_pool._lock = MagicMock()
            mock_pool._lock.__enter__ = MagicMock(return_value=None)
            mock_pool._lock.__exit__ = MagicMock(return_value=False)
            # 4 used out of 10 total = 40%
            mock_pool._used = {f"conn{i}": MagicMock() for i in range(4)}
            mock_pool._pool = [MagicMock() for _ in range(6)]
            mock_conn = MagicMock()
            mock_pool.getconn.return_value = mock_conn
            mock_get_pool.return_value = mock_pool

            health = get_pool_health()

            # 4/10 = 40%
            assert health["pool_utilization_pct"] == 40.0

    def test_pool_utilization_zero_when_empty(self) -> None:
        """Verify utilization is 0 when pool is empty."""
        from bo1.state.database import get_pool_health

        with patch("bo1.state.database.get_connection_pool") as mock_get_pool:
            mock_pool = MagicMock()
            mock_pool._lock = MagicMock()
            mock_pool._lock.__enter__ = MagicMock(return_value=None)
            mock_pool._lock.__exit__ = MagicMock(return_value=False)
            mock_pool._used = {}
            mock_pool._pool = []
            mock_conn = MagicMock()
            mock_pool.getconn.return_value = mock_conn
            mock_get_pool.return_value = mock_pool

            health = get_pool_health()

            # No connections = 0%
            assert health["pool_utilization_pct"] == 0.0


class TestPrometheusPoolMetrics:
    """Test Prometheus gauge updates for pool metrics."""

    def test_update_pool_metrics_sets_gauges(self) -> None:
        """Verify update_pool_metrics sets all gauge values."""
        from backend.api.metrics import prom_metrics

        # Call update
        prom_metrics.update_pool_metrics(
            used_connections=5,
            free_connections=15,
            utilization_pct=25.0,
        )

        # Verify gauges were set (get current value)
        assert prom_metrics.db_pool_used_connections._value.get() == 5.0
        assert prom_metrics.db_pool_free_connections._value.get() == 15.0
        assert prom_metrics.db_pool_utilization_percent._value.get() == 25.0

    def test_pool_metrics_exist(self) -> None:
        """Verify pool metric gauges are registered."""
        from backend.api.metrics import prom_metrics

        assert hasattr(prom_metrics, "db_pool_used_connections")
        assert hasattr(prom_metrics, "db_pool_free_connections")
        assert hasattr(prom_metrics, "db_pool_utilization_percent")


class TestHealthPoolEndpoint:
    """Test /health/db/pool endpoint."""

    @pytest.mark.asyncio
    async def test_health_pool_returns_utilization(self) -> None:
        """Verify /health/db/pool includes utilization metrics."""
        from backend.api.health import health_check_db_pool

        with patch("bo1.state.database.get_pool_health") as mock_health:
            mock_health.return_value = {
                "healthy": True,
                "pool_initialized": True,
                "min_connections": 1,
                "max_connections": 20,
                "used_connections": 3,
                "free_connections": 17,
                "pool_utilization_pct": 15.0,
                "test_query_success": True,
                "error": None,
            }

            response = await health_check_db_pool()

            assert response.used_connections == 3
            assert response.free_connections == 17
            assert response.pool_utilization_pct == 15.0
            assert "15.0% utilization" in response.message

    @pytest.mark.asyncio
    async def test_health_pool_warns_high_utilization(self) -> None:
        """Verify warning message when utilization >= 80%."""
        from backend.api.health import health_check_db_pool

        with patch("bo1.state.database.get_pool_health") as mock_health:
            mock_health.return_value = {
                "healthy": True,
                "pool_initialized": True,
                "min_connections": 1,
                "max_connections": 20,
                "used_connections": 18,
                "free_connections": 2,
                "pool_utilization_pct": 90.0,
                "test_query_success": True,
                "error": None,
            }

            response = await health_check_db_pool()

            assert response.pool_utilization_pct == 90.0
            assert "utilization" in response.message.lower()
