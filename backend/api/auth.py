"""Authentication endpoints for SuperTokens OAuth.

Provides:
- OAuth provider endpoints (automatically handled by SuperTokens middleware)
- Session verification
- User info retrieval

SuperTokens automatically exposes these endpoints under /api/auth:
- GET /api/auth/authorisationurl - Get OAuth authorization URL
- POST /api/auth/signinup - Complete OAuth flow
- POST /api/auth/signout - Sign out user
"""

import logging
import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from backend.api.middleware.rate_limit import AUTH_RATE_LIMIT, limiter
from backend.api.utils.errors import handle_api_errors
from backend.services.email import send_email_async
from backend.services.email_templates import render_verification_email
from bo1.state.repositories import user_repository
from bo1.state.repositories.auth_provider_repository import auth_provider_repository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me")
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("get user info")
async def get_user_info(
    request: Request, session: SessionContainer = Depends(verify_session())
) -> dict:
    """Get current authenticated user information.

    Fetches user data from PostgreSQL (source of truth for persistent data).
    If user not found in DB, returns minimal data from session.

    When admin is impersonating another user:
    - Returns target user's data (id, email, subscription_tier)
    - Adds impersonation metadata (is_impersonation, real_admin_id, impersonation_write_mode)

    Returns:
        User ID, email, auth provider, subscription tier, session info,
        and impersonation metadata if applicable
    """
    user_id = session.get_user_id()
    session_handle = session.get_handle()

    # Check if admin is impersonating another user
    is_impersonation = getattr(request.state, "is_impersonation", False)
    impersonation_target_id = getattr(request.state, "impersonation_target_id", None)
    impersonation_write_mode = getattr(request.state, "impersonation_write_mode", False)
    impersonation_admin_id = getattr(request.state, "impersonation_admin_id", None)

    # If impersonating, fetch target user's data instead
    effective_user_id = impersonation_target_id if is_impersonation else user_id

    logger.info(
        f"User info requested: user_id={user_id}, session={session_handle}"
        + (f", impersonating={impersonation_target_id}" if is_impersonation else "")
    )

    # Fetch complete user data from PostgreSQL
    user_data = user_repository.get(effective_user_id)

    if user_data:
        response = {
            "id": user_data["id"],
            "user_id": user_data["id"],
            "email": user_data["email"],
            "auth_provider": user_data["auth_provider"],
            "subscription_tier": user_data["subscription_tier"],
            "is_admin": user_data.get("is_admin", False),
            "password_upgrade_needed": user_data.get("password_upgrade_needed", False),
            "totp_enabled": user_data.get("totp_enabled", False),
            "session_handle": session_handle,
        }

        # Add impersonation metadata if active
        if is_impersonation and impersonation_admin_id:
            # Use cached session from middleware to avoid duplicate DB query
            imp_session = getattr(request.state, "impersonation_session_cached", None)
            response["is_impersonation"] = True
            response["real_admin_id"] = impersonation_admin_id
            response["impersonation_write_mode"] = impersonation_write_mode
            if imp_session:
                remaining = int((imp_session.expires_at - datetime.now(UTC)).total_seconds())
                response["impersonation_expires_at"] = imp_session.expires_at.isoformat()
                response["impersonation_remaining_seconds"] = max(0, remaining)

        return response

    # Fallback if user not in database (shouldn't happen with proper sync)
    logger.warning(f"User {effective_user_id} not found in PostgreSQL, returning minimal data")
    response = {
        "id": effective_user_id,
        "user_id": effective_user_id,
        "email": None,
        "auth_provider": None,
        "subscription_tier": "free",
        "is_admin": False,
        "password_upgrade_needed": False,
        "totp_enabled": False,
        "session_handle": session_handle,
    }

    # Add impersonation metadata if active
    if is_impersonation and impersonation_admin_id:
        # Use cached session from middleware to avoid duplicate DB query
        imp_session = getattr(request.state, "impersonation_session_cached", None)
        response["is_impersonation"] = True
        response["real_admin_id"] = impersonation_admin_id
        response["impersonation_write_mode"] = impersonation_write_mode
        if imp_session:
            remaining = int((imp_session.expires_at - datetime.now(UTC)).total_seconds())
            response["impersonation_expires_at"] = imp_session.expires_at.isoformat()
            response["impersonation_remaining_seconds"] = max(0, remaining)

    return response


# =============================================================================
# Email Verification Endpoints
# =============================================================================


@router.get("/verify-email")
@limiter.limit("10/minute")  # Prevent token enumeration
async def verify_email(request: Request, token: str) -> RedirectResponse:
    """Verify email address using token from verification email.

    This endpoint is called when user clicks the verification link in their email.
    On success, marks the email as verified and redirects to login with success message.
    On failure, redirects to login with error message.

    Args:
        request: FastAPI request object (for rate limiting)
        token: Verification token from email link

    Returns:
        Redirect to login page with appropriate message
    """
    frontend_url = os.getenv("SUPERTOKENS_WEBSITE_DOMAIN", "http://localhost:5173")

    # Get verification record
    record = auth_provider_repository.get_verification_by_token(token)

    if not record:
        logger.warning(f"Email verification failed: invalid token {token[:8]}...")
        return RedirectResponse(
            url=f"{frontend_url}/login?error=verification_invalid",
            status_code=302,
        )

    # Check if already verified
    if record.get("verified_at"):
        logger.info(f"Email verification: token already used for {record['email'][:3]}***")
        return RedirectResponse(
            url=f"{frontend_url}/login?message=email_already_verified",
            status_code=302,
        )

    # Check expiry
    expires_at = record["expires_at"]
    if isinstance(expires_at, str):
        from datetime import datetime

        expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

    if expires_at < datetime.now(UTC):
        logger.warning(f"Email verification failed: token expired for {record['email'][:3]}***")
        return RedirectResponse(
            url=f"{frontend_url}/login?error=verification_expired",
            status_code=302,
        )

    # Mark token as used and email as verified
    auth_provider_repository.mark_token_verified(token)
    auth_provider_repository.mark_email_verified(record["supertokens_user_id"])

    logger.info(f"Email verified successfully: {record['email'][:3]}***")

    # Redirect to login with success message
    return RedirectResponse(
        url=f"{frontend_url}/login?message=email_verified",
        status_code=302,
    )


@router.post("/resend-verification")
@limiter.limit("1/minute")  # Strict rate limit to prevent abuse
@handle_api_errors("resend verification")
async def resend_verification(request: Request, email: str) -> dict[str, str]:
    """Resend email verification link.

    Rate limited to 1 per minute per IP to prevent abuse.
    Returns same response regardless of whether email exists (prevent enumeration).

    Args:
        request: FastAPI request object (for rate limiting)
        email: Email address to resend verification to

    Returns:
        {"status": "ok"} always (don't reveal if email exists)
    """
    # Check rate limit at database level (1 per 60 seconds per email)
    if auth_provider_repository.check_recent_verification_sent(email, seconds=60):
        logger.info(f"Verification resend rate limited for {email[:3]}***")
        return {"status": "ok"}  # Don't reveal rate limit to prevent timing attacks

    # Find unverified email/password provider for this email
    provider = auth_provider_repository.get_unverified_by_email(email)

    if provider:
        try:
            # Create new verification token
            token = auth_provider_repository.create_verification_token(
                provider["supertokens_user_id"], email
            )
            frontend_url = os.getenv("SUPERTOKENS_WEBSITE_DOMAIN", "http://localhost:5173")
            verify_url = f"{frontend_url}/verify-email?token={token}"

            html, text = render_verification_email(verify_url)
            send_email_async(
                to=email,
                subject="Verify your email - Board of One",
                html=html,
                text=text,
            )
            logger.info(f"Verification email resent to {email[:3]}***")
        except Exception as e:
            # Don't reveal errors to prevent information disclosure
            logger.warning(f"Failed to resend verification email: {e}")

    # Always return success to prevent email enumeration
    return {"status": "ok"}
