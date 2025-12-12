"""Audit logging middleware for API request tracking.

Logs all API requests to the database for:
- Security auditing
- GDPR compliance (user activity tracking)
- Performance monitoring
- Debugging

Excludes health checks and static paths to reduce noise.
Uses fire-and-forget async logging to avoid blocking requests.
"""

import asyncio
import logging
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.services.api_audit import log_api_request

logger = logging.getLogger(__name__)

# Paths to exclude from audit logging
EXCLUDED_PATHS = frozenset(
    {
        "/api/health",
        "/api/ready",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    }
)

# Path prefixes to exclude
EXCLUDED_PREFIXES = (
    "/static/",
    "/assets/",
)


def _should_log(path: str) -> bool:
    """Check if request path should be logged."""
    if path in EXCLUDED_PATHS:
        return False
    for prefix in EXCLUDED_PREFIXES:
        if path.startswith(prefix):
            return False
    return True


def _get_client_ip(request: Request) -> str | None:
    """Extract client IP from request, handling proxies."""
    # Check X-Forwarded-For header (set by reverse proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP in the list is the original client
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct client
    if request.client:
        return request.client.host

    return None


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs all API requests to the database."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process request and log to audit trail.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response from handler
        """
        path = request.url.path

        # Skip excluded paths
        if not _should_log(path):
            return await call_next(request)

        # Capture start time
        start_time = time.perf_counter()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract user_id from request state (set by auth middleware)
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = request.state.user.get("user_id")

        # Extract correlation ID
        request_id = getattr(request.state, "request_id", None)

        # Get client info
        ip_address = _get_client_ip(request)
        user_agent = request.headers.get("User-Agent")

        # Truncate user agent if too long
        if user_agent and len(user_agent) > 500:
            user_agent = user_agent[:500]

        # Fire-and-forget async logging (don't block response)
        asyncio.create_task(
            _log_request_async(
                method=request.method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
            )
        )

        return response


async def _log_request_async(
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    user_id: str | None,
    ip_address: str | None,
    user_agent: str | None,
    request_id: str | None,
) -> None:
    """Log request asynchronously in background task."""
    try:
        # Run blocking DB call in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: log_api_request(
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
            ),
        )
    except Exception as e:
        # Log error but don't fail - audit logging should never break requests
        logger.warning(f"Failed to log API request: {e}")
