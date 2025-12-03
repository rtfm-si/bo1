"""Admin API endpoints for waitlist management.

Provides:
- GET /api/admin/waitlist - List all waitlist entries
- POST /api/admin/waitlist/{email}/approve - Approve waitlist entry
"""

from fastapi import APIRouter, Depends, Query

from backend.api.admin.helpers import (
    AdminApprovalService,
    _row_to_waitlist_entry,
)
from backend.api.admin.models import (
    ApproveWaitlistResponse,
    WaitlistResponse,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.models import ErrorResponse
from backend.api.utils.errors import handle_api_errors
from bo1.state.postgres_manager import db_session
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["Admin - Waitlist"])


@router.get(
    "/waitlist",
    response_model=WaitlistResponse,
    summary="List all waitlist entries",
    description="Get list of all emails on the waitlist with their status.",
    responses={
        200: {"description": "Waitlist retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("list waitlist")
async def list_waitlist(
    status: str | None = Query(None, description="Filter by status (pending, invited, converted)"),
    _admin: str = Depends(require_admin_any),
) -> WaitlistResponse:
    """List all waitlist entries."""
    with db_session() as conn:
        with conn.cursor() as cur:
            # Get total and pending counts
            cur.execute("SELECT COUNT(*) FROM waitlist")
            total_row = cur.fetchone()
            total_count = total_row["count"] if total_row else 0

            cur.execute("SELECT COUNT(*) FROM waitlist WHERE status = 'pending'")
            pending_row = cur.fetchone()
            pending_count = pending_row["count"] if pending_row else 0

            # Get entries with optional status filter
            if status:
                cur.execute(
                    """
                    SELECT id, email, status, source, notes, created_at
                    FROM waitlist
                    WHERE status = %s
                    ORDER BY created_at DESC
                    """,
                    (status,),
                )
            else:
                cur.execute(
                    """
                    SELECT id, email, status, source, notes, created_at
                    FROM waitlist
                    ORDER BY created_at DESC
                    """
                )
            rows = cur.fetchall()
            entries = [_row_to_waitlist_entry(row) for row in rows]

    logger.info(f"Admin: Listed {len(entries)} waitlist entries (total: {total_count})")

    return WaitlistResponse(
        total_count=total_count,
        pending_count=pending_count,
        entries=entries,
    )


@router.post(
    "/waitlist/{email}/approve",
    response_model=ApproveWaitlistResponse,
    summary="Approve waitlist entry",
    description="Approve a waitlist entry - adds to beta whitelist and sends welcome email.",
    responses={
        200: {"description": "Waitlist entry approved successfully"},
        400: {"description": "Email already approved or not on waitlist", "model": ErrorResponse},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("approve waitlist entry")
async def approve_waitlist_entry(
    email: str,
    _admin: str = Depends(require_admin_any),
) -> ApproveWaitlistResponse:
    """Approve a waitlist entry."""
    result = AdminApprovalService.approve_waitlist_entry(email)
    logger.info(f"Admin: {result.message}")

    return ApproveWaitlistResponse(
        email=result.email,
        whitelist_added=result.whitelist_added,
        email_sent=result.email_sent,
        message=result.message,
    )
