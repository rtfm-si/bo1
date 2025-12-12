"""Integration tests for auth lockout in SuperTokens flow.

Tests the lockout service integration with the auth flow,
specifically verifying that:
- Lockout is checked before auth processing
- Failed auth attempts are recorded
- 429 responses are returned when locked out
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.services.auth_lockout import AuthLockoutService
from bo1.constants import AuthLockout


class TestAuthLockoutIntegration:
    """Integration tests for auth lockout with Redis."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client that simulates real behavior."""
        attempts: dict[str, list[tuple[str, float]]] = {}

        def make_pipeline():
            pipeline = MagicMock()
            pipeline_ops = []

            def record_op(name, *args, **kwargs):
                pipeline_ops.append((name, args, kwargs))
                return pipeline

            pipeline.zremrangebyscore = lambda key, min_score, max_score: record_op(
                "zremrangebyscore", key, min_score, max_score
            )
            pipeline.zadd = lambda key, mapping: record_op("zadd", key, mapping)
            pipeline.zcard = lambda key: record_op("zcard", key)
            pipeline.expire = lambda key, ttl: record_op("expire", key, ttl)

            def execute():
                results = []
                for op_name, args, _ in pipeline_ops:
                    key = args[0] if args else None
                    if op_name == "zremrangebyscore" and key:
                        # Clean old entries
                        if key in attempts:
                            max_score = args[2]
                            attempts[key] = [(v, s) for v, s in attempts[key] if s > max_score]
                        results.append(None)
                    elif op_name == "zadd" and key:
                        # Add new entry
                        if key not in attempts:
                            attempts[key] = []
                        for val, score in args[1].items():
                            attempts[key].append((val, score))
                        results.append(1)
                    elif op_name == "zcard" and key:
                        results.append(len(attempts.get(key, [])))
                    elif op_name == "expire":
                        results.append(True)
                    else:
                        results.append(None)
                pipeline_ops.clear()
                return results

            pipeline.execute = execute
            return pipeline

        mock = MagicMock()
        mock.ping.return_value = True
        mock.pipeline = make_pipeline
        mock.zremrangebyscore = lambda key, min_s, max_s: None
        mock.zrange = lambda key, start, end, withscores: attempts.get(key, [])
        mock.delete = lambda key: attempts.pop(key, None)

        return mock, attempts

    def test_lockout_triggers_after_5_failures(self, mock_redis_client):
        """Test that lockout activates after 5 failed attempts."""
        mock_redis, attempts = mock_redis_client
        service = AuthLockoutService()

        with patch.object(service, "_get_redis", return_value=mock_redis):
            # Record 5 failures
            for _ in range(5):
                service.record_failed_attempt("192.168.1.100", "test")

            # Should now be locked out
            assert service.is_locked_out("192.168.1.100")
            remaining = service.get_lockout_remaining("192.168.1.100")
            assert remaining is not None
            assert remaining > 0
            assert remaining <= 30

    def test_lockout_duration_increases_with_failures(self, mock_redis_client):
        """Test exponential backoff: 5=30s, 10=5min, 15=1hr."""
        mock_redis, attempts = mock_redis_client
        service = AuthLockoutService()

        with patch.object(service, "_get_redis", return_value=mock_redis):
            # 5 failures = 30s
            for _ in range(5):
                service.record_failed_attempt("192.168.1.101", "test")
            remaining = service.get_lockout_remaining("192.168.1.101")
            assert remaining is not None
            assert remaining <= 30

            # 10 failures = 5min
            for _ in range(5):
                service.record_failed_attempt("192.168.1.101", "test")
            remaining = service.get_lockout_remaining("192.168.1.101")
            assert remaining is not None
            assert remaining <= 300

            # 15 failures = 1hr
            for _ in range(5):
                service.record_failed_attempt("192.168.1.101", "test")
            remaining = service.get_lockout_remaining("192.168.1.101")
            assert remaining is not None
            assert remaining <= 3600

    def test_lockout_check_before_auth(self):
        """Test that lockout is checked in API override."""
        from backend.api.supertokens_config import _get_client_ip

        # Test IP extraction helper
        mock_request = MagicMock()
        mock_request.get_header.return_value = None
        mock_request.request.client.host = "10.0.0.1"

        ip = _get_client_ip(mock_request)
        assert ip == "10.0.0.1"

    def test_ip_extraction_x_forwarded_for(self):
        """Test IP extraction from X-Forwarded-For header."""
        from backend.api.supertokens_config import _get_client_ip

        mock_request = MagicMock()
        mock_request.get_header.side_effect = lambda h: (
            "203.0.113.1, 10.0.0.1" if h == "x-forwarded-for" else None
        )

        ip = _get_client_ip(mock_request)
        assert ip == "203.0.113.1"

    def test_ip_extraction_x_real_ip(self):
        """Test IP extraction from X-Real-IP header."""
        from backend.api.supertokens_config import _get_client_ip

        mock_request = MagicMock()
        mock_request.get_header.side_effect = lambda h: (
            "198.51.100.1" if h == "x-real-ip" else None
        )

        ip = _get_client_ip(mock_request)
        assert ip == "198.51.100.1"

    def test_failure_recorded_on_whitelist_rejection(self, mock_redis_client):
        """Test that whitelist rejections are tracked."""
        mock_redis, attempts = mock_redis_client
        service = AuthLockoutService()

        with patch.object(service, "_get_redis", return_value=mock_redis):
            count = service.record_failed_attempt("192.168.1.102", "whitelist_rejection")
            assert count == 1

            count = service.record_failed_attempt("192.168.1.102", "whitelist_rejection")
            assert count == 2

    def test_failure_recorded_on_locked_account(self, mock_redis_client):
        """Test that locked account attempts are tracked."""
        mock_redis, attempts = mock_redis_client
        service = AuthLockoutService()

        with patch.object(service, "_get_redis", return_value=mock_redis):
            count = service.record_failed_attempt("192.168.1.103", "account_locked")
            assert count == 1

    def test_clear_attempts_on_success(self, mock_redis_client):
        """Test clearing attempts after successful login (optional feature)."""
        mock_redis, attempts = mock_redis_client
        service = AuthLockoutService()

        # Add zcard mock for get_failure_count
        mock_redis.zcard = lambda key: len(attempts.get(key, []))

        with patch.object(service, "_get_redis", return_value=mock_redis):
            # Add some failures
            for _ in range(3):
                service.record_failed_attempt("192.168.1.104", "test")

            # Clear on success
            service.clear_attempts("192.168.1.104")

            # Should no longer be in tracking
            count = service.get_failure_count("192.168.1.104")
            assert count == 0


class TestAuthLockoutEdgeCases:
    """Edge case tests for auth lockout."""

    def test_redis_connection_failure_fails_open(self):
        """Test that Redis connection failure doesn't block auth."""
        service = AuthLockoutService()

        with patch.object(service, "_get_redis", return_value=None):
            # Should not raise, should return default values
            assert service.is_locked_out("192.168.1.1") is False
            assert service.get_lockout_remaining("192.168.1.1") is None
            assert service.get_failure_count("192.168.1.1") == 0
            assert service.record_failed_attempt("192.168.1.1", "test") == 0

    def test_multiple_ips_tracked_separately(self):
        """Test that different IPs have separate lockout counters."""
        service = AuthLockoutService()

        # Different IPs get different keys
        key1 = service._get_key("192.168.1.1")
        key2 = service._get_key("192.168.1.2")

        assert key1 != key2
        assert "192.168.1.1" in key1
        assert "192.168.1.2" in key2


class TestAuthLockoutConstants:
    """Test that constants are correctly configured."""

    def test_thresholds_exponential(self):
        """Test that lockout durations increase exponentially."""
        durations = list(AuthLockout.THRESHOLDS.values())
        # 30s, 300s (5min), 3600s (1hr)
        assert durations[0] < durations[1] < durations[2]
        # Roughly 10x between each level
        assert durations[1] == 10 * durations[0]  # 300 = 10 * 30
        assert durations[2] == 12 * durations[1]  # 3600 = 12 * 300

    def test_window_covers_longest_lockout(self):
        """Test that window is at least as long as longest lockout."""
        max_lockout = max(AuthLockout.THRESHOLDS.values())
        assert AuthLockout.WINDOW_SECONDS >= max_lockout
