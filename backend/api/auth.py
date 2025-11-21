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

from fastapi import APIRouter, Depends
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me")
async def get_user_info(session: SessionContainer = Depends(verify_session())) -> dict:
    """Get current authenticated user information.

    Returns:
        User ID and session info
    """
    user_id = session.get_user_id()
    session_handle = session.get_handle()

    logger.info(f"User info requested: user_id={user_id}, session={session_handle}")

    return {
        "id": user_id,  # Frontend expects 'id' not 'user_id'
        "user_id": user_id,
        "email": None,  # TODO: Fetch from database
        "auth_provider": "google",  # TODO: Get from session metadata
        "subscription_tier": "free",
        "session_handle": session_handle,
    }
