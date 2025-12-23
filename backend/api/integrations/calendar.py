"""Google Calendar integration API endpoints.

Provides:
- OAuth connection flow for Calendar access
- Connection status check
- Disconnect functionality
"""

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from backend.api.middleware.rate_limit import AUTH_RATE_LIMIT, limiter
from backend.api.oauth_session_manager import SessionManager
from backend.api.utils.errors import handle_api_errors
from backend.services.google_calendar import (
    CalendarError,
    exchange_code,
    get_auth_url,
)
from bo1.config import get_settings
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/integrations/calendar", tags=["integrations"])

# Session manager for OAuth state
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get or create session manager singleton."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


class CalendarStatusResponse(BaseModel):
    """Response for calendar connection status."""

    connected: bool
    connected_at: str | None = None
    feature_enabled: bool = True
    sync_enabled: bool = True


class CalendarSyncToggleRequest(BaseModel):
    """Request to toggle calendar sync."""

    enabled: bool


class CalendarConnectResponse(BaseModel):
    """Response for calendar connection initiation."""

    redirect_url: str


@router.get("/status", response_model=CalendarStatusResponse)
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("get calendar status")
async def get_calendar_status(
    request: Request, session: SessionContainer = Depends(verify_session())
) -> CalendarStatusResponse:
    """Check if user has Google Calendar connected.

    Returns:
        connected: True if user has Calendar tokens
        connected_at: When the connection was established
        feature_enabled: Whether Calendar feature is enabled
        sync_enabled: Whether user has sync enabled (can be paused)
    """
    settings = get_settings()
    user_id = session.get_user_id()

    if not settings.google_calendar_enabled:
        return CalendarStatusResponse(
            connected=False,
            connected_at=None,
            feature_enabled=False,
            sync_enabled=False,
        )

    tokens = user_repository.get_calendar_tokens(user_id)

    if not tokens:
        return CalendarStatusResponse(connected=False, sync_enabled=True)

    connected_at = tokens.get("connected_at")
    connected_at_str = connected_at.isoformat() if connected_at else None

    # Get user's sync preference
    sync_enabled = user_repository.get_calendar_sync_enabled(user_id)

    return CalendarStatusResponse(
        connected=bool(tokens.get("access_token")),
        connected_at=connected_at_str,
        sync_enabled=sync_enabled,
    )


@router.get("/connect")
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("initiate calendar connect")
async def initiate_calendar_connect(
    request: Request, session: SessionContainer = Depends(verify_session())
) -> RedirectResponse:
    """Initiate Google OAuth flow for Calendar access.

    Redirects to Google OAuth consent screen with calendar.events scope.
    """
    settings = get_settings()
    user_id = session.get_user_id()

    if not settings.google_calendar_enabled:
        raise HTTPException(status_code=403, detail="Calendar integration is disabled")

    if not settings.google_oauth_client_id:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    # Create OAuth state for CSRF protection
    session_manager = get_session_manager()
    state = secrets.token_urlsafe(32)
    session_manager.set(
        key=f"calendar_oauth:{state}",
        value={"user_id": user_id, "type": "calendar"},
        expiry=600,  # 10 minute expiry
    )

    # Build redirect URI
    redirect_uri = f"{settings.supertokens_api_domain}/api/v1/integrations/calendar/callback"

    # Get auth URL
    auth_url = get_auth_url(redirect_uri=redirect_uri, state=state)

    logger.info(f"User {user_id} initiating Calendar OAuth flow")
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback")
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("calendar oauth callback")
async def calendar_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Handle Google OAuth callback for Calendar.

    Exchanges authorization code for tokens and stores them.
    """
    settings = get_settings()
    frontend_url = settings.frontend_url

    # Handle OAuth errors
    if error:
        logger.warning(f"Calendar OAuth error: {error}")
        return RedirectResponse(
            url=f"{frontend_url}/settings/integrations?calendar_error={error}",
            status_code=302,
        )

    if not code or not state:
        log_error(
            logger,
            ErrorCode.EXT_CALENDAR_ERROR,
            "Calendar OAuth callback missing code or state",
            code=code,
            state_present=bool(state),
        )
        return RedirectResponse(
            url=f"{frontend_url}/settings/integrations?calendar_error=invalid_request",
            status_code=302,
        )

    # Validate state (CSRF protection)
    session_manager = get_session_manager()
    session_data = session_manager.get(f"calendar_oauth:{state}")

    if not session_data:
        log_error(
            logger,
            ErrorCode.EXT_CALENDAR_ERROR,
            "Calendar OAuth callback: invalid or expired state",
            state=state,
        )
        return RedirectResponse(
            url=f"{frontend_url}/settings/integrations?calendar_error=invalid_state",
            status_code=302,
        )

    user_id = session_data.get("user_id")
    if not user_id:
        log_error(
            logger,
            ErrorCode.EXT_CALENDAR_ERROR,
            "Calendar OAuth callback: missing user_id in state",
            state=state,
        )
        return RedirectResponse(
            url=f"{frontend_url}/settings/integrations?calendar_error=invalid_state",
            status_code=302,
        )

    # Clear the state
    session_manager.delete(f"calendar_oauth:{state}")

    # Exchange code for tokens
    try:
        redirect_uri = f"{settings.supertokens_api_domain}/api/v1/integrations/calendar/callback"
        tokens = exchange_code(code=code, redirect_uri=redirect_uri)

        # Store tokens
        user_repository.save_calendar_tokens(
            user_id=user_id,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            expires_at=tokens.get("expires_at"),
        )

        logger.info(f"User {user_id} connected Google Calendar successfully")
        return RedirectResponse(
            url=f"{frontend_url}/settings/integrations?calendar_connected=true",
            status_code=302,
        )

    except CalendarError as e:
        log_error(
            logger,
            ErrorCode.EXT_CALENDAR_ERROR,
            f"Calendar OAuth token exchange failed: {e}",
            user_id=user_id,
        )
        return RedirectResponse(
            url=f"{frontend_url}/settings/integrations?calendar_error=token_exchange_failed",
            status_code=302,
        )
    except Exception as e:
        logger.exception(f"Unexpected error in Calendar OAuth callback: {e}")
        return RedirectResponse(
            url=f"{frontend_url}/settings/integrations?calendar_error=unexpected_error",
            status_code=302,
        )


@router.delete("/disconnect")
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("disconnect calendar")
async def disconnect_calendar(
    request: Request, session: SessionContainer = Depends(verify_session())
) -> dict:
    """Disconnect Google Calendar integration.

    Clears stored tokens and revokes access.

    Returns:
        success: True if disconnected successfully
    """
    user_id = session.get_user_id()

    # Clear tokens
    user_repository.clear_calendar_tokens(user_id)

    logger.info(f"User {user_id} disconnected Google Calendar")
    return {"success": True}


@router.patch("/status", response_model=CalendarStatusResponse)
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("toggle calendar sync")
async def toggle_calendar_sync(
    request: Request,
    body: CalendarSyncToggleRequest,
    session: SessionContainer = Depends(verify_session()),
) -> CalendarStatusResponse:
    """Toggle calendar sync on/off without disconnecting.

    Allows users to pause sync while keeping calendar connected.

    Returns:
        Updated calendar status
    """
    settings = get_settings()
    user_id = session.get_user_id()

    if not settings.google_calendar_enabled:
        raise HTTPException(status_code=403, detail="Calendar integration is disabled")

    # Update preference
    user_repository.set_calendar_sync_enabled(user_id, body.enabled)

    logger.info(f"User {user_id} {'enabled' if body.enabled else 'disabled'} calendar sync")

    # Return updated status
    tokens = user_repository.get_calendar_tokens(user_id)
    connected_at = tokens.get("connected_at") if tokens else None
    connected_at_str = connected_at.isoformat() if connected_at else None

    return CalendarStatusResponse(
        connected=bool(tokens.get("access_token")) if tokens else False,
        connected_at=connected_at_str,
        sync_enabled=body.enabled,
    )
