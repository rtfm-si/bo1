"""Waitlist management endpoints for closed beta.

Handles:
- Email capture for waitlist
- Whitelist checking for closed beta access
- Duplicate prevention
"""

import logging
import os
import re
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from backend.api.utils.db_helpers import execute_query, exists
from backend.api.utils.errors import handle_api_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/waitlist", tags=["waitlist"])

# Email whitelist (move to database/environment variable in production)
BETA_WHITELIST = os.getenv("BETA_WHITELIST", "").split(",")


class WaitlistRequest(BaseModel):
    """Waitlist signup request."""

    email: EmailStr = Field(..., description="Email address to add to waitlist")


class WaitlistResponse(BaseModel):
    """Waitlist signup response."""

    status: Literal["added", "already_exists", "whitelisted"]
    message: str
    is_whitelisted: bool = False


def is_valid_email(email: str) -> bool:
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


async def _send_waitlist_notification(email: str) -> None:
    """Send ntfy notification for waitlist signup (background task)."""
    try:
        from backend.api.ntfy import notify_waitlist_signup

        await notify_waitlist_signup(email)
    except Exception as e:
        logger.warning(f"Failed to send waitlist notification for {email}: {e}")


def is_whitelisted(email: str) -> bool:
    """Check if email is in closed beta whitelist (env OR database)."""
    email_lower = email.lower()

    # Check env-based whitelist first (fast)
    if email_lower in [e.strip().lower() for e in BETA_WHITELIST if e.strip()]:
        return True

    # Check database whitelist
    try:
        return exists(
            "beta_whitelist",
            where="LOWER(email) = %s",
            params=(email_lower,),
        )
    except Exception:
        return False  # Fail closed - if DB error, don't grant access


@router.post("", response_model=WaitlistResponse, status_code=status.HTTP_200_OK)
@handle_api_errors("add to waitlist")
async def add_to_waitlist(
    request: WaitlistRequest, background_tasks: BackgroundTasks
) -> WaitlistResponse:
    """Add email to waitlist.

    Args:
        request: Waitlist signup request with email
        background_tasks: FastAPI background tasks for async notifications

    Returns:
        WaitlistResponse with status and message

    Raises:
        HTTPException: If database operation fails
    """
    email = request.email.lower()  # Normalize email

    # Validate email format
    if not is_valid_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address format",
        )

    # Check if already whitelisted
    if is_whitelisted(email):
        return WaitlistResponse(
            status="whitelisted",
            message="You're already on the whitelist! Sign up to get started.",
            is_whitelisted=True,
        )

    # Check for duplicate
    existing = execute_query(
        "SELECT id, status FROM waitlist WHERE email = %s",
        (email,),
        fetch="one",
    )

    if existing:
        return WaitlistResponse(
            status="already_exists",
            message="You're already on the waitlist! We'll notify you when you're in.",
        )

    # Insert new waitlist entry
    execute_query(
        """
        INSERT INTO waitlist (email, status, created_at)
        VALUES (%s, %s, %s)
        """,
        (email, "pending", datetime.now(UTC)),
        fetch="none",
    )

    # Send ntfy notification in background
    background_tasks.add_task(_send_waitlist_notification, email)

    return WaitlistResponse(
        status="added",
        message="Success! Check your email for next steps.",
    )


@router.post("/check", response_model=dict[str, bool])
@handle_api_errors("check whitelist")
async def check_whitelist(request: WaitlistRequest) -> dict[str, bool]:
    """Check if email is whitelisted for closed beta.

    Args:
        request: Request with email to check

    Returns:
        Dict with is_whitelisted boolean
    """
    return {"is_whitelisted": is_whitelisted(request.email.lower())}
