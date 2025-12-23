"""SSE Polling Fallback for PostgreSQL-based event streaming.

When Redis PubSub is unavailable (circuit breaker open), this module provides
polling-based event delivery from PostgreSQL as a fallback mechanism.

Usage:
    >>> poller = SSEPollingFallback(session_id)
    >>> async for events in poller.poll_loop():
    ...     for event in events:
    ...         yield format_sse_event(event)
"""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

from backend.api.constants import (
    SSE_CIRCUIT_CHECK_INTERVAL_MS,
    SSE_POLLING_BATCH_SIZE,
    SSE_POLLING_INTERVAL_MS,
)
from backend.api.middleware.metrics import (
    record_sse_polling_batch_size,
    record_sse_polling_duration,
)
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.repositories import session_repository

logger = logging.getLogger(__name__)


def poll_events_from_postgres(
    session_id: str,
    last_sequence: int = 0,
    limit: int = SSE_POLLING_BATCH_SIZE,
) -> list[dict[str, Any]]:
    """Poll events from PostgreSQL session_events table.

    Retrieves events with sequence > last_sequence, ordered chronologically.
    This is the core polling function reused by both history fetch and live polling.

    Args:
        session_id: Session identifier
        last_sequence: Only return events with sequence > this value
        limit: Maximum events to return per poll

    Returns:
        List of event payloads (from data column) with sequence > last_sequence
    """
    start_time = time.perf_counter()

    try:
        # Use existing repository method but filter by sequence
        all_events = session_repository.get_events(session_id)

        # Filter to events after last_sequence and apply limit
        filtered = [
            e.get("data", {})
            for e in all_events
            if e.get("data", {}).get("sequence", 0) > last_sequence
        ][:limit]

        duration = time.perf_counter() - start_time
        record_sse_polling_duration(duration)
        record_sse_polling_batch_size(len(filtered))

        return filtered
    except Exception as e:
        log_error(
            logger,
            ErrorCode.API_SSE_ERROR,
            f"[SSE_POLLING] Failed to poll events for {session_id}: {e}",
            session_id=session_id,
        )
        return []


class SSEPollingFallback:
    """PostgreSQL-based event polling for SSE fallback.

    When Redis PubSub is unavailable, this class provides polling-based
    event delivery from PostgreSQL. Events are retrieved in batches and
    deduplication is handled via sequence tracking.

    Attributes:
        session_id: Session identifier
        poll_interval_ms: Polling interval in milliseconds (default 500ms)
        batch_size: Maximum events per poll (default 50)
        circuit_check_interval_ms: How often to check if Redis recovered (default 5s)
    """

    def __init__(
        self,
        session_id: str,
        poll_interval_ms: int = SSE_POLLING_INTERVAL_MS,
        batch_size: int = SSE_POLLING_BATCH_SIZE,
        circuit_check_interval_ms: int = SSE_CIRCUIT_CHECK_INTERVAL_MS,
    ) -> None:
        """Initialize SSE polling fallback.

        Args:
            session_id: Session identifier to poll events for
            poll_interval_ms: Polling interval in milliseconds
            batch_size: Maximum events to retrieve per poll
            circuit_check_interval_ms: Interval to check Redis recovery
        """
        self.session_id = session_id
        self.poll_interval_ms = poll_interval_ms
        self.batch_size = batch_size
        self.circuit_check_interval_ms = circuit_check_interval_ms
        self._last_sequence = 0
        self._last_circuit_check = 0.0
        self._stop_requested = False

    @property
    def last_sequence(self) -> int:
        """Get last processed sequence number."""
        return self._last_sequence

    def set_last_sequence(self, sequence: int) -> None:
        """Set last processed sequence for deduplication.

        Call this with the highest sequence from replay before starting poll loop.

        Args:
            sequence: Last sequence number processed during replay
        """
        self._last_sequence = sequence

    def stop(self) -> None:
        """Request the polling loop to stop."""
        self._stop_requested = True

    def poll_once(self) -> list[dict[str, Any]]:
        """Poll PostgreSQL once for new events.

        Returns:
            List of new events with sequence > last_sequence
        """
        events = poll_events_from_postgres(
            session_id=self.session_id,
            last_sequence=self._last_sequence,
            limit=self.batch_size,
        )

        # Update last_sequence if we got events
        if events:
            max_seq = max(e.get("sequence", 0) for e in events)
            if max_seq > self._last_sequence:
                self._last_sequence = max_seq
                logger.debug(
                    f"[SSE_POLLING] session={self.session_id}, "
                    f"polled {len(events)} events, new last_sequence={self._last_sequence}"
                )

        return events

    async def poll_loop(self) -> AsyncGenerator[list[dict[str, Any]], None]:
        """Async generator that polls for events at configured interval.

        Yields:
            List of event payloads for each poll cycle (may be empty)

        Stops when:
            - stop() is called
            - A 'complete' or 'error' event is encountered
        """
        poll_interval_s = self.poll_interval_ms / 1000.0

        while not self._stop_requested:
            events = self.poll_once()

            if events:
                yield events

                # Check for terminal events
                for event in events:
                    event_type = event.get("event_type")
                    if event_type in ("complete", "error"):
                        logger.info(
                            f"[SSE_POLLING] Terminal event {event_type} for {self.session_id}"
                        )
                        return

            await asyncio.sleep(poll_interval_s)

    def should_check_redis_recovery(self) -> bool:
        """Check if it's time to probe Redis for recovery.

        Returns:
            True if enough time has passed since last circuit check
        """
        now = time.time()
        elapsed_ms = (now - self._last_circuit_check) * 1000

        if elapsed_ms >= self.circuit_check_interval_ms:
            self._last_circuit_check = now
            return True
        return False


def is_redis_sse_available() -> bool:
    """Check if Redis is available for SSE PubSub operations.

    Combines circuit breaker state check with a quick ping probe.
    Used by stream_session_events to decide between PubSub and polling.

    Returns:
        True if Redis is healthy and circuit is closed/half-open
    """
    from bo1.state.circuit_breaker_wrappers import is_redis_circuit_open

    # Fast path: if circuit is open, Redis is not available
    if is_redis_circuit_open():
        return False

    # Circuit is closed or half-open - try a ping
    try:
        from backend.api.dependencies import get_redis_manager

        redis_manager = get_redis_manager()
        if not redis_manager.is_available:
            return False

        # Quick ping to verify actual connectivity
        redis_manager.redis.ping()
        return True
    except Exception as e:
        logger.warning(f"[SSE_FALLBACK] Redis ping failed: {e}")
        return False
