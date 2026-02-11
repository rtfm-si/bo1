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
from backend.api.utils.auth_helpers import extract_user_id
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

    policy_type: str = Field(..., description="Policy type code ('tc', 'gdpr', 'privacy')")
    policy_label: str = Field(..., description="Display name (e.g., 'Terms & Conditions')")
    version: str = Field(..., description="Version number consented to")
    consented_at: str = Field(..., description="ISO timestamp of consent")
    policy_url: str = Field(..., description="URL to policy page")


# Policy type configuration
POLICY_CONFIG = {
    "tc": {"label": "Terms & Conditions", "url": "/legal/terms"},
    "gdpr": {"label": "GDPR Data Processing", "url": "/legal/privacy#gdpr"},
    "privacy": {"label": "Privacy Policy", "url": "/legal/privacy"},
}


class PolicyConsentStatus(BaseModel):
    """Consent status for a single policy."""

    policy_type: str
    policy_label: str
    policy_url: str
    has_consented: bool
    version: str | None = None
    consented_at: str | None = None


class ConsentStatusResponse(BaseModel):
    """Response model for consent status check."""

    has_consented: bool = Field(..., description="True if all required policies consented")
    missing_policies: list[str] = Field(
        default_factory=list, description="Policy types still needing consent"
    )
    current_version: str | None = None
    consented_version: str | None = None
    consented_at: str | None = None
    policies: list[PolicyConsentStatus] = Field(
        default_factory=list, description="Status of each policy type"
    )
    consents: list[ConsentHistoryItem] = Field(
        default_factory=list, description="Full consent history"
    )


class ConsentRecordResponse(BaseModel):
    """Response model for consent record."""

    id: str
    terms_version_id: str
    policy_type: str
    consented_at: str
    message: str = "Consent recorded successfully"


class ConsentRequest(BaseModel):
    """Request model for recording consent."""

    terms_version_id: str = Field(..., description="UUID of T&C version being accepted")
    policy_type: str = Field(default="tc", description="Policy type: 'tc', 'gdpr', or 'privacy'")


class MultiConsentRequest(BaseModel):
    """Request model for recording multiple policy consents at once."""

    terms_version_id: str = Field(..., description="UUID of T&C version")
    policy_types: list[str] = Field(
        ..., description="List of policy types to consent to (e.g., ['tc', 'gdpr', 'privacy'])"
    )


class MultiConsentResponse(BaseModel):
    """Response model for multiple consent records."""

    consents: list[ConsentRecordResponse]
    message: str = "All consents recorded successfully"


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
    description="Check if user has consented to all required policies, with full consent history.",
)
@handle_api_errors("get consent status")
async def get_consent_status(
    user: dict[str, Any] = Depends(get_current_user),
) -> ConsentStatusResponse:
    """Check user's consent status for all required policies."""
    user_id = extract_user_id(user)

    # Get current active version
    current_version = terms_repository.get_active_version()
    if not current_version:
        return ConsentStatusResponse(
            has_consented=True,  # No T&C to consent to
            current_version=None,
            policies=[],
            consents=[],
        )

    # Check all policies
    all_policy_consents = terms_repository.get_user_all_policy_consents(user_id)
    missing_policies = terms_repository.get_missing_policies(user_id)
    has_all_consented = len(missing_policies) == 0

    # Build per-policy status
    policies = []
    for policy_type, config in POLICY_CONFIG.items():
        consent = all_policy_consents.get(policy_type)
        policies.append(
            PolicyConsentStatus(
                policy_type=policy_type,
                policy_label=config["label"],
                policy_url=config["url"],
                has_consented=consent is not None,
                version=consent["terms_version"] if consent else None,
                consented_at=consent["consented_at"].isoformat() if consent else None,
            )
        )

    # Get latest T&C consent for backwards compat
    latest_tc_consent = all_policy_consents.get("tc")

    # Get full consent history
    all_consents = terms_repository.get_user_consents(user_id)
    consent_history = [
        ConsentHistoryItem(
            policy_type=c.get("policy_type", "tc"),
            policy_label=POLICY_CONFIG.get(c.get("policy_type", "tc"), {}).get("label", "Unknown"),
            version=c["terms_version"],
            consented_at=c["consented_at"].isoformat(),
            policy_url=POLICY_CONFIG.get(c.get("policy_type", "tc"), {}).get("url", "/legal/terms"),
        )
        for c in all_consents
    ]

    return ConsentStatusResponse(
        has_consented=has_all_consented,
        missing_policies=missing_policies,
        current_version=current_version["version"],
        consented_version=latest_tc_consent["terms_version"] if latest_tc_consent else None,
        consented_at=latest_tc_consent["consented_at"].isoformat() if latest_tc_consent else None,
        policies=policies,
        consents=consent_history,
    )


@user_terms_router.post(
    "/terms-consent",
    response_model=ConsentRecordResponse,
    summary="Record consent",
    description="Record user's consent to a specific policy version.",
)
@handle_api_errors("record consent")
async def record_consent(
    request: Request,
    body: ConsentRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> ConsentRecordResponse:
    """Record user's consent to a policy version."""
    user_id = extract_user_id(user)

    # Validate policy type
    if body.policy_type not in POLICY_CONFIG:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_policy_type",
                "message": f"Invalid policy type: {body.policy_type}. Must be one of: tc, gdpr, privacy",
            },
        )

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
        policy_type=body.policy_type,
    )

    logger.info(
        f"Consent recorded: user={user_id} policy={body.policy_type} version={version['version']}"
    )

    return ConsentRecordResponse(
        id=str(consent["id"]),
        terms_version_id=str(consent["terms_version_id"]),
        policy_type=consent["policy_type"],
        consented_at=consent["consented_at"].isoformat(),
    )


@user_terms_router.post(
    "/terms-consent/batch",
    response_model=MultiConsentResponse,
    summary="Record multiple consents",
    description="Record user's consent to multiple policies at once (T&C, GDPR, Privacy).",
)
@handle_api_errors("record multi consent")
async def record_multi_consent(
    request: Request,
    body: MultiConsentRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> MultiConsentResponse:
    """Record user's consent to multiple policies at once."""
    user_id = extract_user_id(user)

    # Validate all policy types
    for pt in body.policy_types:
        if pt not in POLICY_CONFIG:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_policy_type",
                    "message": f"Invalid policy type: {pt}. Must be one of: tc, gdpr, privacy",
                },
            )

    # Validate version exists
    version = terms_repository.get_version_by_id(body.terms_version_id)
    if not version:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "T&C version not found"},
        )

    # Get client IP
    ip_address = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not ip_address:
        ip_address = request.client.host if request.client else None

    # Record all consents
    recorded = []
    for policy_type in body.policy_types:
        consent = terms_repository.create_consent(
            user_id=user_id,
            version_id=body.terms_version_id,
            ip_address=ip_address,
            policy_type=policy_type,
        )
        recorded.append(
            ConsentRecordResponse(
                id=str(consent["id"]),
                terms_version_id=str(consent["terms_version_id"]),
                policy_type=consent["policy_type"],
                consented_at=consent["consented_at"].isoformat(),
            )
        )

    logger.info(
        f"Multi-consent recorded: user={user_id} policies={body.policy_types} version={version['version']}"
    )

    return MultiConsentResponse(consents=recorded)
