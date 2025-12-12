"""Unit tests for security alerting service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSecurityAlertingService:
    """Tests for SecurityAlertingService."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis_mock = MagicMock()
        redis_mock.ping.return_value = True
        return redis_mock

    @pytest.fixture
    def service(self, mock_redis):
        """Create service with mocked Redis."""
        from backend.services.security_alerts import SecurityAlertingService

        svc = SecurityAlertingService()
        svc._redis = mock_redis
        svc._initialized = True
        return svc

    def test_record_event_increments_counter(self, service, mock_redis):
        """Test that recording an event increments the counter."""
        # Setup pipeline mock
        pipeline_mock = MagicMock()
        pipeline_mock.execute.return_value = [None, None, 5, True]
        mock_redis.pipeline.return_value = pipeline_mock

        count = service._record_event("auth_failure", "192.168.1.1", 300, "test")

        assert count == 5
        pipeline_mock.zremrangebyscore.assert_called_once()
        pipeline_mock.zadd.assert_called_once()
        pipeline_mock.zcard.assert_called_once()
        pipeline_mock.expire.assert_called_once()

    def test_record_auth_failure_below_threshold(self, service, mock_redis):
        """Test auth failure below threshold does not trigger alert."""
        # Setup: return count below threshold
        pipeline_mock = MagicMock()
        pipeline_mock.execute.return_value = [None, None, 5, True]  # 5 < 10 threshold
        mock_redis.pipeline.return_value = pipeline_mock

        with patch("backend.services.security_alerts.asyncio.create_task") as mock_task:
            count = service.record_auth_failure("192.168.1.1", "test_reason")

            assert count == 5
            mock_task.assert_not_called()

    def test_record_auth_failure_at_threshold(self, service, mock_redis):
        """Test auth failure at threshold triggers alert."""
        # Setup: return count at threshold
        pipeline_mock = MagicMock()
        pipeline_mock.execute.return_value = [None, None, 10, True]  # 10 = threshold
        mock_redis.pipeline.return_value = pipeline_mock
        mock_redis.exists.return_value = False  # No dedup

        with patch("backend.services.security_alerts.asyncio.create_task") as mock_task:
            count = service.record_auth_failure("192.168.1.1", "test_reason")

            assert count == 10
            mock_task.assert_called_once()

    def test_record_rate_limit_hit_below_threshold(self, service, mock_redis):
        """Test rate limit hit below threshold does not trigger alert."""
        pipeline_mock = MagicMock()
        pipeline_mock.execute.return_value = [None, None, 10, True]  # 10 < 20 threshold
        mock_redis.pipeline.return_value = pipeline_mock

        with patch("backend.services.security_alerts.asyncio.create_task") as mock_task:
            count = service.record_rate_limit_hit("192.168.1.1", "/api/test")

            assert count == 10
            mock_task.assert_not_called()

    def test_record_rate_limit_hit_at_threshold(self, service, mock_redis):
        """Test rate limit hit at threshold triggers alert."""
        pipeline_mock = MagicMock()
        pipeline_mock.execute.return_value = [None, None, 20, True]  # 20 = threshold
        mock_redis.pipeline.return_value = pipeline_mock
        mock_redis.exists.return_value = False  # No dedup

        with patch("backend.services.security_alerts.asyncio.create_task") as mock_task:
            count = service.record_rate_limit_hit("192.168.1.1", "/api/test")

            assert count == 20
            mock_task.assert_called_once()

    def test_record_lockout_below_threshold(self, service, mock_redis):
        """Test lockout below threshold does not trigger alert."""
        pipeline_mock = MagicMock()
        pipeline_mock.execute.return_value = [None, None, 2, True]  # 2 < 3 threshold
        mock_redis.pipeline.return_value = pipeline_mock

        with patch("backend.services.security_alerts.asyncio.create_task") as mock_task:
            count = service.record_lockout("192.168.1.1")

            assert count == 2
            mock_task.assert_not_called()

    def test_record_lockout_at_threshold(self, service, mock_redis):
        """Test lockout at threshold triggers alert."""
        pipeline_mock = MagicMock()
        pipeline_mock.execute.return_value = [None, None, 3, True]  # 3 = threshold
        mock_redis.pipeline.return_value = pipeline_mock
        mock_redis.exists.return_value = False  # No dedup

        with patch("backend.services.security_alerts.asyncio.create_task") as mock_task:
            count = service.record_lockout("192.168.1.1")

            assert count == 3
            mock_task.assert_called_once()

    def test_alert_deduplication_blocks_repeat_alert(self, service, mock_redis):
        """Test that deduplication prevents repeat alerts."""
        pipeline_mock = MagicMock()
        pipeline_mock.execute.return_value = [None, None, 15, True]  # Over threshold
        mock_redis.pipeline.return_value = pipeline_mock
        mock_redis.exists.return_value = True  # Alert already sent

        with patch("backend.services.security_alerts.asyncio.create_task") as mock_task:
            count = service.record_auth_failure("192.168.1.1", "test")

            assert count == 15
            # Alert should NOT be created because dedup key exists
            mock_task.assert_not_called()

    def test_sliding_window_expires_old_events(self, service, mock_redis):
        """Test that old events outside sliding window are removed."""
        pipeline_mock = MagicMock()
        pipeline_mock.execute.return_value = [None, None, 3, True]
        mock_redis.pipeline.return_value = pipeline_mock

        service._record_event("auth_failure", "192.168.1.1", 300, "")

        # Verify zremrangebyscore was called to remove old events
        pipeline_mock.zremrangebyscore.assert_called_once()
        call_args = pipeline_mock.zremrangebyscore.call_args
        assert call_args[0][1] == 0  # Min score

    def test_fails_open_when_redis_unavailable(self, service):
        """Test service fails open when Redis unavailable."""
        service._redis = None

        # Should not raise, just return 0
        count = service.record_auth_failure("192.168.1.1", "test")
        assert count == 0

        count = service.record_rate_limit_hit("192.168.1.1", "/api/test")
        assert count == 0

        count = service.record_lockout("192.168.1.1")
        assert count == 0

    def test_get_event_count(self, service, mock_redis):
        """Test getting event count for an IP."""
        mock_redis.zcard.return_value = 7

        count = service.get_event_count("auth_failure", "192.168.1.1", 300)

        assert count == 7
        mock_redis.zremrangebyscore.assert_called_once()
        mock_redis.zcard.assert_called_once()

    def test_mark_alerted_sets_dedup_key(self, service, mock_redis):
        """Test that marking alert sets dedup key with TTL."""
        from bo1.constants import SecurityAlerts

        service._mark_alerted("auth_failure", "192.168.1.1")

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == SecurityAlerts.ALERT_COOLDOWN_SECONDS
        assert call_args[0][2] == "1"


class TestAlertFunctions:
    """Tests for alert functions in alerts.py."""

    @pytest.mark.asyncio
    async def test_alert_auth_failure_spike(self):
        """Test auth failure spike alert function."""
        from backend.services.alerts import alert_auth_failure_spike

        with patch("backend.services.alerts.send_ntfy_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            with patch(
                "backend.services.alerts._get_ntfy_alerts_topic",
                return_value="test-topic",
            ):
                result = await alert_auth_failure_spike("192.168.1.1", 15, 5)

                assert result is True
                mock_send.assert_called_once()
                call_kwargs = mock_send.call_args[1]
                assert "Auth Failure Spike" in call_kwargs["title"]
                assert "192.168.1.1" in call_kwargs["message"]
                assert "15" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_alert_rate_limit_spike(self):
        """Test rate limit spike alert function."""
        from backend.services.alerts import alert_rate_limit_spike

        with patch("backend.services.alerts.send_ntfy_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            with patch(
                "backend.services.alerts._get_ntfy_alerts_topic",
                return_value="test-topic",
            ):
                result = await alert_rate_limit_spike("192.168.1.1", "/api/sessions", 25)

                assert result is True
                mock_send.assert_called_once()
                call_kwargs = mock_send.call_args[1]
                assert "Rate Limit" in call_kwargs["title"]
                assert "/api/sessions" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_alert_lockout_spike(self):
        """Test lockout spike alert function."""
        from backend.services.alerts import alert_lockout_spike

        with patch("backend.services.alerts.send_ntfy_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            with patch(
                "backend.services.alerts._get_ntfy_alerts_topic",
                return_value="test-topic",
            ):
                result = await alert_lockout_spike("192.168.1.1", 5)

                assert result is True
                mock_send.assert_called_once()
                call_kwargs = mock_send.call_args[1]
                assert "Lockout" in call_kwargs["title"]
                assert "5" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_alert_no_topic_configured(self):
        """Test alerts fail gracefully when no topic configured."""
        from backend.services.alerts import alert_auth_failure_spike

        with patch("backend.services.alerts._get_ntfy_alerts_topic", return_value=""):
            result = await alert_auth_failure_spike("192.168.1.1", 15, 5)
            assert result is False


class TestSecurityAlertsConstants:
    """Tests for SecurityAlerts constants."""

    def test_constants_have_expected_values(self):
        """Test that constants are configured with sensible defaults."""
        from bo1.constants import SecurityAlerts

        # Auth failure: 10 in 5 min
        assert SecurityAlerts.AUTH_FAILURE_THRESHOLD == 10
        assert SecurityAlerts.AUTH_FAILURE_WINDOW_SECONDS == 300

        # Rate limit: 20 in 5 min
        assert SecurityAlerts.RATE_LIMIT_THRESHOLD == 20
        assert SecurityAlerts.RATE_LIMIT_WINDOW_SECONDS == 300

        # Lockout: 3 in 15 min
        assert SecurityAlerts.LOCKOUT_THRESHOLD == 3
        assert SecurityAlerts.LOCKOUT_WINDOW_SECONDS == 900

        # Alert cooldown: 15 min
        assert SecurityAlerts.ALERT_COOLDOWN_SECONDS == 900

    def test_redis_key_prefixes_are_unique(self):
        """Test that Redis key prefixes don't conflict."""
        from bo1.constants import AuthLockout, SecurityAlerts

        prefixes = [
            SecurityAlerts.KEY_PREFIX,
            SecurityAlerts.ALERT_DEDUP_PREFIX,
            AuthLockout.KEY_PREFIX,
        ]
        assert len(prefixes) == len(set(prefixes)), "Key prefixes must be unique"


class TestSecurityAlertingSingleton:
    """Tests for singleton instance."""

    def test_singleton_is_available(self):
        """Test that singleton instance is importable."""
        from backend.services.security_alerts import security_alerting_service

        assert security_alerting_service is not None

    def test_singleton_has_expected_methods(self):
        """Test singleton has all expected methods."""
        from backend.services.security_alerts import security_alerting_service

        assert hasattr(security_alerting_service, "record_auth_failure")
        assert hasattr(security_alerting_service, "record_rate_limit_hit")
        assert hasattr(security_alerting_service, "record_lockout")
        assert hasattr(security_alerting_service, "get_event_count")
