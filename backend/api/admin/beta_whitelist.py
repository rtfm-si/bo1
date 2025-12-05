"""Admin API endpoints for beta whitelist management.

Provides:
- GET /api/admin/beta-whitelist - List all whitelisted emails
- POST /api/admin/beta-whitelist - Add email to whitelist
- DELETE /api/admin/beta-whitelist/{email} - Remove email from whitelist
"""

import os

from fastapi import APIRouter, Depends, HTTPException

from backend.api.admin.helpers import (
    AdminValidationService,
    _row_to_whitelist_entry,
)
from backend.api.admin.models import (
    AddWhitelistRequest,
    BetaWhitelistEntry,
    BetaWhitelistResponse,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.models import ControlResponse, ErrorResponse
from backend.api.utils.db_helpers import execute_query, exists
from backend.api.utils.errors import handle_api_errors
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["Admin - Beta Whitelist"])


@router.get(
    "/beta-whitelist",
    response_model=BetaWhitelistResponse,
    summary="List all whitelisted emails",
    description="Get list of all emails whitelisted for closed beta access (admin only).",
    responses={
        200: {"description": "Whitelist retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("list beta whitelist")
async def list_beta_whitelist(
    _admin: str = Depends(require_admin_any),
) -> BetaWhitelistResponse:
    """List all whitelisted emails for closed beta."""
    # Get env-based whitelist
    env_whitelist = os.getenv("BETA_WHITELIST", "")
    env_emails = [e.strip().lower() for e in env_whitelist.split(",") if e.strip()]

    rows = execute_query(
        """
        SELECT id, email, added_by, notes, created_at
        FROM beta_whitelist
        ORDER BY created_at DESC
        """,
        fetch="all",
    )
    entries = [_row_to_whitelist_entry(row) for row in rows]

    # Get unique db emails for deduplication
    db_emails = {e.email.lower() for e in entries}
    # Only count env emails not already in db
    unique_env_emails = [e for e in env_emails if e not in db_emails]

    total_count = len(entries) + len(unique_env_emails)

    logger.info(
        f"Admin: Retrieved {len(entries)} db + {len(unique_env_emails)} env whitelist entries"
    )

    return BetaWhitelistResponse(
        total_count=total_count,
        emails=entries,
        env_emails=env_emails,
    )


@router.post(
    "/beta-whitelist",
    response_model=BetaWhitelistEntry,
    summary="Add email to whitelist",
    description="Add email address to closed beta whitelist (admin only).",
    responses={
        200: {"description": "Email added to whitelist successfully"},
        400: {"description": "Invalid email or already exists", "model": ErrorResponse},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("add to beta whitelist")
async def add_to_beta_whitelist(
    request: AddWhitelistRequest,
    _admin: str = Depends(require_admin_any),
) -> BetaWhitelistEntry:
    """Add email to beta whitelist."""
    # Validate and normalize email
    email = AdminValidationService.validate_email(request.email)

    # Check if email already exists
    if exists("beta_whitelist", where="email = %s", params=(email,)):
        raise HTTPException(
            status_code=400,
            detail=f"Email already whitelisted: {email}",
        )

    # Insert new entry
    row = execute_query(
        """
        INSERT INTO beta_whitelist (email, added_by, notes)
        VALUES (%s, %s, %s)
        RETURNING id, email, added_by, notes, created_at
        """,
        (email, "admin", request.notes),
        fetch="one",
    )

    entry = _row_to_whitelist_entry(row)
    logger.info(f"Admin: Added {email} to beta whitelist")
    return entry


@router.delete(
    "/beta-whitelist/{email}",
    response_model=ControlResponse,
    summary="Remove email from whitelist",
    description="Remove email address from closed beta whitelist (admin only).",
    responses={
        200: {"description": "Email removed from whitelist successfully"},
        404: {"description": "Email not found in whitelist", "model": ErrorResponse},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("remove from beta whitelist")
async def remove_from_beta_whitelist(
    email: str,
    _admin: str = Depends(require_admin_any),
) -> ControlResponse:
    """Remove email from beta whitelist."""
    # Normalize email
    email = email.strip().lower()

    # Delete email
    row = execute_query(
        "DELETE FROM beta_whitelist WHERE email = %s RETURNING id",
        (email,),
        fetch="one",
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Email not found in whitelist: {email}",
        )

    logger.info(f"Admin: Removed {email} from beta whitelist")

    return ControlResponse(
        session_id=str(row["id"]),
        action="remove_whitelist",
        status="success",
        message=f"Removed {email} from beta whitelist",
    )
