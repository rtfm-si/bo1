"""Terms & Conditions API endpoints.

Provides:
- GET /api/v1/terms/current - Get current active T&C version (public)
- GET /api/v1/user/terms-consent - Get user's consent status (authenticated)
- POST /api/v1/user/terms-consent - Record user consent (authenticated)
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.utils.errors import handle_api_errors
from bo1.state.repositories.terms_repository import terms_repository
from bo1.utils.logging import get_logger

logger = get_logger(__name__)


# --- Pydantic Models ---


class TermsVersionResponse(BaseModel):
    """Response model for T&C version."""

    id: str
    version: str
    content: str
    published_at: str
    is_active: bool


class ConsentHistoryItem(BaseModel):
    """Individual consent record in history."""

    policy_type: str = Field(..., description="Type of policy (e.g., 'Terms & Conditions')")
    version: str = Field(..., description="Version number consented to")
    consented_at: str = Field(..., description="ISO timestamp of consent")
    policy_url: str = Field(..., description="URL to policy page")


class ConsentStatusResponse(BaseModel):
    """Response model for consent status check."""

    has_consented: bool
    current_version: str | None = None
    consented_version: str | None = None
    consented_at: str | None = None
    consents: list[ConsentHistoryItem] = Field(
        default_factory=list, description="Full consent history"
    )


class ConsentRecordResponse(BaseModel):
    """Response model for consent record."""

    id: str
    terms_version_id: str
    consented_at: str
    message: str = "Consent recorded successfully"


class ConsentRequest(BaseModel):
    """Request model for recording consent."""

    terms_version_id: str = Field(..., description="UUID of T&C version being accepted")


# --- Routers ---

terms_router = APIRouter(prefix="/v1/terms", tags=["terms"])
user_terms_router = APIRouter(prefix="/v1/user", tags=["user"])


@terms_router.get(
    "/current",
    response_model=TermsVersionResponse,
    summary="Get current T&C version",
    description="Returns the currently active Terms & Conditions version. Public endpoint.",
)
@handle_api_errors("get current terms")
async def get_current_terms() -> TermsVersionResponse:
    """Get the currently active T&C version."""
    version = terms_repository.get_active_version()
    if not version:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "No active T&C version found"},
        )

    return TermsVersionResponse(
        id=str(version["id"]),
        version=version["version"],
        content=version["content"],
        published_at=version["published_at"].isoformat(),
        is_active=version["is_active"],
    )


@user_terms_router.get(
    "/terms-consent",
    response_model=ConsentStatusResponse,
    summary="Get consent status",
    description="Check if user has consented to current T&C version, with full consent history.",
)
@handle_api_errors("get consent status")
async def get_consent_status(
    user: dict[str, Any] = Depends(get_current_user),
) -> ConsentStatusResponse:
    """Check user's consent status for current T&C version."""
    user_id = user["user_id"]

    # Get current active version
    current_version = terms_repository.get_active_version()
    if not current_version:
        return ConsentStatusResponse(
            has_consented=True,  # No T&C to consent to
            current_version=None,
        )

    # Check if user has consented
    has_consented = terms_repository.has_user_consented_to_current(user_id)

    # Get latest consent info if exists
    latest_consent = terms_repository.get_user_latest_consent(user_id)

    # Get full consent history
    all_consents = terms_repository.get_user_consents(user_id)
    consent_history = [
        ConsentHistoryItem(
            policy_type="Terms & Conditions",
            version=c["terms_version"],
            consented_at=c["consented_at"].isoformat(),
            policy_url="/legal/terms",
        )
        for c in all_consents
    ]

    return ConsentStatusResponse(
        has_consented=has_consented,
        current_version=current_version["version"],
        consented_version=latest_consent["terms_version"] if latest_consent else None,
        consented_at=latest_consent["consented_at"].isoformat() if latest_consent else None,
        consents=consent_history,
    )


@user_terms_router.post(
    "/terms-consent",
    response_model=ConsentRecordResponse,
    summary="Record consent",
    description="Record user's consent to a specific T&C version.",
)
@handle_api_errors("record consent")
async def record_consent(
    request: Request,
    body: ConsentRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> ConsentRecordResponse:
    """Record user's consent to T&C version."""
    user_id = user["user_id"]

    # Validate version exists
    version = terms_repository.get_version_by_id(body.terms_version_id)
    if not version:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "T&C version not found"},
        )

    # Get client IP (X-Forwarded-For if behind proxy, otherwise direct)
    ip_address = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not ip_address:
        ip_address = request.client.host if request.client else None

    # Record consent
    consent = terms_repository.create_consent(
        user_id=user_id,
        version_id=body.terms_version_id,
        ip_address=ip_address,
    )

    logger.info(f"T&C consent recorded: user={user_id} version={version['version']}")

    return ConsentRecordResponse(
        id=str(consent["id"]),
        terms_version_id=str(consent["terms_version_id"]),
        consented_at=consent["consented_at"].isoformat(),
    )
