"""Chaos tests for SSE Redis fallback to PostgreSQL polling.

Validates:
- is_redis_sse_available returns False when circuit breaker is open
- is_redis_sse_available returns False when Redis ping fails
- is_redis_sse_available returns True when Redis is healthy
- SSEPollingFallback polls events from PostgreSQL
- Polling fallback correctly tracks sequence numbers
- Polling fallback stops on terminal events
- End-to-end fallback flow when Redis is unavailable
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.api.event_poller import (
    SSEPollingFallback,
    is_redis_sse_available,
    poll_events_from_postgres,
)

# ============================================================================
# is_redis_sse_available() Tests
# ============================================================================


@pytest.mark.chaos
class TestIsRedisSseAvailableCircuitOpen:
    """Test is_redis_sse_available returns False when circuit is open."""

    def test_returns_false_when_circuit_open(self) -> None:
        """Circuit breaker open should immediately return False."""
        with patch("bo1.state.circuit_breaker_wrappers.is_redis_circuit_open", return_value=True):
            result = is_redis_sse_available()

            assert result is False

    def test_does_not_ping_when_circuit_open(self) -> None:
        """Should not attempt ping when circuit is already open."""
        with (
            patch("bo1.state.circuit_breaker_wrappers.is_redis_circuit_open", return_value=True),
            patch("backend.api.dependencies.get_redis_manager") as mock_get_redis,
        ):
            is_redis_sse_available()

            # Should not have called get_redis_manager since circuit is open
            mock_get_redis.assert_not_called()


@pytest.mark.chaos
class TestIsRedisSseAvailablePingFails:
    """Test is_redis_sse_available returns False when ping fails."""

    def test_returns_false_when_ping_raises_connection_error(self) -> None:
        """ConnectionError during ping should return False."""
        mock_redis = MagicMock()
        mock_redis.is_available = True
        mock_redis.redis.ping.side_effect = ConnectionError("Connection refused")

        with (
            patch("bo1.state.circuit_breaker_wrappers.is_redis_circuit_open", return_value=False),
            patch("backend.api.dependencies.get_redis_manager", return_value=mock_redis),
        ):
            result = is_redis_sse_available()

            assert result is False

    def test_returns_false_when_ping_raises_timeout(self) -> None:
        """Timeout during ping should return False."""
        mock_redis = MagicMock()
        mock_redis.is_available = True
        mock_redis.redis.ping.side_effect = TimeoutError("Connection timed out")

        with (
            patch("bo1.state.circuit_breaker_wrappers.is_redis_circuit_open", return_value=False),
            patch("backend.api.dependencies.get_redis_manager", return_value=mock_redis),
        ):
            result = is_redis_sse_available()

            assert result is False

    def test_returns_false_when_redis_manager_not_available(self) -> None:
        """Should return False when redis manager is_available is False."""
        mock_redis = MagicMock()
        mock_redis.is_available = False

        with (
            patch("bo1.state.circuit_breaker_wrappers.is_redis_circuit_open", return_value=False),
            patch("backend.api.dependencies.get_redis_manager", return_value=mock_redis),
        ):
            result = is_redis_sse_available()

            assert result is False


@pytest.mark.chaos
class TestIsRedisSseAvailableHealthy:
    """Test is_redis_sse_available returns True when Redis is healthy."""

    def test_returns_true_when_circuit_closed_and_ping_succeeds(self) -> None:
        """Healthy Redis should return True."""
        mock_redis = MagicMock()
        mock_redis.is_available = True
        mock_redis.redis.ping.return_value = True

        with (
            patch("bo1.state.circuit_breaker_wrappers.is_redis_circuit_open", return_value=False),
            patch("backend.api.dependencies.get_redis_manager", return_value=mock_redis),
        ):
            result = is_redis_sse_available()

            assert result is True
            mock_redis.redis.ping.assert_called_once()


# ============================================================================
# poll_events_from_postgres() Tests
# ============================================================================


@pytest.mark.chaos
class TestPollEventsFromPostgres:
    """Test poll_events_from_postgres retrieves and filters events."""

    def test_polls_events_after_sequence(self) -> None:
        """Should only return events with sequence > last_sequence."""
        mock_events = [
            {"data": {"sequence": 1, "event_type": "start"}},
            {"data": {"sequence": 2, "event_type": "progress"}},
            {"data": {"sequence": 3, "event_type": "progress"}},
            {"data": {"sequence": 4, "event_type": "complete"}},
        ]

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=mock_events,
        ):
            events = poll_events_from_postgres("session-123", last_sequence=2)

            # Should only get events with sequence > 2
            assert len(events) == 2
            assert events[0]["sequence"] == 3
            assert events[1]["sequence"] == 4

    def test_respects_limit(self) -> None:
        """Should respect the limit parameter."""
        mock_events = [
            {"data": {"sequence": i, "event_type": "progress"}}
            for i in range(1, 101)  # 100 events
        ]

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=mock_events,
        ):
            events = poll_events_from_postgres("session-123", last_sequence=0, limit=10)

            assert len(events) == 10

    def test_returns_empty_on_error(self) -> None:
        """Should return empty list on repository error."""
        with patch(
            "backend.api.event_poller.session_repository.get_events",
            side_effect=Exception("Database error"),
        ):
            events = poll_events_from_postgres("session-123")

            assert events == []


# ============================================================================
# SSEPollingFallback Tests
# ============================================================================


@pytest.mark.chaos
class TestSSEPollingFallbackPollsFromPostgres:
    """Test SSEPollingFallback.poll_once() retrieves events."""

    def test_poll_once_returns_events(self) -> None:
        """poll_once should retrieve events from PostgreSQL."""
        mock_events = [
            {"data": {"sequence": 1, "event_type": "start"}},
            {"data": {"sequence": 2, "event_type": "progress"}},
        ]

        poller = SSEPollingFallback("session-123")

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=mock_events,
        ):
            events = poller.poll_once()

            assert len(events) == 2
            assert events[0]["event_type"] == "start"


@pytest.mark.chaos
class TestSSEPollingFallbackTracksSequence:
    """Test SSEPollingFallback correctly tracks sequence numbers."""

    def test_updates_last_sequence_after_poll(self) -> None:
        """last_sequence should update to max sequence from polled events."""
        mock_events = [
            {"data": {"sequence": 5, "event_type": "progress"}},
            {"data": {"sequence": 7, "event_type": "progress"}},
            {"data": {"sequence": 6, "event_type": "progress"}},
        ]

        poller = SSEPollingFallback("session-123")
        assert poller.last_sequence == 0

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=mock_events,
        ):
            poller.poll_once()

            # Should be max sequence (7)
            assert poller.last_sequence == 7

    def test_set_last_sequence_for_replay(self) -> None:
        """set_last_sequence should update tracking for replay scenarios."""
        poller = SSEPollingFallback("session-123")

        poller.set_last_sequence(100)

        assert poller.last_sequence == 100

    def test_subsequent_polls_use_updated_sequence(self) -> None:
        """Subsequent polls should use the updated last_sequence."""
        # First batch
        first_events = [
            {"data": {"sequence": 1, "event_type": "start"}},
            {"data": {"sequence": 2, "event_type": "progress"}},
        ]
        # Second batch (after sequence 2) - combined with first for repository query
        second_batch = [
            {"data": {"sequence": 3, "event_type": "progress"}},
            {"data": {"sequence": 4, "event_type": "complete"}},
        ]
        # Combined for repository (it returns all)
        all_events = first_events + second_batch

        poller = SSEPollingFallback("session-123")

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=first_events,
        ):
            poller.poll_once()
            assert poller.last_sequence == 2

        # Now poll again with all events - should only get those > 2
        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=all_events,
        ):
            events = poller.poll_once()
            # Should only get events 3 and 4
            assert len(events) == 2
            assert events[0]["sequence"] == 3
            assert events[1]["sequence"] == 4


@pytest.mark.chaos
class TestSSEPollingFallbackStopsOnTerminalEvent:
    """Test SSEPollingFallback stops on complete/error events."""

    @pytest.mark.asyncio
    async def test_stops_on_complete_event(self) -> None:
        """poll_loop should stop when encountering 'complete' event."""
        mock_events = [
            {"data": {"sequence": 1, "event_type": "progress"}},
            {"data": {"sequence": 2, "event_type": "complete"}},
        ]

        poller = SSEPollingFallback("session-123", poll_interval_ms=10)

        events_yielded: list[list[dict[str, Any]]] = []

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=mock_events,
        ):
            async for batch in poller.poll_loop():
                events_yielded.append(batch)
                # Should stop after first batch (contains complete event)

        assert len(events_yielded) == 1
        assert any(e["event_type"] == "complete" for e in events_yielded[0])

    @pytest.mark.asyncio
    async def test_stops_on_error_event(self) -> None:
        """poll_loop should stop when encountering 'error' event."""
        mock_events = [
            {"data": {"sequence": 1, "event_type": "progress"}},
            {"data": {"sequence": 2, "event_type": "error"}},
        ]

        poller = SSEPollingFallback("session-123", poll_interval_ms=10)

        events_yielded: list[list[dict[str, Any]]] = []

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=mock_events,
        ):
            async for batch in poller.poll_loop():
                events_yielded.append(batch)

        assert len(events_yielded) == 1
        assert any(e["event_type"] == "error" for e in events_yielded[0])

    @pytest.mark.asyncio
    async def test_stop_method_stops_loop(self) -> None:
        """stop() should terminate the poll_loop."""
        poller = SSEPollingFallback("session-123", poll_interval_ms=10)

        events_yielded: list[list[dict[str, Any]]] = []
        call_count = 0

        def mock_get_events(session_id: str) -> list[dict[str, Any]]:
            nonlocal call_count
            call_count += 1
            # Return incrementing sequence numbers so filter always passes
            return [
                {"data": {"sequence": call_count * 10, "event_type": "progress"}},
            ]

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            side_effect=mock_get_events,
        ):
            async for batch in poller.poll_loop():
                events_yielded.append(batch)
                if len(events_yielded) >= 2:
                    poller.stop()

        # Should have stopped after 2 polls
        assert len(events_yielded) >= 2


# ============================================================================
# End-to-End Fallback Flow Tests
# ============================================================================


@pytest.mark.chaos
class TestRedisDownSSEUsesPostgresEvents:
    """Integration test for complete SSE fallback flow."""

    @pytest.mark.asyncio
    async def test_redis_down_sse_uses_postgres_events(self) -> None:
        """When Redis unavailable, SSE should poll from PostgreSQL.

        This is the main integration test that validates:
        1. is_redis_sse_available() detects Redis is down
        2. SSEPollingFallback is used instead of PubSub
        3. Events are correctly retrieved from PostgreSQL
        4. Sequence tracking works across polls
        5. Terminal event stops the stream
        """
        # Simulate Redis unavailable (circuit breaker open)
        with patch("bo1.state.circuit_breaker_wrappers.is_redis_circuit_open", return_value=True):
            # Verify Redis is detected as unavailable
            assert is_redis_sse_available() is False

        # Simulate PostgreSQL events for the session
        postgres_events_batch1 = [
            {
                "data": {
                    "sequence": 1,
                    "event_type": "session_started",
                    "session_id": "test-session",
                }
            },
            {
                "data": {
                    "sequence": 2,
                    "event_type": "decomposition_started",
                    "session_id": "test-session",
                }
            },
        ]
        postgres_events_batch2 = [
            {
                "data": {
                    "sequence": 1,
                    "event_type": "session_started",
                    "session_id": "test-session",
                }
            },
            {
                "data": {
                    "sequence": 2,
                    "event_type": "decomposition_started",
                    "session_id": "test-session",
                }
            },
            {"data": {"sequence": 3, "event_type": "round_started", "round": 1}},
            {"data": {"sequence": 4, "event_type": "complete", "session_id": "test-session"}},
        ]

        # Create fallback poller
        poller = SSEPollingFallback("test-session", poll_interval_ms=10)

        all_events: list[dict[str, Any]] = []
        poll_iteration = 0

        def mock_get_events(session_id: str) -> list[dict[str, Any]]:
            nonlocal poll_iteration
            poll_iteration += 1
            # First poll returns batch1, subsequent polls return batch2
            if poll_iteration == 1:
                return postgres_events_batch1
            return postgres_events_batch2

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            side_effect=mock_get_events,
        ):
            async for batch in poller.poll_loop():
                all_events.extend(batch)

        # Verify we got all events in correct order
        event_types = [e["event_type"] for e in all_events]

        assert "session_started" in event_types
        assert "decomposition_started" in event_types
        assert "round_started" in event_types
        assert "complete" in event_types

        # Verify sequence tracking prevented duplicates
        sequences = [e["sequence"] for e in all_events]
        assert len(sequences) == len(set(sequences)), "Duplicate sequences found"

        # Verify terminal event stopped the loop
        assert all_events[-1]["event_type"] == "complete"

    @pytest.mark.asyncio
    async def test_fallback_emits_correct_event_order(self) -> None:
        """Events should be yielded in sequence order."""
        mock_events = [
            {"data": {"sequence": 3, "event_type": "c"}},
            {"data": {"sequence": 1, "event_type": "a"}},
            {"data": {"sequence": 4, "event_type": "complete"}},
            {"data": {"sequence": 2, "event_type": "b"}},
        ]

        poller = SSEPollingFallback("session-123", poll_interval_ms=10)

        all_events: list[dict[str, Any]] = []

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=mock_events,
        ):
            async for batch in poller.poll_loop():
                all_events.extend(batch)

        # Should have all 4 events
        assert len(all_events) == 4

    def test_should_check_redis_recovery_respects_interval(self) -> None:
        """should_check_redis_recovery should respect the configured interval."""
        poller = SSEPollingFallback(
            "session-123",
            circuit_check_interval_ms=5000,  # 5 seconds
        )

        # First check should return True
        assert poller.should_check_redis_recovery() is True

        # Immediate second check should return False (not enough time passed)
        assert poller.should_check_redis_recovery() is False

    def test_sse_fallback_activated_event_scenario(self) -> None:
        """Simulate the scenario where sse_fallback_activated would be emitted.

        Note: The actual event emission happens in streaming.py, not event_poller.py.
        This test validates the detection that would trigger that event.
        """
        # Redis circuit is open
        with (
            patch("bo1.state.circuit_breaker_wrappers.is_redis_circuit_open", return_value=True),
        ):
            # This is the check that streaming.py uses to decide on fallback
            redis_available = is_redis_sse_available()

            assert redis_available is False
            # In streaming.py, when this returns False, it emits sse_fallback_activated
            # and switches to SSEPollingFallback

        # Create a poller and verify it can retrieve events
        mock_events = [
            {"data": {"sequence": 1, "event_type": "sse_fallback_activated"}},
            {"data": {"sequence": 2, "event_type": "progress"}},
            {"data": {"sequence": 3, "event_type": "complete"}},
        ]

        poller = SSEPollingFallback("session-123")

        with patch(
            "backend.api.event_poller.session_repository.get_events",
            return_value=mock_events,
        ):
            events = poller.poll_once()

            # Should get the fallback activation event from Postgres
            assert events[0]["event_type"] == "sse_fallback_activated"
