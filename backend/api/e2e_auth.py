"""E2E Test Authentication endpoint.

Allows E2E tests to create authenticated sessions without OAuth flows.
Protected by E2E_AUTH_SECRET environment variable.

SECURITY: This endpoint MUST only be enabled in staging/test environments.
"""

import logging
import os

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from supertokens_python.recipe.session.asyncio import create_new_session
from supertokens_python.types import RecipeUserId

logger = logging.getLogger(__name__)

router = APIRouter()

# Secret key for E2E auth - must be set to enable this endpoint
E2E_AUTH_SECRET = os.getenv("E2E_AUTH_SECRET", "")


class E2EAuthRequest(BaseModel):
    """Request body for E2E authentication."""

    user_id: str = Field(..., description="User ID to create session for")
    secret: str = Field(..., description="E2E auth secret key")


class E2EAuthResponse(BaseModel):
    """Response for successful E2E authentication."""

    success: bool
    user_id: str
    message: str


@router.post(
    "/e2e/session",
    response_model=E2EAuthResponse,
    tags=["e2e"],
    summary="Create E2E test session",
    description="Creates an authenticated session for E2E testing. Requires E2E_AUTH_SECRET.",
)
async def create_e2e_session(
    request: Request,
    response: Response,
    body: E2EAuthRequest,
) -> E2EAuthResponse:
    """Create a SuperTokens session for E2E testing.

    This endpoint:
    1. Validates the E2E auth secret
    2. Creates a SuperTokens session for the specified user
    3. Sets all necessary cookies (sAccessToken, sRefreshToken, sFrontToken)

    Security:
    - Only enabled if E2E_AUTH_SECRET is set
    - Secret must match to create session
    - Logs all attempts for audit trail
    """
    # Check if E2E auth is enabled
    if not E2E_AUTH_SECRET:
        logger.warning("E2E auth attempt but E2E_AUTH_SECRET not configured")
        raise HTTPException(
            status_code=404,
            detail="Not found",
        )

    # Validate secret
    if body.secret != E2E_AUTH_SECRET:
        logger.warning(f"E2E auth attempt with invalid secret for user {body.user_id}")
        raise HTTPException(
            status_code=401,
            detail="Invalid secret",
        )

    try:
        # Create SuperTokens session - this sets all the proper cookies
        # Signature: create_new_session(request, tenant_id, recipe_user_id, ...)
        session = await create_new_session(
            request,
            "public",
            RecipeUserId(body.user_id),
        )

        logger.info(f"E2E session created for user {body.user_id}, handle: {session.get_handle()}")

        return E2EAuthResponse(
            success=True,
            user_id=body.user_id,
            message="Session created successfully",
        )

    except Exception as e:
        logger.error(f"Failed to create E2E session for user {body.user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session: {str(e)}",
        ) from e
