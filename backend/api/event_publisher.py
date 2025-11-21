"""Event publisher using Redis PubSub for real-time SSE streaming.

Provides:
- EventPublisher: Publishes deliberation events to Redis channels for SSE streaming
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

import redis

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publishes deliberation events to Redis PubSub for SSE streaming.

    Each session has a dedicated Redis channel (events:{session_id}) where
    events are published during graph execution. SSE clients subscribe to
    these channels to receive real-time updates.

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

    def publish_event(
        self,
        session_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Publish event to session's Redis channel AND store in history.

        The event is:
        1. Stored in Redis list (events_history:{session_id}) for historical replay
        2. Published to PubSub channel (events:{session_id}) for real-time streaming

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

        # Add timestamp and session_id to all events
        payload = {
            "event_type": event_type,
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data,
        }

        try:
            message = json.dumps(payload)

            # Store in history list (for reconnection)
            self.redis.rpush(history_key, message)
            # Set TTL of 7 days for event history (matches checkpoint TTL)
            self.redis.expire(history_key, 7 * 24 * 60 * 60)

            # Publish to PubSub (for real-time streaming)
            self.redis.publish(channel, message)

            logger.debug(f"Published {event_type} to {channel} and stored in history")
        except Exception as e:
            logger.error(f"Failed to publish {event_type} to {channel}: {e}")
            # Don't raise - event publishing should not block graph execution
