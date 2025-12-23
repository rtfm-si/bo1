"""Admin authentication middleware for Board of One API.

Provides two authentication methods for admin endpoints:
1. Session-based: Uses SuperTokens session + is_admin flag from database
2. API key-based: Uses X-Admin-Key header (for scripts/automation)

SECURITY: Uses constant-time comparison to prevent timing attacks on API keys.
"""

import logging
import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from bo1.config import get_settings
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

# Load admin API key from centralized settings
_settings = get_settings()
ADMIN_API_KEY = _settings.admin_api_key

if not ADMIN_API_KEY:
    logger.info("ADMIN_API_KEY not set - API key auth disabled, session auth still works")
elif len(ADMIN_API_KEY) < 32:
    logger.warning("SECURITY: ADMIN_API_KEY should be at least 32 characters for adequate entropy")


def verify_admin_key_secure(provided_key: str, expected_key: str) -> bool:
    """Constant-time admin key comparison to prevent timing attacks.

    Uses secrets.compare_digest() for constant-time string comparison,
    preventing attackers from using timing analysis to guess the key.

    Args:
        provided_key: API key from request header
        expected_key: Expected API key from environment

    Returns:
        True if keys match, False otherwise
    """
    if not provided_key or not expected_key:
        return False

    # Use constant-time comparison to prevent timing attacks
    return secrets.compare_digest(provided_key, expected_key)


async def require_admin_session(
    session: Annotated[SessionContainer, Depends(verify_session())],
) -> str:
    """Dependency to require admin authentication via session.

    Checks if the authenticated user has is_admin=true in the database.

    Args:
        session: SuperTokens session container

    Returns:
        User ID if admin

    Raises:
        HTTPException: 403 if user is not an admin
    """
    user_id = session.get_user_id()

    # Get user from database to check admin status
    user_data = user_repository.get(user_id)

    if not user_data:
        logger.warning(f"Admin access attempted by unknown user: {user_id}")
        raise HTTPException(
            status_code=403,
            detail="User not found",
        )

    if not user_data.get("is_admin", False):
        logger.warning(f"Non-admin user attempted admin access: {user_id}")
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    logger.debug(f"Admin session access granted for user: {user_id}")
    return user_id


def require_admin(x_admin_key: str = Header(default=None)) -> str:
    """Dependency to require admin authentication via API key.

    Checks the X-Admin-Key header against the ADMIN_API_KEY environment variable.
    Use this for script/automation access. For browser-based access, use
    require_admin_session instead.

    Args:
        x_admin_key: Admin API key from X-Admin-Key header (optional)

    Returns:
        Admin API key if valid

    Raises:
        HTTPException: 401 if key not provided, 403 if key invalid
    """
    if not ADMIN_API_KEY:
        log_error(
            logger,
            ErrorCode.API_UNAUTHORIZED,
            "Admin API key not configured - API key access denied",
        )
        raise HTTPException(
            status_code=500,
            detail="Admin API key not configured",
        )

    if not x_admin_key:
        logger.warning("Admin access attempted without API key")
        raise HTTPException(
            status_code=401,
            detail="Admin API key required",
        )

    # Use constant-time comparison to prevent timing attacks
    if not verify_admin_key_secure(x_admin_key, ADMIN_API_KEY):
        logger.warning("Invalid admin API key attempted")
        raise HTTPException(
            status_code=403,
            detail="Invalid admin API key",
        )

    logger.debug("Admin API key access granted")
    return x_admin_key


async def require_admin_any(
    request: Request,
    x_admin_key: str = Header(default=None),
) -> str:
    """Flexible admin auth - accepts either session or API key.

    Tries session-based auth first (for browser), falls back to API key (for scripts).

    Args:
        request: FastAPI request object
        x_admin_key: Optional API key from header

    Returns:
        User ID (session) or "api_key" (API key auth)

    Raises:
        HTTPException: 401/403 if neither auth method succeeds
    """
    # Try API key first (simpler check)
    if x_admin_key and ADMIN_API_KEY:
        if verify_admin_key_secure(x_admin_key, ADMIN_API_KEY):
            logger.debug("Admin access granted via API key")
            return "api_key"

    # Try session-based auth
    try:
        session = await verify_session()(request)
        if session:
            user_id = session.get_user_id()
            user_data = user_repository.get(user_id)

            if user_data and user_data.get("is_admin", False):
                logger.debug(f"Admin access granted via session for user: {user_id}")
                return user_id
    except Exception as e:
        logger.debug(f"Session auth failed: {e}")  # Will try other methods or raise below

    # Neither auth method succeeded
    log_error(
        logger, ErrorCode.API_UNAUTHORIZED, "Admin access denied - no valid session or API key"
    )
    raise HTTPException(
        status_code=403,
        detail="Admin access required. Please log in as an admin user.",
    )
