"""Event publisher using Redis PubSub for real-time SSE streaming.

Provides:
- EventPublisher: Publishes deliberation events to Redis channels for SSE streaming
- Persists events to PostgreSQL for permanent storage (Redis is transient)
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

import redis

from bo1.state.postgres_manager import save_session_event

logger = logging.getLogger(__name__)


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

        # Add timestamp and session_id to all events
        timestamp = datetime.now(UTC).isoformat()
        payload = {
            "event_type": event_type,
            "session_id": session_id,
            "timestamp": timestamp,
            "data": data,
        }

        try:
            message = json.dumps(payload)

            # Store in Redis history list (transient - for reconnection)
            self.redis.rpush(history_key, message)
            # Set TTL of 7 days for event history (matches checkpoint TTL)
            self.redis.expire(history_key, 7 * 24 * 60 * 60)

            # Publish to Redis PubSub (for real-time streaming)
            self.redis.publish(channel, message)

            logger.debug(f"Published {event_type} to {channel} and stored in history")

            # Persist to PostgreSQL (permanent storage)
            # CRITICAL: Events MUST be persisted for meeting replay
            # Retry with exponential backoff if persistence fails
            persistence_success = False
            last_error = None

            # Retry persistence without blocking (no sleep between attempts)
            # Note: Blocking sleep was removed to prevent event loop blocking.
            # If persistence fails, we retry immediately which is acceptable
            # since database errors are typically transient connection issues.
            for attempt in range(3):  # 3 immediate retry attempts
                try:
                    save_session_event(
                        session_id=session_id,
                        event_type=event_type,
                        sequence=sequence,
                        data=payload,  # Store full payload including timestamp
                    )
                    persistence_success = True
                    if attempt > 0:
                        logger.info(
                            f"Event persistence succeeded on attempt {attempt + 1} "
                            f"for {event_type} (session {session_id})"
                        )
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

            # If all attempts failed, emit error event to frontend
            if not persistence_success:
                try:
                    error_payload = {
                        "event_type": "persistence_error",
                        "session_id": session_id,
                        "timestamp": payload.get("timestamp"),
                        "data": {
                            "failed_event_type": event_type,
                            "failed_sequence": sequence,
                            "error": str(last_error),
                            "message": "Event was published but failed to persist to database",
                        },
                    }
                    error_message = json.dumps(error_payload)
                    self.redis.publish(channel, error_message)
                    logger.error(f"Emitted persistence_error event for failed {event_type}")
                except Exception as emit_error:
                    logger.error(f"Failed to emit persistence error event: {emit_error}")

        except Exception as e:
            logger.error(f"Failed to publish {event_type} to {channel}: {e}")
            # Don't raise - event publishing should not block graph execution
