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
from enum import Enum
from typing import Any

from backend.api.middleware.metrics import (
    bo1_event_batch_latency_ms,
    bo1_event_batch_size,
    bo1_events_batched_total,
    bo1_pending_events,
)
from bo1.state.repositories import session_repository

logger = logging.getLogger(__name__)


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

    Examples:
        >>> batcher = EventBatcher()
        >>> await batcher.queue_event(
        ...     session_id="ses_123",
        ...     event_type="status_update",
        ...     data={"status": "working"}
        ... )
        >>> # Periodically or on shutdown:
        >>> await batcher.flush()
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

            # Critical events: flush immediately
            if priority == EventPriority.CRITICAL:
                logger.debug(
                    f"[BATCHER] CRITICAL event queued (type={event_type}), flushing immediately"
                )
                bo1_events_batched_total.labels(priority="critical").inc()

                # Flush any pending events first
                if self._buffer:
                    await self._flush_locked()

                # Then persist this critical event
                try:
                    session_repository.save_event(
                        session_id=session_id,
                        event_type=event_type,
                        sequence=seq,
                        data=data,
                    )
                except Exception as e:
                    logger.error(f"Failed to persist critical event: {e}")
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
        """
        if not self._buffer:
            logger.debug("[BATCHER] No events to flush")
            self._window_start = None
            bo1_pending_events.set(0)
            return

        events_to_flush = self._buffer.copy()
        self._buffer = []
        self._window_start = None

        flush_start = time.perf_counter()
        try:
            # Use batch insert for efficiency
            count = session_repository.save_events_batch(events_to_flush)
            flush_ms = (time.perf_counter() - flush_start) * 1000

            # Emit metrics
            bo1_event_batch_size.observe(count)
            bo1_event_batch_latency_ms.observe(flush_ms)
            bo1_pending_events.set(0)

            logger.info(
                f"[BATCHER] Batch persisted {count} events in {flush_ms:.1f}ms "
                f"(avg {flush_ms / count:.2f}ms per event)"
            )
        except Exception as e:
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
                    )
                except Exception as retry_error:
                    logger.error(
                        f"Failed to persist event {event_type} for session {session_id}: {retry_error}"
                    )

    def get_buffer_stats(self) -> dict[str, Any]:
        """Return current buffer statistics for monitoring.

        Returns:
            dict with buffer_size, max_capacity, window_elapsed_ms
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
