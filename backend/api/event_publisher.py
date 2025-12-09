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
from bo1.context import get_request_id
from bo1.state.repositories import session_repository

logger = logging.getLogger(__name__)


# Failed event persistence retry configuration
FAILED_EVENTS_KEY = "failed_events:queue"
FAILED_EVENTS_DLQ_KEY = "failed_events:dlq"
MAX_RETRIES = 5
RETRY_DELAYS = [60, 120, 300, 600, 1800]  # 1min, 2min, 5min, 10min, 30min

# Semaphore to limit concurrent event persistence tasks
# Set below pool max (20) to leave headroom for other operations
PERSIST_SEMAPHORE_LIMIT = 15
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
                logger.error(f"Individual persist failed for {etype}: {ind_error}")
                metrics.increment("event.persist_failed")


async def _batch_flush_loop() -> None:
    """Background loop that flushes batch buffer periodically."""
    while True:
        await asyncio.sleep(BATCH_FLUSH_INTERVAL_MS / 1000.0)
        try:
            await _flush_batch()
        except Exception as e:
            logger.error(f"Batch flush loop error: {e}")


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
            logger.error(f"Failed to flush session events: {e}")
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
        logger.error(f"Failed to queue failed event: {e}")
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
        logger.error(f"Failed to get pending retries: {e}")
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
        logger.error(f"Failed to update retry event: {e}")


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

        logger.error(
            f"CRITICAL: Event moved to DLQ after {MAX_RETRIES} failed retries: "
            f"{event['event_type']} (session {event['session_id']}, seq {event['sequence']})"
        )
    except Exception as e:
        logger.error(f"Failed to move event to DLQ: {e}")


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
        logger.error(f"Failed to get queue depth: {e}")
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
        logger.error(f"Failed to get DLQ depth: {e}")
        return -1


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
    """Persist event to PostgreSQL asynchronously (P2-005 optimization).

    Runs in background to avoid blocking event publishing.
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

    # P2-005: Track DB persistence timing
    persist_start = time.perf_counter()

    # Retry persistence without blocking (no sleep between attempts)
    for attempt in range(3):  # 3 immediate retry attempts
        try:
            session_repository.save_event(
                session_id=session_id,
                event_type=event_type,
                sequence=sequence,
                data=payload,  # Store full payload including timestamp
            )
            persistence_success = True

            # P2-005: Track successful persistence time
            persist_duration_ms = (time.perf_counter() - persist_start) * 1000
            metrics.observe("event.db_persist_ms", persist_duration_ms)
            metrics.increment("event.persisted")

            if attempt > 0:
                logger.info(
                    f"Event persistence succeeded on attempt {attempt + 1} "
                    f"for {event_type} (session {session_id})"
                )
                metrics.increment("event.persist_retry_success")
            break
        except Exception as db_error:
            last_error = db_error
            if attempt < 2:  # Log retry attempts
                logger.warning(
                    f"Event persistence attempt {attempt + 1}/3 failed for "
                    f"{event_type}: {db_error}. Retrying immediately..."
                )
            else:
                logger.error(
                    f"CRITICAL: Event persistence failed after 3 attempts for "
                    f"{event_type} (session {session_id}): {db_error}\n"
                    f"This event will be LOST when Redis expires!"
                )
                metrics.increment("event.persist_failed")

    # If all attempts failed, queue for retry and emit error event to frontend
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
            logger.error(f"Failed to queue failed event: {queue_error}")

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
            logger.error(f"Emitted persistence_error event for failed {event_type}")
        except Exception as emit_error:
            logger.error(f"Failed to emit persistence error event: {emit_error}")


class EventPublisher:
    """Publishes deliberation events to Redis PubSub for SSE streaming.

    Each session has a dedicated Redis channel (events:{session_id}) where
    events are published during graph execution. SSE clients subscribe to
    these channels to receive real-time updates.

    Events are stored in:
    - Redis (transient): For real-time SSE streaming and reconnection
    - PostgreSQL (permanent): For historical access after Redis restart

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

    def __init__(self, redis_client: redis.Redis) -> None:  # type: ignore[type-arg]
        """Initialize EventPublisher.

        Args:
            redis_client: Redis client instance for publishing
        """
        self.redis = redis_client
        self._sequence_counters: dict[str, int] = {}  # Track sequence per session

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
                except Exception as db_error:
                    logger.error(
                        f"CRITICAL: Sync fallback persistence failed for "
                        f"{event_type} (session {session_id}): {db_error}"
                    )

        except Exception as e:
            logger.error(f"Failed to publish {event_type} to {channel}: {e}")
            # Don't raise - event publishing should not block graph execution
