"""Auth lockout service for failed login attempt tracking.

Implements exponential backoff lockout after repeated authentication failures.
Used to prevent brute force attacks on the OAuth sign-in flow.

Lockout thresholds:
- 5 failures: 30 seconds
- 10 failures: 5 minutes
- 15 failures: 1 hour

Features:
- IP-based tracking (whitelist rejections, locked accounts)
- Redis-backed with automatic expiry
- Sliding window for attempt tracking
- Fails open when Redis unavailable
"""

import logging
import time
from typing import Any

from bo1.config import get_settings
from bo1.constants import AuthLockout

logger = logging.getLogger(__name__)


class AuthLockoutService:
    """Service for tracking auth failures and enforcing lockouts."""

    def __init__(self) -> None:
        """Initialize with lazy Redis connection."""
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
                logger.debug("AuthLockoutService: Redis connected")
            except Exception as e:
                logger.warning(f"AuthLockoutService: Redis not available: {e}")
                self._redis = None
                self._initialized = True
        return self._redis

    def _get_key(self, ip: str) -> str:
        """Generate Redis key for IP lockout tracking."""
        return f"{AuthLockout.KEY_PREFIX}{ip}"

    def record_failed_attempt(self, ip: str, reason: str = "unknown") -> int:
        """Record a failed authentication attempt for an IP.

        Args:
            ip: Client IP address
            reason: Failure reason (for logging)

        Returns:
            Current failure count for this IP
        """
        redis_client = self._get_redis()
        if not redis_client:
            logger.debug("AuthLockoutService: Redis unavailable, skipping record")
            return 0

        try:
            current_time = int(time.time())
            window_start = current_time - AuthLockout.WINDOW_SECONDS
            key = self._get_key(ip)

            pipeline = redis_client.pipeline()
            # Remove old attempts outside sliding window
            pipeline.zremrangebyscore(key, 0, window_start)
            # Add new attempt with timestamp as score
            pipeline.zadd(key, {f"{current_time}:{reason}": current_time})
            # Count current attempts
            pipeline.zcard(key)
            # Set TTL to longest lockout + window
            max_ttl = AuthLockout.WINDOW_SECONDS + max(AuthLockout.THRESHOLDS.values())
            pipeline.expire(key, max_ttl)
            results = pipeline.execute()

            count: int = int(results[2])
            logger.info(f"Auth failure recorded for IP {ip}: {reason} (count: {count})")

            # Track in security alerting service for aggregated alerts
            try:
                from backend.services.security_alerts import security_alerting_service

                security_alerting_service.record_auth_failure(ip, reason)
            except Exception as e:
                logger.debug(f"Security alerting unavailable: {e}")

            return count

        except Exception as e:
            logger.error(f"AuthLockoutService: Failed to record attempt: {e}")
            return 0

    def get_failure_count(self, ip: str) -> int:
        """Get current failure count for an IP.

        Args:
            ip: Client IP address

        Returns:
            Number of failures in current window
        """
        redis_client = self._get_redis()
        if not redis_client:
            return 0

        try:
            current_time = int(time.time())
            window_start = current_time - AuthLockout.WINDOW_SECONDS
            key = self._get_key(ip)

            # Clean old entries and count
            redis_client.zremrangebyscore(key, 0, window_start)
            return int(redis_client.zcard(key))

        except Exception as e:
            logger.error(f"AuthLockoutService: Failed to get count: {e}")
            return 0

    def get_lockout_duration(self, failure_count: int) -> int | None:
        """Calculate lockout duration based on failure count.

        Args:
            failure_count: Number of failures

        Returns:
            Lockout duration in seconds, or None if not locked
        """
        # Find applicable threshold (highest that applies)
        applicable_duration = None
        for threshold, duration in sorted(AuthLockout.THRESHOLDS.items()):
            if failure_count >= threshold:
                applicable_duration = duration
        return applicable_duration

    def record_lockout_triggered(self, ip: str) -> None:
        """Record that a lockout was triggered for an IP.

        Args:
            ip: Client IP address
        """
        try:
            from backend.services.security_alerts import security_alerting_service

            security_alerting_service.record_lockout(ip)
        except Exception as e:
            logger.debug(f"Security alerting unavailable for lockout: {e}")

    def is_locked_out(self, ip: str) -> bool:
        """Check if an IP is currently locked out.

        Args:
            ip: Client IP address

        Returns:
            True if locked out, False otherwise
        """
        remaining = self.get_lockout_remaining(ip)
        return remaining is not None and remaining > 0

    def get_lockout_remaining(self, ip: str) -> int | None:
        """Get seconds remaining in lockout for an IP.

        Args:
            ip: Client IP address

        Returns:
            Seconds until lockout expires, or None if not locked
        """
        redis_client = self._get_redis()
        if not redis_client:
            # Fail open - don't block on Redis errors
            return None

        try:
            current_time = int(time.time())
            window_start = current_time - AuthLockout.WINDOW_SECONDS
            key = self._get_key(ip)

            # Get all attempts in window
            redis_client.zremrangebyscore(key, 0, window_start)
            attempts = redis_client.zrange(key, 0, -1, withscores=True)

            if not attempts:
                return None

            failure_count = len(attempts)
            lockout_duration = self.get_lockout_duration(failure_count)

            if lockout_duration is None:
                return None

            # Calculate when lockout ends based on most recent attempt
            most_recent_time = max(score for _, score in attempts)
            lockout_end = int(most_recent_time) + lockout_duration
            remaining = lockout_end - current_time

            if remaining > 0:
                logger.debug(
                    f"IP {ip} locked out: {remaining}s remaining (failures: {failure_count})"
                )
                return remaining

            return None

        except Exception as e:
            logger.error(f"AuthLockoutService: Failed to check lockout: {e}")
            # Fail open
            return None

    def clear_attempts(self, ip: str) -> None:
        """Clear all failure records for an IP (on successful login).

        Args:
            ip: Client IP address
        """
        redis_client = self._get_redis()
        if not redis_client:
            return

        try:
            key = self._get_key(ip)
            redis_client.delete(key)
            logger.info(f"Auth lockout cleared for IP {ip}")
        except Exception as e:
            logger.error(f"AuthLockoutService: Failed to clear attempts: {e}")


# Singleton instance
auth_lockout_service = AuthLockoutService()
