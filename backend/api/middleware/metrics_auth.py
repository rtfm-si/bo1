"""Metrics endpoint authentication middleware.

Protects /metrics Prometheus endpoint with optional bearer token auth.

When METRICS_AUTH_TOKEN is set:
  - Requires Authorization: Bearer <token> header
  - Returns 401 if missing or invalid

When METRICS_AUTH_TOKEN is empty (dev mode):
  - Allows all requests to /metrics

Usage in Prometheus scrape config:
    scrape_configs:
      - job_name: 'api'
        bearer_token_file: /run/secrets/metrics_token
        static_configs:
          - targets: ['api:8000']
"""

import logging
from typing import Any

from bo1.config import get_settings

logger = logging.getLogger(__name__)


class MetricsAuthMiddleware:
    """ASGI middleware for /metrics endpoint authentication.

    Intercepts /metrics requests and validates bearer token if configured.
    All other paths pass through unchanged.
    """

    METRICS_PATH = "/metrics"

    def __init__(self, app: Any) -> None:
        """Initialize middleware with ASGI app."""
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Process ASGI request."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Only intercept /metrics
        if path != self.METRICS_PATH:
            await self.app(scope, receive, send)
            return

        # Get configured token
        settings = get_settings()
        expected_token = settings.metrics_auth_token

        # If no token configured, allow all (dev mode)
        if not expected_token:
            await self.app(scope, receive, send)
            return

        # Extract Authorization header
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()

        # Validate bearer token
        if not auth_header.startswith("Bearer "):
            logger.warning("Metrics endpoint accessed without bearer token")
            await self._send_401_response(send, "Missing or invalid Authorization header")
            return

        provided_token = auth_header[7:]  # Strip "Bearer "

        if provided_token != expected_token:
            logger.warning("Metrics endpoint accessed with invalid token")
            await self._send_401_response(send, "Invalid bearer token")
            return

        # Token valid, allow request
        await self.app(scope, receive, send)

    async def _send_401_response(self, send: Any, message: str) -> None:
        """Send 401 Unauthorized response."""
        import json

        body = json.dumps(
            {
                "error": "Unauthorized",
                "message": message,
            }
        ).encode()

        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"www-authenticate", b"Bearer"],
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )
