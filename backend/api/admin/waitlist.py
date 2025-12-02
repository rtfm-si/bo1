"""Admin API endpoints for waitlist management.

Provides:
- GET /api/admin/waitlist - List all waitlist entries
- POST /api/admin/waitlist/{email}/approve - Approve waitlist entry
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.admin.models import (
    ApproveWaitlistResponse,
    WaitlistEntry,
    WaitlistResponse,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.models import ErrorResponse
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
async def list_waitlist(
    status: str | None = Query(None, description="Filter by status (pending, invited, converted)"),
    _admin: str = Depends(require_admin_any),
) -> WaitlistResponse:
    """List all waitlist entries.

    Args:
        status: Optional status filter
        _admin: Admin user ID or "api_key" (injected by dependency)

    Returns:
        WaitlistResponse with all waitlist entries

    Raises:
        HTTPException: If retrieval fails
    """
    try:
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

                entries = [
                    WaitlistEntry(
                        id=str(row["id"]),
                        email=row["email"],
                        status=row["status"],
                        source=row["source"],
                        notes=row["notes"],
                        created_at=row["created_at"].isoformat() if row["created_at"] else "",
                    )
                    for row in rows
                ]

        logger.info(f"Admin: Listed {len(entries)} waitlist entries (total: {total_count})")

        return WaitlistResponse(
            total_count=total_count,
            pending_count=pending_count,
            entries=entries,
        )

    except Exception as e:
        logger.error(f"Admin: Failed to list waitlist: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list waitlist: {str(e)}",
        ) from e


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
async def approve_waitlist_entry(
    email: str,
    _admin: str = Depends(require_admin_any),
) -> ApproveWaitlistResponse:
    """Approve a waitlist entry.

    This endpoint:
    1. Checks if email is on the waitlist with pending status
    2. Adds email to beta_whitelist table
    3. Updates waitlist status to 'invited'
    4. Sends welcome email via Resend

    Args:
        email: Email address to approve
        _admin: Admin user ID or "api_key" (injected by dependency)

    Returns:
        ApproveWaitlistResponse with approval details

    Raises:
        HTTPException: If email not found, already approved, or operation fails
    """
    try:
        from backend.api.email import send_beta_welcome_email

        email = email.strip().lower()
        whitelist_added = False
        email_sent = False

        with db_session() as conn:
            with conn.cursor() as cur:
                # Check if email is on waitlist
                cur.execute(
                    "SELECT id, status FROM waitlist WHERE email = %s",
                    (email,),
                )
                waitlist_row = cur.fetchone()

                if not waitlist_row:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Email not found on waitlist: {email}",
                    )

                if waitlist_row["status"] == "invited":
                    raise HTTPException(
                        status_code=400,
                        detail=f"Email already approved: {email}",
                    )

                # Check if already on whitelist
                cur.execute(
                    "SELECT id FROM beta_whitelist WHERE email = %s",
                    (email,),
                )
                if cur.fetchone():
                    logger.info(f"Email {email} already on whitelist, skipping add")
                else:
                    # Add to whitelist
                    cur.execute(
                        """
                        INSERT INTO beta_whitelist (email, added_by, notes)
                        VALUES (%s, %s, %s)
                        """,
                        (email, "admin", "Approved from waitlist"),
                    )
                    whitelist_added = True
                    logger.info(f"Added {email} to beta whitelist")

                # Update waitlist status
                cur.execute(
                    """
                    UPDATE waitlist
                    SET status = 'invited', updated_at = NOW()
                    WHERE email = %s
                    """,
                    (email,),
                )

        # Send welcome email (outside transaction)
        result = send_beta_welcome_email(email)
        email_sent = result is not None

        message_parts = []
        if whitelist_added:
            message_parts.append("added to whitelist")
        else:
            message_parts.append("already on whitelist")
        if email_sent:
            message_parts.append("welcome email sent")
        else:
            message_parts.append("email not sent (check RESEND_API_KEY)")

        message = f"Approved {email}: {', '.join(message_parts)}"
        logger.info(f"Admin: {message}")

        return ApproveWaitlistResponse(
            email=email,
            whitelist_added=whitelist_added,
            email_sent=email_sent,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin: Failed to approve {email}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to approve waitlist entry: {str(e)}",
        ) from e
