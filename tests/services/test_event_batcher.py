"""Unit tests for EventBatcher service.

Tests:
- 50ms window batching with mock time
- Critical event immediate flush
- Batch INSERT query generation and batch size metrics
- Priority ordering (critical before normal)
- Concurrent access with asyncio
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.event_batcher import EventBatcher, EventPriority, get_batcher


@pytest.fixture
def batcher():
    """Create a fresh EventBatcher instance for each test."""
    return EventBatcher()


@pytest.mark.asyncio
async def test_queue_event_normal_priority(batcher):
    """Test queuing a normal priority event."""
    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        mock_repo.save_events_batch = MagicMock(return_value=1)

        await batcher.queue_event(
            session_id="ses_123",
            event_type="expert_contribution",
            data={"content": "test"},
        )

        # Should be in buffer, not yet persisted
        assert len(batcher._buffer) == 1
        mock_repo.save_events_batch.assert_not_called()


@pytest.mark.asyncio
async def test_critical_event_immediate_flush(batcher):
    """Test that critical events flush immediately."""
    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        mock_repo.save_event = AsyncMock()
        mock_repo.save_events_batch = MagicMock(return_value=1)

        # Queue normal event
        await batcher.queue_event(
            session_id="ses_123",
            event_type="status_update",
            data={"status": "working"},
        )

        assert len(batcher._buffer) == 1

        # Queue critical event - should flush buffered events first, then persist critical
        await batcher.queue_event(
            session_id="ses_123",
            event_type="error",
            data={"error": "test error"},
        )

        # Buffered event should be persisted
        mock_repo.save_events_batch.assert_called_once()
        # Critical event should be persisted directly
        mock_repo.save_event.assert_called_once()


@pytest.mark.asyncio
async def test_buffer_full_triggers_flush(batcher):
    """Test that buffer full (100 events) triggers flush."""
    # Disable window timer to test buffer-full trigger in isolation
    batcher.BUFFER_WINDOW_MS = 60000  # 60s - won't expire during test

    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        mock_repo.save_events_batch = MagicMock(return_value=100)

        # Queue events to fill buffer
        for i in range(100):
            await batcher.queue_event(
                session_id=f"ses_{i}",
                event_type="status_update",
                data={"index": i},
            )

        # After 100th event, should flush
        mock_repo.save_events_batch.assert_called_once()
        assert len(batcher._buffer) == 0


@pytest.mark.asyncio
async def test_memory_pressure_triggers_flush():
    """Test that memory pressure (500+ events) triggers flush."""
    batcher = EventBatcher()
    # Override capacity for test
    batcher.MAX_BUFFER_CAPACITY = 10

    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        mock_repo.save_events_batch = MagicMock(return_value=10)

        # Queue up to max capacity
        for i in range(10):
            await batcher.queue_event(
                session_id="ses_123",
                event_type="status_update",
                data={"index": i},
            )

        # At 10 (capacity limit), should trigger flush
        mock_repo.save_events_batch.assert_called_once()
        assert len(batcher._buffer) == 0


@pytest.mark.asyncio
async def test_explicit_flush(batcher):
    """Test explicit flush of buffered events."""
    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        mock_repo.save_events_batch = MagicMock(return_value=3)

        # Queue multiple events
        for i in range(3):
            await batcher.queue_event(
                session_id=f"ses_{i}",
                event_type="status_update",
                data={"index": i},
            )

        assert len(batcher._buffer) == 3

        # Explicit flush
        await batcher.flush()

        # Should be persisted
        mock_repo.save_events_batch.assert_called_once()
        assert len(batcher._buffer) == 0


@pytest.mark.asyncio
async def test_critical_event_bypasses_buffer():
    """Test that critical events are not added to buffer."""
    batcher = EventBatcher()

    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        mock_repo.save_event = MagicMock()
        mock_repo.save_events_batch = MagicMock(return_value=1)

        # Queue normal event - goes to buffer
        await batcher.queue_event(
            session_id="ses_123",
            event_type="status_update",
            data={"status": "working"},
        )
        assert len(batcher._buffer) == 1

        # Queue critical event - should flush buffer and persist critical directly
        await batcher.queue_event(
            session_id="ses_123",
            event_type="synthesis_complete",
            data={"synthesis": "result"},
        )

        # Critical event should not be in buffer
        assert len(batcher._buffer) == 0
        # Batch should have been flushed (1 normal event)
        mock_repo.save_events_batch.assert_called_once()
        # Critical should be persisted directly
        mock_repo.save_event.assert_called_once()


@pytest.mark.asyncio
async def test_concurrent_queuing(batcher):
    """Test concurrent event queueing with asyncio."""
    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        mock_repo.save_events_batch = MagicMock(return_value=10)

        # Queue 10 events concurrently
        tasks = [
            batcher.queue_event(
                session_id=f"ses_{i}",
                event_type="status_update",
                data={"index": i},
            )
            for i in range(10)
        ]

        await asyncio.gather(*tasks)

        # All should be queued without errors
        assert len(batcher._buffer) == 10


@pytest.mark.asyncio
async def test_batch_insert_call(batcher):
    """Test that batch INSERT is called with correct parameters."""
    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        mock_repo.save_events_batch = MagicMock(return_value=2)

        await batcher.queue_event(
            session_id="ses_123",
            event_type="event1",
            data={"type": "data1"},
        )
        await batcher.queue_event(
            session_id="ses_456",
            event_type="event2",
            data={"type": "data2"},
        )

        await batcher.flush()

        # Verify save_events_batch was called with list of tuples
        mock_repo.save_events_batch.assert_called_once()
        call_args = mock_repo.save_events_batch.call_args[0][0]

        # Should be a list of (session_id, event_type, seq, data) tuples
        assert len(call_args) == 2
        assert call_args[0][0] == "ses_123"
        assert call_args[0][1] == "event1"
        assert call_args[1][0] == "ses_456"
        assert call_args[1][1] == "event2"


@pytest.mark.asyncio
async def test_get_buffer_stats(batcher):
    """Test buffer statistics reporting."""
    stats = batcher.get_buffer_stats()

    assert "buffer_size" in stats
    assert "max_capacity" in stats
    assert "window_elapsed_ms" in stats
    assert "seq_counter" in stats
    assert stats["buffer_size"] == 0

    # Add event and check stats
    with patch("backend.services.event_batcher.session_repository"):
        await batcher.queue_event(
            session_id="ses_123",
            event_type="status_update",
            data={},
        )

    stats = batcher.get_buffer_stats()
    assert stats["buffer_size"] == 1
    assert stats["seq_counter"] == 1


@pytest.mark.asyncio
async def test_fallback_to_individual_insert_on_batch_failure(batcher):
    """Test fallback to individual inserts when batch fails."""
    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        mock_repo.save_events_batch.side_effect = Exception("Batch insert failed")
        mock_repo.save_event = MagicMock()

        # Queue events
        for i in range(3):
            await batcher.queue_event(
                session_id=f"ses_{i}",
                event_type="status_update",
                data={"index": i},
            )

        # Flush
        await batcher.flush()

        # Batch should have been attempted
        mock_repo.save_events_batch.assert_called_once()
        # Fallback to individual inserts (3 calls)
        assert mock_repo.save_event.call_count == 3


def test_get_batcher_returns_singleton():
    """Test that get_batcher() returns the same instance."""
    batcher1 = get_batcher()
    batcher2 = get_batcher()

    assert batcher1 is batcher2


@pytest.mark.asyncio
async def test_event_priority_mapping():
    """Test that event types are correctly mapped to priorities."""
    from backend.services.event_batcher import EVENT_PRIORITY_MAP

    # Verify critical events
    critical_events = ["error", "synthesis_complete", "meta_synthesis_complete", "complete"]
    for event_type in critical_events:
        assert EVENT_PRIORITY_MAP.get(event_type) == EventPriority.CRITICAL

    # Verify normal events
    normal_events = ["expert_contribution", "contribution", "round_start"]
    for event_type in normal_events:
        assert EVENT_PRIORITY_MAP.get(event_type) == EventPriority.NORMAL

    # Verify low priority events
    low_events = ["status_update", "progress", "working_status"]
    for event_type in low_events:
        assert EVENT_PRIORITY_MAP.get(event_type) == EventPriority.LOW
