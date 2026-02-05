"""Impersonation middleware for admin user view-as functionality.

This middleware:
1. Checks if the admin has an active impersonation session
2. Swaps request.state.user_id to the target user
3. Sets request.state.is_impersonation = True
4. Blocks mutations if write_mode=False

Usage:
    @app.middleware("http")
    async def impersonation_middleware(request, call_next):
        return await apply_impersonation(request, call_next)
"""

import logging
from typing import Any

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from supertokens_python.recipe.session.asyncio import get_session

from backend.services.admin_impersonation import get_active_impersonation

logger = logging.getLogger(__name__)

# HTTP methods that modify data
MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths that are always allowed even in read-only mode
# (e.g., ending impersonation, checking status)
IMPERSONATION_ALLOWED_PATHS = {
    "/api/admin/impersonate",
    "/api/admin/impersonate/status",
}


class ImpersonationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle admin impersonation of users."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Check impersonation state and modify request context.

        If admin is impersonating:
        - Sets request.state.is_impersonation = True
        - Sets request.state.impersonation_admin_id = original admin ID
        - Sets request.state.impersonation_target_id = target user ID
        - Sets request.state.impersonation_write_mode = True/False
        - Blocks mutations if write_mode=False
        """
        # Skip impersonation check for non-API routes
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        # Initialize impersonation state
        request.state.is_impersonation = False
        request.state.impersonation_admin_id = None
        request.state.impersonation_target_id = None
        request.state.impersonation_write_mode = False

        # Get admin user ID from SuperTokens session
        # We need to verify the session here to get the user ID
        try:
            st_session = await get_session(request, session_required=False)
            if st_session is None:
                # No valid session, continue without impersonation
                return await call_next(request)
            admin_id = st_session.get_user_id()
        except Exception as e:
            # Session verification failed (expired, invalid, etc.)
            # Continue without impersonation - let endpoint handle auth
            logger.debug(f"Session verification in impersonation middleware failed: {e}")
            return await call_next(request)

        if not admin_id:
            # No user logged in, continue without impersonation
            return await call_next(request)

        # Check if user is admin from session claim (added at login)
        # This avoids DB/Redis lookup for non-admin users (99%+ of requests)
        try:
            access_token_payload = st_session.get_access_token_payload()
            is_admin = access_token_payload.get("is_admin", False)
        except Exception:
            is_admin = False

        if not is_admin:
            # Non-admin users can't impersonate, skip lookup entirely
            return await call_next(request)

        # Check if this admin has an active impersonation session
        # Cache result in request.state to avoid duplicate DB queries in /me endpoint
        impersonation_session = get_active_impersonation(admin_id)
        request.state.impersonation_session_cached = impersonation_session
        if not impersonation_session:
            # No active impersonation, continue normally
            return await call_next(request)

        # Admin is impersonating - set state
        request.state.is_impersonation = True
        request.state.impersonation_admin_id = admin_id
        request.state.impersonation_target_id = impersonation_session.target_user_id
        request.state.impersonation_write_mode = impersonation_session.is_write_mode

        # Check if this is a mutation in read-only mode
        if request.method in MUTATION_METHODS and not impersonation_session.is_write_mode:
            # Allow certain paths even in read-only mode
            if not any(request.url.path.startswith(p) for p in IMPERSONATION_ALLOWED_PATHS):
                logger.warning(
                    f"Admin {admin_id} blocked from {request.method} {request.url.path} "
                    f"while impersonating {impersonation_session.target_user_id} (read-only mode)"
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Impersonation session is read-only. Cannot perform mutations.",
                        "error_code": "IMPERSONATION_READ_ONLY",
                    },
                )

        logger.debug(
            f"Request from admin {admin_id} impersonating {impersonation_session.target_user_id} "
            f"(write_mode={impersonation_session.is_write_mode})"
        )

        return await call_next(request)


def get_effective_user_id(request: Request) -> str | None:
    """Get the effective user ID, accounting for impersonation.

    Use this function in endpoints that need to act as the impersonated user.

    Args:
        request: FastAPI request object

    Returns:
        Target user ID if impersonating, otherwise actual user ID
    """
    if getattr(request.state, "is_impersonation", False):
        return request.state.impersonation_target_id
    return getattr(request.state, "user_id", None)


def get_real_admin_id(request: Request) -> str | None:
    """Get the real admin ID during impersonation.

    Use this for audit logging during impersonation.

    Args:
        request: FastAPI request object

    Returns:
        Admin user ID if impersonating, otherwise None
    """
    if getattr(request.state, "is_impersonation", False):
        return request.state.impersonation_admin_id
    return None


def is_impersonating(request: Request) -> bool:
    """Check if the current request is from an impersonating admin.

    Args:
        request: FastAPI request object

    Returns:
        True if impersonating, False otherwise
    """
    return getattr(request.state, "is_impersonation", False)


def require_write_mode(request: Request) -> None:
    """Raise exception if impersonating in read-only mode.

    Use this as an additional check in sensitive endpoints.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: 403 if in read-only impersonation mode
    """
    if getattr(request.state, "is_impersonation", False):
        if not getattr(request.state, "impersonation_write_mode", False):
            raise HTTPException(
                status_code=403,
                detail="This action requires write mode impersonation",
            )


def get_impersonation_context(request: Request) -> dict[str, Any] | None:
    """Get full impersonation context for audit logging.

    Args:
        request: FastAPI request object

    Returns:
        Dict with impersonation details, or None if not impersonating
    """
    if not getattr(request.state, "is_impersonation", False):
        return None

    return {
        "is_impersonation": True,
        "admin_id": request.state.impersonation_admin_id,
        "target_id": request.state.impersonation_target_id,
        "write_mode": request.state.impersonation_write_mode,
    }
