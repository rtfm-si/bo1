"""Input validation utilities for Board of One API.

Provides validation functions for:
- Session IDs (UUID format with optional 'bo1_' prefix)
- User IDs (alphanumeric with common separators)
- Other security-critical inputs
"""

import re

from fastapi import HTTPException


def validate_session_id(session_id: str) -> str:
    """Validate session ID format.

    Prevents injection attacks by ensuring session ID follows expected UUID format.
    Accepts:
    - Standard UUID: 550e8400-e29b-41d4-a716-446655440000
    - Prefixed UUID: bo1_550e8400-e29b-41d4-a716-446655440000

    Args:
        session_id: Session identifier to validate

    Returns:
        Validated session ID (lowercased)

    Raises:
        HTTPException: 400 if session ID format is invalid

    Examples:
        >>> validate_session_id("550e8400-e29b-41d4-a716-446655440000")
        '550e8400-e29b-41d4-a716-446655440000'
        >>> validate_session_id("bo1_550e8400-e29b-41d4-a716-446655440000")
        'bo1_550e8400-e29b-41d4-a716-446655440000'
        >>> validate_session_id("invalid'; DROP TABLE sessions;--")
        HTTPException: 400 Bad Request
    """
    # UUID v4 pattern with optional 'bo1_' prefix
    pattern = r"^(bo1_)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

    if not re.match(pattern, session_id, re.IGNORECASE):
        raise HTTPException(
            status_code=400,
            detail="Invalid session ID format. Expected UUID format (with optional 'bo1_' prefix).",
        )

    return session_id.lower()


def validate_user_id(user_id: str) -> str:
    """Validate user ID format.

    Prevents injection attacks by ensuring user ID contains only safe characters.
    Accepts:
    - Alphanumeric characters
    - Hyphens, underscores, and @ symbols
    - Length: 1-255 characters

    Args:
        user_id: User identifier to validate

    Returns:
        Validated user ID

    Raises:
        HTTPException: 400 if user ID format is invalid

    Examples:
        >>> validate_user_id("test_user_1")
        'test_user_1'
        >>> validate_user_id("user@example.com")
        'user@example.com'
        >>> validate_user_id("user'; DROP TABLE users;--")
        HTTPException: 400 Bad Request
    """
    # Allow alphanumeric, hyphens, underscores, and @ symbols
    pattern = r"^[a-zA-Z0-9_@.-]{1,255}$"

    if not re.match(pattern, user_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID format. Only alphanumeric characters, hyphens, underscores, and @ symbols allowed.",
        )

    return user_id


def validate_cache_id(cache_id: str) -> str:
    """Validate research cache ID format.

    Ensures cache ID is a valid UUID string representation.

    Args:
        cache_id: Research cache record ID

    Returns:
        Validated cache ID (lowercased)

    Raises:
        HTTPException: 400 if cache ID format is invalid
    """
    # Standard UUID pattern (no prefix for cache IDs)
    pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

    if not re.match(pattern, cache_id, re.IGNORECASE):
        raise HTTPException(
            status_code=400,
            detail="Invalid cache ID format. Expected UUID format.",
        )

    return cache_id.lower()
