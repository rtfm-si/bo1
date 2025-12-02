"""Admin API endpoints for beta whitelist management.

Provides:
- GET /api/admin/beta-whitelist - List all whitelisted emails
- POST /api/admin/beta-whitelist - Add email to whitelist
- DELETE /api/admin/beta-whitelist/{email} - Remove email from whitelist
"""

import os

from fastapi import APIRouter, Depends, HTTPException

from backend.api.admin.models import (
    AddWhitelistRequest,
    BetaWhitelistEntry,
    BetaWhitelistResponse,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.models import ControlResponse, ErrorResponse
from bo1.state.postgres_manager import db_session
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
async def list_beta_whitelist(
    _admin: str = Depends(require_admin_any),
) -> BetaWhitelistResponse:
    """List all whitelisted emails for closed beta.

    Returns all emails in the beta whitelist (database + env var).

    Args:
        _admin: Admin user ID or "api_key" (injected by dependency)

    Returns:
        BetaWhitelistResponse with database entries and env emails

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # Get env-based whitelist
        env_whitelist = os.getenv("BETA_WHITELIST", "")
        env_emails = [e.strip().lower() for e in env_whitelist.split(",") if e.strip()]

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, email, added_by, notes, created_at
                    FROM beta_whitelist
                    ORDER BY created_at DESC
                    """
                )
                rows = cur.fetchall()

                entries = [
                    BetaWhitelistEntry(
                        id=str(row["id"]),
                        email=row["email"],
                        added_by=row["added_by"],
                        notes=row["notes"],
                        created_at=row["created_at"].isoformat() if row["created_at"] else "",
                    )
                    for row in rows
                ]

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
            env_emails=env_emails,  # Return all env emails (UI can show which are duplicates)
        )

    except Exception as e:
        logger.error(f"Admin: Failed to list beta whitelist: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list beta whitelist: {str(e)}",
        ) from e


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
async def add_to_beta_whitelist(
    request: AddWhitelistRequest,
    _admin: str = Depends(require_admin_any),
) -> BetaWhitelistEntry:
    """Add email to beta whitelist.

    Args:
        request: Email and optional notes
        _admin_key: Admin API key (injected by dependency)

    Returns:
        BetaWhitelistEntry with created entry

    Raises:
        HTTPException: If email is invalid or already exists
    """
    try:
        # Normalize email
        email = request.email.strip().lower()

        # Simple email validation
        if "@" not in email or "." not in email.split("@")[1]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid email address: {email}",
            )

        with db_session() as conn:
            with conn.cursor() as cur:
                # Check if email already exists
                cur.execute("SELECT id FROM beta_whitelist WHERE email = %s", (email,))
                if cur.fetchone():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Email already whitelisted: {email}",
                    )

                # Insert new entry
                cur.execute(
                    """
                    INSERT INTO beta_whitelist (email, added_by, notes)
                    VALUES (%s, %s, %s)
                    RETURNING id, email, added_by, notes, created_at
                    """,
                    (email, "admin", request.notes),
                )
                row = cur.fetchone()

        entry = BetaWhitelistEntry(
            id=str(row["id"]),
            email=row["email"],
            added_by=row["added_by"],
            notes=row["notes"],
            created_at=row["created_at"].isoformat() if row["created_at"] else "",
        )

        logger.info(f"Admin: Added {email} to beta whitelist")

        return entry

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin: Failed to add {request.email} to beta whitelist: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add email to beta whitelist: {str(e)}",
        ) from e


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
async def remove_from_beta_whitelist(
    email: str,
    _admin: str = Depends(require_admin_any),
) -> ControlResponse:
    """Remove email from beta whitelist.

    Args:
        email: Email address to remove
        _admin_key: Admin API key (injected by dependency)

    Returns:
        ControlResponse with removal confirmation

    Raises:
        HTTPException: If email not found or removal fails
    """
    try:
        # Normalize email
        email = email.strip().lower()

        with db_session() as conn:
            with conn.cursor() as cur:
                # Delete email
                cur.execute("DELETE FROM beta_whitelist WHERE email = %s RETURNING id", (email,))
                row = cur.fetchone()

                if not row:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Email not found in whitelist: {email}",
                    )

        logger.info(f"Admin: Removed {email} from beta whitelist")

        return ControlResponse(
            session_id=str(row["id"]),  # Using session_id field for whitelist ID
            action="remove_whitelist",
            status="success",
            message=f"Removed {email} from beta whitelist",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin: Failed to remove {email} from beta whitelist: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove email from beta whitelist: {str(e)}",
        ) from e
