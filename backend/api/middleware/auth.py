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

from fastapi import Depends, Request
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from backend.api.utils.errors import http_error
from bo1.config import get_settings
from bo1.feature_flags import ENABLE_SUPERTOKENS_AUTH
from bo1.logging.errors import ErrorCode, log_error

logger = logging.getLogger(__name__)

# Debug mode check - MVP mode only allowed if DEBUG is true
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

# E2E mode - bypasses auth with real test user (for Playwright testing)
E2E_MODE = os.getenv("PUBLIC_E2E_MODE", "false").lower() == "true"

# MVP: Hardcoded user ID for development (only when DEBUG=true)
DEFAULT_USER_ID = "test_user_1"

# E2E: Real test user ID from database (for E2E testing)
E2E_USER_ID = "00d3cc72-cf20-4263-86de-388ddd951d2d"

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


async def _get_current_user_with_session(
    request: Request,
    session: SessionContainer = Depends(verify_session()),
) -> dict[str, Any]:
    """Internal function that requires SuperTokens session verification.

    Supports admin impersonation: if admin has active impersonation session,
    returns target user's data while preserving admin identity for audit.
    """
    try:
        user_id = session.get_user_id()
        session_handle = session.get_handle()

        logger.info(f"Authenticated user via SuperTokens: {user_id}")

        # Fetch user data from database including is_admin flag
        from bo1.state.repositories import user_repository

        user_data = user_repository.get(user_id)

        # Check for impersonation (set by ImpersonationMiddleware)
        is_impersonation = getattr(request.state, "is_impersonation", False)
        impersonation_target_id = getattr(request.state, "impersonation_target_id", None)

        if is_impersonation and impersonation_target_id:
            # Admin is impersonating - fetch target user's data
            target_data = user_repository.get(impersonation_target_id)
            if target_data:
                logger.info(
                    f"Impersonation active: admin {user_id} viewing as {impersonation_target_id}"
                )
                return {
                    "user_id": impersonation_target_id,
                    "email": target_data.get("email"),
                    "role": "authenticated",
                    "subscription_tier": target_data.get("subscription_tier", "free"),
                    "is_admin": False,  # Never grant admin rights while impersonating
                    "session_handle": session_handle,
                    # Impersonation metadata for audit
                    "is_impersonation": True,
                    "real_admin_id": user_id,
                    "impersonation_write_mode": getattr(
                        request.state, "impersonation_write_mode", False
                    ),
                }

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
        log_error(
            logger,
            ErrorCode.AUTH_TOKEN_ERROR,
            f"Failed to get user from SuperTokens session: {e}",
            exc_info=True,
        )
        raise http_error(ErrorCode.API_UNAUTHORIZED, "Authentication failed", status=401) from e


async def _get_current_user_mvp() -> dict[str, Any]:
    """MVP mode: Return hardcoded user without session verification."""
    if not DEBUG_MODE:
        log_error(
            logger,
            ErrorCode.AUTH_TOKEN_ERROR,
            "Auth bypass attempted in non-DEBUG mode - rejecting",
        )
        raise http_error(
            ErrorCode.API_UNAUTHORIZED, "Authentication misconfigured. Contact support.", status=500
        )
    logger.debug("SuperTokens auth disabled (MVP/DEBUG mode), using hardcoded user")
    return {
        "user_id": DEFAULT_USER_ID,
        "email": f"{DEFAULT_USER_ID}@test.com",
        "role": "authenticated",
        "subscription_tier": "free",
        "is_admin": False,
    }


async def _get_current_user_e2e() -> dict[str, Any]:
    """E2E mode: Return real test user without session verification (for Playwright)."""
    logger.info("E2E mode: using real test user for Playwright testing")
    return {
        "user_id": E2E_USER_ID,
        "email": "e2e.test@boardof.one",
        "role": "authenticated",
        "subscription_tier": "pro",
        "is_admin": True,
    }


# Choose the correct dependency based on feature flag
# This must be at module level so FastAPI picks the right one
# Priority: E2E_MODE > MVP mode > SuperTokens auth
if E2E_MODE:
    get_current_user = _get_current_user_e2e
    logger.warning("E2E mode: auth bypassed with real test user (PUBLIC_E2E_MODE=true)")
elif ENABLE_SUPERTOKENS_AUTH:
    get_current_user = _get_current_user_with_session
else:
    get_current_user = _get_current_user_mvp


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
        raise http_error(ErrorCode.API_UNAUTHORIZED, "Authentication required", status=401)
    return user


async def _require_admin_with_session(
    session: SessionContainer = Depends(verify_session()),
) -> dict[str, Any]:
    """Internal admin function with session verification."""
    user = await _get_current_user_with_session(session)

    if not user or not user.get("user_id"):
        raise http_error(ErrorCode.API_UNAUTHORIZED, "Authentication required", status=401)

    if not user.get("is_admin", False):
        logger.warning(f"Non-admin user {user.get('user_id')} attempted to access admin endpoint")
        raise http_error(ErrorCode.API_FORBIDDEN, "Admin access required", status=403)

    logger.info(f"Admin access granted to {user.get('user_id')}")
    return user


async def _require_admin_mvp() -> dict[str, Any]:
    """MVP mode admin function."""
    user = await _get_current_user_mvp()

    if not user or not user.get("user_id"):
        raise http_error(ErrorCode.API_UNAUTHORIZED, "Authentication required", status=401)

    # In MVP mode, allow admin access (for testing)
    logger.info(f"Admin access granted to {user.get('user_id')} (MVP mode)")
    return user


async def _require_admin_e2e() -> dict[str, Any]:
    """E2E mode admin function."""
    user = await _get_current_user_e2e()

    if not user or not user.get("user_id"):
        raise http_error(ErrorCode.API_UNAUTHORIZED, "Authentication required", status=401)

    # E2E test user has is_admin=True
    logger.info(f"Admin access granted to {user.get('user_id')} (E2E mode)")
    return user


# Choose the correct dependency based on feature flag
# Priority: E2E_MODE > MVP mode > SuperTokens auth
if E2E_MODE:
    require_admin = _require_admin_e2e
elif ENABLE_SUPERTOKENS_AUTH:
    require_admin = _require_admin_with_session
else:
    require_admin = _require_admin_mvp
