"""Tests for SuperTokens error handling utilities."""

from unittest.mock import MagicMock

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from backend.api.middleware.supertokens_error import (
    SUPERTOKENS_CONNECTION_ERRORS,
    SUPERTOKENS_PATHS,
    handle_supertokens_error,
    is_supertokens_connection_error,
    is_supertokens_path,
)


class TestIsSupertokensConnectionError:
    """Tests for is_supertokens_connection_error function."""

    def test_connection_refused_detected(self):
        """Connection refused errors should be detected."""
        exc = ConnectionError("connection refused")
        assert is_supertokens_connection_error(exc) is True

    def test_timeout_error_detected(self):
        """Timeout errors should be detected."""
        exc = TimeoutError("connection timeout")
        assert is_supertokens_connection_error(exc) is True

    def test_connection_reset_detected(self):
        """Connection reset errors should be detected."""
        exc = ConnectionError("connection reset by peer")
        assert is_supertokens_connection_error(exc) is True

    def test_network_unreachable_detected(self):
        """Network unreachable errors should be detected."""
        exc = OSError("network unreachable")
        assert is_supertokens_connection_error(exc) is True

    def test_host_not_found_detected(self):
        """Host not found errors should be detected."""
        exc = Exception("host not found: supertokens")
        assert is_supertokens_connection_error(exc) is True

    def test_generic_value_error_not_detected(self):
        """Generic ValueError should not be detected as connection error."""
        exc = ValueError("invalid value")
        assert is_supertokens_connection_error(exc) is False

    def test_generic_exception_not_detected(self):
        """Generic Exception should not be detected as connection error."""
        exc = Exception("something went wrong")
        assert is_supertokens_connection_error(exc) is False

    def test_httpx_error_detected(self):
        """httpx errors should be detected."""
        exc = Exception("httpx.ConnectError: failed to connect")
        assert is_supertokens_connection_error(exc) is True


class TestIsSupertokensPath:
    """Tests for is_supertokens_path function."""

    def test_session_refresh_path_detected(self):
        """Session refresh path should be detected."""
        assert is_supertokens_path("/api/auth/session/refresh") is True

    def test_signout_path_detected(self):
        """Signout path should be detected."""
        assert is_supertokens_path("/api/auth/signout") is True

    def test_other_auth_path_not_detected(self):
        """Other auth paths should not be detected."""
        assert is_supertokens_path("/api/auth/signin") is False

    def test_non_auth_path_not_detected(self):
        """Non-auth paths should not be detected."""
        assert is_supertokens_path("/api/v1/sessions") is False

    def test_root_path_not_detected(self):
        """Root path should not be detected."""
        assert is_supertokens_path("/") is False


class TestHandleSupertokensError:
    """Tests for handle_supertokens_error function."""

    def create_mock_request(self, path: str = "/api/auth/session/refresh") -> MagicMock:
        """Create a mock request object."""
        request = MagicMock()
        # Set up url.path
        request.url = MagicMock()
        request.url.path = path
        request.method = "POST"
        # Set up client.host - needs to be a real attribute not a MagicMock
        client = MagicMock()
        client.host = "127.0.0.1"
        request.client = client
        return request

    def test_connection_error_on_auth_path_returns_503(self):
        """Connection error on auth path should return 503."""
        request = self.create_mock_request("/api/auth/session/refresh")
        exc = ConnectionError("connection refused")

        response = handle_supertokens_error(request, exc)

        assert response is not None
        assert response.status_code == 503
        # Parse the body
        import json

        body = json.loads(response.body)
        assert body["error_code"] == "SERVICE_UNAVAILABLE"
        assert "temporarily unavailable" in body["detail"]

    def test_timeout_on_auth_path_returns_503(self):
        """Timeout on auth path should return 503."""
        request = self.create_mock_request("/api/auth/session/refresh")
        exc = TimeoutError("timeout")

        response = handle_supertokens_error(request, exc)

        assert response is not None
        assert response.status_code == 503

    def test_retry_after_header_set(self):
        """503 response should have Retry-After header."""
        request = self.create_mock_request("/api/auth/session/refresh")
        exc = ConnectionError("connection refused")

        response = handle_supertokens_error(request, exc)

        assert response is not None
        assert response.headers.get("Retry-After") == "10"

    def test_connection_error_on_non_auth_path_returns_none(self):
        """Connection error on non-auth path should return None."""
        request = self.create_mock_request("/api/v1/sessions")
        exc = ConnectionError("connection refused")

        response = handle_supertokens_error(request, exc)

        assert response is None

    def test_non_connection_error_on_auth_path_returns_none(self):
        """Non-connection error on auth path should return None."""
        request = self.create_mock_request("/api/auth/session/refresh")
        exc = ValueError("invalid value")

        response = handle_supertokens_error(request, exc)

        assert response is None

    def test_signout_path_handled(self):
        """Signout path should also be handled."""
        request = self.create_mock_request("/api/auth/signout")
        exc = ConnectionError("connection refused")

        response = handle_supertokens_error(request, exc)

        assert response is not None
        assert response.status_code == 503


class TestConnectionErrorPatterns:
    """Tests for connection error pattern constants."""

    def test_all_expected_indicators_defined(self):
        """Verify all expected connection error indicators are defined."""
        expected_indicators = [
            "connection refused",
            "connection reset",
            "timeout",
            "connection error",
            "failed to connect",
        ]
        for indicator in expected_indicators:
            assert indicator in SUPERTOKENS_CONNECTION_ERRORS


class TestSupertokensPaths:
    """Tests for SuperTokens path constants."""

    def test_session_refresh_path_included(self):
        """Session refresh path should be included."""
        assert "/api/auth/session/refresh" in SUPERTOKENS_PATHS

    def test_signout_path_included(self):
        """Signout path should be included."""
        assert "/api/auth/signout" in SUPERTOKENS_PATHS


class TestIntegrationWithFastAPI:
    """Integration tests with actual FastAPI app."""

    def test_503_returned_for_connection_error_on_refresh_path(self):
        """FastAPI app should return 503 for connection errors on refresh path."""
        app = FastAPI()

        @app.get("/api/auth/session/refresh")
        async def session_refresh():
            raise ConnectionError("connection refused")

        @app.exception_handler(Exception)
        async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
            response = handle_supertokens_error(request, exc)
            if response is not None:
                return response
            return JSONResponse(status_code=500, content={"error": str(exc)})

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/auth/session/refresh")

        assert response.status_code == 503
        assert response.json()["error_code"] == "SERVICE_UNAVAILABLE"

    def test_500_returned_for_other_errors_on_refresh_path(self):
        """FastAPI app should return 500 for other errors on refresh path."""
        app = FastAPI()

        @app.get("/api/auth/session/refresh")
        async def session_refresh():
            raise ValueError("some other error")

        @app.exception_handler(Exception)
        async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
            response = handle_supertokens_error(request, exc)
            if response is not None:
                return response
            return JSONResponse(status_code=500, content={"error": str(exc)})

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/auth/session/refresh")

        assert response.status_code == 500

    def test_connection_error_on_other_path_returns_500(self):
        """Connection error on non-auth path should return 500."""
        app = FastAPI()

        @app.get("/api/v1/sessions")
        async def sessions():
            raise ConnectionError("connection refused")

        @app.exception_handler(Exception)
        async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
            response = handle_supertokens_error(request, exc)
            if response is not None:
                return response
            return JSONResponse(status_code=500, content={"error": str(exc)})

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/sessions")

        assert response.status_code == 500
