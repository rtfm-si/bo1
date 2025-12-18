"""Security event alerting service.

Tracks security events (auth failures, rate limit hits, lockouts) in Redis
using sliding window counters. Triggers ntfy alerts when thresholds exceeded.

Features:
- Redis-backed sliding window counters (ZADD with timestamps)
- Configurable thresholds per event type
- Alert deduplication (max 1 alert per IP per 15 min)
- Fails open when Redis unavailable
- Async alert sending to avoid blocking request path
"""

import asyncio
import logging
import time
from typing import Any

from bo1.config import get_settings
from bo1.constants import SecurityAlerts
from bo1.logging import ErrorCode, log_error

logger = logging.getLogger(__name__)


class SecurityAlertingService:
    """Service for tracking security events and triggering alerts."""

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
                logger.debug("SecurityAlertingService: Redis connected")
            except Exception as e:
                logger.warning(f"SecurityAlertingService: Redis not available: {e}")
                self._redis = None
                self._initialized = True
        return self._redis

    def _get_event_key(self, event_type: str, ip: str) -> str:
        """Generate Redis key for event tracking."""
        return f"{SecurityAlerts.KEY_PREFIX}{event_type}:{ip}"

    def _get_alert_dedup_key(self, event_type: str, ip: str) -> str:
        """Generate Redis key for alert deduplication."""
        return f"{SecurityAlerts.ALERT_DEDUP_PREFIX}{event_type}:{ip}"

    def _record_event(
        self,
        event_type: str,
        ip: str,
        window_seconds: int,
        metadata: str = "",
    ) -> int:
        """Record a security event and return current count in window.

        Args:
            event_type: Type of event (auth_failure, rate_limit, lockout)
            ip: Client IP address
            window_seconds: Sliding window duration
            metadata: Optional metadata (endpoint, reason, etc.)

        Returns:
            Current event count for this IP in the window
        """
        redis_client = self._get_redis()
        if not redis_client:
            logger.debug(f"SecurityAlertingService: Redis unavailable for {event_type}")
            return 0

        try:
            current_time = int(time.time())
            window_start = current_time - window_seconds
            key = self._get_event_key(event_type, ip)

            pipeline = redis_client.pipeline()
            # Remove old events outside sliding window
            pipeline.zremrangebyscore(key, 0, window_start)
            # Add new event with timestamp as score
            member = f"{current_time}:{metadata}" if metadata else str(current_time)
            pipeline.zadd(key, {member: current_time})
            # Count current events
            pipeline.zcard(key)
            # Set TTL to 2x window for cleanup
            pipeline.expire(key, window_seconds * 2)
            results = pipeline.execute()

            count: int = int(results[2])
            logger.debug(f"Security event {event_type} from {ip}: count={count}")
            return count

        except Exception as e:
            log_error(
                logger,
                ErrorCode.REDIS_WRITE_ERROR,
                f"SecurityAlertingService: Failed to record {event_type}: {e}",
            )
            return 0

    def _should_alert(self, event_type: str, ip: str) -> bool:
        """Check if we should send an alert (dedup check).

        Returns True if no alert sent for this IP/event in last 15 min.
        """
        redis_client = self._get_redis()
        if not redis_client:
            return True  # Allow alert if can't check dedup

        try:
            key = self._get_alert_dedup_key(event_type, ip)
            # Check if key exists (alert already sent)
            if redis_client.exists(key):
                logger.debug(f"Alert dedup: skipping {event_type} alert for {ip}")
                return False
            return True
        except Exception as e:
            log_error(
                logger,
                ErrorCode.REDIS_READ_ERROR,
                f"SecurityAlertingService: Dedup check failed: {e}",
            )
            return True  # Fail open - send alert

    def _mark_alerted(self, event_type: str, ip: str) -> None:
        """Mark that we've sent an alert for this IP/event."""
        redis_client = self._get_redis()
        if not redis_client:
            return

        try:
            key = self._get_alert_dedup_key(event_type, ip)
            redis_client.setex(key, SecurityAlerts.ALERT_COOLDOWN_SECONDS, "1")
        except Exception as e:
            log_error(
                logger,
                ErrorCode.REDIS_WRITE_ERROR,
                f"SecurityAlertingService: Failed to mark alerted: {e}",
            )

    async def _send_alert_async(
        self,
        event_type: str,
        ip: str,
        count: int,
        window_minutes: int,
        extra_info: str = "",
    ) -> None:
        """Send alert via ntfy asynchronously."""
        try:
            from backend.services.alerts import (
                alert_auth_failure_spike,
                alert_lockout_spike,
                alert_rate_limit_spike,
            )

            if event_type == "auth_failure":
                await alert_auth_failure_spike(ip, count, window_minutes)
            elif event_type == "rate_limit":
                await alert_rate_limit_spike(ip, extra_info, count)
            elif event_type == "lockout":
                await alert_lockout_spike(ip, count)

            self._mark_alerted(event_type, ip)
            logger.info(f"Security alert sent: {event_type} from {ip} ({count} events)")

        except Exception as e:
            log_error(logger, ErrorCode.SECURITY_ALERT_ERROR, f"Failed to send security alert: {e}")

    def record_auth_failure(self, ip: str, reason: str = "unknown") -> int:
        """Record an authentication failure and check threshold.

        Args:
            ip: Client IP address
            reason: Failure reason (for logging)

        Returns:
            Current failure count
        """
        count = self._record_event(
            "auth_failure",
            ip,
            SecurityAlerts.AUTH_FAILURE_WINDOW_SECONDS,
            reason,
        )

        # Check threshold and send alert if exceeded
        if count >= SecurityAlerts.AUTH_FAILURE_THRESHOLD:
            if self._should_alert("auth_failure", ip):
                window_minutes = SecurityAlerts.AUTH_FAILURE_WINDOW_SECONDS // 60
                # Send alert async to not block request
                asyncio.create_task(
                    self._send_alert_async("auth_failure", ip, count, window_minutes)
                )

        return count

    def record_rate_limit_hit(self, ip: str, endpoint: str = "") -> int:
        """Record a rate limit hit (429 response) and check threshold.

        Args:
            ip: Client IP address
            endpoint: API endpoint that was rate limited

        Returns:
            Current hit count
        """
        count = self._record_event(
            "rate_limit",
            ip,
            SecurityAlerts.RATE_LIMIT_WINDOW_SECONDS,
            endpoint,
        )

        # Check threshold and send alert if exceeded
        if count >= SecurityAlerts.RATE_LIMIT_THRESHOLD:
            if self._should_alert("rate_limit", ip):
                window_minutes = SecurityAlerts.RATE_LIMIT_WINDOW_SECONDS // 60
                asyncio.create_task(
                    self._send_alert_async("rate_limit", ip, count, window_minutes, endpoint)
                )

        return count

    def record_lockout(self, ip: str) -> int:
        """Record an account lockout and check threshold.

        Args:
            ip: Client IP address

        Returns:
            Current lockout count
        """
        count = self._record_event(
            "lockout",
            ip,
            SecurityAlerts.LOCKOUT_WINDOW_SECONDS,
        )

        # Check threshold and send alert if exceeded
        if count >= SecurityAlerts.LOCKOUT_THRESHOLD:
            if self._should_alert("lockout", ip):
                window_minutes = SecurityAlerts.LOCKOUT_WINDOW_SECONDS // 60
                asyncio.create_task(self._send_alert_async("lockout", ip, count, window_minutes))

        return count

    def get_event_count(self, event_type: str, ip: str, window_seconds: int) -> int:
        """Get current event count for an IP.

        Args:
            event_type: Type of event
            ip: Client IP address
            window_seconds: Sliding window duration

        Returns:
            Number of events in current window
        """
        redis_client = self._get_redis()
        if not redis_client:
            return 0

        try:
            current_time = int(time.time())
            window_start = current_time - window_seconds
            key = self._get_event_key(event_type, ip)

            # Clean old entries and count
            redis_client.zremrangebyscore(key, 0, window_start)
            return int(redis_client.zcard(key))

        except Exception as e:
            log_error(
                logger,
                ErrorCode.REDIS_READ_ERROR,
                f"SecurityAlertingService: Failed to get count: {e}",
            )
            return 0


# Singleton instance
security_alerting_service = SecurityAlertingService()
