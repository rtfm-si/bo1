"""Tests for event_publisher batch persistence functions."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_add_to_batch_collects_events():
    """Verify events are added to batch buffer."""
    # Reset module state
    import backend.api.event_publisher as ep

    ep._batch_buffer = []
    ep._batch_lock = None

    await ep.add_to_batch("session1", "test_event", 1, {"data": "test"})
    await ep.add_to_batch("session1", "test_event", 2, {"data": "test2"})

    assert len(ep._batch_buffer) == 2
    assert ep._batch_buffer[0] == ("session1", "test_event", 1, {"data": "test"})


@pytest.mark.asyncio
async def test_add_to_batch_triggers_flush_at_threshold():
    """Verify flush is triggered when buffer reaches BATCH_MAX_SIZE."""
    import backend.api.event_publisher as ep

    ep._batch_buffer = []
    ep._batch_lock = None

    with patch.object(ep, "_flush_batch", new_callable=AsyncMock) as mock_flush:
        # Add events up to threshold
        for i in range(ep.BATCH_MAX_SIZE):
            await ep.add_to_batch("session1", "event", i, {"seq": i})

        # Flush should have been called when we hit threshold
        mock_flush.assert_called()


@pytest.mark.asyncio
async def test_flush_batch_calls_save_events_batch():
    """Verify flush_batch uses batch repository method."""
    import backend.api.event_publisher as ep

    ep._batch_buffer = [
        ("session1", "event1", 1, {"d": 1}),
        ("session1", "event2", 2, {"d": 2}),
    ]
    ep._batch_lock = None

    with patch.object(ep.session_repository, "save_events_batch", return_value=2) as mock_save:
        await ep._flush_batch()

        mock_save.assert_called_once()
        events = mock_save.call_args[0][0]
        assert len(events) == 2

    # Buffer should be cleared after flush
    assert len(ep._batch_buffer) == 0


@pytest.mark.asyncio
async def test_flush_batch_fallback_on_error():
    """Verify fallback to individual inserts on batch failure."""
    import backend.api.event_publisher as ep

    ep._batch_buffer = [
        ("session1", "event1", 1, {"d": 1}),
        ("session1", "event2", 2, {"d": 2}),
    ]
    ep._batch_lock = None

    with patch.object(
        ep.session_repository, "save_events_batch", side_effect=Exception("DB error")
    ):
        with patch.object(ep.session_repository, "save_event") as mock_individual:
            await ep._flush_batch()

            # Should fall back to individual inserts
            assert mock_individual.call_count == 2


@pytest.mark.asyncio
async def test_flush_session_events_filters_by_session():
    """Verify flush_session_events only flushes events for specified session."""
    import backend.api.event_publisher as ep

    ep._batch_buffer = [
        ("session1", "event", 1, {"d": 1}),
        ("session2", "event", 2, {"d": 2}),
        ("session1", "event", 3, {"d": 3}),
    ]
    ep._batch_lock = None

    with patch.object(ep.session_repository, "save_events_batch", return_value=2) as mock_save:
        await ep.flush_session_events("session1")

        # Should only save session1 events
        events = mock_save.call_args[0][0]
        assert len(events) == 2
        assert all(e[0] == "session1" for e in events)

    # session2 event should remain in buffer
    assert len(ep._batch_buffer) == 1
    assert ep._batch_buffer[0][0] == "session2"


@pytest.mark.asyncio
async def test_buffer_cap_prevents_unbounded_growth():
    """Verify buffer drops oldest event when cap is reached."""
    import backend.api.event_publisher as ep

    ep._batch_buffer = []
    ep._batch_lock = None

    # Mock flush to prevent actual flushing
    with patch.object(ep, "_flush_batch", new_callable=AsyncMock):
        # Fill buffer to cap
        for i in range(ep.BATCH_MAX_BUFFER):
            await ep.add_to_batch("session1", "event", i, {"seq": i})

        # Add one more - should drop oldest
        await ep.add_to_batch("session1", "event", 999, {"seq": 999})

        assert len(ep._batch_buffer) <= ep.BATCH_MAX_BUFFER
        # Newest event should be present
        assert ep._batch_buffer[-1][2] == 999
