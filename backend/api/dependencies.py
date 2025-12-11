"""Dependency injection providers for Board of One API.

Provides singleton instances of:
- RedisManager: Redis connection management
- SessionManager: Active session management with ownership tracking
- EventPublisher: Event publishing for SSE streaming
- ContributionSummarizer: AI-powered contribution summarization
- PostgreSQL connection pool (via bo1.state.database)

Also provides reusable dependencies for:
- Authentication + session verification (get_verified_session)

All singletons use @lru_cache for caching.
"""

import os
from functools import lru_cache
from typing import Annotated, Any

from anthropic import AsyncAnthropic
from fastapi import Depends, HTTPException

from backend.api.contribution_summarizer import ContributionSummarizer
from backend.api.event_publisher import EventPublisher
from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.security import verify_session_ownership
from bo1.config import get_settings
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


@lru_cache(maxsize=1)
def get_contribution_summarizer() -> ContributionSummarizer:
    """Get singleton contribution summarizer instance.

    The summarizer uses Claude Haiku for cost-effective AI summarization
    of expert contributions.

    Returns:
        ContributionSummarizer instance (cached)
    """
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return ContributionSummarizer(client)


async def get_verified_session(
    session_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> tuple[str, dict[str, Any]]:
    """Verify user owns the session and return (user_id, metadata).

    This dependency combines:
    1. User authentication (via get_current_user)
    2. Redis availability check
    3. Session metadata loading
    4. Ownership verification

    Use this dependency in authenticated endpoints that need to verify session
    ownership. It consolidates the common pattern of extracting user_id,
    checking Redis availability, loading metadata, and verifying ownership.

    Args:
        session_id: Session identifier from path parameter
        user: Authenticated user from SuperTokens (injected)
        redis_manager: Redis manager instance (injected)

    Returns:
        tuple: (user_id, verified_metadata)

    Raises:
        HTTPException: 500 if Redis unavailable
        HTTPException: 404 if session not found
        HTTPException: 403 if user doesn't own session (returned as 404 to prevent enumeration)

    Examples:
        >>> # In endpoint signature
        >>> @router.get("/{session_id}")
        >>> async def get_session(
        ...     session_id: str,
        ...     session_data: VerifiedSession,
        ... ):
        ...     user_id, metadata = session_data
        ...     # ... endpoint logic
    """
    if not redis_manager.is_available:
        raise HTTPException(
            status_code=500,
            detail="Redis unavailable - cannot access session",
        )

    user_id = extract_user_id(user)
    metadata = redis_manager.load_metadata(session_id)
    metadata = await verify_session_ownership(session_id, user_id, metadata)

    return user_id, metadata


# Type alias for cleaner endpoint signatures
VerifiedSession = Annotated[tuple[str, dict[str, Any]], Depends(get_verified_session)]
