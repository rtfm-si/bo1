"""Tests for event history fallback from Redis to PostgreSQL.

Validates:
- Normal Redis retrieval works
- Fallback to PostgreSQL when Redis unavailable
- Fallback to PostgreSQL when Redis empty
- Last-Event-ID filtering
- Error handling
"""

from unittest.mock import MagicMock, patch

import pytest
import redis

from backend.api.event_publisher import (
    get_event_history_with_fallback,
    get_missed_events,
)


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = MagicMock()
    return client


@pytest.fixture
def sample_events():
    """Sample event data for testing."""
    return [
        {"sequence": 1, "event_type": "session_started", "data": {"session_id": "test"}},
        {"sequence": 2, "event_type": "decomposition_started", "data": {}},
        {"sequence": 3, "event_type": "contribution", "data": {"persona": "CFO"}},
    ]


@pytest.fixture
def sample_pg_events():
    """Sample PostgreSQL events format."""
    return [
        {"data": {"sequence": 1, "event_type": "session_started", "data": {"session_id": "test"}}},
        {"data": {"sequence": 2, "event_type": "decomposition_started", "data": {}}},
        {"data": {"sequence": 3, "event_type": "contribution", "data": {"persona": "CFO"}}},
    ]


class TestGetEventHistoryWithFallback:
    """Test get_event_history_with_fallback function."""

    @pytest.mark.asyncio
    async def test_retrieves_from_redis_when_available(self, mock_redis_client, sample_events):
        """Events retrieved from Redis when available."""
        import json

        mock_redis_client.lrange.return_value = [json.dumps(e) for e in sample_events]

        events = await get_event_history_with_fallback(
            redis_client=mock_redis_client,
            session_id="test_session",
        )

        assert len(events) == 3
        assert events[0]["sequence"] == 1
        mock_redis_client.lrange.assert_called_once_with("events_history:test_session", 0, -1)

    @pytest.mark.asyncio
    async def test_falls_back_to_postgres_when_redis_empty(
        self, mock_redis_client, sample_pg_events
    ):
        """Falls back to PostgreSQL when Redis returns empty."""
        mock_redis_client.lrange.return_value = []

        with patch(
            "backend.api.event_publisher.session_repository.get_events",
            return_value=sample_pg_events,
        ):
            events = await get_event_history_with_fallback(
                redis_client=mock_redis_client,
                session_id="test_session",
            )

        assert len(events) == 3
        assert events[0]["sequence"] == 1

    @pytest.mark.asyncio
    async def test_falls_back_to_postgres_when_redis_unavailable(self, sample_pg_events):
        """Falls back to PostgreSQL when Redis is None."""
        with patch(
            "backend.api.event_publisher.session_repository.get_events",
            return_value=sample_pg_events,
        ):
            events = await get_event_history_with_fallback(
                redis_client=None,  # Redis unavailable
                session_id="test_session",
            )

        assert len(events) == 3
        assert events[0]["sequence"] == 1

    @pytest.mark.asyncio
    async def test_falls_back_to_postgres_on_redis_connection_error(
        self, mock_redis_client, sample_pg_events
    ):
        """Falls back to PostgreSQL when Redis raises ConnectionError."""
        mock_redis_client.lrange.side_effect = redis.ConnectionError("Connection lost")

        with patch(
            "backend.api.event_publisher.session_repository.get_events",
            return_value=sample_pg_events,
        ):
            events = await get_event_history_with_fallback(
                redis_client=mock_redis_client,
                session_id="test_session",
            )

        assert len(events) == 3
        assert events[0]["sequence"] == 1

    @pytest.mark.asyncio
    async def test_filters_by_last_event_id(self, mock_redis_client, sample_events):
        """Events filtered by last_event_id."""
        import json

        mock_redis_client.lrange.return_value = [json.dumps(e) for e in sample_events]

        events = await get_event_history_with_fallback(
            redis_client=mock_redis_client,
            session_id="test_session",
            last_event_id="test_session:1",  # Filter events after sequence 1
        )

        assert len(events) == 2  # Only sequences 2 and 3
        assert events[0]["sequence"] == 2
        assert events[1]["sequence"] == 3

    @pytest.mark.asyncio
    async def test_handles_invalid_last_event_id_format(self, mock_redis_client, sample_events):
        """Invalid last_event_id format doesn't break retrieval."""
        import json

        mock_redis_client.lrange.return_value = [json.dumps(e) for e in sample_events]

        events = await get_event_history_with_fallback(
            redis_client=mock_redis_client,
            session_id="test_session",
            last_event_id="invalid_format",  # No sequence number
        )

        # Should return all events (no filtering)
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_handles_json_decode_error(self, mock_redis_client):
        """Invalid JSON in Redis is skipped."""
        mock_redis_client.lrange.return_value = [
            "invalid json",
            '{"sequence": 1, "event_type": "test", "data": {}}',
        ]

        events = await get_event_history_with_fallback(
            redis_client=mock_redis_client,
            session_id="test_session",
        )

        # Only valid JSON event returned
        assert len(events) == 1
        assert events[0]["sequence"] == 1


class TestGetMissedEvents:
    """Test get_missed_events convenience wrapper."""

    @pytest.mark.asyncio
    async def test_calls_fallback_with_last_event_id(self, mock_redis_client, sample_events):
        """Wrapper passes last_event_id correctly."""
        import json

        mock_redis_client.lrange.return_value = [json.dumps(e) for e in sample_events]

        events = await get_missed_events(
            redis_client=mock_redis_client,
            session_id="test_session",
            last_event_id="test_session:2",
        )

        # Only sequence 3 (after sequence 2)
        assert len(events) == 1
        assert events[0]["sequence"] == 3


class TestMetricsTracking:
    """Test that fallback increments metrics."""

    @pytest.mark.asyncio
    async def test_increments_postgres_fallback_metric(self, sample_pg_events):
        """Metrics incremented on PostgreSQL fallback."""
        with patch(
            "backend.api.event_publisher.session_repository.get_events",
            return_value=sample_pg_events,
        ):
            with patch("backend.api.event_publisher.metrics.increment") as mock_incr:
                await get_event_history_with_fallback(
                    redis_client=None,
                    session_id="test_session",
                )

                mock_incr.assert_called_with("event.postgres_fallback")
