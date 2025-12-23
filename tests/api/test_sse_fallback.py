"""Tests for SSE PostgreSQL polling fallback.

Tests for:
- SSEPollingFallback class
- poll_events_from_postgres function
- is_redis_sse_available helper
- Fallback activation and deduplication
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.api.event_poller import (
    SSEPollingFallback,
    is_redis_sse_available,
    poll_events_from_postgres,
)


class TestPollEventsFromPostgres:
    """Tests for poll_events_from_postgres function."""

    def test_poll_returns_events_after_sequence(self):
        """Events with sequence > last_sequence are returned."""
        mock_events = [
            {"data": {"sequence": 1, "event_type": "session_started", "data": {}}},
            {"data": {"sequence": 2, "event_type": "contribution", "data": {}}},
            {"data": {"sequence": 3, "event_type": "complete", "data": {}}},
        ]

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=mock_events,
        ):
            result = poll_events_from_postgres("bo1_test", last_sequence=1, limit=50)

        assert len(result) == 2
        assert result[0]["sequence"] == 2
        assert result[1]["sequence"] == 3

    def test_poll_respects_limit(self):
        """Only up to limit events are returned."""
        mock_events = [
            {"data": {"sequence": i, "event_type": "contribution", "data": {}}}
            for i in range(1, 20)
        ]

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=mock_events,
        ):
            result = poll_events_from_postgres("bo1_test", last_sequence=0, limit=5)

        assert len(result) == 5

    def test_poll_returns_empty_on_error(self):
        """Empty list returned on repository error."""
        with patch(
            "backend.api.event_poller.session_repository.get_events",
            side_effect=Exception("DB error"),
        ):
            result = poll_events_from_postgres("bo1_test")

        assert result == []

    def test_poll_handles_missing_data_column(self):
        """Events without data column are filtered out."""
        mock_events = [
            {"data": {"sequence": 1, "event_type": "session_started", "data": {}}},
            {},  # Missing data column
            {"data": {"sequence": 3, "event_type": "complete", "data": {}}},
        ]

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=mock_events,
        ):
            result = poll_events_from_postgres("bo1_test", last_sequence=0)

        # Only events with valid data are returned
        assert len(result) == 2


class TestSSEPollingFallback:
    """Tests for SSEPollingFallback class."""

    def test_init_defaults(self):
        """Default configuration is applied."""
        poller = SSEPollingFallback("bo1_test")

        assert poller.session_id == "bo1_test"
        assert poller.poll_interval_ms == 500
        assert poller.batch_size == 50
        assert poller.circuit_check_interval_ms == 5000
        assert poller.last_sequence == 0

    def test_set_last_sequence(self):
        """Last sequence can be set for deduplication."""
        poller = SSEPollingFallback("bo1_test")
        poller.set_last_sequence(42)

        assert poller.last_sequence == 42

    def test_poll_once_updates_last_sequence(self):
        """poll_once updates last_sequence based on returned events."""
        mock_events = [
            {"data": {"sequence": 5, "event_type": "contribution", "data": {}}},
            {"data": {"sequence": 6, "event_type": "contribution", "data": {}}},
        ]

        poller = SSEPollingFallback("bo1_test")

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=mock_events,
        ):
            events = poller.poll_once()

        assert len(events) == 2
        assert poller.last_sequence == 6

    def test_poll_once_deduplicates(self):
        """Subsequent polls skip already-seen sequences."""
        poller = SSEPollingFallback("bo1_test")
        poller.set_last_sequence(5)

        mock_events = [
            {"data": {"sequence": 4, "event_type": "contribution", "data": {}}},
            {"data": {"sequence": 5, "event_type": "contribution", "data": {}}},
            {"data": {"sequence": 6, "event_type": "contribution", "data": {}}},
        ]

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=mock_events,
        ):
            events = poller.poll_once()

        # Only sequence 6 should be returned (> 5)
        assert len(events) == 1
        assert events[0]["sequence"] == 6

    def test_stop_flag(self):
        """stop() sets the stop flag."""
        poller = SSEPollingFallback("bo1_test")

        assert poller._stop_requested is False
        poller.stop()
        assert poller._stop_requested is True

    def test_should_check_redis_recovery(self):
        """Recovery check respects interval."""
        poller = SSEPollingFallback("bo1_test", circuit_check_interval_ms=100)

        # First call should return True
        assert poller.should_check_redis_recovery() is True

        # Immediate second call should return False
        assert poller.should_check_redis_recovery() is False

    @pytest.mark.asyncio
    async def test_poll_loop_stops_on_complete_event(self):
        """poll_loop exits when complete event is received."""
        mock_events_sequence = [
            [{"sequence": 1, "event_type": "contribution", "data": {}}],
            [{"sequence": 2, "event_type": "complete", "data": {}}],
        ]
        call_count = 0

        def mock_poll():
            nonlocal call_count
            if call_count < len(mock_events_sequence):
                result = mock_events_sequence[call_count]
                call_count += 1
                return result
            return []

        poller = SSEPollingFallback("bo1_test", poll_interval_ms=10)

        with patch.object(poller, "poll_once", side_effect=mock_poll):
            events_received = []
            async for events in poller.poll_loop():
                events_received.extend(events)

        assert len(events_received) == 2
        assert events_received[1]["event_type"] == "complete"

    @pytest.mark.asyncio
    async def test_poll_loop_stops_on_error_event(self):
        """poll_loop exits when error event is received."""
        mock_events = [{"sequence": 1, "event_type": "error", "data": {}}]

        poller = SSEPollingFallback("bo1_test", poll_interval_ms=10)

        with patch.object(poller, "poll_once", return_value=mock_events):
            events_received = []
            async for events in poller.poll_loop():
                events_received.extend(events)

        assert len(events_received) == 1
        assert events_received[0]["event_type"] == "error"

    @pytest.mark.asyncio
    async def test_poll_loop_respects_stop(self):
        """poll_loop exits when stop() is called."""
        poller = SSEPollingFallback("bo1_test", poll_interval_ms=10)
        loop_iterations = 0

        def mock_poll():
            nonlocal loop_iterations
            loop_iterations += 1
            if loop_iterations >= 3:
                poller.stop()
            return []

        with patch.object(poller, "poll_once", side_effect=mock_poll):
            async for _ in poller.poll_loop():
                pass

        assert loop_iterations == 3


class TestIsRedisSSEAvailable:
    """Tests for is_redis_sse_available helper."""

    def test_returns_false_when_circuit_open(self):
        """Returns False when Redis circuit breaker is open."""
        with patch(
            "bo1.state.circuit_breaker_wrappers.is_redis_circuit_open",
            return_value=True,
        ):
            assert is_redis_sse_available() is False

    def test_returns_false_when_redis_manager_unavailable(self):
        """Returns False when RedisManager reports unavailable."""
        mock_manager = MagicMock()
        mock_manager.is_available = False

        with (
            patch(
                "bo1.state.circuit_breaker_wrappers.is_redis_circuit_open",
                return_value=False,
            ),
            patch(
                "backend.api.dependencies.get_redis_manager",
                return_value=mock_manager,
            ),
        ):
            assert is_redis_sse_available() is False

    def test_returns_false_when_ping_fails(self):
        """Returns False when Redis ping fails."""
        mock_manager = MagicMock()
        mock_manager.is_available = True
        mock_manager.redis.ping.side_effect = Exception("Connection refused")

        with (
            patch(
                "bo1.state.circuit_breaker_wrappers.is_redis_circuit_open",
                return_value=False,
            ),
            patch(
                "backend.api.dependencies.get_redis_manager",
                return_value=mock_manager,
            ),
        ):
            assert is_redis_sse_available() is False

    def test_returns_true_when_all_checks_pass(self):
        """Returns True when circuit closed, manager available, and ping succeeds."""
        mock_manager = MagicMock()
        mock_manager.is_available = True
        mock_manager.redis.ping.return_value = True

        with (
            patch(
                "bo1.state.circuit_breaker_wrappers.is_redis_circuit_open",
                return_value=False,
            ),
            patch(
                "backend.api.dependencies.get_redis_manager",
                return_value=mock_manager,
            ),
        ):
            assert is_redis_sse_available() is True


class TestFallbackActivation:
    """Tests for SSE fallback activation scenarios."""

    def test_fallback_emits_activation_event(self):
        """Fallback activation should emit sse_fallback_activated event."""
        # This is more of an integration test - the event is emitted in streaming.py
        # but we verify the event format here
        from backend.api import events as sse_events

        fallback_event = sse_events.format_sse_event(
            "sse_fallback_activated",
            {"session_id": "bo1_test", "mode": "polling", "reason": "circuit_open"},
        )

        assert "event: sse_fallback_activated" in fallback_event
        assert '"mode": "polling"' in fallback_event
        assert '"reason": "circuit_open"' in fallback_event


class TestFallbackDeduplication:
    """Tests for event deduplication during fallback."""

    def test_deduplicates_by_sequence(self):
        """Events already seen via PubSub are not re-sent via polling."""
        poller = SSEPollingFallback("bo1_test")

        # Simulate having seen sequences 1-5 via PubSub
        poller.set_last_sequence(5)

        # Polling returns events 3-7 (overlap with seen)
        mock_events = [
            {"data": {"sequence": i, "event_type": "contribution", "data": {}}} for i in range(3, 8)
        ]

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=mock_events,
        ):
            events = poller.poll_once()

        # Only sequences 6, 7 should be returned
        assert len(events) == 2
        assert events[0]["sequence"] == 6
        assert events[1]["sequence"] == 7


class TestFallbackRecoveryCheck:
    """Tests for Redis recovery detection."""

    def test_recovery_check_interval(self):
        """Recovery checks respect configured interval."""
        import time

        poller = SSEPollingFallback("bo1_test", circuit_check_interval_ms=50)

        # First check should succeed
        assert poller.should_check_redis_recovery() is True

        # Immediate recheck should fail
        assert poller.should_check_redis_recovery() is False

        # Wait for interval
        time.sleep(0.06)

        # Now check should succeed again
        assert poller.should_check_redis_recovery() is True
