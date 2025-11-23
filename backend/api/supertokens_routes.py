"""SuperTokens custom endpoints.

This module provides ONLY custom endpoints that extend SuperTokens functionality.
SuperTokens middleware automatically handles these standard routes:
- GET /api/auth/authorisationurl - Get OAuth authorization URL
- GET/POST /api/auth/callback/thirdparty - OAuth callback
- POST /api/auth/signinup - Complete sign-in/up
- POST /api/auth/signout - Sign out

We only add custom endpoints that are NOT handled by SuperTokens middleware.
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session
from supertokens_python.recipe.thirdparty import asyncio as thirdparty_asyncio

from backend.api.middleware.rate_limit import AUTH_RATE_LIMIT, limiter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/user")
@limiter.limit(AUTH_RATE_LIMIT)
async def get_user_info(
    request: Request, session: SessionContainer = Depends(verify_session())
) -> JSONResponse:
    """Get current user information.

    Rate limit: 10 requests per minute per IP.

    Returns:
        User ID, email, and session info
    """
    try:
        user_id = session.get_user_id()

        # Get user info from SuperTokens
        user = await thirdparty_asyncio.get_user_by_id(user_id)

        if user is None:
            return JSONResponse({"status": "ERROR", "message": "User not found"}, status_code=404)

        # Get email from login methods
        email = None
        if user.login_methods:
            for method in user.login_methods:
                if hasattr(method, "email"):
                    email = method.email
                    break

        return JSONResponse(
            {
                "status": "OK",
                "user": {
                    "id": user_id,
                    "email": email,
                    "timeJoined": user.time_joined,
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to get user info: {e}", exc_info=True)
        return JSONResponse({"status": "ERROR", "message": str(e)}, status_code=500)
