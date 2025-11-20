"""Supabase authentication middleware for Board of One API.

Provides JWT-based authentication using self-hosted Supabase GoTrue.

For MVP: Uses hardcoded user ID (test_user_1) for development
For Closed Beta: Supabase auth + email whitelist validation
For v2+: Full Supabase auth with OAuth providers (Google, LinkedIn, GitHub)

SECURITY: MVP mode MUST be disabled in production environments.
"""

import logging
import os
from typing import Any

from fastapi import Depends, Header, HTTPException

from bo1.config import get_settings

logger = logging.getLogger(__name__)

# Feature flag for Supabase auth (disabled for MVP)
ENABLE_SUPABASE_AUTH = os.getenv("ENABLE_SUPABASE_AUTH", "false").lower() == "true"
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:9999")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# MVP: Hardcoded user ID for development
DEFAULT_USER_ID = "test_user_1"


def require_production_auth() -> None:
    """Validates that authentication is properly configured in production.

    This function MUST be called during application startup to prevent
    deploying with MVP mode enabled in production.

    Raises:
        RuntimeError: If authentication is not enabled in production mode
    """
    settings = get_settings()

    # Check if running in production (not debug mode)
    if not settings.debug and not ENABLE_SUPABASE_AUTH:
        error_msg = (
            "SECURITY VIOLATION: Supabase authentication MUST be enabled in production. "
            "Set ENABLE_SUPABASE_AUTH=true in environment variables. "
            "Current settings: DEBUG=false, ENABLE_SUPABASE_AUTH=false"
        )
        logger.critical(error_msg)
        raise RuntimeError(error_msg)


async def verify_jwt(authorization: str = Header(None)) -> dict[str, Any]:
    """Verify JWT token from Supabase auth.

    For MVP: Returns hardcoded user data (no auth required)
    For v2+: Validates JWT token and returns user data from Supabase

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        User data dictionary with user_id, email, role

    Raises:
        HTTPException: 401 if token is invalid or missing (v2+ only)
    """
    # MVP: Skip authentication, return hardcoded user
    if not ENABLE_SUPABASE_AUTH:
        logger.debug("Supabase auth disabled (MVP mode), using hardcoded user")
        return {
            "user_id": DEFAULT_USER_ID,
            "email": f"{DEFAULT_USER_ID}@test.com",
            "role": "authenticated",
            "subscription_tier": "free",
            "is_admin": False,  # MVP user is not admin
        }

    # v2+: Full Supabase authentication
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning("Missing or invalid Authorization header")
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authorization header",
        )

    token = authorization.replace("Bearer ", "")

    try:
        # Import PyJWT for local token validation (avoid HTTP request)
        try:
            import jwt
        except ImportError as e:
            logger.error("PyJWT not installed - required for auth")
            raise HTTPException(
                status_code=500,
                detail="Authentication system not configured",
            ) from e

        # Validate JWT secret is configured
        if not SUPABASE_JWT_SECRET:
            logger.error("SUPABASE_JWT_SECRET not configured")
            raise HTTPException(
                status_code=500,
                detail="Authentication system not configured",
            )

        # Decode and verify JWT token locally
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",  # Verify aud claim
                options={
                    "verify_iss": False  # GoTrue v2.158.1 doesn't include iss claim
                },
            )
        except jwt.ExpiredSignatureError as e:
            logger.warning("Token has expired")
            raise HTTPException(
                status_code=401,
                detail="Token has expired",
            ) from e
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid token",
            ) from e

        # Extract user data from JWT claims
        user_id = payload.get("sub")
        user_email = payload.get("email")
        user_role = payload.get("role", "authenticated")
        user_metadata = payload.get("user_metadata", {})
        app_metadata = payload.get("app_metadata", {})

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing user ID",
            )

        logger.info(f"Authenticated user: {user_id}")

        # Check beta whitelist if closed beta mode is enabled
        settings = get_settings()
        if settings.closed_beta_mode:
            email_for_check = (user_email or "").lower()
            if email_for_check not in settings.beta_whitelist_emails:
                logger.warning(
                    f"User {email_for_check} not in beta whitelist. "
                    f"Whitelist has {len(settings.beta_whitelist_emails)} emails."
                )
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "closed_beta",
                        "message": "Thanks for your interest! We're currently in closed beta. "
                        "Join our waitlist at https://boardof.one/waitlist",
                    },
                )
            logger.info(f"User {email_for_check} found in beta whitelist - access granted")

        # Extract role from user metadata (custom claim)
        # SECURITY: Removed email-based admin auto-grant
        # Admin access must be explicitly set in database admin_users table
        is_admin = user_metadata.get("is_admin", False) or app_metadata.get("is_admin", False)

        return {
            "user_id": user_id,
            "email": user_email,
            "role": user_role,
            "subscription_tier": user_metadata.get("subscription_tier", "free"),
            "is_admin": is_admin,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Token verification failed: {str(e)}",
        ) from e


async def get_current_user(authorization: str = Header(None)) -> dict[str, Any]:
    """Get current authenticated user.

    Alias for verify_jwt() to match common FastAPI patterns.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        User data dictionary

    Raises:
        HTTPException: 401 if authentication fails
    """
    return await verify_jwt(authorization)


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


async def require_admin(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Dependency to require admin access for an endpoint.

    Usage:
        @app.get("/admin/endpoint")
        async def admin_route(user: dict = Depends(require_admin)):
            return {"message": "Admin access granted"}

    Args:
        user: User data from get_current_user()

    Returns:
        User data if user is admin

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin
    """
    if not user or not user.get("user_id"):
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    if not user.get("is_admin", False):
        logger.warning(
            f"Non-admin user {user.get('email', 'unknown')} attempted to access admin endpoint"
        )
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    logger.info(f"Admin access granted to {user.get('email', 'unknown')}")
    return user
