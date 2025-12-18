"""Event batching service for reducing PostgreSQL insert overhead.

Provides:
- EventBatcher: Batches events in memory for 50ms window, flushes on window expiry, buffer full, or critical event
- Priority queuing: Critical events bypass buffer and flush immediately
- Thread-safe event queueing with asyncio.Lock
- Batch INSERT via executemany() for efficiency
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from backend.api.middleware.metrics import (
    bo1_event_batch_latency_ms,
    bo1_event_batch_size,
    bo1_events_batched_total,
    bo1_pending_events,
)
from bo1.logging import ErrorCode, log_error
from bo1.state.repositories import session_repository

logger = logging.getLogger(__name__)


@dataclass
class EventBatcherStats:
    """Statistics for the event batcher.

    Attributes:
        queue_depth: Current number of events in buffer
        flush_count: Total number of flush operations
        error_count: Total number of flush errors
        max_capacity: Maximum buffer capacity
        window_elapsed_ms: Time elapsed in current window
    """

    queue_depth: int
    flush_count: int
    error_count: int
    max_capacity: int
    window_elapsed_ms: float


class EventPriority(Enum):
    """Event priority levels for batching."""

    CRITICAL = 1  # error, synthesis_complete, meeting_complete, facilitator_action
    NORMAL = 2  # expert_contribution, round_start, round_end
    LOW = 3  # status_update, progress


# Event type to priority mapping
EVENT_PRIORITY_MAP = {
    "error": EventPriority.CRITICAL,
    "synthesis_complete": EventPriority.CRITICAL,
    "meeting_complete": EventPriority.CRITICAL,
    "meta_synthesis_complete": EventPriority.CRITICAL,
    "facilitator_decision": EventPriority.CRITICAL,
    "complete": EventPriority.CRITICAL,
    "expert_contribution": EventPriority.NORMAL,
    "round_start": EventPriority.NORMAL,
    "round_end": EventPriority.NORMAL,
    "contribution": EventPriority.NORMAL,
    "persona_selected": EventPriority.NORMAL,
    "parallel_round_start": EventPriority.NORMAL,
    "status_update": EventPriority.LOW,
    "progress": EventPriority.LOW,
    "working_status": EventPriority.LOW,
    "discussion_quality_status": EventPriority.LOW,
}


class EventBatcher:
    """Batches events to reduce PostgreSQL insert overhead.

    Features:
    - 50ms buffer window for event batching
    - Critical events bypass buffer and flush immediately
    - Batch INSERT via executemany() for efficiency
    - Async-safe with asyncio.Lock
    - Configurable flush limits (buffer size, window time)
    - User ID caching to avoid per-event SELECT queries
    - Flush completion tracking for deterministic verification

    Examples:
        >>> batcher = EventBatcher()
        >>> await batcher.queue_event(
        ...     session_id="ses_123",
        ...     event_type="status_update",
        ...     data={"status": "working"}
        ... )
        >>> # Periodically or on shutdown:
        >>> await batcher.flush()
        >>> # Wait for flush completion:
        >>> await batcher.wait_for_flush_complete()
    """

    # Batch configuration
    BUFFER_WINDOW_MS = 50  # Flush window
    MAX_BUFFER_SIZE = 100  # Flush when buffer reaches this size
    MAX_BUFFER_CAPACITY = 500  # Prevent unbounded growth

    def __init__(self) -> None:
        """Initialize event batcher."""
        self._buffer: list[tuple[str, str, int, dict[str, Any]]] = []
        self._lock = asyncio.Lock()
        self._window_start: float | None = None
        self._flush_task: asyncio.Task[None] | None = None
        self._seq_counter = 0
        self._flush_count = 0
        self._error_count = 0
        # Cache user_ids per session to avoid SELECT per event
        self._user_id_cache: dict[str, str] = {}
        # Flush completion tracking for deterministic verification
        self._pending_flushes = 0
        self._flush_complete = asyncio.Event()
        self._flush_complete.set()  # Initially complete (no pending flushes)
        # Per-session flush tracking
        self._session_pending: dict[str, asyncio.Event] = {}

    def _get_user_id(self, session_id: str) -> str | None:
        """Get user_id from cache or Redis metadata.

        Args:
            session_id: Session identifier

        Returns:
            user_id if found, None otherwise
        """
        # Check local cache first
        if session_id in self._user_id_cache:
            return self._user_id_cache[session_id]

        # Fetch from Redis metadata (with DB fallback)
        try:
            from backend.api.dependencies import get_redis_manager

            redis_manager = get_redis_manager()
            user_id = redis_manager.get_cached_user_id(session_id)
            if user_id:
                self._user_id_cache[session_id] = user_id
                return user_id
        except Exception as e:
            logger.debug(f"Failed to get cached user_id for {session_id}: {e}")

        return None

    async def queue_event(
        self,
        session_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Queue an event for batching.

        Critical events flush immediately; others are buffered.

        Args:
            session_id: Session identifier
            event_type: Event type string
            data: Event data payload
        """
        priority = EVENT_PRIORITY_MAP.get(event_type, EventPriority.NORMAL)

        async with self._lock:
            self._seq_counter += 1
            seq = self._seq_counter

            # Get cached user_id upfront
            user_id = self._get_user_id(session_id)

            # Critical events: flush immediately
            if priority == EventPriority.CRITICAL:
                logger.debug(
                    f"[BATCHER] CRITICAL event queued (type={event_type}), flushing immediately"
                )
                bo1_events_batched_total.labels(priority="critical").inc()

                # Flush any pending events first
                if self._buffer:
                    await self._flush_locked()

                # Then persist this critical event (with cached user_id)
                try:
                    session_repository.save_event(
                        session_id=session_id,
                        event_type=event_type,
                        sequence=seq,
                        data=data,
                        user_id=user_id,
                    )
                except Exception as e:
                    log_error(
                        logger, ErrorCode.DB_WRITE_ERROR, f"Failed to persist critical event: {e}"
                    )
                    # Re-raise so caller knows persistence failed
                    raise

                return

            # Normal/Low events: buffer and check thresholds
            self._buffer.append((session_id, event_type, seq, data))
            bo1_events_batched_total.labels(priority="normal_or_low").inc()
            bo1_pending_events.set(len(self._buffer))

            # Initialize window on first buffer add
            if self._window_start is None:
                self._window_start = time.monotonic()

            current_time = time.monotonic()
            window_elapsed = (current_time - self._window_start) * 1000

            # Flush conditions:
            # 1. Buffer full (100 events)
            # 2. Window expired (50ms)
            # 3. Memory pressure (500+ events)
            should_flush = (
                len(self._buffer) >= self.MAX_BUFFER_SIZE
                or window_elapsed >= self.BUFFER_WINDOW_MS
                or len(self._buffer) >= self.MAX_BUFFER_CAPACITY
            )

            if should_flush:
                logger.debug(
                    f"[BATCHER] Flush triggered: "
                    f"buffer_size={len(self._buffer)}, "
                    f"window_elapsed={window_elapsed:.1f}ms, "
                    f"reason={'buffer_full' if len(self._buffer) >= self.MAX_BUFFER_SIZE else 'window_expired' if window_elapsed >= self.BUFFER_WINDOW_MS else 'memory_pressure'}"
                )
                await self._flush_locked()

    async def flush(self) -> None:
        """Flush all pending events to PostgreSQL.

        Safe to call multiple times or when buffer is empty.
        """
        async with self._lock:
            await self._flush_locked()

    async def _flush_locked(self) -> None:
        """Flush pending events (must be called with lock held).

        Uses batch INSERT via executemany() for efficiency.
        Falls back to individual inserts on batch failure.
        Sets completion events for deterministic verification.
        """
        if not self._buffer:
            logger.debug("[BATCHER] No events to flush")
            self._window_start = None
            bo1_pending_events.set(0)
            return

        events_to_flush = self._buffer.copy()
        self._buffer = []
        self._window_start = None

        # Track pending flush
        self._pending_flushes += 1
        self._flush_complete.clear()

        # Collect session_ids for tracking and user_ids for efficiency
        session_ids = {ev[0] for ev in events_to_flush}
        user_ids = {}
        for sid in session_ids:
            uid = self._get_user_id(sid)
            if uid:
                user_ids[sid] = uid
            # Create pending event for session if not exists
            if sid not in self._session_pending:
                self._session_pending[sid] = asyncio.Event()
            self._session_pending[sid].clear()

        flush_start = time.perf_counter()
        try:
            # Use batch insert for efficiency (with cached user_ids)
            count = session_repository.save_events_batch(events_to_flush, user_ids=user_ids)
            flush_ms = (time.perf_counter() - flush_start) * 1000

            # Emit metrics
            bo1_event_batch_size.observe(count)
            bo1_event_batch_latency_ms.observe(flush_ms)
            bo1_pending_events.set(0)

            self._flush_count += 1
            logger.info(
                f"[BATCHER] Batch persisted {count} events in {flush_ms:.1f}ms "
                f"(avg {flush_ms / count:.2f}ms per event)"
            )
        except Exception as e:
            self._error_count += 1
            logger.warning(f"[BATCHER] Batch persist failed, falling back to individual: {e}")
            bo1_pending_events.set(0)

            # Fallback to individual inserts
            for session_id, event_type, seq, data in events_to_flush:
                try:
                    session_repository.save_event(
                        session_id=session_id,
                        event_type=event_type,
                        sequence=seq,
                        data=data,
                        user_id=user_ids.get(session_id),
                    )
                except Exception as retry_error:
                    log_error(
                        logger,
                        ErrorCode.DB_WRITE_ERROR,
                        f"Failed to persist event {event_type} for session {session_id}: {retry_error}",
                    )
        finally:
            # Mark flush complete (even on error - events attempted)
            self._pending_flushes -= 1
            if self._pending_flushes == 0:
                self._flush_complete.set()
            # Mark session flushes complete
            for sid in session_ids:
                if sid in self._session_pending:
                    self._session_pending[sid].set()

    def get_queue_depth(self) -> int:
        """Get the current number of events in the buffer.

        Returns:
            Number of pending events waiting to be flushed
        """
        return len(self._buffer)

    def get_stats(self) -> EventBatcherStats:
        """Get comprehensive statistics for the event batcher.

        Returns:
            EventBatcherStats with queue depth, flush/error counts, and timing info
        """
        current_time = time.monotonic()
        window_elapsed = 0.0
        if self._window_start is not None:
            window_elapsed = (current_time - self._window_start) * 1000

        return EventBatcherStats(
            queue_depth=len(self._buffer),
            flush_count=self._flush_count,
            error_count=self._error_count,
            max_capacity=self.MAX_BUFFER_CAPACITY,
            window_elapsed_ms=window_elapsed,
        )

    def get_buffer_stats(self) -> dict[str, Any]:
        """Return current buffer statistics for monitoring.

        Returns:
            dict with buffer_size, max_capacity, window_elapsed_ms

        Note:
            Prefer get_stats() for structured access. This method exists
            for backwards compatibility.
        """
        current_time = time.monotonic()
        window_elapsed = 0.0
        if self._window_start is not None:
            window_elapsed = (current_time - self._window_start) * 1000

        return {
            "buffer_size": len(self._buffer),
            "max_capacity": self.MAX_BUFFER_CAPACITY,
            "window_elapsed_ms": window_elapsed,
            "seq_counter": self._seq_counter,
        }

    async def wait_for_flush_complete(self, timeout: float = 5.0) -> bool:
        """Wait for all pending flushes to complete.

        Args:
            timeout: Maximum time to wait in seconds (default 5.0)

        Returns:
            True if all flushes completed, False if timeout exceeded
        """
        if self._pending_flushes == 0:
            return True

        try:
            await asyncio.wait_for(self._flush_complete.wait(), timeout=timeout)
            return True
        except TimeoutError:
            logger.warning(
                f"[BATCHER] wait_for_flush_complete timed out after {timeout}s "
                f"(pending_flushes={self._pending_flushes})"
            )
            return False

    async def wait_for_session_flush(self, session_id: str, timeout: float = 5.0) -> bool:
        """Wait for a specific session's events to be flushed.

        Args:
            session_id: Session identifier to wait for
            timeout: Maximum time to wait in seconds (default 5.0)

        Returns:
            True if session flush completed, False if timeout or no pending events
        """
        event = self._session_pending.get(session_id)
        if event is None:
            # No pending events for this session
            return True

        if event.is_set():
            return True

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return True
        except TimeoutError:
            logger.warning(
                f"[BATCHER] wait_for_session_flush timed out after {timeout}s "
                f"for session {session_id}"
            )
            return False

    def clear_session_tracking(self, session_id: str) -> None:
        """Clear tracking state for a completed session.

        Called on session completion to prevent memory growth.

        Args:
            session_id: Session identifier to clear
        """
        self._session_pending.pop(session_id, None)
        self._user_id_cache.pop(session_id, None)


# Global batcher instance
_batcher: EventBatcher | None = None


def get_batcher() -> EventBatcher:
    """Get or create the global event batcher.

    Lazy initialization to support async context.
    """
    global _batcher
    if _batcher is None:
        _batcher = EventBatcher()
    return _batcher


async def flush_batcher() -> None:
    """Flush the global event batcher.

    Called during shutdown or when flushing a specific session's events.
    """
    batcher = get_batcher()
    await batcher.flush()


async def wait_for_all_flushes(timeout: float = 5.0) -> bool:
    """Wait for all pending event flushes to complete.

    Module-level convenience function that wraps the global batcher.
    Used by event_collector._verify_event_persistence() to deterministically
    wait for persistence instead of using a fixed sleep delay.

    Args:
        timeout: Maximum time to wait in seconds (default 5.0)

    Returns:
        True if all flushes completed, False if timeout exceeded
    """
    batcher = get_batcher()
    return await batcher.wait_for_flush_complete(timeout)
