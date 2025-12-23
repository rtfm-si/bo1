"""Event publisher using Redis PubSub for real-time SSE streaming.

Provides:
- EventPublisher: Publishes deliberation events to Redis channels for SSE streaming
- Persists events to PostgreSQL for permanent storage (Redis is transient)
- Failed event queue management with retry logic
"""

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

import redis

from backend.api.metrics import metrics
from backend.services.event_batcher import get_batcher
from bo1.context import get_request_id
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.repositories import session_repository

logger = logging.getLogger(__name__)


# Failed event persistence retry configuration
FAILED_EVENTS_KEY = "failed_events:queue"
FAILED_EVENTS_DLQ_KEY = "failed_events:dlq"
MAX_RETRIES = 5
RETRY_DELAYS = [60, 120, 300, 600, 1800]  # 1min, 2min, 5min, 10min, 30min

# DLQ alert thresholds
DLQ_ALERT_THRESHOLD = 10  # Warning log at this depth
DLQ_CRITICAL_THRESHOLD = 50  # Error log at this depth

# Semaphore to limit concurrent event persistence tasks
# Set below pool max (75) to leave headroom for other operations
PERSIST_SEMAPHORE_LIMIT = 50
_persist_semaphore: asyncio.Semaphore | None = None

# Batch persistence configuration
BATCH_FLUSH_INTERVAL_MS = 100  # Flush every 100ms
BATCH_MAX_SIZE = 10  # Flush when buffer reaches 10 events
BATCH_MAX_BUFFER = 100  # Cap buffer to prevent unbounded growth

# Batch persistence state
_batch_buffer: list[tuple[str, str, int, dict[str, Any]]] = []
_batch_lock: asyncio.Lock | None = None
_batch_flush_task: asyncio.Task[None] | None = None


def _get_persist_semaphore() -> asyncio.Semaphore:
    """Get or create the persistence semaphore.

    Lazy initialization to avoid issues with event loop not running at import time.
    """
    global _persist_semaphore
    if _persist_semaphore is None:
        _persist_semaphore = asyncio.Semaphore(PERSIST_SEMAPHORE_LIMIT)
    return _persist_semaphore


def _get_batch_lock() -> asyncio.Lock:
    """Get or create the batch buffer lock."""
    global _batch_lock
    if _batch_lock is None:
        _batch_lock = asyncio.Lock()
    return _batch_lock


async def _flush_batch() -> None:
    """Flush pending events to PostgreSQL using batch insert.

    Called periodically or when buffer reaches threshold.
    Falls back to individual inserts on batch failure.
    """
    global _batch_buffer
    lock = _get_batch_lock()

    async with lock:
        if not _batch_buffer:
            return

        events_to_flush = _batch_buffer.copy()
        _batch_buffer = []

    if not events_to_flush:
        return

    flush_start = time.perf_counter()
    try:
        count = session_repository.save_events_batch(events_to_flush)
        flush_ms = (time.perf_counter() - flush_start) * 1000
        metrics.observe("event.batch_persist_ms", flush_ms)
        metrics.increment("event.batch_persisted", count)
        logger.debug(f"Batch persisted {count} events in {flush_ms:.1f}ms")
    except Exception as e:
        logger.warning(f"Batch persist failed, falling back to individual: {e}")
        # Fallback to individual inserts
        for sid, etype, seq, data in events_to_flush:
            try:
                session_repository.save_event(sid, etype, seq, data)
            except Exception as ind_error:
                log_error(
                    logger,
                    ErrorCode.DB_WRITE_ERROR,
                    f"Individual persist failed for {etype}: {ind_error}",
                    event_type=etype,
                )
                metrics.increment("event.persist_failed")


async def _batch_flush_loop() -> None:
    """Background loop that flushes batch buffer periodically."""
    while True:
        await asyncio.sleep(BATCH_FLUSH_INTERVAL_MS / 1000.0)
        try:
            await _flush_batch()
        except Exception as e:
            log_error(logger, ErrorCode.DB_WRITE_ERROR, f"Batch flush loop error: {e}")


def start_batch_flush_task() -> None:
    """Start the background batch flush task if not already running."""
    global _batch_flush_task
    if _batch_flush_task is None or _batch_flush_task.done():
        try:
            _batch_flush_task = asyncio.create_task(_batch_flush_loop())
            logger.info("Started batch event persistence task")
        except RuntimeError:
            # No event loop
            pass


def stop_batch_flush_task() -> None:
    """Stop the background batch flush task."""
    global _batch_flush_task
    if _batch_flush_task and not _batch_flush_task.done():
        _batch_flush_task.cancel()
        _batch_flush_task = None


async def add_to_batch(
    session_id: str,
    event_type: str,
    sequence: int,
    data: dict[str, Any],
) -> None:
    """Add an event to the batch buffer for deferred persistence.

    Triggers immediate flush if buffer reaches threshold.

    Args:
        session_id: Session identifier
        event_type: Event type
        sequence: Event sequence number
        data: Event payload
    """
    global _batch_buffer
    lock = _get_batch_lock()

    async with lock:
        if len(_batch_buffer) >= BATCH_MAX_BUFFER:
            # Cap reached, drop oldest to prevent unbounded growth
            logger.warning("Batch buffer full, dropping oldest event")
            _batch_buffer.pop(0)

        _batch_buffer.append((session_id, event_type, sequence, data))
        should_flush = len(_batch_buffer) >= BATCH_MAX_SIZE

    if should_flush:
        await _flush_batch()


async def flush_session_events(session_id: str) -> None:
    """Flush all pending events for a specific session.

    Call this when a session completes to ensure all events are persisted.

    Args:
        session_id: Session identifier to flush events for
    """
    global _batch_buffer
    lock = _get_batch_lock()

    async with lock:
        session_events = [e for e in _batch_buffer if e[0] == session_id]
        _batch_buffer = [e for e in _batch_buffer if e[0] != session_id]

    if session_events:
        try:
            session_repository.save_events_batch(session_events)
            logger.debug(f"Flushed {len(session_events)} events for session {session_id}")
        except Exception as e:
            log_error(
                logger,
                ErrorCode.DB_WRITE_ERROR,
                f"Failed to flush session events: {e}",
                session_id=session_id,
            )
            # Fallback to individual
            for sid, etype, seq, data in session_events:
                try:
                    session_repository.save_event(sid, etype, seq, data)
                except Exception as fallback_err:
                    logger.warning(f"Failed to save event {etype} for {sid}: {fallback_err}")


async def queue_failed_event(
    redis_client: redis.Redis,  # type: ignore[type-arg]
    session_id: str,
    event_type: str,
    sequence: int,
    event_data: dict[str, Any],
    original_error: str,
) -> bool:
    """Queue a failed event for later retry.

    Args:
        redis_client: Redis client instance
        session_id: Session identifier
        event_type: SSE event type
        sequence: Event sequence number
        event_data: Event payload (full payload including timestamp)
        original_error: Error message from failed persistence attempt

    Returns:
        True if queued successfully, False otherwise
    """
    try:
        failed_event = {
            "session_id": session_id,
            "event_type": event_type,
            "sequence": sequence,
            "event_data": event_data,
            "retry_count": 0,
            "first_failed_at": datetime.now(UTC).isoformat(),
            "next_retry_at": datetime.now(UTC).isoformat(),
            "original_error": original_error,
        }

        # Add to sorted set with current timestamp as score (for FIFO ordering)
        score = datetime.now(UTC).timestamp()
        redis_client.zadd(FAILED_EVENTS_KEY, {json.dumps(failed_event): score})

        logger.info(
            f"Queued failed event for retry: {event_type} (session {session_id}, seq {sequence})"
        )
        return True
    except Exception as e:
        log_error(
            logger,
            ErrorCode.REDIS_WRITE_ERROR,
            f"Failed to queue failed event: {e}",
            session_id=session_id,
            event_type=event_type,
        )
        return False


async def get_pending_retries(
    redis_client: redis.Redis,  # type: ignore[type-arg]
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get events ready for retry (next_retry_at <= now).

    Args:
        redis_client: Redis client instance
        limit: Maximum number of events to retrieve

    Returns:
        List of failed event dictionaries ready for retry
    """
    try:
        now = datetime.now(UTC).timestamp()

        # Get events where score (timestamp) <= now
        raw_events = redis_client.zrangebyscore(FAILED_EVENTS_KEY, 0, now, start=0, num=limit)

        if not raw_events:
            return []

        events = []
        for raw_event in raw_events:
            try:
                event = json.loads(raw_event)
                # Filter by next_retry_at to ensure it's actually ready
                next_retry_at = datetime.fromisoformat(event["next_retry_at"])
                if next_retry_at <= datetime.now(UTC):
                    events.append(event)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse queued event: {e}")
                # Remove invalid event
                redis_client.zrem(FAILED_EVENTS_KEY, raw_event)
                continue

        return events
    except Exception as e:
        log_error(logger, ErrorCode.REDIS_READ_ERROR, f"Failed to get pending retries: {e}")
        return []


async def retry_event(
    redis_client: redis.Redis,  # type: ignore[type-arg]
    event: dict[str, Any],
) -> bool:
    """Attempt to persist the event. Returns True on success.

    Args:
        redis_client: Redis client instance
        event: Failed event dictionary

    Returns:
        True if persistence succeeded, False otherwise
    """
    try:
        # Attempt to persist to PostgreSQL
        session_repository.save_event(
            session_id=event["session_id"],
            event_type=event["event_type"],
            sequence=event["sequence"],
            data=event["event_data"],
        )

        logger.info(
            f"Successfully retried event persistence: {event['event_type']} "
            f"(session {event['session_id']}, retry {event['retry_count'] + 1})"
        )
        return True
    except Exception as e:
        logger.warning(
            f"Retry attempt {event['retry_count'] + 1}/{MAX_RETRIES} failed for "
            f"{event['event_type']}: {e}"
        )
        return False


async def update_retry_event(
    redis_client: redis.Redis,  # type: ignore[type-arg]
    event: dict[str, Any],
    success: bool,
) -> None:
    """Update event after retry attempt.

    Args:
        redis_client: Redis client instance
        event: Failed event dictionary
        success: Whether the retry succeeded
    """
    try:
        # Remove old entry
        old_entry = json.dumps(event)
        redis_client.zrem(FAILED_EVENTS_KEY, old_entry)

        if success:
            # Success - event is now persisted, nothing more to do
            return

        # Increment retry count
        event["retry_count"] += 1

        # Check if we've exceeded max retries
        if event["retry_count"] >= MAX_RETRIES:
            await move_to_dlq(redis_client, event)
            return

        # Calculate next retry time with exponential backoff
        delay_seconds = RETRY_DELAYS[event["retry_count"] - 1]
        next_retry = datetime.now(UTC).timestamp() + delay_seconds
        event["next_retry_at"] = datetime.fromtimestamp(next_retry, UTC).isoformat()

        # Re-add to queue with new retry time as score
        redis_client.zadd(FAILED_EVENTS_KEY, {json.dumps(event): next_retry})

        logger.info(
            f"Scheduled retry {event['retry_count']}/{MAX_RETRIES} for "
            f"{event['event_type']} in {delay_seconds}s"
        )
    except Exception as e:
        log_error(logger, ErrorCode.REDIS_WRITE_ERROR, f"Failed to update retry event: {e}")


async def move_to_dlq(
    redis_client: redis.Redis,  # type: ignore[type-arg]
    event: dict[str, Any],
) -> None:
    """Move permanently failed event to dead letter queue.

    Args:
        redis_client: Redis client instance
        event: Failed event dictionary
    """
    try:
        # Add to DLQ with current timestamp
        score = datetime.now(UTC).timestamp()
        event["moved_to_dlq_at"] = datetime.now(UTC).isoformat()
        redis_client.zadd(FAILED_EVENTS_DLQ_KEY, {json.dumps(event): score})

        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"CRITICAL: Event moved to DLQ after {MAX_RETRIES} failed retries: {event['event_type']}",
            session_id=event["session_id"],
            sequence=event["sequence"],
            event_type=event["event_type"],
        )
    except Exception as e:
        log_error(logger, ErrorCode.REDIS_WRITE_ERROR, f"Failed to move event to DLQ: {e}")


async def get_queue_depth(redis_client: redis.Redis) -> int:  # type: ignore[type-arg]
    """Get number of events in retry queue.

    Args:
        redis_client: Redis client instance

    Returns:
        Number of events in queue
    """
    try:
        return redis_client.zcard(FAILED_EVENTS_KEY)
    except Exception as e:
        log_error(logger, ErrorCode.REDIS_READ_ERROR, f"Failed to get queue depth: {e}")
        return -1


async def get_dlq_depth(redis_client: redis.Redis) -> int:  # type: ignore[type-arg]
    """Get number of events in dead letter queue.

    Args:
        redis_client: Redis client instance

    Returns:
        Number of events in DLQ
    """
    try:
        return redis_client.zcard(FAILED_EVENTS_DLQ_KEY)
    except Exception as e:
        log_error(logger, ErrorCode.REDIS_READ_ERROR, f"Failed to get DLQ depth: {e}")
        return -1


def check_dlq_alerts(dlq_depth: int) -> None:
    """Check DLQ depth and log alerts if thresholds exceeded.

    Args:
        dlq_depth: Current number of events in DLQ
    """
    if dlq_depth < 0:
        # Error retrieving depth, skip alerting
        return

    if dlq_depth >= DLQ_CRITICAL_THRESHOLD:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"[DLQ_ALERT] Critical: DLQ depth {dlq_depth} exceeds critical threshold {DLQ_CRITICAL_THRESHOLD}",
            dlq_depth=dlq_depth,
            threshold=DLQ_CRITICAL_THRESHOLD,
        )
    elif dlq_depth >= DLQ_ALERT_THRESHOLD:
        logger.warning(
            "[DLQ_ALERT] Warning: DLQ depth %d exceeds warning threshold %d",
            dlq_depth,
            DLQ_ALERT_THRESHOLD,
        )


async def get_event_history_with_fallback(
    redis_client: redis.Redis | None,  # type: ignore[type-arg]
    session_id: str,
    last_event_id: str | None = None,
) -> list[dict[str, Any]]:
    """Get event history with Redis first, PostgreSQL fallback.

    Handles Redis connection errors gracefully by falling back to PostgreSQL.
    This ensures SSE clients can receive missed events even during Redis outages.

    Args:
        redis_client: Redis client instance (may be None if unavailable)
        session_id: Session identifier
        last_event_id: Optional Last-Event-ID for resume (format: "{session_id}:{sequence}")

    Returns:
        List of events in chronological order, filtered by last_event_id if provided
    """
    events: list[dict[str, Any]] = []
    used_fallback = False

    # Parse sequence from last_event_id
    last_sequence = 0
    if last_event_id:
        try:
            # Format: "{session_id}:{sequence}"
            parts = last_event_id.split(":")
            if len(parts) >= 2:
                last_sequence = int(parts[-1])
        except (ValueError, IndexError):
            logger.warning(f"Invalid Last-Event-ID format: {last_event_id}")

    # Try Redis first
    if redis_client is not None:
        try:
            history_key = f"events_history:{session_id}"
            raw_events = redis_client.lrange(history_key, 0, -1)

            if raw_events:
                for event_data in raw_events:
                    try:
                        payload = json.loads(event_data)
                        events.append(payload)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse Redis event for {session_id}")
                        continue

                logger.debug(f"Retrieved {len(events)} events from Redis for {session_id}")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"[REDIS_FALLBACK] Redis unavailable for {session_id}: {e}")
            used_fallback = True
        except Exception as e:
            log_error(
                logger,
                ErrorCode.REDIS_READ_ERROR,
                f"[REDIS_FALLBACK] Unexpected Redis error for {session_id}: {e}",
                session_id=session_id,
            )
            used_fallback = True
    else:
        used_fallback = True

    # Fall back to PostgreSQL if Redis is empty or unavailable
    if not events:
        if used_fallback:
            logger.info(f"[REDIS_FALLBACK] Using PostgreSQL fallback for {session_id}")

        pg_events = session_repository.get_events(session_id)
        for pg_event in pg_events:
            # PostgreSQL stores the full payload in 'data' column
            event_data = pg_event.get("data", {})
            if event_data:
                events.append(event_data)

        if events:
            logger.info(
                f"[REDIS_FALLBACK] Loaded {len(events)} events from PostgreSQL for {session_id}"
            )
            metrics.increment("event.postgres_fallback")

    # Filter by last_event_id if provided (for resume)
    if last_sequence > 0:
        events = [e for e in events if e.get("sequence", 0) > last_sequence]
        logger.debug(f"Filtered to {len(events)} events after sequence {last_sequence}")

    return events


async def get_missed_events(
    redis_client: redis.Redis | None,  # type: ignore[type-arg]
    session_id: str,
    last_event_id: str,
) -> list[dict[str, Any]]:
    """Get events missed since Last-Event-ID for SSE resume.

    Convenience wrapper around get_event_history_with_fallback for SSE reconnection.

    Args:
        redis_client: Redis client instance (may be None)
        session_id: Session identifier
        last_event_id: SSE Last-Event-ID header value

    Returns:
        List of events with sequence > last_event_id's sequence
    """
    return await get_event_history_with_fallback(
        redis_client=redis_client,
        session_id=session_id,
        last_event_id=last_event_id,
    )


class ExpertEventBuffer:
    """Per-expert event buffer for micro-batching expert contributions.

    Buffers events on a per-expert basis with a 50ms window, merging adjacent
    expert contribution events (expert_started → expert_reasoning → expert_conclusion)
    into single events to reduce SSE frame volume.

    Features:
    - Per-expert queue keyed by expert_id
    - 50ms buffer window (matches event batcher)
    - Flush on: window timeout, critical event, or round boundary
    - Preserves order: buffer within same expert, flush in expert_id order
    """

    BUFFER_WINDOW_MS = 50

    def __init__(self) -> None:
        """Initialize expert event buffer."""
        self._buffers: dict[str, list[dict[str, Any]]] = {}  # Per-expert queues
        self._last_flush_time: dict[str, float] = {}  # Track flush time per expert
        self._lock = asyncio.Lock()

    async def queue_event(
        self,
        session_id: str,
        expert_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> bool:
        """Queue event in expert buffer.

        Args:
            session_id: Session identifier
            expert_id: Expert identifier
            event_type: Event type
            data: Event payload

        Returns:
            True if event was buffered, False if should flush immediately
        """
        async with self._lock:
            if expert_id not in self._buffers:
                self._buffers[expert_id] = []
                self._last_flush_time[expert_id] = time.time()

            # Critical events bypass buffer
            if self._should_flush_immediately(event_type):
                return False

            # Add to expert's buffer
            self._buffers[expert_id].append(
                {
                    "event_type": event_type,
                    "data": data,
                    "timestamp": time.time(),
                }
            )

            # Check if should flush based on window timeout
            elapsed = time.time() - self._last_flush_time[expert_id]
            should_flush = elapsed >= (self.BUFFER_WINDOW_MS / 1000.0)

            return not should_flush

    async def flush_expert(self, expert_id: str) -> list[dict[str, Any]]:
        """Flush buffered events for a specific expert.

        Returns merged event if applicable, otherwise returns individual events.

        Args:
            expert_id: Expert identifier

        Returns:
            List of events to publish (merged or original)
        """
        async with self._lock:
            if expert_id not in self._buffers or not self._buffers[expert_id]:
                return []

            buffered = self._buffers[expert_id]
            self._buffers[expert_id] = []
            self._last_flush_time[expert_id] = time.time()

            # Try to merge adjacent expert contribution events
            merged = self._merge_expert_events(buffered)
            return merged

    async def flush_all(self) -> dict[str, list[dict[str, Any]]]:
        """Flush all buffered events for all experts.

        Returns:
            Dict mapping expert_id to list of events
        """
        async with self._lock:
            result = {}
            for expert_id in list(self._buffers.keys()):
                if self._buffers[expert_id]:
                    buffered = self._buffers[expert_id]
                    self._buffers[expert_id] = []
                    self._last_flush_time[expert_id] = time.time()
                    merged = self._merge_expert_events(buffered)
                    result[expert_id] = merged
            return result

    @staticmethod
    def _should_flush_immediately(event_type: str) -> bool:
        """Check if event should bypass buffer and flush immediately.

        Critical events that should not be buffered:
        - Round boundaries
        - System events
        - Synthesis/conclusion events

        Args:
            event_type: Event type

        Returns:
            True if event should flush immediately
        """
        critical_types = {
            "round_start",
            "round_end",
            "subproblem_waiting",
            "synthesis_complete",
            "meta_synthesis_complete",
            "meeting_complete",
            "complete",
            "facilitator_decision",
            "error",
            "working_status",
            "discussion_quality_status",
        }
        return event_type in critical_types

    @staticmethod
    def _merge_expert_events(buffered: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Merge adjacent expert contribution events.

        Detects pattern: expert_started → expert_reasoning → expert_conclusion
        and merges into single event: expert_contribution_complete

        Args:
            buffered: List of buffered events

        Returns:
            List of merged/original events
        """
        if len(buffered) < 3:
            # Can't merge if fewer than 3 events
            return buffered

        # Check for standard merge pattern
        if (
            len(buffered) >= 3
            and buffered[0]["event_type"] == "expert_started"
            and buffered[1]["event_type"] == "expert_reasoning"
            and buffered[2]["event_type"] == "expert_conclusion"
        ):
            # Merge first 3 events into expert_contribution_complete
            started = buffered[0]["data"]
            reasoning = buffered[1]["data"]
            conclusion = buffered[2]["data"]

            merged_event = {
                "event_type": "expert_contribution_complete",
                "data": {
                    "expert_id": reasoning.get("expert_id", started.get("expert_id")),
                    "round": reasoning.get("round", started.get("round")),
                    "phase": started.get("phase", "thinking"),
                    "reasoning": reasoning.get("reasoning", ""),
                    "confidence_score": reasoning.get("confidence_score"),
                    "recommendation": conclusion.get("recommendation", ""),
                    "merged": True,
                },
                "timestamp": buffered[2]["timestamp"],
            }

            # Return merged event + any remaining buffered events
            return [merged_event] + buffered[3:]

        # No merge pattern detected, return original events
        return buffered


async def _persist_event_with_semaphore(
    redis_client: redis.Redis,  # type: ignore[type-arg]
    session_id: str,
    event_type: str,
    sequence: int,
    payload: dict[str, Any],
    channel: str,
) -> None:
    """Wrapper that acquires semaphore before persisting event.

    Limits concurrent persistence tasks to prevent pool exhaustion.
    """
    semaphore = _get_persist_semaphore()
    async with semaphore:
        await _persist_event_async(redis_client, session_id, event_type, sequence, payload, channel)


async def _persist_event_async(
    redis_client: redis.Redis,  # type: ignore[type-arg]
    session_id: str,
    event_type: str,
    sequence: int,
    payload: dict[str, Any],
    channel: str,
) -> None:
    """Persist event to PostgreSQL asynchronously with batching (P2-PERF optimization).

    Runs in background to avoid blocking event publishing.
    Uses EventBatcher for priority-based batching (critical events flush immediately).
    On failure, queues event for retry and emits error to frontend.

    Args:
        redis_client: Redis client for error event publishing
        session_id: Session identifier
        event_type: SSE event type
        sequence: Event sequence number
        payload: Full event payload including timestamp
        channel: Redis channel for error event publishing
    """
    persistence_success = False
    last_error = None

    # P2-PERF: Track DB persistence timing
    persist_start = time.perf_counter()

    try:
        # Use event batcher for priority-based batching
        batcher = get_batcher()
        await batcher.queue_event(
            session_id=session_id,
            event_type=event_type,
            data=payload,  # Store full payload including timestamp
        )
        persistence_success = True

        # P2-PERF: Track successful persistence time
        persist_duration_ms = (time.perf_counter() - persist_start) * 1000
        metrics.observe("event.db_persist_ms", persist_duration_ms)
        metrics.increment("event.persisted")

        logger.debug(
            f"Event queued for batching: {event_type} (session {session_id}, priority-aware)"
        )
    except Exception as batch_error:
        last_error = batch_error
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            "CRITICAL: Event batching failed - event will be LOST when Redis expires!",
            exc_info=True,
            session_id=session_id,
            event_type=event_type,
        )
        metrics.increment("event.persist_failed")

    # If batching failed, queue for retry and emit error event to frontend
    if not persistence_success:
        # Queue the failed event for background retry
        try:
            await queue_failed_event(
                redis_client=redis_client,
                session_id=session_id,
                event_type=event_type,
                sequence=sequence,
                event_data=payload,
                original_error=str(last_error),
            )
        except Exception as queue_error:
            log_error(
                logger,
                ErrorCode.REDIS_WRITE_ERROR,
                f"Failed to queue failed event: {queue_error}",
                session_id=session_id,
            )

        # Emit error event to frontend
        try:
            error_payload = {
                "event_type": "persistence_error",
                "session_id": session_id,
                "timestamp": payload.get("timestamp"),
                "data": {
                    "failed_event_type": event_type,
                    "failed_sequence": sequence,
                    "error": str(last_error),
                    "message": "Event was published but failed to persist to database. Queued for retry.",
                },
            }
            error_message = json.dumps(error_payload)
            redis_client.publish(channel, error_message)
            log_error(
                logger,
                ErrorCode.API_SSE_ERROR,
                f"Emitted persistence_error event for failed {event_type}",
                session_id=session_id,
                event_type=event_type,
            )
        except Exception as emit_error:
            log_error(
                logger,
                ErrorCode.API_SSE_ERROR,
                f"Failed to emit persistence error event: {emit_error}",
                session_id=session_id,
            )


class EventPublisher:
    """Publishes deliberation events to Redis PubSub for SSE streaming.

    Each session has a dedicated Redis channel (events:{session_id}) where
    events are published during graph execution. SSE clients subscribe to
    these channels to receive real-time updates.

    Events are stored in:
    - Redis (transient): For real-time SSE streaming and reconnection
    - PostgreSQL (permanent): For historical access after Redis restart

    Supports optional expert event buffering for per-expert micro-batching
    and event merging to reduce SSE frame volume (P2-PERF optimization).

    Includes reconnection awareness:
    - Buffers events in memory during Redis disconnection
    - Flushes buffered events to Redis on reconnection
    - Falls back to PostgreSQL-only persistence if Redis unavailable

    Examples:
        >>> from bo1.state.redis_manager import RedisManager
        >>> redis_manager = RedisManager()
        >>> publisher = EventPublisher(redis_manager.redis)
        >>> publisher.publish_event(
        ...     "bo1_abc123",
        ...     "decomposition_complete",
        ...     {"sub_problems": [...], "count": 3}
        ... )
    """

    def __init__(
        self,
        redis_client: redis.Redis,  # type: ignore[type-arg]
        expert_buffer: ExpertEventBuffer | None = None,
        redis_manager: Any = None,
    ) -> None:
        """Initialize EventPublisher.

        Args:
            redis_client: Redis client instance for publishing
            expert_buffer: Optional ExpertEventBuffer for per-expert micro-batching
            redis_manager: Optional RedisManager for reconnection support
        """
        self.redis = redis_client
        self._sequence_counters: dict[str, int] = {}  # Track sequence per session
        self._expert_buffer = expert_buffer
        self._redis_manager = redis_manager

        # Event buffer for disconnection resilience
        from bo1.constants import RedisReconnection

        self._disconnect_buffer: list[tuple[str, str, int, dict[str, Any]]] = []
        self._buffer_max_events = RedisReconnection.BUFFER_MAX_EVENTS
        self._buffer_lock = asyncio.Lock()

    @property
    def buffer_depth(self) -> int:
        """Get current number of events in disconnection buffer."""
        return len(self._disconnect_buffer)

    async def _buffer_event(
        self,
        session_id: str,
        event_type: str,
        sequence: int,
        payload: dict[str, Any],
    ) -> None:
        """Buffer an event during Redis disconnection.

        Uses FIFO eviction when buffer reaches max capacity.

        Args:
            session_id: Session identifier
            event_type: Event type
            sequence: Event sequence number
            payload: Full event payload
        """
        async with self._buffer_lock:
            if len(self._disconnect_buffer) >= self._buffer_max_events:
                # FIFO eviction - drop oldest event
                dropped = self._disconnect_buffer.pop(0)
                logger.warning(
                    f"[REDIS_BUFFER] Buffer full, dropped oldest event: "
                    f"{dropped[1]} (session {dropped[0]}, seq {dropped[2]})"
                )
                metrics.increment("event.buffer_overflow")

            self._disconnect_buffer.append((session_id, event_type, sequence, payload))

            # Update Prometheus gauge
            try:
                from backend.api.metrics import prom_metrics

                prom_metrics.redis_buffer_depth.set(len(self._disconnect_buffer))
            except ImportError:
                pass

    async def _flush_buffer_to_redis(self) -> int:
        """Flush buffered events to Redis after reconnection.

        Returns:
            Number of events flushed
        """
        async with self._buffer_lock:
            if not self._disconnect_buffer:
                return 0

            events_to_flush = self._disconnect_buffer.copy()
            self._disconnect_buffer = []

        flushed = 0
        for session_id, event_type, sequence, payload in events_to_flush:
            try:
                channel = f"events:{session_id}"
                history_key = f"events_history:{session_id}"
                message = json.dumps(payload)

                # Store in Redis history and publish
                self.redis.rpush(history_key, message)
                self.redis.expire(history_key, 7 * 24 * 60 * 60)
                self.redis.publish(channel, message)

                flushed += 1
            except Exception:
                log_error(
                    logger,
                    ErrorCode.REDIS_WRITE_ERROR,
                    f"[REDIS_BUFFER] Failed to flush buffered event {event_type}",
                    session_id=session_id,
                    event_type=event_type,
                )
                # Re-buffer failed events
                async with self._buffer_lock:
                    self._disconnect_buffer.append((session_id, event_type, sequence, payload))

        if flushed > 0:
            logger.info(f"[REDIS_BUFFER] Flushed {flushed} buffered events to Redis")
            metrics.increment("event.buffer_flushed", flushed)

        # Update Prometheus gauge
        try:
            from backend.api.metrics import prom_metrics

            prom_metrics.redis_buffer_depth.set(len(self._disconnect_buffer))
        except ImportError:
            pass

        return flushed

    async def on_redis_reconnect(self) -> None:
        """Callback when Redis connection is restored.

        Flushes buffered events to Redis and resumes normal operation.
        """
        logger.info("[REDIS_RECONNECT] Redis reconnected, flushing buffered events")
        flushed = await self._flush_buffer_to_redis()
        logger.info(f"[REDIS_RECONNECT] Flush complete: {flushed} events")

    def _is_redis_available(self) -> bool:
        """Check if Redis is available for publishing.

        Returns:
            True if Redis is connected and available
        """
        if self._redis_manager is not None:
            return self._redis_manager.is_available
        # Fallback: try a ping
        try:
            self.redis.ping()
            return True
        except Exception:
            return False

    async def publish_event_buffered(
        self,
        session_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Publish event with optional expert buffering for micro-batching.

        If expert_buffer is configured and event can be buffered:
        - Adds event to per-expert buffer
        - Flushes on timeout, critical events, or round boundaries
        - Merges adjacent expert contribution events into single events

        Otherwise falls through to standard publish_event.

        Args:
            session_id: Session identifier
            event_type: SSE event type
            data: Event payload
        """
        # If no buffer configured, use standard publish
        if not self._expert_buffer:
            self.publish_event(session_id, event_type, data)
            return

        # Extract expert_id if available
        expert_id = data.get("expert_id") or data.get("persona_code")

        # If no expert_id, not a bufferable event (use standard publish)
        if not expert_id:
            self.publish_event(session_id, event_type, data)
            return

        # Try to buffer the event
        was_buffered = await self._expert_buffer.queue_event(
            session_id=session_id,
            expert_id=expert_id,
            event_type=event_type,
            data=data,
        )

        if was_buffered:
            # Event queued in buffer, will be flushed on timeout or critical event
            logger.debug(f"Event buffered for {expert_id}: {event_type}")
            return

        # Event should be published immediately (critical event or not bufferable)
        # Check if need to flush any pending buffered events before publishing
        if ExpertEventBuffer._should_flush_immediately(event_type):
            # Flush all pending buffered events before critical event
            all_buffered = await self._expert_buffer.flush_all()
            for _exp_id, buffered_events in all_buffered.items():
                for buffered_event in buffered_events:
                    self.publish_event(
                        session_id,
                        buffered_event["event_type"],
                        buffered_event["data"],
                    )
            logger.debug(f"Flushed {len(all_buffered)} expert buffers before {event_type}")

        # Publish the critical event
        self.publish_event(session_id, event_type, data)

    def publish_event(
        self,
        session_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Publish event to session's Redis channel AND store in history.

        The event is stored in:
        1. Redis list (events_history:{session_id}) - transient, for reconnection
        2. Redis PubSub channel (events:{session_id}) - real-time streaming
        3. PostgreSQL session_events table - permanent storage

        Args:
            session_id: Session identifier
            event_type: SSE event type (e.g., "decomposition_started")
            data: Event payload (will be JSON serialized)

        Examples:
            >>> publisher.publish_event(
            ...     "bo1_abc123",
            ...     "contribution",
            ...     {
            ...         "persona_code": "CFO",
            ...         "persona_name": "Zara Kim",
            ...         "content": "From a financial perspective...",
            ...         "round": 1
            ...     }
            ... )
        """
        channel = f"events:{session_id}"
        history_key = f"events_history:{session_id}"

        # Get next sequence number for this session
        if session_id not in self._sequence_counters:
            self._sequence_counters[session_id] = 0
        self._sequence_counters[session_id] += 1
        sequence = self._sequence_counters[session_id]

        # Add timestamp, session_id, sequence, and request_id to all events
        timestamp = datetime.now(UTC).isoformat()
        request_id = get_request_id()
        payload = {
            "event_type": event_type,
            "session_id": session_id,
            "sequence": sequence,
            "timestamp": timestamp,
            "data": data,
        }
        if request_id:
            payload["request_id"] = request_id

        # P2-005: Track event publish timing
        publish_start = time.perf_counter()

        try:
            message = json.dumps(payload)

            # Store in Redis history list (transient - for reconnection)
            self.redis.rpush(history_key, message)
            # Set TTL of 7 days for event history (matches checkpoint TTL)
            self.redis.expire(history_key, 7 * 24 * 60 * 60)

            # Publish to Redis PubSub (for real-time streaming)
            self.redis.publish(channel, message)

            # P2-005: Track Redis publish latency (should be <10ms)
            publish_duration_ms = (time.perf_counter() - publish_start) * 1000
            metrics.observe("event.redis_publish_ms", publish_duration_ms)
            metrics.increment("event.published")

            logger.debug(f"Published {event_type} to {channel} and stored in history")

            # P2-005 Quick Win: Persist to PostgreSQL asynchronously
            # Events are immediately available in Redis for SSE streaming.
            # PostgreSQL persistence runs in background to avoid blocking.
            # CRITICAL: Events MUST be persisted for meeting replay.
            # Uses semaphore to limit concurrent tasks and prevent pool exhaustion.
            try:
                asyncio.create_task(
                    _persist_event_with_semaphore(
                        redis_client=self.redis,
                        session_id=session_id,
                        event_type=event_type,
                        sequence=sequence,
                        payload=payload,
                        channel=channel,
                    )
                )
            except RuntimeError:
                # No event loop running (happens in sync tests or CLI)
                # Fall back to synchronous persistence
                try:
                    session_repository.save_event(
                        session_id=session_id,
                        event_type=event_type,
                        sequence=sequence,
                        data=payload,
                    )
                except Exception:
                    log_error(
                        logger,
                        ErrorCode.DB_WRITE_ERROR,
                        f"CRITICAL: Sync fallback persistence failed for {event_type}",
                        exc_info=True,
                        session_id=session_id,
                        event_type=event_type,
                    )

        except Exception as e:
            log_error(
                logger,
                ErrorCode.REDIS_WRITE_ERROR,
                f"Failed to publish {event_type} to {channel}: {e}",
                session_id=session_id,
                event_type=event_type,
            )
            # Don't raise - event publishing should not block graph execution
