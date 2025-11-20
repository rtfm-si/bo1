"""OAuth authentication endpoints for Board of One API.

Handles Google OAuth flow:
1. User clicks "Sign in with Google" in frontend
2. Frontend redirects to Google OAuth
3. Google redirects to callback with code
4. Frontend sends code to /api/auth/google/callback
5. Backend exchanges code for user data, creates/updates user, returns JWT

For MVP: Google OAuth only (LinkedIn/GitHub deferred to v2.0)
"""

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from bo1.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# OAuth configuration
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:9999")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")


# Request/Response Models
class OAuthCallbackRequest(BaseModel):
    """Request model for OAuth callback."""

    code: str  # Authorization code from OAuth provider
    redirect_uri: str  # Redirect URI used in OAuth flow (must match)


class OAuthCallbackResponse(BaseModel):
    """Response model for OAuth callback."""

    access_token: str  # JWT access token
    refresh_token: str  # JWT refresh token
    expires_in: int  # Token expiry in seconds
    user: dict[str, Any]  # User data


class UserResponse(BaseModel):
    """User data response."""

    id: str
    email: EmailStr
    auth_provider: str
    subscription_tier: str
    created_at: str


@router.post("/auth/google/callback", response_model=OAuthCallbackResponse)
async def google_oauth_callback(request: OAuthCallbackRequest) -> OAuthCallbackResponse:
    """Handle Google OAuth callback and exchange code for JWT.

    Flow:
    1. Verify code with Supabase GoTrue
    2. Get user data from Google
    3. Create user in database if first sign-in
    4. Link user to trial tier
    5. Return JWT tokens

    Args:
        request: OAuth callback request with authorization code

    Returns:
        JWT tokens and user data

    Raises:
        HTTPException: 400 if code is invalid, 500 if OAuth provider error
    """
    if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
        logger.error("Google OAuth credentials not configured")
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. Please contact support.",
        )

    try:
        # Import supabase client
        try:
            from supabase import create_client
        except ImportError as e:
            logger.error("supabase-py not installed - required for OAuth")
            raise HTTPException(
                status_code=500,
                detail="Authentication system not configured",
            ) from e

        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

        # Exchange authorization code for tokens via Supabase GoTrue
        # This validates the code with Google and returns user data
        logger.info(
            f"Exchanging authorization code for tokens (redirect_uri: {request.redirect_uri})"
        )

        # Use Supabase's OAuth token exchange
        # Note: Supabase GoTrue handles the Google OAuth flow internally
        auth_response = supabase.auth.exchange_code_for_session(
            {
                "auth_code": request.code,
            }
        )

        if not auth_response or not auth_response.session:
            logger.error("Failed to exchange code for session")
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired authorization code",
            )

        session = auth_response.session
        user = auth_response.user

        if not user or not user.id or not user.email:
            logger.error("OAuth response missing user data")
            raise HTTPException(
                status_code=400,
                detail="Failed to get user data from Google",
            )

        logger.info(f"Successfully authenticated user: {user.email} (id: {user.id})")

        # Check beta whitelist if closed beta mode is enabled
        settings = get_settings()
        if settings.closed_beta_mode:
            user_email = user.email.lower()
            if user_email not in settings.beta_whitelist_emails:
                logger.warning(
                    f"User {user_email} not in beta whitelist. "
                    f"Whitelist has {len(settings.beta_whitelist_emails)} emails."
                )
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "closed_beta",
                        "message": "Thanks for your interest! We're currently in closed beta. "
                        "Join our waitlist at https://boardof.one/waitlist",
                    },
                )
            logger.info(f"User {user_email} found in beta whitelist - access granted")

        # Create or update user in database
        await _ensure_user_exists(
            user_id=user.id,
            email=user.email,
            auth_provider="google",
        )

        # Return tokens and user data
        return OAuthCallbackResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token or "",
            expires_in=session.expires_in or 3600,
            user={
                "id": user.id,
                "email": user.email,
                "auth_provider": "google",
                "subscription_tier": user.user_metadata.get("subscription_tier", "free"),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"OAuth authentication failed: {str(e)}",
        ) from e


@router.post("/auth/refresh", response_model=OAuthCallbackResponse)
async def refresh_token(refresh_token: str) -> OAuthCallbackResponse:
    """Refresh JWT access token using refresh token.

    Args:
        refresh_token: JWT refresh token

    Returns:
        New JWT tokens

    Raises:
        HTTPException: 401 if refresh token is invalid or expired
    """
    try:
        from supabase import create_client

        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

        # Refresh session
        auth_response = supabase.auth.refresh_session(refresh_token)

        if not auth_response or not auth_response.session:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired refresh token",
            )

        session = auth_response.session
        user = auth_response.user

        return OAuthCallbackResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token or refresh_token,
            expires_in=session.expires_in or 3600,
            user={
                "id": user.id,
                "email": user.email,
                "auth_provider": user.app_metadata.get("provider", "google"),
                "subscription_tier": user.user_metadata.get("subscription_tier", "free"),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Token refresh failed: {str(e)}",
        ) from e


@router.post("/auth/signout")
async def signout(access_token: str) -> dict[str, str]:
    """Sign out user and invalidate tokens.

    Args:
        access_token: JWT access token

    Returns:
        Success message

    Raises:
        HTTPException: 401 if token is invalid
    """
    try:
        from supabase import create_client

        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

        # Sign out (invalidates tokens)
        supabase.auth.sign_out(access_token)

        return {"message": "Successfully signed out"}

    except Exception as e:
        logger.error(f"Signout failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Signout failed: {str(e)}",
        ) from e


async def _ensure_user_exists(user_id: str, email: str, auth_provider: str) -> None:
    """Create user in database if not exists, or update if exists.

    Links user to free trial tier on first sign-in.

    Args:
        user_id: Supabase user ID (UUID from auth.users)
        email: User email
        auth_provider: OAuth provider (google, linkedin, github)
    """
    from sqlalchemy import text

    from bo1.state.postgres_manager import get_database_session

    try:
        async with get_database_session() as session:
            # Check if user exists
            result = await session.execute(
                text("SELECT id FROM users WHERE id = :user_id"),
                {"user_id": user_id},
            )
            existing_user = result.fetchone()

            if existing_user:
                logger.info(f"User {email} already exists, updating last login")
                # Update user (updated_at timestamp auto-updated by trigger)
                await session.execute(
                    text(
                        """
                        UPDATE users
                        SET email = :email,
                            auth_provider = :auth_provider
                        WHERE id = :user_id
                        """
                    ),
                    {
                        "user_id": user_id,
                        "email": email,
                        "auth_provider": auth_provider,
                    },
                )
            else:
                logger.info(f"Creating new user: {email} (tier: free)")
                # Create user with free tier
                await session.execute(
                    text(
                        """
                        INSERT INTO users (id, email, auth_provider, subscription_tier)
                        VALUES (:user_id, :email, :auth_provider, 'free')
                        """
                    ),
                    {
                        "user_id": user_id,
                        "email": email,
                        "auth_provider": auth_provider,
                    },
                )

            await session.commit()
            logger.info(f"User {email} ensured in database")

    except Exception as e:
        logger.error(f"Failed to ensure user exists: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create user account",
        ) from e
