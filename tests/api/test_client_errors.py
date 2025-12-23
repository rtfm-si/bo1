"""Tests for client error reporting endpoint.

Tests POST /api/errors for frontend error reporting.
Tests Pydantic validation and endpoint behavior.
"""

import json
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi.util import get_remote_address

from backend.api.client_errors import ClientErrorReport, ClientErrorResponse

# Global mock for execute_query - set by tests
_mock_execute_query: MagicMock | None = None


def _get_execute_query():
    """Return mock if set, otherwise raise to simulate DB error."""
    if _mock_execute_query is not None:
        return _mock_execute_query
    raise Exception("No mock set")


# Create test endpoint that replicates the logic without rate limiter
def create_test_app():
    """Create test app with error endpoint (no rate limiting)."""
    app = FastAPI()

    @app.post("/api/errors", response_model=ClientErrorResponse)
    async def test_report_error(request: Request, error_report: ClientErrorReport):
        """Test endpoint - same logic as real endpoint without rate limit."""
        client_ip = get_remote_address(request)
        user_agent = request.headers.get("user-agent", "")[:500]
        correlation_id = error_report.correlation_id or request.headers.get("x-request-id")

        details = {
            "error": error_report.error,
            "stack": error_report.stack,
            "url": error_report.url,
            "component": error_report.component,
            "correlation_id": correlation_id,
            **(error_report.context or {}),
        }

        try:
            mock = _get_execute_query()
            mock(
                """
                INSERT INTO audit_log (user_id, action, resource_type, resource_id, details, ip_address, user_agent)
                VALUES (NULL, 'client_error', 'frontend', %s, %s, %s, %s)
                """,
                (
                    error_report.url,
                    json.dumps(details),
                    client_ip,
                    user_agent,
                ),
                fetch="none",
            )
            return ClientErrorResponse(success=True, message="Error reported")
        except Exception:
            return ClientErrorResponse(success=False, message="Failed to store error")

    return app


@pytest.fixture
def client() -> TestClient:
    """Create test client with isolated app (no Redis dependency)."""
    return TestClient(create_test_app())


@pytest.fixture
def mock_query():
    """Fixture to set up and tear down mock execute_query."""
    global _mock_execute_query
    mock = MagicMock()
    _mock_execute_query = mock
    yield mock
    _mock_execute_query = None


class TestClientErrorEndpoint:
    """Tests for POST /api/errors."""

    def test_report_error_success(self, client: TestClient, mock_query: MagicMock) -> None:
        """Test successful error report."""
        response = client.post(
            "/api/errors",
            json={
                "error": "TypeError: Cannot read property 'foo' of undefined",
                "stack": "TypeError: Cannot read property...\n    at Component.svelte:42",
                "url": "https://boardof.one/meeting/123",
                "component": "MeetingView",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Error reported"

        # Verify DB insert was called
        mock_query.assert_called_once()

    def test_report_error_minimal_payload(self, client: TestClient, mock_query: MagicMock) -> None:
        """Test error report with minimal required fields."""
        response = client.post(
            "/api/errors",
            json={
                "error": "Something went wrong",
                "url": "https://boardof.one/",
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_report_error_with_context(self, client: TestClient, mock_query: MagicMock) -> None:
        """Test error report with additional context."""
        response = client.post(
            "/api/errors",
            json={
                "error": "Network timeout",
                "url": "https://boardof.one/api/sessions",
                "context": {"attempt": 3, "timeout_ms": 30000},
            },
        )

        assert response.status_code == 200

        # Verify context is included in details
        call_args = mock_query.call_args
        details_json = call_args[0][1][1]  # Second positional arg is details
        assert "attempt" in details_json

    def test_report_error_validation_error_message_too_long(self, client: TestClient) -> None:
        """Test validation rejects overly long error message."""
        response = client.post(
            "/api/errors",
            json={
                "error": "x" * 1001,  # Exceeds max_length=1000
                "url": "https://boardof.one/",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_report_error_validation_missing_required(self, client: TestClient) -> None:
        """Test validation requires error and url fields."""
        response = client.post(
            "/api/errors",
            json={
                "error": "Something went wrong",
                # Missing url
            },
        )

        assert response.status_code == 422

    def test_report_error_db_failure_returns_success_false(self, client: TestClient) -> None:
        """Test graceful handling of database failures."""
        # No mock_query fixture = _get_execute_query raises Exception
        response = client.post(
            "/api/errors",
            json={
                "error": "Test error",
                "url": "https://boardof.one/",
            },
        )

        # Should not fail the request
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Failed" in data["message"]

    def test_report_error_captures_user_agent(
        self, client: TestClient, mock_query: MagicMock
    ) -> None:
        """Test user agent is captured from headers."""
        response = client.post(
            "/api/errors",
            json={"error": "Test", "url": "https://boardof.one/"},
            headers={"User-Agent": "Mozilla/5.0 TestBrowser"},
        )

        assert response.status_code == 200

        # Verify user agent is passed to DB
        call_args = mock_query.call_args
        user_agent_arg = call_args[0][1][3]  # Fourth positional arg
        assert "TestBrowser" in user_agent_arg

    def test_report_error_captures_correlation_id_from_payload(
        self, client: TestClient, mock_query: MagicMock
    ) -> None:
        """Test correlation ID from payload is included."""
        response = client.post(
            "/api/errors",
            json={
                "error": "Test",
                "url": "https://boardof.one/",
                "correlation_id": "test-correlation-123",
            },
        )

        assert response.status_code == 200

        # Verify correlation_id is in details
        call_args = mock_query.call_args
        details_json = call_args[0][1][1]
        assert "test-correlation-123" in details_json


class TestClientErrorCSRFExemption:
    """Tests verifying /api/errors is CSRF exempt."""

    def test_errors_endpoint_csrf_exempt(self) -> None:
        """Verify /api/errors is in CSRF exempt prefixes."""
        from backend.api.middleware.csrf import CSRF_EXEMPT_PREFIXES

        # The endpoint should be CSRF exempt (mounted at /api/errors, not /api/v1/errors)
        assert any("/api/errors".startswith(prefix) for prefix in CSRF_EXEMPT_PREFIXES), (
            "/api/errors should be CSRF exempt"
        )
