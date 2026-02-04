"""Google Search Console integration API endpoints.

Provides:
- OAuth connection flow for admin-level GSC access
- Connection status check
- Site selection
- Disconnect functionality

Note: This is admin-only (unlike calendar which is per-user).
"""

import logging
import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import AUTH_RATE_LIMIT, limiter
from backend.api.oauth_session_manager import SessionManager
from backend.api.utils.errors import handle_api_errors, http_error
from backend.services.encryption import EncryptionError, get_encryption_service
from backend.services.google_search_console import (
    GSCError,
    exchange_code,
    get_auth_url,
    get_gsc_client,
)
from bo1.config import get_settings
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.repositories.gsc_repository import gsc_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/integrations/search-console", tags=["integrations"])

# Session manager for OAuth state
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get or create session manager singleton."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


class GSCStatusResponse(BaseModel):
    """Response for GSC connection status."""

    connected: bool
    site_url: str | None = None
    connected_at: str | None = None
    connected_by: str | None = None
    feature_enabled: bool = True


class GSCSiteResponse(BaseModel):
    """A GSC site/property."""

    site_url: str
    permission_level: str


class GSCSitesResponse(BaseModel):
    """Response for list of GSC sites."""

    sites: list[GSCSiteResponse]


class GSCSiteSelectRequest(BaseModel):
    """Request to select a GSC site."""

    site_url: str


@router.get("/status", response_model=GSCStatusResponse)
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("get GSC status")
async def get_gsc_status(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> GSCStatusResponse:
    """Check if GSC is connected (admin only).

    Returns:
        connected: True if GSC tokens exist
        site_url: Selected property URL
        connected_at: When the connection was established
        connected_by: User ID who connected
        feature_enabled: Whether GSC feature is enabled
    """
    settings = get_settings()

    if not settings.google_search_console_enabled:
        return GSCStatusResponse(
            connected=False,
            site_url=None,
            connected_at=None,
            connected_by=None,
            feature_enabled=False,
        )

    connection = gsc_repository.get_connection()

    if not connection:
        return GSCStatusResponse(connected=False)

    connected_at = connection.get("connected_at")
    connected_at_str = connected_at.isoformat() if connected_at else None

    return GSCStatusResponse(
        connected=bool(connection.get("access_token")),
        site_url=connection.get("site_url"),
        connected_at=connected_at_str,
        connected_by=connection.get("connected_by"),
    )


@router.get("/connect")
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("initiate GSC connect")
async def initiate_gsc_connect(
    request: Request,
    admin_user: str = Depends(require_admin_any),
) -> RedirectResponse:
    """Initiate Google OAuth flow for GSC access (admin only).

    Redirects to Google OAuth consent screen with webmasters.readonly scope.
    """
    settings = get_settings()

    if not settings.google_search_console_enabled:
        raise http_error(ErrorCode.FEATURE_DISABLED, "Search Console integration is disabled", 403)

    if not settings.google_oauth_client_id:
        raise http_error(ErrorCode.CONFIG_ERROR, "Google OAuth not configured", 500)

    # Create OAuth state for CSRF protection
    session_manager = get_session_manager()
    state = secrets.token_urlsafe(32)
    session_manager.set(
        key=f"gsc_oauth:{state}",
        value={"user_id": admin_user, "type": "gsc"},
        expiry=600,  # 10 minute expiry
    )

    # Build redirect URI
    redirect_uri = f"{settings.supertokens_api_domain}/api/v1/integrations/search-console/callback"

    # Get auth URL
    auth_url = get_auth_url(redirect_uri=redirect_uri, state=state)

    logger.info(f"Admin {admin_user} initiating GSC OAuth flow")
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback")
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("GSC oauth callback")
async def gsc_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Handle Google OAuth callback for GSC.

    Exchanges authorization code for tokens and stores them.
    """
    settings = get_settings()
    frontend_url = settings.frontend_url

    # Handle OAuth errors
    if error:
        logger.warning(f"GSC OAuth error: {error}")
        return RedirectResponse(
            url=f"{frontend_url}/admin/integrations?gsc_error={error}",
            status_code=302,
        )

    if not code or not state:
        log_error(
            logger,
            ErrorCode.EXT_API_ERROR,
            "GSC OAuth callback missing code or state",
            code=code,
            state_present=bool(state),
        )
        return RedirectResponse(
            url=f"{frontend_url}/admin/integrations?gsc_error=invalid_request",
            status_code=302,
        )

    # Validate state (CSRF protection)
    session_manager = get_session_manager()
    session_data = session_manager.get(f"gsc_oauth:{state}")

    if not session_data:
        log_error(
            logger,
            ErrorCode.EXT_API_ERROR,
            "GSC OAuth callback: invalid or expired state",
            state=state,
        )
        return RedirectResponse(
            url=f"{frontend_url}/admin/integrations?gsc_error=invalid_state",
            status_code=302,
        )

    user_id = session_data.get("user_id")
    if not user_id:
        log_error(
            logger,
            ErrorCode.EXT_API_ERROR,
            "GSC OAuth callback: missing user_id in state",
            state=state,
        )
        return RedirectResponse(
            url=f"{frontend_url}/admin/integrations?gsc_error=invalid_state",
            status_code=302,
        )

    # Clear the state
    session_manager.delete(f"gsc_oauth:{state}")

    # Exchange code for tokens
    try:
        redirect_uri = (
            f"{settings.supertokens_api_domain}/api/v1/integrations/search-console/callback"
        )
        tokens = exchange_code(code=code, redirect_uri=redirect_uri)

        # Encrypt tokens before storage
        try:
            service = get_encryption_service()
            encrypted_access = service.encrypt(tokens["access_token"])
            encrypted_refresh = (
                service.encrypt(tokens["refresh_token"]) if tokens.get("refresh_token") else None
            )
        except EncryptionError as e:
            logger.warning(f"Encryption unavailable, storing tokens plaintext: {e}")
            encrypted_access = tokens["access_token"]
            encrypted_refresh = tokens.get("refresh_token")

        # Store tokens with placeholder site_url (user will select later)
        gsc_repository.save_connection(
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            expires_at=tokens.get("expires_at"),
            site_url="",  # Will be selected in next step
            connected_by=user_id if user_id != "api_key" else "admin",
        )

        logger.info(f"Admin {user_id} connected GSC successfully")
        return RedirectResponse(
            url=f"{frontend_url}/admin/integrations?gsc_connected=true",
            status_code=302,
        )

    except GSCError as e:
        log_error(
            logger,
            ErrorCode.EXT_API_ERROR,
            f"GSC OAuth token exchange failed: {e}",
            user_id=user_id,
        )
        return RedirectResponse(
            url=f"{frontend_url}/admin/integrations?gsc_error=token_exchange_failed",
            status_code=302,
        )
    except Exception as e:
        logger.exception(f"Unexpected error in GSC OAuth callback: {e}")
        return RedirectResponse(
            url=f"{frontend_url}/admin/integrations?gsc_error=unexpected_error",
            status_code=302,
        )


@router.get("/sites", response_model=GSCSitesResponse)
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("list GSC sites")
async def list_gsc_sites(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> GSCSitesResponse:
    """List available GSC sites/properties (admin only).

    Returns sites that the connected account has access to.
    """
    settings = get_settings()

    if not settings.google_search_console_enabled:
        raise http_error(ErrorCode.FEATURE_DISABLED, "Search Console integration is disabled", 403)

    client = get_gsc_client()
    if not client:
        raise http_error(ErrorCode.NOT_FOUND, "GSC not connected", 404)

    try:
        sites = client.list_sites()
        return GSCSitesResponse(
            sites=[
                GSCSiteResponse(
                    site_url=site.get("siteUrl", ""),
                    permission_level=site.get("permissionLevel", "unknown"),
                )
                for site in sites
            ]
        )
    except GSCError as e:
        raise http_error(ErrorCode.EXT_API_ERROR, str(e), 502) from None


@router.patch("/site")
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("select GSC site")
async def select_gsc_site(
    request: Request,
    body: GSCSiteSelectRequest,
    _admin: str = Depends(require_admin_any),
) -> GSCStatusResponse:
    """Select which GSC site/property to track (admin only).

    Args:
        request: FastAPI request object
        body: Contains site_url to select

    Returns:
        Updated GSC status
    """
    settings = get_settings()

    if not settings.google_search_console_enabled:
        raise http_error(ErrorCode.FEATURE_DISABLED, "Search Console integration is disabled", 403)

    # Verify connection exists
    connection = gsc_repository.get_connection()
    if not connection:
        raise http_error(ErrorCode.NOT_FOUND, "GSC not connected", 404)

    # Update site URL
    gsc_repository.update_site_url(body.site_url)

    logger.info(f"GSC site selected: {body.site_url}")

    # Return updated status
    connection = gsc_repository.get_connection()
    connected_at = connection.get("connected_at") if connection else None
    connected_at_str = connected_at.isoformat() if connected_at else None

    return GSCStatusResponse(
        connected=True,
        site_url=body.site_url,
        connected_at=connected_at_str,
        connected_by=connection.get("connected_by") if connection else None,
    )


@router.delete("/disconnect")
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("disconnect GSC")
async def disconnect_gsc(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> dict:
    """Disconnect GSC integration (admin only).

    Clears stored tokens.

    Returns:
        success: True if disconnected successfully
    """
    gsc_repository.delete_connection()

    logger.info("GSC disconnected")
    return {"success": True}
