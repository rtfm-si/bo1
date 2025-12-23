"""Security utilities for API endpoints.

Provides reusable security functions for:
- Session ownership validation
- Resource access control
- Security-focused error responses
"""

import logging

from fastapi import HTTPException

from bo1.logging.errors import ErrorCode, log_error

logger = logging.getLogger(__name__)


async def verify_session_ownership(
    session_id: str,
    user_id: str,
    session_metadata: dict | None = None,
) -> dict:
    """Verify user owns the session. Returns session metadata if authorized.

    This function implements security best practices:
    - Returns 404 (not 403) to prevent session enumeration
    - Logs security events for audit trail
    - Validates both session existence and ownership
    - Falls back to PostgreSQL if Redis doesn't have the metadata

    Args:
        session_id: Session identifier to check
        user_id: User ID claiming ownership
        session_metadata: Optional pre-loaded metadata (avoids duplicate DB call)

    Returns:
        Session metadata dict if authorized

    Raises:
        HTTPException: 404 if session not found or user doesn't own it
                      (never reveals whether session exists to unauthorized users)

    Examples:
        >>> # Basic usage (loads metadata internally)
        >>> metadata = await verify_session_ownership(session_id, user_id)

        >>> # Efficient usage (metadata already loaded)
        >>> metadata = redis_manager.load_metadata(session_id)
        >>> metadata = await verify_session_ownership(session_id, user_id, metadata)
    """
    # Import here to avoid circular dependency
    from backend.api.dependencies import get_redis_manager
    from bo1.state.repositories import session_repository

    # Load metadata if not provided
    if session_metadata is None:
        redis_manager = get_redis_manager()
        session_metadata = redis_manager.load_metadata(session_id)

    # If Redis doesn't have metadata, fall back to PostgreSQL
    # This handles cases where Redis was restarted but session exists in DB
    if not session_metadata:
        logger.debug(f"Session {session_id} not in Redis, checking PostgreSQL fallback")
        session_metadata = session_repository.get_metadata(session_id)
        if session_metadata:
            logger.info(f"Session {session_id} loaded from PostgreSQL fallback")

    # Session doesn't exist in either Redis or PostgreSQL - return 404
    if not session_metadata:
        logger.warning(
            f"Session ownership check failed: session {session_id} not found "
            f"(requested by user {user_id})"
        )
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    # Check ownership
    session_owner = session_metadata.get("user_id")
    if session_owner != user_id:
        # SECURITY: Return 404 (not 403) to prevent session enumeration
        # Don't reveal that session exists to unauthorized users
        logger.warning(
            f"Session ownership check failed: user {user_id} attempted to access "
            f"session {session_id} owned by {session_owner}"
        )
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    # Ownership verified - return metadata
    logger.debug(f"Session ownership verified: {session_id} owned by {user_id}")
    return session_metadata


async def verify_resource_ownership(
    resource_type: str,
    resource_id: str,
    user_id: str,
    owner_id: str | None,
) -> None:
    """Generic resource ownership verification.

    Args:
        resource_type: Type of resource (e.g., "session", "context", "clarification")
        resource_id: Resource identifier
        user_id: User ID claiming ownership
        owner_id: Actual owner ID from database

    Raises:
        HTTPException: 404 if user doesn't own resource (prevents enumeration)
    """
    if owner_id != user_id:
        logger.warning(
            f"{resource_type.capitalize()} ownership check failed: "
            f"user {user_id} attempted to access {resource_type} {resource_id} "
            f"owned by {owner_id}"
        )
        raise HTTPException(
            status_code=404,
            detail=f"{resource_type.capitalize()} not found",
        )


def sanitize_error_for_production(
    error: Exception,
    debug_mode: bool = False,
) -> dict:
    """Sanitize error messages for production (prevent info leakage).

    Args:
        error: Exception that occurred
        debug_mode: Whether to include detailed error info

    Returns:
        Sanitized error dict safe for client response
    """
    error_type = type(error).__name__

    if debug_mode:
        # Development: Return full error details
        return {
            "error": "Internal server error",
            "message": str(error),
            "type": error_type,
        }
    else:
        # Production: Return generic error (log details server-side)
        log_error(logger, ErrorCode.API_REQUEST_ERROR, f"Internal error ({error_type}): {error}")
        return {
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "type": "InternalError",
        }
