"""Research Sharing API endpoints.

Provides:
- GET /api/v1/research-sharing/consent - Current consent status
- POST /api/v1/research-sharing/consent - Opt in
- DELETE /api/v1/research-sharing/consent - Opt out
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import CONTEXT_RATE_LIMIT, limiter
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors
from backend.services.research_sharing import (
    get_consent_status,
    give_consent,
    revoke_consent,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/research-sharing", tags=["research-sharing"])


# =============================================================================
# Models
# =============================================================================


class ConsentStatusResponse(BaseModel):
    """Research sharing consent status response."""

    consented: bool = Field(..., description="Whether user has active consent")
    consented_at: datetime | None = Field(None, description="When consent was given")
    revoked_at: datetime | None = Field(None, description="When consent was revoked")


# =============================================================================
# Consent Endpoints
# =============================================================================


@router.get("/consent", response_model=ConsentStatusResponse)
@handle_api_errors("get research sharing consent")
@limiter.limit(CONTEXT_RATE_LIMIT)
async def get_consent(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> ConsentStatusResponse:
    """Get user's current research sharing consent status."""
    user_id = extract_user_id(current_user)

    status = get_consent_status(user_id)

    return ConsentStatusResponse(
        consented=status.consented,
        consented_at=status.consented_at,
        revoked_at=status.revoked_at,
    )


@router.post("/consent", response_model=ConsentStatusResponse)
@handle_api_errors("opt in research sharing")
@limiter.limit(CONTEXT_RATE_LIMIT)
async def opt_in(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> ConsentStatusResponse:
    """Opt in to research sharing.

    Your anonymized research insights will be shared with similar businesses.
    No personal information is shared - only the research findings.
    """
    user_id = extract_user_id(current_user)

    status = give_consent(user_id)

    logger.info("research_sharing_consent_given", extra={"user_id": user_id})

    return ConsentStatusResponse(
        consented=status.consented,
        consented_at=status.consented_at,
        revoked_at=status.revoked_at,
    )


@router.delete("/consent", response_model=ConsentStatusResponse)
@handle_api_errors("opt out research sharing")
@limiter.limit(CONTEXT_RATE_LIMIT)
async def opt_out(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> ConsentStatusResponse:
    """Opt out of research sharing.

    Your existing research is immediately marked as non-shareable.
    You can still benefit from shared research from other users.
    """
    user_id = extract_user_id(current_user)

    status = revoke_consent(user_id)

    logger.info("research_sharing_consent_revoked", extra={"user_id": user_id})

    return ConsentStatusResponse(
        consented=status.consented,
        consented_at=status.consented_at,
        revoked_at=status.revoked_at,
    )
