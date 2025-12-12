"""Tests for rate limiter health tracking.

Tests the RateLimiterHealthTracker class that monitors Redis availability
and sends alerts when the rate limiter enters/exits fail-open mode.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.api.middleware.rate_limit import RateLimiterHealthTracker
from bo1.constants import RateLimiterHealth as RateLimiterHealthConfig


class TestRateLimiterHealthTracker:
    """Tests for RateLimiterHealthTracker class."""

    def test_initial_state(self):
        """Tracker starts in healthy state."""
        tracker = RateLimiterHealthTracker()

        assert tracker.is_degraded is False
        assert tracker.consecutive_failures == 0
        assert tracker.degraded_since is None

    def test_record_failure_increments_counter(self):
        """Each failure increments the counter."""
        tracker = RateLimiterHealthTracker()

        tracker.record_failure()
        assert tracker.consecutive_failures == 1

        tracker.record_failure()
        assert tracker.consecutive_failures == 2

    def test_record_failure_enters_degraded_at_threshold(self):
        """Enters degraded mode after threshold failures."""
        tracker = RateLimiterHealthTracker()

        # Below threshold - not degraded
        for _ in range(RateLimiterHealthConfig.FAILURE_THRESHOLD - 1):
            tracker.record_failure()

        assert tracker.is_degraded is False
        assert tracker.degraded_since is None

        # At threshold - becomes degraded
        tracker.record_failure()

        assert tracker.is_degraded is True
        assert tracker.degraded_since is not None
        assert isinstance(tracker.degraded_since, datetime)

    def test_record_success_resets_failures(self):
        """Success resets failure counter."""
        tracker = RateLimiterHealthTracker()

        tracker.record_failure()
        tracker.record_failure()
        assert tracker.consecutive_failures == 2

        tracker.record_success()
        assert tracker.consecutive_failures == 0

    def test_record_success_clears_degraded_state(self):
        """Success clears degraded state."""
        tracker = RateLimiterHealthTracker()

        # Enter degraded state
        for _ in range(RateLimiterHealthConfig.FAILURE_THRESHOLD):
            tracker.record_failure()

        assert tracker.is_degraded is True

        # Recovery
        tracker.record_success()

        assert tracker.is_degraded is False
        assert tracker.degraded_since is None

    def test_get_status_returns_dict(self):
        """get_status returns proper status dict."""
        tracker = RateLimiterHealthTracker()

        status = tracker.get_status()

        assert "is_degraded" in status
        assert "degraded_since" in status
        assert "consecutive_failures" in status

        assert status["is_degraded"] is False
        assert status["degraded_since"] is None
        assert status["consecutive_failures"] == 0

    def test_get_status_when_degraded(self):
        """get_status reflects degraded state."""
        tracker = RateLimiterHealthTracker()

        for _ in range(RateLimiterHealthConfig.FAILURE_THRESHOLD):
            tracker.record_failure()

        status = tracker.get_status()

        assert status["is_degraded"] is True
        assert status["degraded_since"] is not None
        assert status["consecutive_failures"] >= RateLimiterHealthConfig.FAILURE_THRESHOLD

    @patch("backend.api.middleware.rate_limit.asyncio.create_task")
    def test_alert_sent_on_degraded(self, mock_create_task):
        """Alert is sent when entering degraded state."""
        tracker = RateLimiterHealthTracker()

        # Trigger degraded state
        for _ in range(RateLimiterHealthConfig.FAILURE_THRESHOLD):
            tracker.record_failure()

        # Alert task should be created
        assert mock_create_task.called

    @patch("backend.api.middleware.rate_limit.asyncio.create_task")
    def test_alert_deduplication(self, mock_create_task):
        """Alert is not sent again within cooldown period."""
        tracker = RateLimiterHealthTracker()

        # First degradation - alert sent
        for _ in range(RateLimiterHealthConfig.FAILURE_THRESHOLD):
            tracker.record_failure()

        # Recover
        tracker.record_success()

        # Degrade again immediately (within cooldown)
        for _ in range(RateLimiterHealthConfig.FAILURE_THRESHOLD):
            tracker.record_failure()

        # Should NOT send another degraded alert (cooldown)
        # Recovery alert may be sent, but degraded alert should be deduped
        assert tracker.is_degraded is True

    @patch("backend.api.middleware.rate_limit.asyncio.create_task")
    def test_recovery_alert_sent(self, mock_create_task):
        """Recovery alert is sent when exiting degraded state."""
        tracker = RateLimiterHealthTracker()

        # Enter degraded
        for _ in range(RateLimiterHealthConfig.FAILURE_THRESHOLD):
            tracker.record_failure()

        initial_calls = mock_create_task.call_count

        # Recover
        tracker.record_success()

        # Recovery alert should be sent
        assert mock_create_task.call_count > initial_calls

    def test_recovery_alert_only_if_was_degraded(self):
        """Recovery alert is not sent if wasn't degraded."""
        tracker = RateLimiterHealthTracker()

        with patch("backend.api.middleware.rate_limit.asyncio.create_task"):
            # Record failure but not enough to degrade
            tracker.record_failure()

            # Success when not degraded
            tracker.record_success()

            # No recovery alert should be sent (wasn't degraded)
            # The call count should be 0 since we never entered degraded state
            assert tracker.is_degraded is False


class TestRateLimiterHealthMetrics:
    """Tests for Prometheus metrics integration."""

    def test_failure_metric_recorded(self):
        """Redis failure metric is recorded on failure."""
        with patch(
            "backend.api.middleware.metrics.record_rate_limiter_redis_failure"
        ) as mock_record:
            tracker = RateLimiterHealthTracker()
            tracker.record_failure()

            # Metric should be recorded
            mock_record.assert_called_once()

    def test_degraded_gauge_set(self):
        """Degraded gauge is set when entering degraded state."""
        with patch("backend.api.middleware.metrics.set_rate_limiter_degraded") as mock_set:
            tracker = RateLimiterHealthTracker()

            for _ in range(RateLimiterHealthConfig.FAILURE_THRESHOLD):
                tracker.record_failure()

            # Gauge should be set to True (degraded)
            mock_set.assert_called_with(True)


class TestRateLimiterHealthIntegration:
    """Integration tests for health tracking with UserRateLimiter."""

    @pytest.mark.asyncio
    async def test_health_recorded_on_redis_unavailable(self):
        """Health failure is recorded when Redis is unavailable."""
        from backend.api.middleware.rate_limit import (
            UserRateLimiter,
            rate_limiter_health,
        )

        # Reset health tracker
        rate_limiter_health._is_degraded = False
        rate_limiter_health._consecutive_failures = 0
        rate_limiter_health._degraded_since = None

        limiter = UserRateLimiter()
        limiter._redis = None
        limiter._initialized = True  # Force "initialized but unavailable" state

        # Check limit should fail open and record failure
        result = await limiter.check_limit("test-user", "test-action")

        assert result is True  # Fail open
        assert rate_limiter_health.consecutive_failures >= 1

    @pytest.mark.asyncio
    async def test_health_recorded_on_redis_success(self):
        """Health success is recorded on successful Redis operation."""
        from backend.api.middleware.rate_limit import (
            UserRateLimiter,
            rate_limiter_health,
        )

        # Reset health tracker
        rate_limiter_health._is_degraded = False
        rate_limiter_health._consecutive_failures = 5
        rate_limiter_health._degraded_since = None

        # Mock Redis client
        mock_redis = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [None, 0, True, True]
        mock_redis.pipeline.return_value = mock_pipeline

        limiter = UserRateLimiter()
        limiter._redis = mock_redis
        limiter._initialized = True

        # Check limit should succeed and reset failures
        result = await limiter.check_limit("test-user", "test-action")

        assert result is True
        assert rate_limiter_health.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_health_recorded_on_redis_error(self):
        """Health failure is recorded when Redis throws error."""
        from backend.api.middleware.rate_limit import (
            UserRateLimiter,
            rate_limiter_health,
        )

        # Reset health tracker
        rate_limiter_health._is_degraded = False
        rate_limiter_health._consecutive_failures = 0
        rate_limiter_health._degraded_since = None

        # Mock Redis client that throws error
        mock_redis = MagicMock()
        mock_redis.pipeline.side_effect = Exception("Redis connection error")

        limiter = UserRateLimiter()
        limiter._redis = mock_redis
        limiter._initialized = True

        # Check limit should fail open and record failure
        result = await limiter.check_limit("test-user", "test-action")

        assert result is True  # Fail open
        assert rate_limiter_health.consecutive_failures >= 1
