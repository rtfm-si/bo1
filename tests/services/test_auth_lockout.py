"""Unit tests for auth lockout service."""

import time
from unittest.mock import MagicMock, patch

import pytest

from backend.services.auth_lockout import AuthLockoutService, auth_lockout_service
from bo1.constants import AuthLockout


class TestAuthLockoutService:
    """Tests for AuthLockoutService."""

    @pytest.fixture
    def service(self) -> AuthLockoutService:
        """Create a fresh service instance for each test."""
        return AuthLockoutService()

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock = MagicMock()
        mock.ping.return_value = True
        return mock

    def test_get_lockout_duration_below_threshold(self):
        """Test no lockout for failures below threshold."""
        service = AuthLockoutService()
        assert service.get_lockout_duration(0) is None
        assert service.get_lockout_duration(1) is None
        assert service.get_lockout_duration(4) is None

    def test_get_lockout_duration_at_5_failures(self):
        """Test 30s lockout at 5 failures."""
        service = AuthLockoutService()
        assert service.get_lockout_duration(5) == 30

    def test_get_lockout_duration_at_10_failures(self):
        """Test 5min lockout at 10 failures."""
        service = AuthLockoutService()
        assert service.get_lockout_duration(10) == 300

    def test_get_lockout_duration_at_15_failures(self):
        """Test 1hr lockout at 15 failures."""
        service = AuthLockoutService()
        assert service.get_lockout_duration(15) == 3600

    def test_get_lockout_duration_between_thresholds(self):
        """Test lockout uses highest applicable threshold."""
        service = AuthLockoutService()
        # 6-9 failures still use 5-failure threshold
        assert service.get_lockout_duration(6) == 30
        assert service.get_lockout_duration(9) == 30
        # 11-14 failures use 10-failure threshold
        assert service.get_lockout_duration(11) == 300
        assert service.get_lockout_duration(14) == 300
        # 16+ failures use 15-failure threshold
        assert service.get_lockout_duration(20) == 3600

    def test_record_failed_attempt_redis_unavailable(self, service: AuthLockoutService):
        """Test recording fails gracefully when Redis unavailable."""
        with patch.object(service, "_get_redis", return_value=None):
            count = service.record_failed_attempt("192.168.1.1", "test")
            assert count == 0

    def test_get_failure_count_redis_unavailable(self, service: AuthLockoutService):
        """Test failure count returns 0 when Redis unavailable."""
        with patch.object(service, "_get_redis", return_value=None):
            count = service.get_failure_count("192.168.1.1")
            assert count == 0

    def test_is_locked_out_redis_unavailable(self, service: AuthLockoutService):
        """Test lockout check fails open when Redis unavailable."""
        with patch.object(service, "_get_redis", return_value=None):
            # Should fail open - not locked out
            assert service.is_locked_out("192.168.1.1") is False

    def test_get_lockout_remaining_redis_unavailable(self, service: AuthLockoutService):
        """Test lockout remaining returns None when Redis unavailable."""
        with patch.object(service, "_get_redis", return_value=None):
            remaining = service.get_lockout_remaining("192.168.1.1")
            assert remaining is None

    def test_clear_attempts_redis_unavailable(self, service: AuthLockoutService):
        """Test clear attempts succeeds gracefully when Redis unavailable."""
        with patch.object(service, "_get_redis", return_value=None):
            # Should not raise
            service.clear_attempts("192.168.1.1")

    def test_record_failed_attempt_with_redis(
        self, service: AuthLockoutService, mock_redis: MagicMock
    ):
        """Test recording increments counter in Redis."""
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [None, None, 1, None]  # zcard returns 1
        mock_redis.pipeline.return_value = mock_pipeline

        with patch.object(service, "_get_redis", return_value=mock_redis):
            count = service.record_failed_attempt("192.168.1.1", "whitelist_rejection")

        assert count == 1
        mock_pipeline.zremrangebyscore.assert_called_once()
        mock_pipeline.zadd.assert_called_once()
        mock_pipeline.expire.assert_called_once()

    def test_get_lockout_remaining_not_locked(
        self, service: AuthLockoutService, mock_redis: MagicMock
    ):
        """Test no lockout when failures below threshold."""
        mock_redis.zremrangebyscore.return_value = None
        mock_redis.zrange.return_value = [
            ("1:test", time.time()),
            ("2:test", time.time()),
        ]  # Only 2 failures

        with patch.object(service, "_get_redis", return_value=mock_redis):
            remaining = service.get_lockout_remaining("192.168.1.1")

        assert remaining is None

    def test_get_lockout_remaining_locked_30s(
        self, service: AuthLockoutService, mock_redis: MagicMock
    ):
        """Test 30s lockout after 5 failures."""
        current_time = time.time()
        # 5 failures, most recent just now
        mock_redis.zremrangebyscore.return_value = None
        mock_redis.zrange.return_value = [(f"{i}:test", current_time - 5 + i) for i in range(5)]

        with patch.object(service, "_get_redis", return_value=mock_redis):
            remaining = service.get_lockout_remaining("192.168.1.1")

        # Should be locked out for ~30 seconds (from most recent attempt)
        assert remaining is not None
        assert 25 < remaining <= 30

    def test_get_lockout_remaining_lockout_expired(
        self, service: AuthLockoutService, mock_redis: MagicMock
    ):
        """Test no lockout when duration has passed."""
        # 5 failures but 31 seconds ago
        old_time = time.time() - 31
        mock_redis.zremrangebyscore.return_value = None
        mock_redis.zrange.return_value = [(f"{i}:test", old_time) for i in range(5)]

        with patch.object(service, "_get_redis", return_value=mock_redis):
            remaining = service.get_lockout_remaining("192.168.1.1")

        assert remaining is None

    def test_is_locked_out_true(self, service: AuthLockoutService):
        """Test is_locked_out returns True when locked."""
        with patch.object(service, "get_lockout_remaining", return_value=25):
            assert service.is_locked_out("192.168.1.1") is True

    def test_is_locked_out_false(self, service: AuthLockoutService):
        """Test is_locked_out returns False when not locked."""
        with patch.object(service, "get_lockout_remaining", return_value=None):
            assert service.is_locked_out("192.168.1.1") is False

    def test_clear_attempts_with_redis(self, service: AuthLockoutService, mock_redis: MagicMock):
        """Test clearing attempts deletes Redis key."""
        with patch.object(service, "_get_redis", return_value=mock_redis):
            service.clear_attempts("192.168.1.1")

        mock_redis.delete.assert_called_once_with("auth_lockout:192.168.1.1")

    def test_key_prefix(self, service: AuthLockoutService):
        """Test Redis key uses correct prefix."""
        key = service._get_key("192.168.1.1")
        assert key == f"{AuthLockout.KEY_PREFIX}192.168.1.1"
        assert key == "auth_lockout:192.168.1.1"


class TestAuthLockoutConstants:
    """Tests for AuthLockout constants."""

    def test_thresholds_defined(self):
        """Test all thresholds are defined."""
        assert 5 in AuthLockout.THRESHOLDS
        assert 10 in AuthLockout.THRESHOLDS
        assert 15 in AuthLockout.THRESHOLDS

    def test_threshold_values(self):
        """Test threshold lockout durations."""
        assert AuthLockout.THRESHOLDS[5] == 30
        assert AuthLockout.THRESHOLDS[10] == 300
        assert AuthLockout.THRESHOLDS[15] == 3600

    def test_window_seconds(self):
        """Test sliding window is 1 hour."""
        assert AuthLockout.WINDOW_SECONDS == 3600

    def test_key_prefix(self):
        """Test Redis key prefix."""
        assert AuthLockout.KEY_PREFIX == "auth_lockout:"


class TestSingletonInstance:
    """Tests for singleton service instance."""

    def test_singleton_exists(self):
        """Test auth_lockout_service singleton is available."""
        assert auth_lockout_service is not None
        assert isinstance(auth_lockout_service, AuthLockoutService)
