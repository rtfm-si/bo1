"""Tests for EventBatcher health monitoring features."""

import asyncio

import pytest

from backend.services.event_batcher import EventBatcher, EventBatcherStats


class TestEventBatcherQueueDepth:
    """Test EventBatcher queue depth methods."""

    def test_get_queue_depth_empty(self) -> None:
        """Returns 0 when buffer is empty."""
        batcher = EventBatcher()
        assert batcher.get_queue_depth() == 0

    def test_get_queue_depth_with_pending(self) -> None:
        """Returns correct count with pending events."""
        batcher = EventBatcher()
        # Manually add events to buffer
        batcher._buffer.append(("ses_1", "test_event", 1, {"data": "value"}))
        batcher._buffer.append(("ses_1", "test_event", 2, {"data": "value2"}))
        batcher._buffer.append(("ses_2", "test_event", 3, {"data": "value3"}))

        assert batcher.get_queue_depth() == 3


class TestEventBatcherStats:
    """Test EventBatcher get_stats method."""

    def test_get_stats_includes_all_fields(self) -> None:
        """Stats dataclass includes all required fields."""
        batcher = EventBatcher()
        stats = batcher.get_stats()

        assert isinstance(stats, EventBatcherStats)
        assert stats.queue_depth == 0
        assert stats.flush_count == 0
        assert stats.error_count == 0
        assert stats.max_capacity == EventBatcher.MAX_BUFFER_CAPACITY
        assert stats.window_elapsed_ms >= 0

    def test_get_stats_reflects_buffer_state(self) -> None:
        """Stats reflect actual buffer state."""
        batcher = EventBatcher()
        # Add events
        batcher._buffer.append(("ses_1", "event", 1, {}))
        batcher._buffer.append(("ses_1", "event", 2, {}))

        stats = batcher.get_stats()
        assert stats.queue_depth == 2

    def test_get_stats_tracks_flush_count(self) -> None:
        """Stats track flush count correctly."""
        batcher = EventBatcher()
        batcher._flush_count = 5
        batcher._error_count = 2

        stats = batcher.get_stats()
        assert stats.flush_count == 5
        assert stats.error_count == 2


class TestEventBatcherStatsDataclass:
    """Test EventBatcherStats dataclass."""

    def test_stats_dataclass_fields(self) -> None:
        """EventBatcherStats has all expected fields."""
        stats = EventBatcherStats(
            queue_depth=10,
            flush_count=5,
            error_count=1,
            max_capacity=500,
            window_elapsed_ms=25.5,
        )

        assert stats.queue_depth == 10
        assert stats.flush_count == 5
        assert stats.error_count == 1
        assert stats.max_capacity == 500
        assert stats.window_elapsed_ms == 25.5


class TestWaitForFlushComplete:
    """Test flush completion tracking."""

    @pytest.mark.asyncio
    async def test_wait_for_flush_complete_no_pending(self) -> None:
        """Returns True immediately when no pending flushes."""
        batcher = EventBatcher()
        # No events queued, should return immediately
        result = await batcher.wait_for_flush_complete(timeout=0.1)
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_flush_complete_waits_for_flush(self) -> None:
        """Blocks until flush completes."""
        batcher = EventBatcher()

        # Simulate pending flush state
        batcher._pending_flushes = 1
        batcher._flush_complete.clear()

        async def complete_flush_after_delay():
            await asyncio.sleep(0.05)
            batcher._pending_flushes = 0
            batcher._flush_complete.set()

        # Start completion task
        task = asyncio.create_task(complete_flush_after_delay())

        # Wait should succeed once flush completes
        result = await batcher.wait_for_flush_complete(timeout=1.0)
        assert result is True
        await task

    @pytest.mark.asyncio
    async def test_wait_for_flush_complete_timeout(self) -> None:
        """Returns False after timeout when flush doesn't complete."""
        batcher = EventBatcher()

        # Simulate stuck flush
        batcher._pending_flushes = 1
        batcher._flush_complete.clear()

        # Wait should timeout
        result = await batcher.wait_for_flush_complete(timeout=0.05)
        assert result is False


class TestWaitForSessionFlush:
    """Test per-session flush tracking."""

    @pytest.mark.asyncio
    async def test_wait_for_session_flush_no_tracking(self) -> None:
        """Returns True immediately when session has no pending events."""
        batcher = EventBatcher()
        # No session tracking, should return True
        result = await batcher.wait_for_session_flush("unknown-session", timeout=0.1)
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_session_flush_specific_session(self) -> None:
        """Waits for specific session's flush to complete."""
        batcher = EventBatcher()

        # Set up tracking for specific session
        session_event = asyncio.Event()
        batcher._session_pending["ses_123"] = session_event

        async def complete_session_flush():
            await asyncio.sleep(0.05)
            session_event.set()

        task = asyncio.create_task(complete_session_flush())

        result = await batcher.wait_for_session_flush("ses_123", timeout=1.0)
        assert result is True
        await task

    @pytest.mark.asyncio
    async def test_wait_for_session_flush_already_complete(self) -> None:
        """Returns True immediately if session flush already complete."""
        batcher = EventBatcher()

        session_event = asyncio.Event()
        session_event.set()  # Already complete
        batcher._session_pending["ses_456"] = session_event

        result = await batcher.wait_for_session_flush("ses_456", timeout=0.1)
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_session_flush_timeout(self) -> None:
        """Returns False on timeout for specific session."""
        batcher = EventBatcher()

        session_event = asyncio.Event()  # Not set
        batcher._session_pending["ses_789"] = session_event

        result = await batcher.wait_for_session_flush("ses_789", timeout=0.05)
        assert result is False


class TestClearSessionTracking:
    """Test session tracking cleanup."""

    def test_clear_session_tracking_removes_data(self) -> None:
        """Clears session tracking state."""
        batcher = EventBatcher()
        batcher._session_pending["ses_123"] = asyncio.Event()
        batcher._user_id_cache["ses_123"] = "user_abc"

        batcher.clear_session_tracking("ses_123")

        assert "ses_123" not in batcher._session_pending
        assert "ses_123" not in batcher._user_id_cache

    def test_clear_session_tracking_unknown_session(self) -> None:
        """Handles unknown session gracefully."""
        batcher = EventBatcher()
        # Should not raise
        batcher.clear_session_tracking("unknown-session")
