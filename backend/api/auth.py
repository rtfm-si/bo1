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
    code_verifier: str  # PKCE code verifier for secure code exchange


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
    # Note: We call GoTrue's token endpoint directly instead of using Supabase client
    # because we need to pass the PKCE code_verifier

    try:
        import httpx

        # Exchange authorization code for tokens via Supabase GoTrue with PKCE
        # PKCE (Proof Key for Code Exchange) ensures secure code exchange
        logger.info(
            f"Exchanging authorization code for tokens with PKCE (redirect_uri: {request.redirect_uri})"
        )

        # Exchange code for session using PKCE verifier
        # Call GoTrue's token endpoint directly with the code_verifier

        token_url = f"{SUPABASE_URL}/token?grant_type=pkce"
        token_data = {
            "auth_code": request.code,
            "code_verifier": request.code_verifier,
        }

        headers = {
            "Content-Type": "application/json",
        }

        # Add apikey header if available (not required for self-hosted GoTrue)
        if SUPABASE_ANON_KEY and SUPABASE_ANON_KEY != "your_supabase_anon_key_here":
            headers["apikey"] = SUPABASE_ANON_KEY

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_url,
                json=token_data,
                headers=headers,
            )

            if token_response.status_code != 200:
                logger.error(
                    f"Token exchange failed: {token_response.status_code} - {token_response.text}"
                )
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or expired authorization code",
                )

            token_data_response = token_response.json()

        # Extract session and user data from response
        if not token_data_response or "access_token" not in token_data_response:
            logger.error("Failed to exchange code for session")
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired authorization code",
            )

        # Create session object manually from token response
        class Session:
            def __init__(self, data: dict[str, Any]) -> None:
                self.access_token = data.get("access_token", "")
                self.refresh_token = data.get("refresh_token")
                self.expires_in = data.get("expires_in", 3600)
                self.user_data = data.get("user", {})

        class User:
            def __init__(self, data: dict[str, Any]) -> None:
                self.id = data.get("id", "")
                self.email = data.get("email", "")
                self.user_metadata = data.get("user_metadata", {})
                self.app_metadata = data.get("app_metadata", {})

        session = Session(token_data_response)
        user = User(token_data_response.get("user", {}))

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
        _ensure_user_exists(
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


def _ensure_user_exists(user_id: str, email: str, auth_provider: str) -> None:
    """Create user in database if not exists, or update if exists.

    Links user to free trial tier on first sign-in.

    Args:
        user_id: Supabase user ID (UUID from auth.users)
        email: User email
        auth_provider: OAuth provider (google, linkedin, github)
    """
    from bo1.state.postgres_manager import get_connection

    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # Set search path to public schema
                cur.execute("SET search_path TO public")

                # Check if user exists
                cur.execute(
                    "SELECT id FROM public.users WHERE id = %s",
                    (user_id,),
                )
                existing_user = cur.fetchone()

                if existing_user:
                    logger.info(f"User {email} already exists, updating last login")
                    # Update user (updated_at timestamp auto-updated by trigger)
                    cur.execute(
                        """
                        UPDATE public.users
                        SET email = %s,
                            auth_provider = %s
                        WHERE id = %s
                        """,
                        (email, auth_provider, user_id),
                    )
                else:
                    logger.info(f"Creating new user: {email} (tier: free)")
                    # Create user with free tier
                    cur.execute(
                        """
                        INSERT INTO public.users (id, email, auth_provider, subscription_tier)
                        VALUES (%s, %s, %s, 'free')
                        """,
                        (user_id, email, auth_provider),
                    )

                conn.commit()
                logger.info(f"User {email} ensured in database")
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Failed to ensure user exists: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create user account",
        ) from e
