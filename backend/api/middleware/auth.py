"""SuperTokens authentication middleware for Board of One API - BFF Pattern.

Provides session-based authentication using httpOnly session cookies via SuperTokens.

Flow:
1. Frontend sends request with httpOnly SuperTokens session cookie
2. SuperTokens middleware validates session automatically
3. verify_session() extracts user_id from session
4. Returns user data if valid, raises 401 if not

Security:
- Tokens stored server-side (never exposed to frontend)
- httpOnly cookies prevent XSS attacks
- Session expiry enforced by SuperTokens
- Beta whitelist checking

For MVP: Uses hardcoded user ID (test_user_1) for development
For Closed Beta: SuperTokens auth + email whitelist validation
For Production: Full SuperTokens auth with OAuth providers (Google, LinkedIn, GitHub)

SECURITY: MVP mode MUST be disabled in production environments.
"""

import logging
import os
from typing import Any

from fastapi import Depends, HTTPException
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from bo1.config import get_settings
from bo1.feature_flags import ENABLE_SUPERTOKENS_AUTH

logger = logging.getLogger(__name__)

# Debug mode check - MVP mode only allowed if DEBUG is true
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

# MVP: Hardcoded user ID for development (only when DEBUG=true)
DEFAULT_USER_ID = "test_user_1"

# Security check on import: warn if MVP mode enabled in non-debug
if not ENABLE_SUPERTOKENS_AUTH:
    if not DEBUG_MODE:
        logger.critical(
            "SECURITY WARNING: SuperTokens auth disabled but DEBUG mode is OFF. "
            "This should NEVER happen in production. Set ENABLE_SUPERTOKENS_AUTH=true "
            "or DEBUG=true for development."
        )
    else:
        logger.warning("MVP mode: SuperTokens auth disabled (DEBUG=true)")


def require_production_auth() -> None:
    """Validates that authentication is properly configured in production.

    This function MUST be called during application startup to prevent
    deploying with MVP mode enabled in production.

    Raises:
        RuntimeError: If authentication is not enabled in production mode
    """
    settings = get_settings()

    # Check if running in production (not debug mode)
    if not settings.debug and not ENABLE_SUPERTOKENS_AUTH:
        error_msg = (
            "SECURITY VIOLATION: SuperTokens authentication MUST be enabled in production. "
            "Set ENABLE_SUPERTOKENS_AUTH=true in environment variables. "
            "Current settings: DEBUG=false, ENABLE_SUPERTOKENS_AUTH=false"
        )
        logger.critical(error_msg)
        raise RuntimeError(error_msg)


async def get_current_user(
    session: SessionContainer = Depends(verify_session()),
) -> dict[str, Any]:
    """Get current authenticated user from SuperTokens session.

    For MVP: Returns hardcoded user data (no auth required)
    For Production: Uses SuperTokens session verification

    Args:
        session: SuperTokens session container (auto-validated by middleware)

    Returns:
        User data dictionary with user_id, email, role

    Raises:
        HTTPException: 401 if session is invalid (SuperTokens handles this)
    """
    # MVP: Skip authentication, return hardcoded user (only in DEBUG mode)
    if not ENABLE_SUPERTOKENS_AUTH:
        if not DEBUG_MODE:
            logger.error("Auth bypass attempted in non-DEBUG mode - rejecting")
            raise HTTPException(
                status_code=500,
                detail="Authentication misconfigured. Contact support.",
            )
        logger.debug("SuperTokens auth disabled (MVP/DEBUG mode), using hardcoded user")
        return {
            "user_id": DEFAULT_USER_ID,
            "email": f"{DEFAULT_USER_ID}@test.com",
            "role": "authenticated",
            "subscription_tier": "free",
            "is_admin": False,
        }

    # Production: Use SuperTokens session
    try:
        user_id = session.get_user_id()
        session_handle = session.get_handle()

        logger.info(f"Authenticated user via SuperTokens: {user_id}")

        # Fetch user data from database including is_admin flag
        from bo1.state.postgres_manager import get_user

        user_data = get_user(user_id)

        # Use database values if available, otherwise defaults
        return {
            "user_id": user_id,
            "email": user_data.get("email") if user_data else None,
            "role": "authenticated",
            "subscription_tier": user_data.get("subscription_tier", "free")
            if user_data
            else "free",
            "is_admin": user_data.get("is_admin", False) if user_data else False,
            "session_handle": session_handle,
        }

    except Exception as e:
        logger.error(f"Failed to get user from SuperTokens session: {e}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
        ) from e


def require_auth(user: dict[str, Any]) -> dict[str, Any]:
    """Dependency to require authentication for an endpoint.

    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"user_id": user["user_id"]}

    Args:
        user: User data from verify_jwt()

    Returns:
        User data if authenticated

    Raises:
        HTTPException: 401 if not authenticated
    """
    if not user or not user.get("user_id"):
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )
    return user


async def require_admin(
    session: SessionContainer = Depends(verify_session()),
) -> dict[str, Any]:
    """Dependency to require admin access for an endpoint.

    Usage:
        @app.get("/admin/endpoint")
        async def admin_route(user: dict = Depends(require_admin)):
            return {"message": "Admin access granted"}

    Args:
        session: SuperTokens session container (auto-validated by middleware)

    Returns:
        User data if user is admin

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin
    """
    user = await get_current_user(session)

    if not user or not user.get("user_id"):
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    if not user.get("is_admin", False):
        logger.warning(f"Non-admin user {user.get('user_id')} attempted to access admin endpoint")
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    logger.info(f"Admin access granted to {user.get('user_id')}")
    return user
