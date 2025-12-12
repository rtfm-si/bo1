"""Integration tests for event batching during deliberation.

Tests:
- Event batching during active deliberation rounds
- Critical event immediate flush
- Session completion with all events persisted
- SSE disconnect with graceful flush
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.event_batcher import flush_batcher, get_batcher


@pytest.mark.asyncio
async def test_event_batching_during_deliberation():
    """Test that events are batched during a deliberation round."""
    batcher = get_batcher()

    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        mock_repo.save_events_batch = MagicMock(return_value=5)

        session_id = "ses_deliberation_123"

        # Simulate 5 status update events during a round
        for i in range(5):
            await batcher.queue_event(
                session_id=session_id,
                event_type="working_status",
                data={"phase": f"Working on round {i}", "round": i},
            )

        # All should be buffered
        assert len(batcher._buffer) == 5

        # Flush explicitly
        await flush_batcher()

        # Should be persisted as a batch
        mock_repo.save_events_batch.assert_called_once()
        call_args = mock_repo.save_events_batch.call_args[0][0]
        assert len(call_args) == 5


@pytest.mark.asyncio
async def test_critical_event_during_deliberation():
    """Test that critical events flush pending events immediately."""
    batcher = get_batcher()

    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        mock_repo.save_event = AsyncMock()
        mock_repo.save_events_batch = MagicMock(return_value=3)

        session_id = "ses_with_error"

        # Queue normal events
        for i in range(3):
            await batcher.queue_event(
                session_id=session_id,
                event_type="working_status",
                data={"phase": f"Phase {i}"},
            )

        assert len(batcher._buffer) == 3

        # Queue critical event (error)
        await batcher.queue_event(
            session_id=session_id,
            event_type="error",
            data={"error": "Critical issue detected"},
        )

        # Pending events should be flushed
        mock_repo.save_events_batch.assert_called_once()
        # Critical event persisted directly
        mock_repo.save_event.assert_called_once()
        # Buffer should be empty
        assert len(batcher._buffer) == 0


@pytest.mark.asyncio
async def test_session_completion_flushes_all_events():
    """Test that session completion flushes all pending events."""
    batcher = get_batcher()

    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        mock_repo.save_events_batch = MagicMock(return_value=10)

        session_id = "ses_completion_test"

        # Simulate events during deliberation
        for i in range(10):
            await batcher.queue_event(
                session_id=session_id,
                event_type="parallel_round_start" if i % 2 == 0 else "working_status",
                data={"round": i // 2},
            )

        assert len(batcher._buffer) == 10

        # Session completes - flush all pending
        await flush_batcher()

        # All events should be persisted
        mock_repo.save_events_batch.assert_called_once()
        call_args = mock_repo.save_events_batch.call_args[0][0]
        assert len(call_args) == 10
        assert len(batcher._buffer) == 0


@pytest.mark.asyncio
async def test_no_events_lost_on_flush():
    """Test that no events are lost during batch flush."""
    batcher = get_batcher()

    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        # Successful batch insert
        mock_repo.save_events_batch = MagicMock(return_value=9)
        mock_repo.save_event = MagicMock()

        session_id = "ses_no_loss"
        event_types = ["status_update", "working_status", "progress"]

        # Queue events of different types
        for i, event_type in enumerate(event_types * 3):
            await batcher.queue_event(
                session_id=session_id,
                event_type=event_type,
                data={"index": i},
            )

        assert len(batcher._buffer) == 9

        # Flush
        await flush_batcher()

        # All should be persisted via batch insert
        mock_repo.save_events_batch.assert_called_once()
        call_args = mock_repo.save_events_batch.call_args[0][0]
        assert len(call_args) == 9


@pytest.mark.asyncio
async def test_concurrent_sessions_with_batching():
    """Test event batching with multiple concurrent sessions."""
    batcher = get_batcher()

    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        mock_repo.save_events_batch = MagicMock(return_value=20)

        # Queue events from multiple sessions concurrently
        async def queue_session_events(session_id: str, count: int):
            for i in range(count):
                await batcher.queue_event(
                    session_id=session_id,
                    event_type="working_status",
                    data={"session": session_id, "index": i},
                )

        # 5 concurrent sessions with 4 events each
        await asyncio.gather(
            queue_session_events("ses_1", 4),
            queue_session_events("ses_2", 4),
            queue_session_events("ses_3", 4),
            queue_session_events("ses_4", 4),
            queue_session_events("ses_5", 4),
        )

        assert len(batcher._buffer) == 20

        # Flush all
        await flush_batcher()

        # Should be persisted as a batch of 20
        mock_repo.save_events_batch.assert_called_once()
        call_args = mock_repo.save_events_batch.call_args[0][0]
        assert len(call_args) == 20

        # Verify sessions are interleaved (batched across sessions)
        sessions = [args[0] for args in call_args]
        assert len(set(sessions)) == 5  # All 5 sessions


@pytest.mark.asyncio
async def test_batch_metrics_recorded():
    """Test that batch metrics are recorded correctly."""
    batcher = get_batcher()

    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        with patch("backend.services.event_batcher.bo1_event_batch_size"):
            with patch("backend.services.event_batcher.bo1_event_batch_latency_ms"):
                with patch("backend.services.event_batcher.bo1_pending_events") as mock_pending:
                    mock_repo.save_events_batch = MagicMock(return_value=5)

                    # Queue events
                    for i in range(5):
                        await batcher.queue_event(
                            session_id="ses_metrics",
                            event_type="working_status",
                            data={"index": i},
                        )

                    # Flush
                    await flush_batcher()

                    # Verify metrics were recorded
                    # Note: In real tests, these would be actual Prometheus metrics
                    # Here we're just verifying they're called
                    mock_pending.set.assert_called()


@pytest.mark.asyncio
async def test_sse_disconnect_graceful_flush():
    """Test graceful flush on SSE client disconnect."""
    batcher = get_batcher()

    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        mock_repo.save_events_batch = MagicMock(return_value=3)

        session_id = "ses_disconnect"

        # Queue events
        for i in range(3):
            await batcher.queue_event(
                session_id=session_id,
                event_type="working_status",
                data={"phase": f"Phase {i}"},
            )

        # SSE client disconnects - graceful flush
        # In real scenario, this would be called from stream_session_events finally block
        await flush_batcher()

        # All pending should be persisted
        mock_repo.save_events_batch.assert_called_once()
        assert len(batcher._buffer) == 0


@pytest.mark.asyncio
async def test_batch_size_variations():
    """Test batching with various buffer fill scenarios."""
    batcher = get_batcher()

    with patch("backend.services.event_batcher.session_repository") as mock_repo:
        mock_repo.save_events_batch = MagicMock(return_value=1)

        # Test 1: Single event batch
        await batcher.queue_event("ses_1", "status", {"data": 1})
        await flush_batcher()
        assert mock_repo.save_events_batch.call_count == 1

        # Reset
        mock_repo.reset_mock()

        # Test 2: 50 event batch (half of max)
        for i in range(50):
            await batcher.queue_event("ses_2", "status", {"index": i})
        await flush_batcher()
        assert mock_repo.save_events_batch.call_count == 1

        # Reset
        mock_repo.reset_mock()

        # Test 3: 100 event batch (full max)
        for i in range(100):
            await batcher.queue_event("ses_3", "status", {"index": i})
        # Should auto-flush at 100
        assert mock_repo.save_events_batch.call_count == 1


def test_event_priority_levels():
    """Test that all event priorities are correctly defined."""
    from backend.services.event_batcher import EVENT_PRIORITY_MAP, EventPriority

    # Check that all critical events are present
    critical = [e for e, p in EVENT_PRIORITY_MAP.items() if p == EventPriority.CRITICAL]
    assert "error" in critical
    assert "synthesis_complete" in critical
    assert "complete" in critical

    # Check that normal events are present
    normal = [e for e, p in EVENT_PRIORITY_MAP.items() if p == EventPriority.NORMAL]
    assert "expert_contribution" in normal or "contribution" in normal

    # Check that low priority events are present
    low = [e for e, p in EVENT_PRIORITY_MAP.items() if p == EventPriority.LOW]
    assert "working_status" in low
    assert "status_update" in low
