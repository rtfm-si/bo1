"""Supabase authentication middleware for Board of One API.

Provides JWT-based authentication using self-hosted Supabase GoTrue.

For MVP: Uses hardcoded user ID (test_user_1) for development
For v2+: Full Supabase auth with OAuth providers (Google, LinkedIn, GitHub)
"""

import logging
import os
from typing import Any

from fastapi import Header, HTTPException

logger = logging.getLogger(__name__)

# Feature flag for Supabase auth (disabled for MVP)
ENABLE_SUPABASE_AUTH = os.getenv("ENABLE_SUPABASE_AUTH", "false").lower() == "true"
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:9999")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# MVP: Hardcoded user ID for development
DEFAULT_USER_ID = "test_user_1"


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
        # Import supabase client only when auth is enabled (avoid dependency for MVP)
        try:
            from supabase import create_client  # type: ignore[import-untyped]
        except ImportError as e:
            logger.error("supabase-py not installed - required for auth")
            raise HTTPException(
                status_code=500,
                detail="Authentication system not configured",
            ) from e

        # Verify token with Supabase
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token",
            )

        user = user_response.user
        logger.info(f"Authenticated user: {user.id}")

        return {
            "user_id": user.id,
            "email": user.email,
            "role": user.role or "authenticated",
            "subscription_tier": user.user_metadata.get("subscription_tier", "free"),
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
