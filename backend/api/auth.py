"""OAuth authentication endpoints for Board of One API - BFF Pattern.

BFF (Backend-for-Frontend) OAuth flow:
1. User clicks "Sign in with Google" → GET /api/auth/google/login
2. Backend generates PKCE challenge, stores verifier in Redis
3. Backend redirects browser to Supabase /authorize
4. Supabase redirects to Google, user signs in
5. Google redirects to Supabase, Supabase redirects to backend callback
6. Backend receives code → GET /api/auth/callback
7. Backend retrieves verifier, exchanges code+verifier for tokens
8. Backend stores tokens in Redis, sets httpOnly cookie
9. Backend redirects browser to frontend /dashboard

Security:
- PKCE prevents authorization code interception
- State parameter prevents CSRF attacks
- Tokens never exposed to frontend (stored in Redis)
- httpOnly cookies prevent XSS attacks
"""

import hashlib
import logging
import os
import secrets
from base64 import urlsafe_b64encode
from typing import Any

from fastapi import APIRouter, Cookie, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr

from backend.api.session import SessionManager
from bo1.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# OAuth configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:9999")  # Internal API calls
SUPABASE_BROWSER_URL = os.getenv(
    "SUPABASE_BROWSER_URL", "http://localhost:9999"
)  # Browser redirects
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Frontend configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Cookie configuration
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "bo1_session")
OAUTH_STATE_COOKIE_NAME = "oauth_state"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", "localhost")

# Initialize session manager
session_manager = SessionManager()


# Response Models
class UserResponse(BaseModel):
    """User data response."""

    id: str
    email: EmailStr
    auth_provider: str
    subscription_tier: str
    created_at: str


# Helper Functions
def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge.

    Returns:
        Tuple of (code_verifier, code_challenge)

    Examples:
        >>> verifier, challenge = generate_pkce_pair()
        >>> print(len(verifier), len(challenge))
        128 43
    """
    # Generate code verifier (random 128 char string)
    code_verifier = secrets.token_urlsafe(96)  # 96 bytes = 128 chars base64url

    # Generate code challenge (SHA256 hash of verifier)
    verifier_bytes = code_verifier.encode("ascii")
    sha256_hash = hashlib.sha256(verifier_bytes).digest()
    code_challenge = urlsafe_b64encode(sha256_hash).decode("ascii").rstrip("=")

    return code_verifier, code_challenge


# OAuth Endpoints


@router.get("/auth/google/login")
async def google_oauth_login() -> RedirectResponse:
    """Initiate Google OAuth flow with PKCE.

    Flow:
    1. Generate PKCE code_verifier and code_challenge
    2. Generate random state parameter (CSRF protection)
    3. Store code_verifier in Redis with state as key
    4. Set temporary cookie with state
    5. Redirect to Supabase /authorize

    Returns:
        Redirect to Supabase OAuth URL
    """
    try:
        # Generate PKCE pair
        code_verifier, code_challenge = generate_pkce_pair()
        logger.info(
            f"Generated PKCE pair (verifier: {len(code_verifier)} chars, challenge: {len(code_challenge)} chars)"
        )

        # Store code_verifier in Redis and get state_id
        state_id = session_manager.create_oauth_state(
            code_verifier=code_verifier,
            redirect_uri=f"{FRONTEND_URL}/dashboard",
        )

        # Build Supabase OAuth URL
        callback_url = f"{BACKEND_URL}/api/auth/callback"
        params = {
            "provider": "google",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state_id,
            "redirect_to": callback_url,
        }

        # Build query string with proper URL encoding
        from urllib.parse import urlencode

        query_string = urlencode(params)
        oauth_url = f"{SUPABASE_BROWSER_URL}/authorize?{query_string}"

        logger.info(f"Redirecting to Supabase OAuth URL (state: {state_id[:8]}...)")

        # Create redirect response
        response = RedirectResponse(url=oauth_url, status_code=302)

        # Set temporary cookie with state (for CSRF validation)
        response.set_cookie(
            key=OAUTH_STATE_COOKIE_NAME,
            value=state_id,
            max_age=600,  # 10 minutes
            httponly=True,
            samesite="lax",
            secure=COOKIE_SECURE,
            domain=COOKIE_DOMAIN if COOKIE_DOMAIN != "localhost" else None,
        )

        return response

    except Exception as e:
        logger.error(f"OAuth login failed: {e}", exc_info=True)
        # Redirect to frontend login with error
        return RedirectResponse(
            url=f"{FRONTEND_URL}/login?error=auth_init_failed",
            status_code=302,
        )


@router.get("/auth/callback")
async def google_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str | None = Cookie(None),
) -> RedirectResponse:
    """Handle Google OAuth callback and create session.

    Flow:
    1. Validate state parameter (CSRF check)
    2. Retrieve code_verifier from Redis
    3. Exchange code + verifier for tokens via Supabase
    4. Check beta whitelist
    5. Create/update user in database
    6. Create session in Redis
    7. Set httpOnly session cookie
    8. Redirect to frontend dashboard

    Args:
        code: Authorization code from Supabase
        state: State parameter (CSRF protection)
        error: Error from OAuth provider
        oauth_state: State from cookie (for validation)

    Returns:
        Redirect to frontend (dashboard or login with error)
    """
    try:
        # Check for OAuth errors
        if error:
            logger.error(f"OAuth error: {error}")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=oauth_error",
                status_code=302,
            )

        # Validate required parameters
        if not code or not state:
            logger.error("Missing code or state parameter")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=missing_parameters",
                status_code=302,
            )

        # CSRF check: state from query must match state from cookie
        if state != oauth_state:
            logger.error(
                f"CSRF validation failed: state mismatch (query: {state[:8]}..., cookie: {oauth_state[:8] if oauth_state else 'None'}...)"
            )
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=csrf_validation_failed",
                status_code=302,
            )

        # Retrieve code_verifier from Redis
        oauth_state_data = session_manager.get_oauth_state(state)
        if not oauth_state_data:
            logger.error(f"OAuth state not found or expired: {state[:8]}...")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=state_expired",
                status_code=302,
            )

        code_verifier = oauth_state_data.get("code_verifier")
        if not code_verifier:
            logger.error("Code verifier missing from OAuth state")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=invalid_state",
                status_code=302,
            )

        # Delete OAuth state (one-time use)
        session_manager.delete_oauth_state(state)

        logger.info(
            f"Exchanging authorization code for tokens (code: {code[:10]}..., verifier: {code_verifier[:10]}...)"
        )

        # Exchange code + verifier for tokens via Supabase
        import httpx

        token_url = f"{SUPABASE_URL}/token"
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": f"{BACKEND_URL}/api/auth/callback",
        }

        headers = {}
        if SUPABASE_ANON_KEY and SUPABASE_ANON_KEY != "your_supabase_anon_key_here":
            headers["apikey"] = SUPABASE_ANON_KEY

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_url,
                data=token_data,  # Form-encoded (OAuth2 spec)
                headers=headers,
            )

            # Check response status
            if token_response.status_code != 200:
                error_text = token_response.text
                logger.error(f"Token exchange failed: {token_response.status_code} - {error_text}")
                return RedirectResponse(
                    url=f"{FRONTEND_URL}/login?error=token_exchange_failed",
                    status_code=302,
                )

            # Parse tokens
            token_data_response = token_response.json()

        # Extract user and token data
        if not token_data_response or "access_token" not in token_data_response:
            logger.error("Token response missing access_token")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=invalid_token_response",
                status_code=302,
            )

        user_data = token_data_response.get("user", {})
        user_id = user_data.get("id")
        user_email = user_data.get("email")

        if not user_id or not user_email:
            logger.error("User data missing from token response")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=missing_user_data",
                status_code=302,
            )

        logger.info(f"Successfully authenticated user: {user_email} (id: {user_id})")

        # Check beta whitelist if closed beta mode is enabled
        settings = get_settings()
        if settings.closed_beta_mode:
            user_email_lower = user_email.lower()
            if user_email_lower not in settings.beta_whitelist_emails:
                logger.warning(
                    f"User {user_email_lower} not in beta whitelist. "
                    f"Whitelist has {len(settings.beta_whitelist_emails)} emails."
                )
                return RedirectResponse(
                    url=f"{FRONTEND_URL}/login?error=closed_beta",
                    status_code=302,
                )
            logger.info(f"User {user_email_lower} found in beta whitelist - access granted")

        # Create or update user in database
        _ensure_user_exists(
            user_id=user_id,
            email=user_email,
            auth_provider="google",
        )

        # Create session in Redis
        tokens = {
            "access_token": token_data_response.get("access_token", ""),
            "refresh_token": token_data_response.get("refresh_token", ""),
            "expires_in": token_data_response.get("expires_in", 3600),
        }

        session_id = session_manager.create_session(
            user_id=user_id,
            email=user_email,
            tokens=tokens,
        )

        # Create redirect response to frontend dashboard
        response = RedirectResponse(url=f"{FRONTEND_URL}/dashboard", status_code=302)

        # Set httpOnly session cookie
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            max_age=3600,  # 1 hour
            httponly=True,
            samesite="lax",
            secure=COOKIE_SECURE,
            domain=COOKIE_DOMAIN if COOKIE_DOMAIN != "localhost" else None,
        )

        # Delete OAuth state cookie
        response.delete_cookie(
            key=OAUTH_STATE_COOKIE_NAME,
            domain=COOKIE_DOMAIN if COOKIE_DOMAIN != "localhost" else None,
        )

        logger.info(f"Session created for {user_email}, redirecting to dashboard")
        return response

    except Exception as e:
        logger.error(f"OAuth callback failed: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{FRONTEND_URL}/login?error=callback_failed",
            status_code=302,
        )


@router.post("/auth/logout")
async def logout(
    request: Request,
    bo1_session: str | None = Cookie(None),
) -> dict[str, str]:
    """Sign out user and invalidate session.

    Args:
        bo1_session: Session ID from cookie

    Returns:
        Success message
    """
    try:
        if bo1_session:
            # Delete session from Redis
            session_manager.delete_session(bo1_session)
            logger.info(f"User logged out: {bo1_session[:8]}...")

        return {"message": "Successfully signed out"}

    except Exception as e:
        logger.error(f"Logout failed: {e}")
        # Return success anyway (local cleanup will happen)
        return {"message": "Signed out"}


@router.post("/auth/refresh")
async def refresh_token(
    request: Request,
    bo1_session: str | None = Cookie(None),
) -> dict[str, str]:
    """Refresh access token using refresh token from session.

    Args:
        bo1_session: Session ID from cookie

    Returns:
        Success message

    Raises:
        HTTPException: 401 if session not found or refresh fails
    """
    try:
        if not bo1_session:
            raise HTTPException(
                status_code=401,
                detail="No session cookie",
            )

        # Get session from Redis
        session = session_manager.get_session(bo1_session)
        if not session:
            raise HTTPException(
                status_code=401,
                detail="Session not found or expired",
            )

        # Check if token is near expiry
        import time

        expires_at = session.get("expires_at", 0)
        now = time.time()
        time_until_expiry = expires_at - now

        # Only refresh if < 5 minutes remaining
        if time_until_expiry > 300:
            return {"message": "Token still valid, no refresh needed"}

        # Get refresh token
        refresh_token = session.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=401,
                detail="No refresh token available",
            )

        # Refresh via Supabase
        from supabase import create_client

        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        auth_response = supabase.auth.refresh_session(refresh_token)

        if not auth_response or not auth_response.session:
            raise HTTPException(
                status_code=401,
                detail="Token refresh failed",
            )

        # Update session with new tokens
        new_tokens = {
            "access_token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token or refresh_token,
            "expires_in": auth_response.session.expires_in or 3600,
        }

        session_manager.refresh_session(bo1_session, new_tokens)

        logger.info(f"Refreshed tokens for session: {bo1_session[:8]}...")
        return {"message": "Token refreshed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail=f"Token refresh failed: {str(e)}",
        ) from e


@router.get("/auth/me")
async def get_current_user_info(
    request: Request,
    bo1_session: str | None = Cookie(None),
) -> dict[str, Any]:
    """Get current user info from session.

    Args:
        bo1_session: Session ID from cookie

    Returns:
        User data

    Raises:
        HTTPException: 401 if not authenticated
    """
    try:
        if not bo1_session:
            raise HTTPException(
                status_code=401,
                detail="Not authenticated",
            )

        # Get session from Redis
        session = session_manager.get_session(bo1_session)
        if not session:
            raise HTTPException(
                status_code=401,
                detail="Session expired",
            )

        # Return user data (no tokens!)
        return {
            "id": session.get("user_id"),
            "email": session.get("email"),
            "auth_provider": "google",
            "subscription_tier": "free",  # TODO: Get from database
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get user info",
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
