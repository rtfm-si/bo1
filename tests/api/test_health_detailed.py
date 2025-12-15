"""Tests for /api/health/detailed endpoint."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.api.main import app
from bo1.constants import HealthThresholds

client = TestClient(app)


class TestDetailedHealthAllHealthy:
    """Test /health/detailed when all systems healthy."""

    @patch("backend.services.event_batcher.get_batcher")
    @patch("bo1.llm.circuit_breaker.get_all_circuit_breaker_status")
    def test_detailed_health_all_healthy(
        self, mock_cb_status: MagicMock, mock_get_batcher: MagicMock
    ) -> None:
        """Returns 200 when all healthy."""
        mock_batcher = MagicMock()
        mock_batcher.get_queue_depth.return_value = 5
        mock_get_batcher.return_value = mock_batcher

        mock_cb_status.return_value = {
            "anthropic": {"state": "closed", "failure_count": 0},
            "voyage": {"state": "closed", "failure_count": 0},
        }

        response = client.get("/api/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["healthy"] is True
        assert data["event_queue"]["depth"] == 5
        assert data["event_queue"]["healthy"] is True
        assert data["circuit_breakers"]["healthy"] is True
        assert data["circuit_breakers"]["open_circuits"] == []


class TestDetailedHealthQueueWarning:
    """Test /health/detailed with queue warning."""

    @patch("backend.services.event_batcher.get_batcher")
    @patch("bo1.llm.circuit_breaker.get_all_circuit_breaker_status")
    def test_detailed_health_queue_warning(
        self, mock_cb_status: MagicMock, mock_get_batcher: MagicMock
    ) -> None:
        """Returns 200 with warning flag when queue depth high but not critical."""
        mock_batcher = MagicMock()
        mock_batcher.get_queue_depth.return_value = 75  # Between 50 and 100
        mock_get_batcher.return_value = mock_batcher

        mock_cb_status.return_value = {
            "anthropic": {"state": "closed", "failure_count": 0},
        }

        response = client.get("/api/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "warning"
        assert data["healthy"] is True  # Still healthy, just warning
        assert data["event_queue"]["status"] == "warning"
        assert data["event_queue"]["depth"] == 75


class TestDetailedHealthQueueCritical:
    """Test /health/detailed with critical queue depth."""

    @patch("backend.services.event_batcher.get_batcher")
    @patch("bo1.llm.circuit_breaker.get_all_circuit_breaker_status")
    def test_detailed_health_queue_critical(
        self, mock_cb_status: MagicMock, mock_get_batcher: MagicMock
    ) -> None:
        """Returns 503 when queue depth critical."""
        mock_batcher = MagicMock()
        mock_batcher.get_queue_depth.return_value = 150  # Above 100
        mock_get_batcher.return_value = mock_batcher

        mock_cb_status.return_value = {
            "anthropic": {"state": "closed", "failure_count": 0},
        }

        response = client.get("/api/health/detailed")

        assert response.status_code == 503
        data = response.json()["detail"]
        assert data["status"] == "critical"
        assert data["healthy"] is False
        assert data["event_queue"]["status"] == "critical"
        assert data["event_queue"]["healthy"] is False


class TestDetailedHealthCircuitOpen:
    """Test /health/detailed with circuit breaker open."""

    @patch("backend.services.event_batcher.get_batcher")
    @patch("bo1.llm.circuit_breaker.get_all_circuit_breaker_status")
    def test_detailed_health_circuit_open(
        self, mock_cb_status: MagicMock, mock_get_batcher: MagicMock
    ) -> None:
        """Returns 503 when circuit breaker is open."""
        mock_batcher = MagicMock()
        mock_batcher.get_queue_depth.return_value = 5
        mock_get_batcher.return_value = mock_batcher

        mock_cb_status.return_value = {
            "anthropic": {"state": "open", "failure_count": 5},
            "voyage": {"state": "closed", "failure_count": 0},
        }

        response = client.get("/api/health/detailed")

        assert response.status_code == 503
        data = response.json()["detail"]
        assert data["status"] == "critical"
        assert data["healthy"] is False
        assert data["circuit_breakers"]["healthy"] is False
        assert "anthropic" in data["circuit_breakers"]["open_circuits"]

    @patch("backend.services.event_batcher.get_batcher")
    @patch("bo1.llm.circuit_breaker.get_all_circuit_breaker_status")
    def test_detailed_health_circuit_half_open_is_healthy(
        self, mock_cb_status: MagicMock, mock_get_batcher: MagicMock
    ) -> None:
        """Half-open circuit is considered healthy (testing recovery)."""
        mock_batcher = MagicMock()
        mock_batcher.get_queue_depth.return_value = 5
        mock_get_batcher.return_value = mock_batcher

        mock_cb_status.return_value = {
            "anthropic": {"state": "half_open", "failure_count": 3},
        }

        response = client.get("/api/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["healthy"] is True
        assert data["circuit_breakers"]["healthy"] is True
        assert data["circuit_breakers"]["open_circuits"] == []


class TestDetailedHealthThresholds:
    """Test health threshold values are correctly applied."""

    def test_thresholds_match_constants(self) -> None:
        """Verify threshold constants are correct."""
        assert HealthThresholds.EVENT_QUEUE_WARNING == 50
        assert HealthThresholds.EVENT_QUEUE_CRITICAL == 100
        assert "closed" in HealthThresholds.CIRCUIT_BREAKER_HEALTHY_STATES
        assert "half_open" in HealthThresholds.CIRCUIT_BREAKER_HEALTHY_STATES
        assert "open" not in HealthThresholds.CIRCUIT_BREAKER_HEALTHY_STATES
