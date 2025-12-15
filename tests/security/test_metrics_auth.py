"""Metrics endpoint authentication tests.

Tests cover:
- /metrics allowed without token when METRICS_AUTH_TOKEN is empty (dev mode)
- /metrics blocked without auth header when token is set
- /metrics blocked with wrong token
- /metrics allowed with correct token
- Other endpoints not affected by MetricsAuthMiddleware
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client():
    """Create test client."""
    from backend.api.main import app

    return TestClient(app, raise_server_exceptions=False)


def run_async(coro):
    """Helper to run coroutines in tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# =============================================================================
# METRICS AUTH MIDDLEWARE TESTS
# =============================================================================


class TestMetricsAuthMiddleware:
    """Test MetricsAuthMiddleware behavior."""

    def test_metrics_allowed_without_token_when_disabled(self):
        """When METRICS_AUTH_TOKEN is empty, /metrics should be accessible without auth."""
        # Patch at the middleware module level where get_settings is imported
        with patch("backend.api.middleware.metrics_auth.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.metrics_auth_token = ""
            mock_get_settings.return_value = mock_settings

            from backend.api.middleware.metrics_auth import MetricsAuthMiddleware

            # Create a test ASGI app that returns 200
            async def test_app(scope, receive, send):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [[b"content-type", b"text/plain"]],
                    }
                )
                await send({"type": "http.response.body", "body": b"metrics data"})

            middleware = MetricsAuthMiddleware(test_app)

            # Create test scope for /metrics
            scope = {
                "type": "http",
                "path": "/metrics",
                "headers": [],
            }

            # Collect response
            responses = []

            async def receive():
                return {"type": "http.request", "body": b""}

            async def send(message):
                responses.append(message)

            async def run_middleware():
                await middleware(scope, receive, send)

            run_async(run_middleware())

            # Should pass through to app (200 status)
            assert responses[0]["status"] == 200

    def test_metrics_blocked_without_auth_when_enabled(self):
        """When METRICS_AUTH_TOKEN is set, /metrics requires auth header."""
        with patch("backend.api.middleware.metrics_auth.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.metrics_auth_token = "test-secret-token"  # noqa: S105
            mock_get_settings.return_value = mock_settings

            from backend.api.middleware.metrics_auth import MetricsAuthMiddleware

            async def test_app(scope, receive, send):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [],
                    }
                )
                await send({"type": "http.response.body", "body": b""})

            middleware = MetricsAuthMiddleware(test_app)

            scope = {
                "type": "http",
                "path": "/metrics",
                "headers": [],  # No Authorization header
            }

            responses = []

            async def receive():
                return {"type": "http.request", "body": b""}

            async def send(message):
                responses.append(message)

            async def run_middleware():
                await middleware(scope, receive, send)

            run_async(run_middleware())

            # Should return 401
            assert responses[0]["status"] == 401
            # Should have WWW-Authenticate header
            headers_dict = dict(responses[0]["headers"])
            assert headers_dict.get(b"www-authenticate") == b"Bearer"

    def test_metrics_blocked_with_wrong_token(self):
        """When METRICS_AUTH_TOKEN is set, wrong token returns 401."""
        with patch("backend.api.middleware.metrics_auth.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.metrics_auth_token = "correct-token"  # noqa: S105
            mock_get_settings.return_value = mock_settings

            from backend.api.middleware.metrics_auth import MetricsAuthMiddleware

            async def test_app(scope, receive, send):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [],
                    }
                )
                await send({"type": "http.response.body", "body": b""})

            middleware = MetricsAuthMiddleware(test_app)

            scope = {
                "type": "http",
                "path": "/metrics",
                "headers": [(b"authorization", b"Bearer wrong-token")],
            }

            responses = []

            async def receive():
                return {"type": "http.request", "body": b""}

            async def send(message):
                responses.append(message)

            async def run_middleware():
                await middleware(scope, receive, send)

            run_async(run_middleware())

            # Should return 401
            assert responses[0]["status"] == 401

    def test_metrics_allowed_with_correct_token(self):
        """When METRICS_AUTH_TOKEN is set, correct token allows access."""
        with patch("backend.api.middleware.metrics_auth.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.metrics_auth_token = "correct-token"  # noqa: S105
            mock_get_settings.return_value = mock_settings

            from backend.api.middleware.metrics_auth import MetricsAuthMiddleware

            async def test_app(scope, receive, send):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [[b"content-type", b"text/plain"]],
                    }
                )
                await send({"type": "http.response.body", "body": b"metrics data"})

            middleware = MetricsAuthMiddleware(test_app)

            scope = {
                "type": "http",
                "path": "/metrics",
                "headers": [(b"authorization", b"Bearer correct-token")],
            }

            responses = []

            async def receive():
                return {"type": "http.request", "body": b""}

            async def send(message):
                responses.append(message)

            async def run_middleware():
                await middleware(scope, receive, send)

            run_async(run_middleware())

            # Should pass through to app (200 status)
            assert responses[0]["status"] == 200

    def test_other_endpoints_not_affected(self):
        """Middleware only affects /metrics, other paths pass through unchanged."""
        with patch("backend.api.middleware.metrics_auth.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.metrics_auth_token = "secret-token"  # noqa: S105
            mock_get_settings.return_value = mock_settings

            from backend.api.middleware.metrics_auth import MetricsAuthMiddleware

            async def test_app(scope, receive, send):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [[b"content-type", b"application/json"]],
                    }
                )
                await send({"type": "http.response.body", "body": b'{"status":"healthy"}'})

            middleware = MetricsAuthMiddleware(test_app)

            # Test /api/health (should not require auth)
            scope = {
                "type": "http",
                "path": "/api/health",
                "headers": [],  # No Authorization header
            }

            responses = []

            async def receive():
                return {"type": "http.request", "body": b""}

            async def send(message):
                responses.append(message)

            async def run_middleware():
                await middleware(scope, receive, send)

            run_async(run_middleware())

            # Should pass through without auth check
            assert responses[0]["status"] == 200

    def test_invalid_auth_header_format(self):
        """Auth header without 'Bearer ' prefix returns 401."""
        with patch("backend.api.middleware.metrics_auth.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.metrics_auth_token = "secret-token"  # noqa: S105
            mock_get_settings.return_value = mock_settings

            from backend.api.middleware.metrics_auth import MetricsAuthMiddleware

            async def test_app(scope, receive, send):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [],
                    }
                )
                await send({"type": "http.response.body", "body": b""})

            middleware = MetricsAuthMiddleware(test_app)

            scope = {
                "type": "http",
                "path": "/metrics",
                "headers": [(b"authorization", b"Basic dXNlcjpwYXNz")],  # Basic auth instead
            }

            responses = []

            async def receive():
                return {"type": "http.request", "body": b""}

            async def send(message):
                responses.append(message)

            async def run_middleware():
                await middleware(scope, receive, send)

            run_async(run_middleware())

            # Should return 401
            assert responses[0]["status"] == 401

    def test_websocket_requests_pass_through(self):
        """WebSocket requests should not be affected."""
        with patch("backend.api.middleware.metrics_auth.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.metrics_auth_token = "secret-token"  # noqa: S105
            mock_get_settings.return_value = mock_settings

            from backend.api.middleware.metrics_auth import MetricsAuthMiddleware

            was_called = []

            async def test_app(scope, receive, send):
                was_called.append(True)

            middleware = MetricsAuthMiddleware(test_app)

            # WebSocket scope
            scope = {
                "type": "websocket",
                "path": "/metrics",
                "headers": [],
            }

            async def receive():
                return {"type": "websocket.connect"}

            async def send(message):
                pass

            async def run_middleware():
                await middleware(scope, receive, send)

            run_async(run_middleware())

            # Should pass through without auth check
            assert was_called == [True]
