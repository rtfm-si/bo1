"""Rate limiting middleware for API endpoints.

Prevents abuse and brute force attacks using SlowAPI with Redis storage.

Features:
- Redis-backed storage for multi-instance deployments
- Combined IP + User rate limiting for authenticated endpoints
- Tiered limits based on subscription level
- Graceful fallback to in-memory if Redis unavailable

Rate limits by endpoint type:
- Auth endpoints (/api/auth/*): 10 requests per minute per IP
- Session creation: 5 requests per minute per user (prevents free account spam)
- Streaming (expensive): 5 requests per minute per IP
- General API endpoints: 60 requests per minute per IP
"""

import logging
from typing import Any

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from bo1.config import get_settings
from bo1.constants import RateLimits

logger = logging.getLogger(__name__)


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

            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"UserRateLimiter error: {e}")
            # Fail open on errors
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
