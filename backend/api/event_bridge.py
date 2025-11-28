"""Event bridge for emitting events from non-graph contexts.

Allows parallel sub-problem execution to emit real-time events
without requiring LangGraph node wrapping.
"""

import logging
from typing import Any

from backend.api.event_publisher import EventPublisher

logger = logging.getLogger(__name__)


class EventBridge:
    """Bridge for emitting events from parallel sub-problem execution.

    This class wraps EventPublisher to automatically tag events with
    sub_problem_index, allowing sub-problem deliberations that execute
    outside the main graph to still emit real-time events.

    The EventBridge solves the problem where _deliberate_subproblem() is
    a standalone async function (not a LangGraph node), so EventCollector
    can't intercept its internal operations. By passing an EventBridge
    instance, the function can directly publish events to Redis + PostgreSQL.

    Examples:
        >>> from backend.api.dependencies import get_event_publisher
        >>> publisher = get_event_publisher()
        >>> bridge = EventBridge("bo1_abc123", publisher)
        >>> bridge.set_sub_problem_index(0)
        >>> bridge.emit("persona_selected", {"personas": [...], "count": 3})
    """

    def __init__(self, session_id: str, publisher: EventPublisher) -> None:
        """Initialize EventBridge.

        Args:
            session_id: Session identifier for event routing
            publisher: EventPublisher instance for publishing events
        """
        self.session_id = session_id
        self.publisher = publisher
        self.sub_problem_index: int | None = None

    def set_sub_problem_index(self, index: int) -> None:
        """Set the current sub-problem index for event tagging.

        All subsequent emit() calls will include this index in the event data.

        Args:
            index: Sub-problem index (0-based)
        """
        self.sub_problem_index = index

    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit event with automatic sub-problem tagging.

        The event is published to:
        1. Redis PubSub channel (events:{session_id}) - real-time streaming
        2. Redis list (events_history:{session_id}) - reconnection support
        3. PostgreSQL session_events table - permanent storage

        Args:
            event_type: Event type (e.g., "contribution_added", "round_complete")
            data: Event payload (will be JSON serialized by EventPublisher)

        Examples:
            >>> bridge.emit("persona_selected", {
            ...     "personas": [{"code": "CFO", "name": "Zara Kim"}],
            ...     "count": 1
            ... })
            >>> # Event published with sub_problem_index automatically added
        """
        # Add sub_problem_index to all events
        event_data = {**data}
        if self.sub_problem_index is not None:
            event_data["sub_problem_index"] = self.sub_problem_index

        # Publish to Redis + PostgreSQL via EventPublisher
        try:
            self.publisher.publish_event(
                self.session_id,
                event_type,
                event_data,
            )
            logger.debug(
                f"EventBridge: Emitted {event_type} for sub-problem {self.sub_problem_index}"
            )
        except Exception as e:
            # Don't raise - event emission should not block deliberation
            logger.warning(f"EventBridge: Failed to emit {event_type}: {e}")
