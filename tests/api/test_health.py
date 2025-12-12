"""Tests for health check endpoints.

Tests:
- /api/health (liveness probe)
- /api/ready (readiness probe)
- Graceful shutdown behavior
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    # Reset shutdown state before each test
    import backend.api.main as main_module

    main_module._shutdown_event = None
    main_module._in_flight_requests = 0

    from backend.api.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestHealthEndpoint:
    """Tests for /api/health liveness probe."""

    def test_health_returns_200(self, client: TestClient):
        """Health endpoint should always return 200 if process is alive."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "details" in data

    def test_health_includes_build_info(self, client: TestClient):
        """Health endpoint should include build info in details."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        details = data.get("details", {})
        assert "version" in details
        assert "api" in details


class TestReadyEndpoint:
    """Tests for /api/ready readiness probe."""

    def test_ready_returns_200_when_deps_healthy(self, client: TestClient):
        """Ready endpoint should return 200 when Postgres and Redis are up."""
        # Mock both dependencies as healthy
        with (
            patch("backend.api.health.psycopg2.connect") as mock_pg,
            patch("backend.api.health.redis.from_url") as mock_redis,
        ):
            # Setup Postgres mock
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_pg.return_value = mock_conn

            # Setup Redis mock
            mock_redis_client = MagicMock()
            mock_redis.return_value = mock_redis_client

            response = client.get("/api/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["ready"] is True
            assert data["checks"]["postgres"] is True
            assert data["checks"]["redis"] is True

    def test_ready_returns_503_when_postgres_down(self, client: TestClient):
        """Ready endpoint should return 503 when Postgres is down."""
        with (
            patch("backend.api.health.psycopg2.connect") as mock_pg,
            patch("backend.api.health.redis.from_url") as mock_redis,
        ):
            # Postgres fails
            mock_pg.side_effect = Exception("Connection refused")

            # Redis works
            mock_redis_client = MagicMock()
            mock_redis.return_value = mock_redis_client

            response = client.get("/api/ready")
            assert response.status_code == 503
            data = response.json()["detail"]
            assert data["ready"] is False
            assert data["checks"]["postgres"] is False
            assert data["checks"]["redis"] is True

    def test_ready_returns_503_when_redis_down(self, client: TestClient):
        """Ready endpoint should return 503 when Redis is down."""
        with (
            patch("backend.api.health.psycopg2.connect") as mock_pg,
            patch("backend.api.health.redis.from_url") as mock_redis,
        ):
            # Postgres works
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_pg.return_value = mock_conn

            # Redis fails
            mock_redis.side_effect = Exception("Connection refused")

            response = client.get("/api/ready")
            assert response.status_code == 503
            data = response.json()["detail"]
            assert data["ready"] is False
            assert data["checks"]["postgres"] is True
            assert data["checks"]["redis"] is False

    def test_ready_returns_503_during_shutdown(self, client: TestClient):
        """Ready endpoint should return 503 during graceful shutdown."""
        import backend.api.main as main_module

        # Simulate shutdown
        shutdown_event = main_module.get_shutdown_event()
        shutdown_event.set()

        response = client.get("/api/ready")
        assert response.status_code == 503
        data = response.json()["detail"]
        assert data["status"] == "shutting_down"
        assert data["ready"] is False


class TestHSTSEndpoint:
    """Tests for /api/health/hsts HSTS compliance check."""

    def test_hsts_returns_compliant(self, client: TestClient):
        """HSTS endpoint should return compliant with preload configuration."""
        response = client.get("/api/health/hsts")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "compliant"
        assert data["component"] == "hsts"
        assert data["preload_eligible"] is True
        assert data["header_value"] == "max-age=31536000; includeSubDomains; preload"
        assert data["checks"]["max_age_sufficient"] is True
        assert data["checks"]["include_subdomains"] is True
        assert data["checks"]["preload_directive"] is True
        assert data["submission_url"] == "https://hstspreload.org"
        assert "timestamp" in data

    def test_hsts_includes_message(self, client: TestClient):
        """HSTS endpoint should include helpful message."""
        response = client.get("/api/health/hsts")
        assert response.status_code == 200
        data = response.json()
        assert "meets all preload requirements" in data["message"]


class TestGracefulShutdown:
    """Tests for graceful shutdown behavior."""

    def test_is_shutting_down_false_initially(self):
        """is_shutting_down should return False initially."""
        import backend.api.main as main_module

        main_module._shutdown_event = None
        assert main_module.is_shutting_down() is False

    def test_is_shutting_down_true_after_signal(self):
        """is_shutting_down should return True after shutdown event is set."""
        import backend.api.main as main_module

        shutdown_event = main_module.get_shutdown_event()
        shutdown_event.set()
        assert main_module.is_shutting_down() is True

    def test_shutdown_event_singleton(self):
        """get_shutdown_event should return same instance."""
        import backend.api.main as main_module

        main_module._shutdown_event = None
        event1 = main_module.get_shutdown_event()
        event2 = main_module.get_shutdown_event()
        assert event1 is event2
