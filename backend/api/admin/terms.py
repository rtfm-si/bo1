"""Admin API endpoints for T&C version management and consent audit.

Provides:
- T&C version CRUD (list, create, update, publish)
- Consent audit with time-period filtering
"""

from fastapi import APIRouter, Depends, Query, Request

from backend.api.admin.models import (
    ConsentAuditItem,
    ConsentAuditResponse,
    CreateTermsVersionRequest,
    TermsVersionItem,
    TermsVersionListResponse,
    TimePeriod,
    UpdateTermsVersionRequest,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.models import ErrorResponse
from backend.api.utils.errors import handle_api_errors, http_error
from backend.api.utils.pagination import make_pagination_fields
from bo1.logging import ErrorCode
from bo1.state.repositories.terms_repository import terms_repository
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/terms", tags=["Admin - Terms"])


def _get_consent_time_filter(period: TimePeriod) -> str:
    """Convert time period to SQL interval filter for consented_at.

    Args:
        period: Time period enum value

    Returns:
        SQL WHERE clause fragment for filtering by consented_at
    """
    if period == TimePeriod.ALL:
        return "TRUE"

    intervals = {
        TimePeriod.HOUR: "1 hour",
        TimePeriod.DAY: "1 day",
        TimePeriod.WEEK: "7 days",
        TimePeriod.MONTH: "30 days",
    }
    interval = intervals[period]
    return f"tc.consented_at >= (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - INTERVAL '{interval}'"


def _to_iso(value: object) -> str:
    """Convert datetime to ISO format string."""
    return value.isoformat() if value else ""


# ==============================================================================
# Version Management Endpoints
# ==============================================================================


@router.get(
    "/versions",
    response_model=TermsVersionListResponse,
    summary="List T&C versions",
    description="Get paginated list of all T&C versions (drafts and published).",
    responses={
        200: {"description": "Versions retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("list terms versions")
async def list_terms_versions(
    request: Request,
    limit: int = Query(50, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    _admin: str = Depends(require_admin_any),
) -> TermsVersionListResponse:
    """Get paginated list of T&C versions."""
    records, total = terms_repository.get_all_versions(limit=limit, offset=offset)

    items = [
        TermsVersionItem(
            id=str(row["id"]),
            version=row["version"],
            content=row["content"],
            is_active=row["is_active"],
            published_at=_to_iso(row["published_at"]) if row["published_at"] else None,
            created_at=_to_iso(row["created_at"]),
        )
        for row in records
    ]

    pagination = make_pagination_fields(total, limit, offset)
    logger.info(f"Admin: Retrieved {len(items)} T&C versions")

    return TermsVersionListResponse(items=items, **pagination)


@router.post(
    "/versions",
    response_model=TermsVersionItem,
    summary="Create T&C version",
    description="Create a new T&C version as a draft.",
    responses={
        200: {"description": "Version created successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        409: {"description": "Version string already exists", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("create terms version")
async def create_terms_version(
    request: Request,
    body: CreateTermsVersionRequest,
    _admin: str = Depends(require_admin_any),
) -> TermsVersionItem:
    """Create a new draft T&C version."""
    try:
        record = terms_repository.create_version(
            version=body.version,
            content=body.content,
            is_active=False,
        )
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise http_error(
                ErrorCode.VALIDATION_ERROR,
                f"Version '{body.version}' already exists",
                status=409,
            ) from e
        raise

    logger.info(f"Admin: Created T&C version {body.version} (draft)")

    return TermsVersionItem(
        id=str(record["id"]),
        version=record["version"],
        content=record["content"],
        is_active=record["is_active"],
        published_at=_to_iso(record["published_at"]) if record["published_at"] else None,
        created_at=_to_iso(record["created_at"]),
    )


@router.put(
    "/versions/{version_id}",
    response_model=TermsVersionItem,
    summary="Update draft T&C version",
    description="Update content of a draft T&C version. Cannot update published versions.",
    responses={
        200: {"description": "Version updated successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        404: {"description": "Version not found or already published", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("update terms version")
async def update_terms_version(
    request: Request,
    version_id: str,
    body: UpdateTermsVersionRequest,
    _admin: str = Depends(require_admin_any),
) -> TermsVersionItem:
    """Update a draft T&C version's content."""
    record = terms_repository.update_version(version_id=version_id, content=body.content)

    if not record:
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            "Version not found or already published (cannot edit active versions)",
            status=404,
        )

    logger.info(f"Admin: Updated T&C version {version_id}")

    return TermsVersionItem(
        id=str(record["id"]),
        version=record["version"],
        content=record["content"],
        is_active=record["is_active"],
        published_at=_to_iso(record["published_at"]) if record["published_at"] else None,
        created_at=_to_iso(record["created_at"]),
    )


@router.post(
    "/versions/{version_id}/publish",
    response_model=TermsVersionItem,
    summary="Publish T&C version",
    description="Publish a T&C version, making it the active version. Deactivates previous active version.",
    responses={
        200: {"description": "Version published successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        404: {"description": "Version not found", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("publish terms version")
async def publish_terms_version(
    request: Request,
    version_id: str,
    _admin: str = Depends(require_admin_any),
) -> TermsVersionItem:
    """Publish a T&C version (atomically deactivates previous active version)."""
    record = terms_repository.publish_version(version_id=version_id)

    if not record:
        raise http_error(ErrorCode.API_NOT_FOUND, "Version not found", status=404)

    logger.info(f"Admin: Published T&C version {record['version']} (id={version_id})")

    return TermsVersionItem(
        id=str(record["id"]),
        version=record["version"],
        content=record["content"],
        is_active=record["is_active"],
        published_at=_to_iso(record["published_at"]) if record["published_at"] else None,
        created_at=_to_iso(record["created_at"]),
    )


# ==============================================================================
# Consent Audit Endpoints
# ==============================================================================


@router.get(
    "/consents",
    response_model=ConsentAuditResponse,
    summary="List consent audit records",
    description="Get paginated list of user T&C consents with time period filtering.",
    responses={
        200: {"description": "Consent records retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get consent audit")
async def get_consent_audit(
    request: Request,
    period: TimePeriod = Query(TimePeriod.ALL, description="Time period filter"),
    limit: int = Query(50, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    _admin: str = Depends(require_admin_any),
) -> ConsentAuditResponse:
    """Get paginated list of T&C consent records."""
    time_filter = _get_consent_time_filter(period)

    records, total = terms_repository.get_all_consents(
        limit=limit,
        offset=offset,
        time_filter_sql=time_filter,
    )

    items = [
        ConsentAuditItem(
            user_id=row["user_id"],
            email=row.get("email"),
            terms_version=row["terms_version"],
            consented_at=_to_iso(row["consented_at"]),
            ip_address=row.get("ip_address"),
        )
        for row in records
    ]

    pagination = make_pagination_fields(total, limit, offset)
    logger.info(f"Admin: Retrieved {len(items)} consent records for period={period.value}")

    return ConsentAuditResponse(
        items=items,
        period=period.value,
        **pagination,
    )
