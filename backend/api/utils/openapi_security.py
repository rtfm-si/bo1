"""OpenAPI security scheme utilities for auto-documenting protected routes.

This module provides FastAPI Security dependencies that automatically add
security requirements to OpenAPI spec for protected routes.

Usage:
    from backend.api.utils.openapi_security import require_session_auth, require_csrf

    @router.get("/protected")
    async def protected_route(
        user: dict = Depends(require_session_auth),
    ):
        ...

    @router.post("/mutating")
    async def mutating_route(
        user: dict = Depends(require_session_auth),
        _csrf: str | None = Depends(require_csrf),
    ):
        ...

The security schemes (sessionAuth, csrfToken) are defined in main.py's custom_openapi().
These dependencies just attach the security requirements to specific routes.
"""

from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import APIKeyCookie, APIKeyHeader

from backend.api.middleware.auth import get_current_user

# Security scheme instances - these register in OpenAPI spec
# scheme_name must match the key in main.py's securitySchemes
session_auth_scheme = APIKeyCookie(
    name="sAccessToken",
    scheme_name="sessionAuth",
    description=(
        "SuperTokens session cookie. Set automatically after OAuth login. "
        "Contains encrypted session token validated on each request."
    ),
    auto_error=False,  # Don't auto-error; let get_current_user handle auth
)

csrf_scheme = APIKeyHeader(
    name="X-CSRF-Token",
    scheme_name="csrfToken",
    description=(
        "CSRF protection token. Must match the value in the csrf_token cookie. "
        "Required for all mutating requests (POST, PUT, DELETE, PATCH)."
    ),
    auto_error=False,  # CSRF is enforced by middleware, not this dependency
)


async def require_session_auth(
    request: Request,
    _session_cookie: Annotated[str | None, Depends(session_auth_scheme)] = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Dependency that requires session authentication and documents it in OpenAPI.

    This wraps get_current_user to add sessionAuth security scheme to the route's
    OpenAPI spec. The actual authentication is handled by get_current_user.

    Args:
        request: FastAPI request object
        _session_cookie: Session cookie (used for OpenAPI documentation only)
        user: Authenticated user from get_current_user

    Returns:
        Authenticated user data dict
    """
    return user


async def require_csrf(
    _csrf_token: Annotated[str | None, Depends(csrf_scheme)] = None,
) -> str | None:
    """Dependency that documents CSRF token requirement in OpenAPI.

    This dependency is for OpenAPI documentation only - actual CSRF validation
    is handled by the CSRFMiddleware. Adding this dependency to a route will
    show the csrfToken security requirement in the OpenAPI spec.

    Args:
        _csrf_token: CSRF token from header (used for OpenAPI documentation only)

    Returns:
        The CSRF token value (or None if not provided)
    """
    return _csrf_token


# Type aliases for cleaner route signatures
SessionAuthDep = Annotated[dict[str, Any], Depends(require_session_auth)]
CSRFTokenDep = Annotated[str | None, Depends(require_csrf)]
