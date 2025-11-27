"""Authentication endpoints for SuperTokens OAuth.

Provides:
- OAuth provider endpoints (automatically handled by SuperTokens middleware)
- Session verification
- User info retrieval

SuperTokens automatically exposes these endpoints under /api/auth:
- GET /api/auth/authorisationurl - Get OAuth authorization URL
- POST /api/auth/signinup - Complete OAuth flow
- POST /api/auth/signout - Sign out user
"""

import logging

from fastapi import APIRouter, Depends, Request
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from backend.api.middleware.rate_limit import AUTH_RATE_LIMIT, limiter
from bo1.state.postgres_manager import get_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me")
@limiter.limit(AUTH_RATE_LIMIT)
async def get_user_info(
    request: Request, session: SessionContainer = Depends(verify_session())
) -> dict:
    """Get current authenticated user information.

    Fetches user data from PostgreSQL (source of truth for persistent data).
    If user not found in DB, returns minimal data from session.

    Returns:
        User ID, email, auth provider, subscription tier, and session info
    """
    user_id = session.get_user_id()
    session_handle = session.get_handle()

    logger.info(f"User info requested: user_id={user_id}, session={session_handle}")

    # Fetch complete user data from PostgreSQL
    user_data = get_user(user_id)

    if user_data:
        return {
            "id": user_data["id"],
            "user_id": user_data["id"],
            "email": user_data["email"],
            "auth_provider": user_data["auth_provider"],
            "subscription_tier": user_data["subscription_tier"],
            "session_handle": session_handle,
        }

    # Fallback if user not in database (shouldn't happen with proper sync)
    logger.warning(f"User {user_id} not found in PostgreSQL, returning minimal data")
    return {
        "id": user_id,
        "user_id": user_id,
        "email": None,
        "auth_provider": None,
        "subscription_tier": "free",
        "session_handle": session_handle,
    }
