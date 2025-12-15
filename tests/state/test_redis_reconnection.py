"""Tests for Redis reconnection logic in RedisManager.

Validates:
- Connection state tracking (connected/disconnected/reconnecting)
- Exponential backoff calculation
- Reconnection attempt limits
- Connection error handling
"""

from unittest.mock import MagicMock, patch

import redis

from bo1.constants import RedisReconnection
from bo1.state.redis_manager import RedisConnectionState, RedisManager


class TestRedisConnectionState:
    """Test RedisConnectionState enum values."""

    def test_state_values(self):
        """All expected states exist."""
        assert RedisConnectionState.CONNECTED.value == "connected"
        assert RedisConnectionState.DISCONNECTED.value == "disconnected"
        assert RedisConnectionState.RECONNECTING.value == "reconnecting"


class TestRedisManagerConnectionTracking:
    """Test RedisManager connection state tracking."""

    def test_initial_state_connected_on_success(self):
        """Connection state is CONNECTED after successful initialization."""
        with patch("bo1.state.redis_manager.redis.ConnectionPool"):
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True

            with patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis):
                manager = RedisManager(host="localhost", port=6379)

                assert manager.connection_state == RedisConnectionState.CONNECTED
                assert manager.is_available is True
                assert manager.reconnect_attempts == 0

    def test_initial_state_disconnected_on_failure(self):
        """Connection state is DISCONNECTED after failed initialization."""
        with patch("bo1.state.redis_manager.redis.ConnectionPool"):
            mock_redis = MagicMock()
            mock_redis.ping.side_effect = redis.ConnectionError("Connection refused")

            with patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis):
                manager = RedisManager(host="localhost", port=6379)

                assert manager.connection_state == RedisConnectionState.DISCONNECTED
                assert manager.is_available is False


class TestBackoffCalculation:
    """Test exponential backoff delay calculation."""

    def test_initial_delay(self):
        """First attempt uses INITIAL_DELAY_MS."""
        with patch("bo1.state.redis_manager.redis.ConnectionPool"):
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True

            with patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis):
                manager = RedisManager(host="localhost", port=6379)
                manager._reconnect_attempts = 0

                delay = manager._calculate_backoff_delay()

                expected = RedisReconnection.INITIAL_DELAY_MS / 1000.0
                assert delay == expected

    def test_exponential_backoff(self):
        """Delay doubles with each attempt."""
        with patch("bo1.state.redis_manager.redis.ConnectionPool"):
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True

            with patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis):
                manager = RedisManager(host="localhost", port=6379)

                # First attempt
                manager._reconnect_attempts = 0
                delay_0 = manager._calculate_backoff_delay()

                # Second attempt
                manager._reconnect_attempts = 1
                delay_1 = manager._calculate_backoff_delay()

                # Third attempt
                manager._reconnect_attempts = 2
                delay_2 = manager._calculate_backoff_delay()

                # Verify exponential growth
                assert delay_1 == delay_0 * RedisReconnection.BACKOFF_FACTOR
                assert delay_2 == delay_1 * RedisReconnection.BACKOFF_FACTOR

    def test_max_delay_cap(self):
        """Delay capped at MAX_DELAY_MS."""
        with patch("bo1.state.redis_manager.redis.ConnectionPool"):
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True

            with patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis):
                manager = RedisManager(host="localhost", port=6379)
                manager._reconnect_attempts = 100  # Very high attempt count

                delay = manager._calculate_backoff_delay()

                max_delay = RedisReconnection.MAX_DELAY_MS / 1000.0
                assert delay == max_delay


class TestReconnectionAttempts:
    """Test reconnection attempt handling."""

    def test_max_attempts_exceeded(self):
        """Reconnection fails after MAX_ATTEMPTS exceeded."""
        with patch("bo1.state.redis_manager.redis.ConnectionPool"):
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True

            with patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis):
                manager = RedisManager(host="localhost", port=6379)
                manager._reconnect_attempts = RedisReconnection.MAX_ATTEMPTS
                manager._connection_state = RedisConnectionState.DISCONNECTED
                manager._available = False

                result = manager._attempt_reconnect()

                assert result is False
                # Attempts should not increase beyond max
                assert manager._reconnect_attempts == RedisReconnection.MAX_ATTEMPTS

    def test_successful_reconnect_resets_attempts(self):
        """Successful reconnection resets attempt counter."""
        with patch("bo1.state.redis_manager.redis.ConnectionPool"):
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True

            with patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis):
                with patch("time.sleep"):  # Skip actual sleep
                    with patch("bo1.state.redis_manager.redis.ConnectionPool"):
                        manager = RedisManager(host="localhost", port=6379)
                        manager._reconnect_attempts = 3
                        manager._connection_state = RedisConnectionState.DISCONNECTED
                        manager._available = False

                        result = manager._attempt_reconnect()

                        assert result is True
                        assert manager._reconnect_attempts == 0
                        assert manager._connection_state == RedisConnectionState.CONNECTED
                        assert manager._available is True


class TestConnectionErrorHandling:
    """Test _handle_connection_error behavior."""

    def test_error_sets_disconnected_state(self):
        """Connection error transitions to DISCONNECTED state."""
        with patch("bo1.state.redis_manager.redis.ConnectionPool"):
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True

            with patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis):
                manager = RedisManager(host="localhost", port=6379)
                assert manager._connection_state == RedisConnectionState.CONNECTED

                manager._handle_connection_error(Exception("Connection lost"))

                assert manager._connection_state == RedisConnectionState.DISCONNECTED
                assert manager._available is False

    def test_error_only_transitions_once(self):
        """Multiple errors don't re-trigger disconnect handling."""
        with patch("bo1.state.redis_manager.redis.ConnectionPool"):
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True

            with patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis):
                manager = RedisManager(host="localhost", port=6379)

                # First error
                manager._handle_connection_error(Exception("Error 1"))
                assert manager._connection_state == RedisConnectionState.DISCONNECTED

                # Second error should not change state (already disconnected)
                manager._handle_connection_error(Exception("Error 2"))
                assert manager._connection_state == RedisConnectionState.DISCONNECTED


class TestEnsureConnected:
    """Test _ensure_connected guard method."""

    def test_returns_true_when_connected(self):
        """Returns True immediately when already connected."""
        with patch("bo1.state.redis_manager.redis.ConnectionPool"):
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True

            with patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis):
                manager = RedisManager(host="localhost", port=6379)

                result = manager._ensure_connected()

                assert result is True

    def test_returns_false_when_reconnecting(self):
        """Returns False when reconnection already in progress."""
        with patch("bo1.state.redis_manager.redis.ConnectionPool"):
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True

            with patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis):
                manager = RedisManager(host="localhost", port=6379)
                manager._connection_state = RedisConnectionState.RECONNECTING

                result = manager._ensure_connected()

                assert result is False

    def test_attempts_reconnect_when_disconnected(self):
        """Attempts reconnection when disconnected."""
        with patch("bo1.state.redis_manager.redis.ConnectionPool"):
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True

            with patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis):
                with patch("time.sleep"):
                    manager = RedisManager(host="localhost", port=6379)
                    manager._connection_state = RedisConnectionState.DISCONNECTED
                    manager._available = False

                    result = manager._ensure_connected()

                    assert result is True
                    assert manager._connection_state == RedisConnectionState.CONNECTED
