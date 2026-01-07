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

    def test_health_includes_system_metrics(self, client: TestClient):
        """Health endpoint should include system metrics."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "system" in data
        system = data["system"]
        assert "cpu_percent" in system
        assert "memory_percent" in system
        assert "memory_rss_mb" in system
        assert "open_fds" in system
        assert "threads" in system

    def test_health_system_metrics_are_valid(self, client: TestClient):
        """Health endpoint system metrics should have valid values."""
        # Reset the metrics cache to get fresh values
        import backend.api.system_metrics as sm

        sm._last_metrics = None
        sm._last_fetch_time = 0.0

        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        system = data["system"]

        # Memory metrics should be present and positive
        assert system["memory_percent"] is not None
        assert system["memory_percent"] >= 0
        assert system["memory_rss_mb"] is not None
        assert system["memory_rss_mb"] > 0

        # Thread count should be at least 1
        assert system["threads"] is not None
        assert system["threads"] >= 1


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
            # Status can be "ok" or "degraded" if optional services aren't configured
            assert data["status"] in ("ok", "degraded")
            assert data["ready"] is True
            assert data["checks"]["postgres"] is True
            assert data["checks"]["redis"] is True

    def test_ready_returns_503_when_postgres_down(self, client: TestClient):
        """Ready endpoint should return 503 when Postgres is down."""
        # Mock RedisManager to return available
        mock_manager = MagicMock()
        mock_manager.is_available = True
        mock_manager.connection_state.value = "connected"

        with (
            patch("backend.api.health.psycopg2.connect") as mock_pg,
            patch(
                "backend.api.dependencies.get_redis_manager",
                return_value=mock_manager,
            ),
        ):
            # Postgres fails
            mock_pg.side_effect = Exception("Connection refused")

            response = client.get("/api/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["ready"] is False
            assert data["checks"]["postgres"] is False
            assert data["checks"]["redis"] is True
            # Verify error_code is present (structured error response)
            assert "error_code" in data

    def test_ready_returns_503_when_redis_down(self, client: TestClient):
        """Ready endpoint should return 503 when Redis is down."""
        # Mock RedisManager to return unavailable
        mock_manager = MagicMock()
        mock_manager.is_available = False
        mock_manager.connection_state.value = "disconnected"

        with (
            patch("backend.api.health.psycopg2.connect") as mock_pg,
            patch(
                "backend.api.dependencies.get_redis_manager",
                return_value=mock_manager,
            ),
        ):
            # Postgres works
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_pg.return_value = mock_conn

            response = client.get("/api/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["ready"] is False
            assert data["checks"]["postgres"] is True
            assert data["checks"]["redis"] is False
            # Verify error_code is present (structured error response)
            assert "error_code" in data

    def test_ready_returns_503_during_shutdown(self, client: TestClient):
        """Ready endpoint should return 503 during graceful shutdown."""
        import backend.api.main as main_module

        # Simulate shutdown
        shutdown_event = main_module.get_shutdown_event()
        shutdown_event.set()

        response = client.get("/api/ready")
        assert response.status_code == 503
        data = response.json()
        # http_error() returns structured response with error_code
        assert data["error_code"] == "SERVICE_UNAVAILABLE"
        assert data["status_detail"] == "shutting_down"
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


class TestVoyageHealthEndpoint:
    """Tests for /api/health/voyage endpoint."""

    def test_voyage_returns_200_when_key_set(self, client: TestClient):
        """Voyage health should return 200 when API key is configured."""
        with patch.dict("os.environ", {"VOYAGE_API_KEY": "pa-test-valid-key-12345"}):
            response = client.get("/api/health/voyage")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["component"] == "voyage"
            assert data["healthy"] is True
            assert data["message"] == "Voyage API key configured"
            assert "timestamp" in data

    def test_voyage_returns_503_when_key_missing(self, client: TestClient):
        """Voyage health should return 503 when API key is not set."""
        with patch.dict("os.environ", {}, clear=True):
            # Ensure VOYAGE_API_KEY is not in environment
            import os

            original = os.environ.pop("VOYAGE_API_KEY", None)
            try:
                response = client.get("/api/health/voyage")
                assert response.status_code == 503
                data = response.json()
                # http_error() uses status_detail to avoid conflict with status param
                assert data["status_detail"] == "unhealthy"
                assert data["component"] == "voyage"
                assert data["healthy"] is False
                assert "not set" in data["message"]
                assert "error_code" in data
            finally:
                if original:
                    os.environ["VOYAGE_API_KEY"] = original

    def test_voyage_returns_503_when_key_invalid_format(self, client: TestClient):
        """Voyage health should return 503 when API key has invalid format."""
        with patch.dict("os.environ", {"VOYAGE_API_KEY": "invalid-key-no-pa-prefix"}):
            response = client.get("/api/health/voyage")
            assert response.status_code == 503
            data = response.json()
            # http_error() uses status_detail to avoid conflict with status param
            assert data["status_detail"] == "unhealthy"
            assert data["component"] == "voyage"
            assert data["healthy"] is False
            assert "invalid format" in data["message"]
            assert "error_code" in data

    def test_voyage_key_too_short(self, client: TestClient):
        """Voyage health should return 503 when API key is too short."""
        with patch.dict("os.environ", {"VOYAGE_API_KEY": "pa-short"}):
            response = client.get("/api/health/voyage")
            assert response.status_code == 503


class TestBraveHealthEndpoint:
    """Tests for /api/health/brave endpoint."""

    def test_brave_returns_200_when_key_set(self, client: TestClient):
        """Brave health should return 200 when API key is configured."""
        with patch.dict("os.environ", {"BRAVE_API_KEY": "BSAtest1234567890abcdef12345"}):
            response = client.get("/api/health/brave")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["component"] == "brave"
            assert data["healthy"] is True
            assert data["message"] == "Brave API key configured"
            assert "timestamp" in data

    def test_brave_returns_503_when_key_missing(self, client: TestClient):
        """Brave health should return 503 when API key is not set."""
        import os

        original = os.environ.pop("BRAVE_API_KEY", None)
        try:
            response = client.get("/api/health/brave")
            assert response.status_code == 503
            data = response.json()
            # http_error() uses status_detail to avoid conflict with status param
            assert data["status_detail"] == "unhealthy"
            assert data["component"] == "brave"
            assert data["healthy"] is False
            assert "not set" in data["message"]
            assert "error_code" in data
        finally:
            if original:
                os.environ["BRAVE_API_KEY"] = original

    def test_brave_returns_503_when_key_invalid_format(self, client: TestClient):
        """Brave health should return 503 when API key has invalid format."""
        with patch.dict("os.environ", {"BRAVE_API_KEY": "sh"}):
            response = client.get("/api/health/brave")
            assert response.status_code == 503
            data = response.json()
            # http_error() uses status_detail to avoid conflict with status param
            assert data["status_detail"] == "unhealthy"
            assert data["component"] == "brave"
            assert data["healthy"] is False
            assert "invalid format" in data["message"]
            assert "error_code" in data

    def test_brave_key_with_special_chars(self, client: TestClient):
        """Brave health should accept keys with hyphens and underscores."""
        with patch.dict("os.environ", {"BRAVE_API_KEY": "BSA_test-key_12345678901234"}):
            response = client.get("/api/health/brave")
            assert response.status_code == 200
            data = response.json()
            assert data["healthy"] is True
