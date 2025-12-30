"""Rate limit headers middleware.

Adds standard X-RateLimit-* headers to API responses to enable
clients to implement backoff strategies without guessing.

Headers added:
- X-RateLimit-Limit: Maximum requests allowed per window
- X-RateLimit-Remaining: Requests remaining in current window
- X-RateLimit-Reset: Unix timestamp when window resets

Skipped for health/metrics endpoints to avoid unnecessary overhead.
"""

import logging
import time
from typing import Any

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from bo1.config import get_settings
from bo1.constants import RateLimits

logger = logging.getLogger(__name__)

# Endpoints to skip (health/monitoring should not have rate limit headers)
SKIP_PATHS = frozenset(
    {"/health", "/ready", "/metrics", "/api/health", "/api/ready", "/api/metrics"}
)


class RateLimitHeadersMiddleware:
    """ASGI middleware to add rate limit headers to responses.

    Parses the rate limit from endpoint-specific limiter state and adds
    X-RateLimit-* headers to all responses.

    For endpoints using SlowAPI decorator limits, extracts limit from the
    limiter's internal state. For endpoints without specific limits, uses
    the global IP limit as fallback.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize middleware with ASGI app."""
        self.app = app
        self._redis: Any = None
        self._initialized = False

    def _get_redis(self) -> Any:
        """Lazy-initialize Redis connection for querying rate limit state."""
        if not self._initialized:
            try:
                import redis

                settings = get_settings()
                self._redis = redis.Redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                )
                self._redis.ping()
                self._initialized = True
            except Exception as e:
                logger.debug(f"RateLimitHeadersMiddleware: Redis not available: {e}")
                self._redis = None
                self._initialized = True
        return self._redis

    def _parse_limit(self, limit_str: str) -> tuple[int, int]:
        """Parse limit string like '60/minute' into (count, window_seconds)."""
        parts = limit_str.split("/")
        count = int(parts[0])
        unit = parts[1]
        window_map = {"second": 1, "minute": 60, "hour": 3600}
        return count, window_map.get(unit, 60)

    def _get_endpoint_limit(self, path: str, method: str) -> tuple[int, int]:
        """Determine rate limit for endpoint based on path pattern.

        Returns (limit, window_seconds) tuple.
        Falls back to GENERAL limit if no specific limit found.
        """
        # Admin endpoints
        if path.startswith("/api/admin/"):
            return self._parse_limit(RateLimits.ADMIN)

        # Control endpoints (start/kill deliberation)
        if "/control/" in path or path.endswith("/start") or path.endswith("/kill"):
            return self._parse_limit(RateLimits.CONTROL)

        # Auth endpoints
        if "/auth/" in path:
            return self._parse_limit(RateLimits.AUTH)

        # Streaming endpoints
        if "/stream" in path:
            return self._parse_limit(RateLimits.STREAMING)

        # Session creation
        if path == "/api/v1/sessions" and method == "POST":
            return self._parse_limit(RateLimits.SESSION)

        # Dataset upload
        if "/datasets" in path and method == "POST":
            return self._parse_limit(RateLimits.UPLOAD)

        # Context endpoints
        if "/context/" in path or "/context" in path:
            return self._parse_limit(RateLimits.CONTEXT)

        # User profile endpoints
        if "/user/" in path:
            return self._parse_limit(RateLimits.USER)

        # Projects endpoints
        if "/projects" in path:
            return self._parse_limit(RateLimits.PROJECTS)

        # Mentor endpoints
        if "/mentor" in path:
            return self._parse_limit(RateLimits.MENTOR)

        # SEO endpoints
        if "/seo/" in path:
            if "/generate" in path:
                return self._parse_limit(RateLimits.SEO_GENERATE)
            if "/analyze" in path:
                return self._parse_limit(RateLimits.SEO_ANALYZE)

        # Billing endpoints
        if "/billing" in path:
            return self._parse_limit(RateLimits.BILLING)

        # Default to general limit
        return self._parse_limit(RateLimits.GENERAL)

    def _get_remaining_from_redis(
        self, ip: str, path: str, limit: int, window: int
    ) -> tuple[int, int]:
        """Query Redis for remaining requests in current window.

        Returns (remaining, reset_timestamp) tuple.
        Falls back to (limit, now + window) if Redis unavailable.
        """
        redis_client = self._get_redis()
        current_time = int(time.time())
        reset_time = current_time + window

        if not redis_client:
            return limit, reset_time

        try:
            # Query global IP limit key (most common path)
            key = f"global_ip_limit:{ip}"
            window_start = current_time - window

            # Clean and count in single pipeline
            pipeline = redis_client.pipeline()
            pipeline.zremrangebyscore(key, 0, window_start)
            pipeline.zcard(key)
            results = pipeline.execute()

            current_count = results[1] if results[1] else 0
            remaining = max(0, limit - current_count)

            # Calculate actual reset time based on oldest entry in window
            oldest = redis_client.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_time = int(oldest[0][1])
                reset_time = oldest_time + window

            return remaining, reset_time

        except Exception as e:
            logger.debug(f"Failed to get remaining from Redis: {e}")
            return limit, reset_time

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process ASGI request and add rate limit headers to response."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip health/metrics endpoints
        if path in SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        # Extract client IP
        ip = self._get_client_ip(scope)
        method = scope.get("method", "GET")

        # Determine rate limit for this endpoint
        limit, window = self._get_endpoint_limit(path, method)

        # Get remaining count from Redis
        remaining, reset_time = self._get_remaining_from_redis(ip, path, limit, window)

        # Create send wrapper to add headers
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("X-RateLimit-Limit", str(limit))
                headers.append("X-RateLimit-Remaining", str(remaining))
                headers.append("X-RateLimit-Reset", str(reset_time))
            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _get_client_ip(self, scope: Scope) -> str:
        """Extract client IP from request scope."""
        headers = dict(scope.get("headers", []))
        forwarded_for = headers.get(b"x-forwarded-for", b"").decode()

        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        client = scope.get("client")
        if client:
            return client[0]

        return "unknown"
