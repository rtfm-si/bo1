"""Rate limiting middleware for API endpoints.

Prevents abuse and brute force attacks using SlowAPI with Redis storage.

Features:
- Redis-backed storage for multi-instance deployments
- Combined IP + User rate limiting for authenticated endpoints
- Tiered limits based on subscription level
- Graceful fallback to in-memory if Redis unavailable
- Health monitoring with ntfy alerts when degraded

Rate limits by endpoint type:
- Auth endpoints (/api/auth/*): 10 requests per minute per IP
- Session creation: 5 requests per minute per user (prevents free account spam)
- Streaming (expensive): 5 requests per minute per IP
- General API endpoints: 60 requests per minute per IP
"""

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from bo1.config import get_settings
from bo1.constants import RateLimiterHealth as RateLimiterHealthConfig
from bo1.constants import RateLimits
from bo1.logging.errors import ErrorCode, log_error

logger = logging.getLogger(__name__)


class RateLimiterHealthTracker:
    """Tracks Redis health for rate limiter fail-open monitoring.

    Monitors Redis availability and sends alerts when the rate limiter
    enters or exits fail-open mode (degraded state).

    Thread-safe via simple atomic operations on primitive types.
    """

    def __init__(self) -> None:
        """Initialize health tracker."""
        self._is_degraded = False
        self._degraded_since: datetime | None = None
        self._consecutive_failures = 0
        self._last_alert_time: float = 0.0
        self._last_check_time: float = 0.0

    @property
    def is_degraded(self) -> bool:
        """Check if rate limiter is in degraded mode."""
        return self._is_degraded

    @property
    def consecutive_failures(self) -> int:
        """Get consecutive failure count."""
        return self._consecutive_failures

    @property
    def degraded_since(self) -> datetime | None:
        """Get timestamp when degradation started."""
        return self._degraded_since

    def record_failure(self) -> None:
        """Record a Redis failure and potentially trigger alert.

        Called when Redis is unavailable during rate limit check.
        """
        self._consecutive_failures += 1
        current_time = time.time()

        # Update metrics
        try:
            from backend.api.middleware.metrics import (
                record_rate_limiter_redis_failure,
                set_rate_limiter_degraded,
            )

            record_rate_limiter_redis_failure()
        except ImportError:
            pass

        # Check if we should enter degraded state
        if (
            not self._is_degraded
            and self._consecutive_failures >= RateLimiterHealthConfig.FAILURE_THRESHOLD
        ):
            self._is_degraded = True
            self._degraded_since = datetime.now(tz=UTC)

            try:
                set_rate_limiter_degraded(True)
            except (ImportError, NameError):
                pass

            logger.warning(
                f"Rate limiter entering degraded mode after "
                f"{self._consecutive_failures} consecutive Redis failures"
            )

            # Send alert (deduped)
            self._maybe_send_degraded_alert(current_time)

    def record_success(self) -> None:
        """Record a successful Redis operation.

        Called when Redis responds successfully.
        """
        was_degraded = self._is_degraded

        self._consecutive_failures = 0

        if was_degraded:
            self._is_degraded = False
            degraded_duration = None
            if self._degraded_since:
                degraded_duration = datetime.now(tz=UTC) - self._degraded_since
            self._degraded_since = None

            # Update metrics
            try:
                from backend.api.middleware.metrics import set_rate_limiter_degraded

                set_rate_limiter_degraded(False)
            except ImportError:
                pass

            logger.info(
                "Rate limiter recovered from degraded mode"
                + (f" (was degraded for {degraded_duration})" if degraded_duration else "")
            )

            # Send recovery alert
            self._send_recovery_alert()

    def _maybe_send_degraded_alert(self, current_time: float) -> None:
        """Send degraded alert if cooldown has passed."""
        if current_time - self._last_alert_time < RateLimiterHealthConfig.ALERT_COOLDOWN_SECONDS:
            logger.debug("Skipping degraded alert due to cooldown")
            return

        self._last_alert_time = current_time

        # Fire and forget async alert
        try:
            from backend.services.alerts import alert_rate_limiter_degraded

            asyncio.create_task(
                alert_rate_limiter_degraded(
                    degraded_since=self._degraded_since.isoformat() if self._degraded_since else "",
                    consecutive_failures=self._consecutive_failures,
                )
            )
        except Exception as e:
            logger.debug(f"Failed to send degraded alert: {e}")

    def _send_recovery_alert(self) -> None:
        """Send recovery alert."""
        try:
            from backend.services.alerts import alert_rate_limiter_recovered

            asyncio.create_task(alert_rate_limiter_recovered())
        except Exception as e:
            logger.debug(f"Failed to send recovery alert: {e}")

    def get_status(self) -> dict[str, Any]:
        """Get current health status."""
        return {
            "is_degraded": self._is_degraded,
            "degraded_since": self._degraded_since.isoformat() if self._degraded_since else None,
            "consecutive_failures": self._consecutive_failures,
        }


# Singleton health tracker instance
rate_limiter_health = RateLimiterHealthTracker()


def get_user_id_from_request(request: Request) -> str | None:
    """Extract user_id from request state if available.

    The user is set by the auth middleware before rate limiting runs.
    Returns None if user is not authenticated.
    """
    # Check if user was set by auth dependency
    if hasattr(request.state, "user") and request.state.user:
        return request.state.user.get("user_id")
    return None


def get_user_and_ip_key(request: Request) -> str:
    """Generate rate limit key combining user_id and IP address.

    For authenticated requests: "user:{user_id}:ip:{ip}"
    For unauthenticated requests: "ip:{ip}"

    This prevents:
    - Single user spamming from multiple IPs
    - Multiple users behind same NAT from being unfairly limited
    """
    ip = get_remote_address(request)
    user_id = get_user_id_from_request(request)

    if user_id:
        return f"user:{user_id}:ip:{ip}"
    return f"ip:{ip}"


def get_user_only_key(request: Request) -> str:
    """Generate rate limit key based on user_id only.

    For authenticated requests: "user:{user_id}"
    For unauthenticated requests: Falls back to IP

    Use this for expensive operations where we want to limit per-user
    regardless of IP (e.g., session creation to prevent free tier abuse).
    """
    user_id = get_user_id_from_request(request)

    if user_id:
        return f"user:{user_id}"
    # Fallback to IP for unauthenticated (shouldn't happen for protected endpoints)
    return f"ip:{get_remote_address(request)}"


def _get_redis_url() -> str | None:
    """Get Redis URL from settings, return None if not configured."""
    try:
        settings = get_settings()
        redis_url = settings.redis_url
        if redis_url and redis_url != "redis://localhost:6379/0":
            return redis_url
        # For local dev, check if Redis is actually available
        if redis_url:
            return redis_url
    except Exception as e:
        logger.warning(f"Could not get Redis URL for rate limiting: {e}")
    return None


def _create_limiter() -> Limiter:
    """Create limiter with Redis storage if available, else in-memory."""
    redis_url = _get_redis_url()

    if redis_url:
        try:
            # SlowAPI uses limits library which supports redis:// URLs
            limiter = Limiter(
                key_func=get_remote_address,
                storage_uri=redis_url,
                strategy="fixed-window",
            )
            logger.info(f"Rate limiter initialized with Redis storage: {redis_url.split('@')[-1]}")
            return limiter
        except Exception as e:
            logger.warning(
                f"Failed to initialize Redis rate limiter, falling back to in-memory: {e}"
            )

    # Fallback to in-memory (works for single instance)
    logger.info("Rate limiter initialized with in-memory storage (single instance mode)")
    return Limiter(key_func=get_remote_address, strategy="fixed-window")


# Create limiter instance (lazy initialization via function)
limiter = _create_limiter()

# Rate limit constants for different endpoint types
# Imported from constants for centralized configuration
AUTH_RATE_LIMIT = RateLimits.AUTH
SESSION_RATE_LIMIT = RateLimits.SESSION
SESSION_RATE_LIMIT_USER = RateLimits.SESSION_USER  # Per-user limit for session creation
STREAMING_RATE_LIMIT = RateLimits.STREAMING
UPLOAD_RATE_LIMIT = RateLimits.UPLOAD  # For dataset uploads
GENERAL_RATE_LIMIT = RateLimits.GENERAL
CONTROL_RATE_LIMIT = RateLimits.CONTROL
ADMIN_RATE_LIMIT = RateLimits.ADMIN  # Higher limit for admin dashboard endpoints


def get_tiered_session_limit(request: Request) -> str:
    """Get session creation limit based on user's subscription tier.

    Returns:
        Rate limit string like "5/minute" based on user tier
    """
    user_id = get_user_id_from_request(request)

    if not user_id:
        # Unauthenticated - use strict limit (shouldn't happen for this endpoint)
        return RateLimits.SESSION_FREE

    # Check user tier from request state (set by auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        tier = request.state.user.get("subscription_tier", "free")
        if tier == "pro":
            return RateLimits.SESSION_PRO
        elif tier == "enterprise":
            return RateLimits.SESSION_ENTERPRISE

    return RateLimits.SESSION_FREE


class UserRateLimitMiddleware:
    """Middleware to set user info in request state for rate limiting.

    This runs AFTER auth but BEFORE rate limiting, making user info
    available to the rate limiter key functions.
    """

    def __init__(self, app: Any) -> None:
        """Initialize the middleware with the ASGI application."""
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Process ASGI request, preparing state for rate limiting."""
        if scope["type"] == "http":
            # User info will be set by auth dependency when endpoint is called
            # This middleware just ensures the state exists
            pass
        await self.app(scope, receive, send)


def set_user_for_rate_limiting(request: Request, user: dict[str, Any] | None) -> None:
    """Helper to set user info in request state for rate limiting.

    Call this from auth dependency to make user available to rate limiter.

    Args:
        request: FastAPI request object
        user: User dict from auth with user_id, subscription_tier, etc.
    """
    if user:
        request.state.user = user


class UserRateLimiter:
    """Redis-backed rate limiter for user-based limits.

    Use this for user-based rate limiting that runs AFTER authentication,
    since SlowAPI decorators run before dependencies are resolved.

    Usage in endpoint:
        user_limiter = UserRateLimiter()
        await user_limiter.check_limit(user_id, "session_create", limit=5)
    """

    def __init__(self) -> None:
        """Initialize the rate limiter with lazy Redis connection."""
        self._redis: Any = None
        self._initialized = False

    def _get_redis(self) -> Any:
        """Lazy-initialize Redis connection."""
        if not self._initialized:
            try:
                import redis

                settings = get_settings()
                self._redis = redis.Redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                )
                # Test connection
                self._redis.ping()
                self._initialized = True
            except Exception as e:
                logger.warning(f"UserRateLimiter: Redis not available: {e}")
                self._redis = None
                self._initialized = True
        return self._redis

    async def check_limit(
        self,
        user_id: str,
        action: str,
        limit: int = 5,
        window_seconds: int = 60,
        tier: str = "free",
    ) -> bool:
        """Check if user is within rate limit.

        Args:
            user_id: User identifier
            action: Action being limited (e.g., "session_create")
            limit: Max requests per window
            window_seconds: Time window in seconds
            tier: User's subscription tier (adjusts limit)

        Returns:
            True if within limit, raises HTTPException if exceeded

        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        from fastapi import HTTPException

        # Adjust limit based on tier
        tier_multipliers = {
            "free": 1,
            "pro": 4,
            "enterprise": 20,
        }
        adjusted_limit = limit * tier_multipliers.get(tier, 1)

        redis_client = self._get_redis()

        if not redis_client:
            # Redis not available, allow request (fail open for availability)
            logger.debug("UserRateLimiter: Redis unavailable, allowing request")
            rate_limiter_health.record_failure()
            return True

        try:
            # Use sliding window with Redis
            import time

            current_time = int(time.time())
            window_start = current_time - window_seconds
            key = f"user_rate_limit:{action}:{user_id}"

            # Remove old entries and count current window
            pipeline = redis_client.pipeline()
            pipeline.zremrangebyscore(key, 0, window_start)
            pipeline.zcard(key)
            pipeline.zadd(key, {str(current_time): current_time})
            pipeline.expire(key, window_seconds + 10)  # Cleanup buffer
            results = pipeline.execute()

            current_count = results[1]

            if current_count >= adjusted_limit:
                logger.warning(
                    f"Rate limit exceeded for user {user_id} on {action}: "
                    f"{current_count}/{adjusted_limit} (tier: {tier})"
                )
                # Track rate limit hit for security alerting
                try:
                    from backend.services.security_alerts import (
                        security_alerting_service,
                    )

                    ip = f"user:{user_id}"  # Use user ID as identifier
                    security_alerting_service.record_rate_limit_hit(ip, action)
                except Exception:
                    logger.debug("Failed to record rate limit alert (non-critical)")
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Free users can create up to {limit} meetings per minute. "
                        "Please wait before creating another meeting.",
                        "type": "UserRateLimitExceeded",
                        "limit": adjusted_limit,
                        "window_seconds": window_seconds,
                    },
                    headers={"Retry-After": str(window_seconds)},
                )

            # Record successful Redis operation
            rate_limiter_health.record_success()
            return True

        except HTTPException:
            raise
        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"UserRateLimiter error: {e}",
                exc_info=True,
                user_id=user_id,
                action=action,
            )
            # Fail open on errors - track degraded state
            rate_limiter_health.record_failure()
            return True

    async def get_usage(
        self, user_id: str, action: str, window_seconds: int = 60
    ) -> dict[str, int]:
        """Get current usage stats for a user.

        Returns:
            Dict with current count and limit info
        """
        redis_client = self._get_redis()

        if not redis_client:
            return {"count": 0, "available": True}

        try:
            import time

            current_time = int(time.time())
            window_start = current_time - window_seconds
            key = f"user_rate_limit:{action}:{user_id}"

            # Clean and count
            redis_client.zremrangebyscore(key, 0, window_start)
            count = redis_client.zcard(key)

            return {"count": count, "window_seconds": window_seconds}
        except Exception:
            return {"count": 0, "available": True}


# Singleton instance
user_rate_limiter = UserRateLimiter()


class GlobalIPRateLimiter:
    """Redis-backed global IP rate limiter.

    Provides flood protection at the infrastructure level, running BEFORE
    any authentication or endpoint-specific rate limits.

    Uses sliding window algorithm for accuracy.
    Fails open (allows requests) when Redis is unavailable.
    """

    # Endpoints to skip (health/monitoring must always respond)
    SKIP_PATHS = frozenset({"/health", "/ready", "/metrics", "/api/health", "/api/ready"})

    def __init__(self) -> None:
        """Initialize the global rate limiter."""
        self._redis: Any = None
        self._initialized = False

    def _get_redis(self) -> Any:
        """Lazy-initialize Redis connection."""
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
                logger.warning(f"GlobalIPRateLimiter: Redis not available: {e}")
                self._redis = None
                self._initialized = True
        return self._redis

    def _parse_limit(self, limit_str: str) -> tuple[int, int]:
        """Parse limit string like '500/minute' into (count, window_seconds)."""
        parts = limit_str.split("/")
        count = int(parts[0])
        unit = parts[1]
        window_map = {"second": 1, "minute": 60, "hour": 3600}
        return count, window_map.get(unit, 60)

    def check_limit(self, ip: str) -> tuple[bool, int | None]:
        """Check if IP is within global rate limit.

        Args:
            ip: Client IP address

        Returns:
            (allowed, retry_after) - allowed=True if within limit,
            retry_after=seconds to wait if blocked
        """
        redis_client = self._get_redis()

        if not redis_client:
            # Fail open for availability
            rate_limiter_health.record_failure()
            return True, None

        try:
            import time

            current_time = int(time.time())
            limit, window = self._parse_limit(RateLimits.GLOBAL_IP)
            window_start = current_time - window
            key = f"global_ip_limit:{ip}"

            # Sliding window: remove old, count, add new, set expiry
            pipeline = redis_client.pipeline()
            pipeline.zremrangebyscore(key, 0, window_start)
            pipeline.zcard(key)
            pipeline.zadd(key, {str(current_time): current_time})
            pipeline.expire(key, window + 10)
            results = pipeline.execute()

            current_count = results[1]

            if current_count >= limit:
                logger.warning(f"Global IP rate limit exceeded for {ip}: {current_count}/{limit}")
                # Record metric
                try:
                    from backend.api.middleware.metrics import record_global_rate_limit_blocked

                    record_global_rate_limit_blocked(ip)
                except ImportError:
                    pass
                return False, window

            rate_limiter_health.record_success()
            return True, None

        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"GlobalIPRateLimiter error: {e}",
                exc_info=True,
                ip=ip,
            )
            rate_limiter_health.record_failure()
            return True, None  # Fail open


# Singleton instance
global_ip_rate_limiter = GlobalIPRateLimiter()


class GlobalRateLimitMiddleware:
    """ASGI middleware for global IP-based rate limiting.

    Runs before all other middleware to provide flood protection.
    Skips health/metrics endpoints to allow monitoring.

    Ordering (app processes in reverse):
    CORS > GlobalRateLimit > Auth > EndpointRateLimit
    """

    def __init__(self, app: Any) -> None:
        """Initialize middleware with ASGI app."""
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Process ASGI request."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract path
        path = scope.get("path", "")

        # Skip health/metrics endpoints
        if path in GlobalIPRateLimiter.SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        # Extract IP address
        ip = self._get_client_ip(scope)

        # Check global limit
        allowed, retry_after = global_ip_rate_limiter.check_limit(ip)

        if not allowed:
            # Record metric
            try:
                from backend.api.middleware.metrics import record_global_rate_limit_hit

                record_global_rate_limit_hit()
            except ImportError:
                pass

            # Return 429 response
            await self._send_rate_limit_response(send, retry_after or 60)
            return

        await self.app(scope, receive, send)

    def _get_client_ip(self, scope: dict[str, Any]) -> str:
        """Extract client IP from request scope.

        Respects X-Forwarded-For if present (for reverse proxy setups).
        """
        # Check headers for X-Forwarded-For
        headers = dict(scope.get("headers", []))
        forwarded_for = headers.get(b"x-forwarded-for", b"").decode()

        if forwarded_for:
            # Take first IP (client IP in chain)
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct client
        client = scope.get("client")
        if client:
            return client[0]

        return "unknown"

    async def _send_rate_limit_response(self, send: Any, retry_after: int) -> None:
        """Send 429 Too Many Requests response."""
        import json

        body = json.dumps(
            {
                "error": "Rate limit exceeded",
                "message": "Too many requests from this IP. Please slow down.",
                "type": "GlobalRateLimitExceeded",
            }
        ).encode()

        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"retry-after", str(retry_after).encode()],
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )
