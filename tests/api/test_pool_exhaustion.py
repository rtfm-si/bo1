"""Integration tests for pool exhaustion API behavior.

Tests:
- 503 response with Retry-After header
- Degraded read returns appropriate response
- Load shedding for write endpoints
"""

from unittest.mock import MagicMock, patch

import pytest

from bo1.state.pool_degradation import (
    PoolExhaustionError,
    reset_degradation_manager,
)


@pytest.fixture(autouse=True)
def reset_manager():
    """Reset global manager before each test."""
    reset_degradation_manager()
    yield
    reset_degradation_manager()


class TestPoolExhaustionResponses:
    """Tests for API responses during pool exhaustion."""

    def test_check_pool_health_returns_503_when_shedding(self):
        """check_pool_health dependency returns 503 when shedding load."""
        from fastapi import HTTPException

        from backend.api.utils.degradation import check_pool_health
        from bo1.state.pool_degradation import get_degradation_manager

        manager = get_degradation_manager()
        # Set to load shedding mode
        manager.update_pool_state(19, 1, 20)  # 95%

        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(check_pool_health(MagicMock()))

        assert exc_info.value.status_code == 503
        assert "Retry-After" in exc_info.value.headers
        assert exc_info.value.detail["error"] == "service_unavailable"

    def test_raise_pool_exhausted_includes_retry_after(self):
        """raise_pool_exhausted includes Retry-After header."""
        from fastapi import HTTPException

        from backend.api.utils.degradation import raise_pool_exhausted

        with pytest.raises(HTTPException) as exc_info:
            raise_pool_exhausted(queue_depth=10, wait_estimate=5.0)

        assert exc_info.value.status_code == 503
        assert "Retry-After" in exc_info.value.headers
        retry_after = int(exc_info.value.headers["Retry-After"])
        assert retry_after >= 5  # Base value
        assert retry_after <= 8  # Base + max jitter

    def test_pool_exhaustion_response_content(self):
        """Pool exhaustion response includes queue depth."""
        from backend.api.utils.degradation import pool_exhaustion_response

        exc = PoolExhaustionError(
            message="Test exhaustion",
            queue_depth=25,
            wait_estimate=10.0,
        )
        response = pool_exhaustion_response(exc)

        assert response.status_code == 503
        assert "Retry-After" in response.headers
        # Parse JSON body
        import json

        body = json.loads(response.body)
        assert body["queue_depth"] == 25
        assert body["error"] == "service_unavailable"

    def test_get_degradation_status_returns_stats(self):
        """get_degradation_status returns current stats."""
        from backend.api.utils.degradation import get_degradation_status
        from bo1.state.pool_degradation import get_degradation_manager

        manager = get_degradation_manager()
        manager.update_pool_state(18, 2, 20)  # 90% - degraded
        manager.record_shed_load()

        status = get_degradation_status()

        assert status["is_degraded"] is True
        assert status["pool_utilization_pct"] == 90.0
        assert status["requests_shed_total"] == 1


class TestHandlePoolExhaustionDecorator:
    """Tests for handle_pool_exhaustion decorator."""

    @pytest.mark.asyncio
    async def test_decorator_catches_pool_exhaustion_error(self):
        """Decorator converts PoolExhaustionError to 503."""
        from fastapi import HTTPException

        from backend.api.utils.degradation import handle_pool_exhaustion

        @handle_pool_exhaustion
        async def failing_endpoint():
            raise PoolExhaustionError(
                message="Pool full",
                queue_depth=10,
                wait_estimate=5.0,
            )

        with pytest.raises(HTTPException) as exc_info:
            await failing_endpoint()

        assert exc_info.value.status_code == 503
        assert "Retry-After" in exc_info.value.headers

    @pytest.mark.asyncio
    async def test_decorator_passes_through_success(self):
        """Decorator passes through successful responses."""
        from backend.api.utils.degradation import handle_pool_exhaustion

        @handle_pool_exhaustion
        async def successful_endpoint():
            return {"status": "ok"}

        result = await successful_endpoint()
        assert result == {"status": "ok"}


class TestDbSessionDegradation:
    """Tests for db_session with allow_degraded parameter."""

    def test_db_session_raises_when_shedding_and_not_allowed(self):
        """db_session raises PoolExhaustionError when shedding and not allowed."""
        from bo1.state.database import db_session
        from bo1.state.pool_degradation import get_degradation_manager

        manager = get_degradation_manager()
        manager.update_pool_state(19, 1, 20)  # 95% - shedding

        with pytest.raises(PoolExhaustionError):
            with db_session(allow_degraded=False):
                pass

    def test_db_session_queues_when_degraded_and_allowed(self):
        """db_session queues request when degraded and allow_degraded=True."""
        from bo1.state.database import db_session
        from bo1.state.pool_degradation import get_degradation_manager

        manager = get_degradation_manager()
        manager.update_pool_state(18, 2, 20)  # 90% - degraded but not shedding

        # Mock the connection pool to avoid actual DB connection
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = MagicMock()
        mock_conn.cursor.return_value.__exit__ = MagicMock()

        with patch("bo1.state.database.get_connection_pool", return_value=mock_pool):
            with db_session(allow_degraded=True):
                stats = manager.get_stats()
                # Request should be tracked as queued during degradation
                # Note: actual queue depth would be 0 here since we're inside the context

        stats = manager.get_stats()
        assert stats.requests_queued_total == 1


class TestHealthEndpointDegradation:
    """Tests for health endpoint degradation reporting."""

    def test_pool_health_reports_degradation(self):
        """Pool health endpoint reports degradation status."""
        from bo1.state.pool_degradation import get_degradation_manager

        _manager = get_degradation_manager()  # noqa: F841 - initializes singleton

        # Mock get_pool_health to return controlled values
        health_data = {
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

        with patch("bo1.state.database.get_pool_health", return_value=health_data):
            import asyncio

            from backend.api.health import health_check_db_pool
            from backend.api.metrics import prom_metrics

            # Need to patch metrics to avoid actual metric updates
            with patch.object(prom_metrics, "update_pool_metrics"):
                with patch.object(prom_metrics, "update_degradation_metrics"):
                    response = asyncio.run(health_check_db_pool())

        assert response.pool_degraded is True
        assert response.status == "degraded"
