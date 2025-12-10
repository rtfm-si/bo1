"""Authentication endpoints for SuperTokens OAuth.

Provides:
- OAuth provider endpoints (automatically handled by SuperTokens middleware)
- Session verification
- User info retrieval
- Google Sheets connection (incremental auth for existing users)

SuperTokens automatically exposes these endpoints under /api/auth:
- GET /api/auth/authorisationurl - Get OAuth authorization URL
- POST /api/auth/signinup - Complete OAuth flow
- POST /api/auth/signout - Sign out user
"""

import logging
import os
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from backend.api.middleware.rate_limit import AUTH_RATE_LIMIT, limiter
from backend.api.oauth_session_manager import SessionManager
from backend.api.utils.errors import handle_api_errors
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

router = APIRouter()

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105

# Sheets scope for incremental auth
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"

# Session manager for OAuth state
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get or create session manager singleton."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


@router.get("/me")
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("get user info")
async def get_user_info(
    request: Request, session: SessionContainer = Depends(verify_session())
) -> dict:
    """Get current authenticated user information.

    Fetches user data from PostgreSQL (source of truth for persistent data).
    If user not found in DB, returns minimal data from session.

    Returns:
        User ID, email, auth provider, subscription tier, and session info
    """
    user_id = session.get_user_id()
    session_handle = session.get_handle()

    logger.info(f"User info requested: user_id={user_id}, session={session_handle}")

    # Fetch complete user data from PostgreSQL
    user_data = user_repository.get(user_id)

    if user_data:
        return {
            "id": user_data["id"],
            "user_id": user_data["id"],
            "email": user_data["email"],
            "auth_provider": user_data["auth_provider"],
            "subscription_tier": user_data["subscription_tier"],
            "is_admin": user_data.get("is_admin", False),
            "session_handle": session_handle,
        }

    # Fallback if user not in database (shouldn't happen with proper sync)
    logger.warning(f"User {user_id} not found in PostgreSQL, returning minimal data")
    return {
        "id": user_id,
        "user_id": user_id,
        "email": None,
        "auth_provider": None,
        "subscription_tier": "free",
        "is_admin": False,
        "session_handle": session_handle,
    }


@router.get("/google/sheets/status")
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("get sheets status")
async def get_sheets_connection_status(
    request: Request, session: SessionContainer = Depends(verify_session())
) -> dict:
    """Check if user has Google Sheets connected.

    Returns:
        connected: True if user has sheets scope authorized
        scopes: Authorized scopes (if connected)
    """
    user_id = session.get_user_id()
    tokens = user_repository.get_google_tokens(user_id)

    if not tokens:
        return {"connected": False, "scopes": None}

    scopes = tokens.get("scopes", "")
    has_sheets = "spreadsheets" in scopes

    return {
        "connected": has_sheets,
        "scopes": scopes if has_sheets else None,
    }


@router.get("/google/sheets/connect")
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("initiate sheets connect")
async def initiate_sheets_connect(
    request: Request, session: SessionContainer = Depends(verify_session())
) -> RedirectResponse:
    """Initiate Google OAuth flow for Sheets access.

    For existing users who signed up before Sheets scope was added,
    or users who want to grant Sheets access.

    Redirects to Google OAuth consent screen with spreadsheets.readonly scope.
    """
    user_id = session.get_user_id()

    # Get OAuth credentials
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    if not client_id:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    # Create OAuth state for CSRF protection
    session_manager = get_session_manager()
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)

    # Store state with user_id for callback
    session_manager.create_oauth_state(code_verifier, redirect_uri=f"user:{user_id}")

    # Build Google OAuth URL
    redirect_uri = os.getenv("SUPERTOKENS_API_DOMAIN", "http://localhost:8000")
    redirect_uri = f"{redirect_uri}/api/v1/auth/google/sheets/callback"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": f"openid email profile {SHEETS_SCOPE}",
        "access_type": "offline",  # Get refresh token
        "prompt": "consent",  # Force consent to get refresh token
        "state": state,
    }

    # Store state -> code_verifier mapping
    session_manager.create_oauth_state(state, redirect_uri=f"user:{user_id}:{code_verifier}")

    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    logger.info(f"Initiating Sheets connect for user {user_id}")

    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/google/sheets/callback")
@limiter.limit(AUTH_RATE_LIMIT)
async def sheets_connect_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Handle Google OAuth callback for Sheets connection.

    Exchanges authorization code for tokens and saves to user record.
    Redirects to datasets page on success or with error param on failure.
    """
    frontend_url = os.getenv("SUPERTOKENS_WEBSITE_DOMAIN", "http://localhost:5173")
    datasets_url = f"{frontend_url}/datasets"

    # Handle OAuth errors
    if error:
        logger.warning(f"Sheets OAuth error: {error}")
        return RedirectResponse(url=f"{datasets_url}?sheets_error={error}", status_code=302)

    if not code or not state:
        logger.warning("Sheets callback missing code or state")
        return RedirectResponse(url=f"{datasets_url}?sheets_error=missing_params", status_code=302)

    # Validate state and get user_id
    session_manager = get_session_manager()
    state_data = session_manager.get_oauth_state(state)

    if not state_data:
        logger.warning(f"Invalid or expired OAuth state: {state[:8]}...")
        return RedirectResponse(url=f"{datasets_url}?sheets_error=invalid_state", status_code=302)

    # Extract user_id from stored redirect_uri
    redirect_info = state_data.get("redirect_uri", "")
    if not redirect_info.startswith("user:"):
        logger.warning("Invalid state data format")
        return RedirectResponse(url=f"{datasets_url}?sheets_error=invalid_state", status_code=302)

    parts = redirect_info.split(":")
    if len(parts) < 2:
        logger.warning("Invalid state data format")
        return RedirectResponse(url=f"{datasets_url}?sheets_error=invalid_state", status_code=302)

    user_id = parts[1]

    # Delete state (one-time use)
    session_manager.delete_oauth_state(state)

    # Exchange code for tokens
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
    redirect_uri = os.getenv("SUPERTOKENS_API_DOMAIN", "http://localhost:8000")
    redirect_uri = f"{redirect_uri}/api/v1/auth/google/sheets/callback"

    try:
        token_response = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            timeout=30,
        )

        if token_response.status_code != 200:
            logger.error(f"Token exchange failed: {token_response.text}")
            return RedirectResponse(
                url=f"{datasets_url}?sheets_error=token_exchange_failed", status_code=302
            )

        tokens = token_response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in")
        scope = tokens.get("scope", "")

        if not access_token:
            logger.error("No access token in response")
            return RedirectResponse(
                url=f"{datasets_url}?sheets_error=no_access_token", status_code=302
            )

        # Calculate expiry
        expires_at = None
        if expires_in:
            expires_at = (datetime.now(UTC) + timedelta(seconds=int(expires_in))).isoformat()

        # Save tokens
        user_repository.save_google_tokens(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scopes=scope,
        )

        logger.info(f"Sheets connected for user {user_id} (scopes: {scope[:50]}...)")
        return RedirectResponse(url=f"{datasets_url}?sheets_connected=true", status_code=302)

    except requests.RequestException as e:
        logger.error(f"Token exchange request failed: {e}")
        return RedirectResponse(url=f"{datasets_url}?sheets_error=request_failed", status_code=302)


@router.delete("/google/sheets/disconnect")
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("disconnect sheets")
async def disconnect_sheets(
    request: Request, session: SessionContainer = Depends(verify_session())
) -> dict:
    """Disconnect Google Sheets (clear stored tokens).

    Returns:
        success: True if tokens were cleared
    """
    user_id = session.get_user_id()
    success = user_repository.clear_google_tokens(user_id)

    if success:
        logger.info(f"Sheets disconnected for user {user_id}")
    else:
        logger.warning(f"Failed to disconnect sheets for user {user_id}")

    return {"success": success}
