"""Dependency injection providers for Board of One API.

Provides singleton instances of:
- RedisManager: Redis connection management
- SessionManager: Active session management with ownership tracking
- EventPublisher: Event publishing for SSE streaming
- PostgreSQL connection pool (via postgres_manager)

All dependencies use @lru_cache for singleton pattern.
"""

import os
from functools import lru_cache

from backend.api.event_publisher import EventPublisher
from bo1.graph.execution import SessionManager
from bo1.state.redis_manager import RedisManager


@lru_cache(maxsize=1)
def get_redis_manager() -> RedisManager:
    """Get singleton Redis manager instance.

    Returns:
        RedisManager instance (cached)

    Examples:
        >>> redis_manager = get_redis_manager()
        >>> session_id = redis_manager.create_session()
    """
    return RedisManager()


@lru_cache(maxsize=1)
def get_session_manager() -> SessionManager:
    """Get singleton session manager instance.

    The session manager tracks active deliberation sessions and enforces
    ownership rules for session control operations.

    Returns:
        SessionManager instance (cached)

    Examples:
        >>> session_manager = get_session_manager()
        >>> await session_manager.start_session(session_id, user_id, coro)
    """
    redis_manager = get_redis_manager()

    # Load admin user IDs from environment
    # Format: Comma-separated list (e.g., "admin,user123")
    admin_users_env = os.getenv("ADMIN_USER_IDS", "admin")
    admin_user_ids = {user.strip() for user in admin_users_env.split(",") if user.strip()}

    return SessionManager(redis_manager, admin_user_ids=admin_user_ids)


@lru_cache(maxsize=1)
def get_event_publisher() -> EventPublisher:
    """Get singleton event publisher instance.

    The event publisher broadcasts deliberation events to Redis PubSub
    channels for real-time SSE streaming to web clients.

    Returns:
        EventPublisher instance (cached)

    Examples:
        >>> publisher = get_event_publisher()
        >>> publisher.publish_event(session_id, "decomposition_complete", {...})
    """
    redis_manager = get_redis_manager()
    return EventPublisher(redis_manager.redis)
