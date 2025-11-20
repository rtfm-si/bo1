"""Waitlist management endpoints for closed beta.

Handles:
- Email capture for waitlist
- Whitelist checking for closed beta access
- Duplicate prevention
"""

import os
import re
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from bo1.state.postgres_manager import db_session

router = APIRouter(prefix="/waitlist", tags=["waitlist"])

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


def is_whitelisted(email: str) -> bool:
    """Check if email is in closed beta whitelist."""
    return email.lower() in [e.strip().lower() for e in BETA_WHITELIST if e.strip()]


@router.post("", response_model=WaitlistResponse, status_code=status.HTTP_200_OK)
async def add_to_waitlist(request: WaitlistRequest) -> WaitlistResponse:
    """Add email to waitlist.

    Args:
        request: Waitlist signup request with email

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

    # Check if already in waitlist
    try:
        with db_session() as conn:
            with conn.cursor() as cursor:
                # Check for duplicate
                cursor.execute("SELECT id, status FROM waitlist WHERE email = %s", (email,))
                existing = cursor.fetchone()

                if existing:
                    return WaitlistResponse(
                        status="already_exists",
                        message="You're already on the waitlist! We'll notify you when you're in.",
                    )

                # Insert new waitlist entry
                cursor.execute(
                    """
                    INSERT INTO waitlist (email, status, created_at)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (email, "pending", datetime.now(UTC)),
                )

                return WaitlistResponse(
                    status="added",
                    message="Success! Check your email for next steps.",
                )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add to waitlist: {str(e)}",
        ) from e


@router.post("/check", response_model=dict[str, bool])
async def check_whitelist(request: WaitlistRequest) -> dict[str, bool]:
    """Check if email is whitelisted for closed beta.

    Args:
        request: Request with email to check

    Returns:
        Dict with is_whitelisted boolean
    """
    return {"is_whitelisted": is_whitelisted(request.email.lower())}
