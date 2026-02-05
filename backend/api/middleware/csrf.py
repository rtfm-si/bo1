"""CSRF protection middleware using double-submit cookie pattern.

Protects non-SuperTokens routes from CSRF attacks. SuperTokens routes have
built-in anti-CSRF via anti-csrf header; this middleware covers custom endpoints.

Pattern:
- GET requests: Set csrf_token cookie (random 32-byte hex, httponly=False for JS access)
- POST/PUT/PATCH/DELETE: Verify X-CSRF-Token header matches csrf_token cookie
- Exempt paths: webhooks, health checks, CSP reports

SameSite=Lax already mitigates most cross-site attacks; this is defense-in-depth.
"""

import logging
import secrets
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Token configuration
CSRF_TOKEN_LENGTH = 32  # bytes (64 hex chars)
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_COOKIE_MAX_AGE = 86400  # 24 hours
CSRF_COOKIE_DELETE_AGE = 0  # Immediate expiry for deletion

# Methods requiring CSRF validation
CSRF_PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths exempt from CSRF (webhooks, health, browser-initiated reports)
CSRF_EXEMPT_PREFIXES = (
    "/api/health",
    "/api/ready",
    "/api/v1/webhooks/",
    "/api/v1/email/webhook",  # Resend webhook (verified via svix signature)
    "/api/v1/csp-report",
    "/api/v1/waitlist",  # Public form submission
    "/api/v1/metrics/client",  # Browser sendBeacon for observability metrics
    "/api/v1/analytics/",  # Public page analytics (uses sendBeacon, no user data mutation)
    "/api/v1/blog/posts/",  # Blog tracking (view/click counts, rate-limited, no user data)
    "/api/errors",  # Client error reporting (rate-limited, no auth, audit logging only)
    "/api/e2e/",  # E2E testing endpoints (protected by E2E_AUTH_SECRET)
)

# SuperTokens paths (have their own anti-csrf via 'anti-csrf' header)
SUPERTOKENS_PREFIXES = (
    "/auth/",
    "/api/auth/",  # SuperTokens mounted at /api/auth
)


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_hex(CSRF_TOKEN_LENGTH)


def set_csrf_cookie_on_response(
    response: Any,
    token: str,
    secure: bool = False,
    domain: str | None = None,
) -> None:
    """Set CSRF token cookie on a SuperTokens BaseResponse.

    Used by auth callbacks to rotate CSRF token on sign-in.

    Args:
        response: SuperTokens BaseResponse object
        token: The new CSRF token value
        secure: Whether to set Secure flag (True for HTTPS)
        domain: Cookie domain (e.g., '.boardof.one')
    """
    # SuperTokens BaseResponse uses expires (timestamp), not max_age
    import time

    expires = int(time.time()) + CSRF_COOKIE_MAX_AGE
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        expires=expires,
        path="/",
        domain=domain,
        secure=secure,
        httponly=False,  # JS must read this for X-CSRF-Token header
        samesite="lax",
    )
    logger.debug(f"Rotated CSRF token on auth state change (domain={domain})")


def clear_csrf_cookie_on_response(
    response: Any,
    secure: bool = False,
    domain: str | None = None,
) -> None:
    """Clear CSRF token cookie on a SuperTokens BaseResponse.

    Used by auth callbacks to clear CSRF token on sign-out.

    Args:
        response: SuperTokens BaseResponse object
        secure: Whether to set Secure flag (True for HTTPS)
        domain: Cookie domain (e.g., '.boardof.one')
    """
    import time

    # Expire immediately by setting expires to past
    expires = int(time.time()) - 1
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value="",
        expires=expires,
        path="/",
        domain=domain,
        secure=secure,
        httponly=False,
        samesite="lax",
    )
    logger.debug(f"Cleared CSRF token on sign-out (domain={domain})")


def is_exempt_path(path: str) -> bool:
    """Check if path is exempt from CSRF validation."""
    # Health/webhook/CSP paths
    if path.startswith(CSRF_EXEMPT_PREFIXES):
        return True
    # SuperTokens handles its own CSRF
    if path.startswith(SUPERTOKENS_PREFIXES):
        return True
    return False


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware using double-submit cookie pattern.

    For safe methods (GET, HEAD, OPTIONS):
        - Sets csrf_token cookie if not present
        - Cookie is httponly=False so frontend JS can read it

    For unsafe methods (POST, PUT, PATCH, DELETE):
        - Validates X-CSRF-Token header matches csrf_token cookie
        - Returns 403 if mismatch or missing
        - Exempt paths bypass validation
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        """Process request and apply CSRF protection."""
        path = request.url.path
        method = request.method

        # Skip CSRF for exempt paths
        if is_exempt_path(path):
            response: Response = await call_next(request)
            return response

        # For safe methods: ensure token cookie exists
        if method in ("GET", "HEAD", "OPTIONS"):
            response = await call_next(request)

            # Set CSRF cookie if not present (or refresh on GET)
            if method == "GET":
                existing_token = request.cookies.get(CSRF_COOKIE_NAME)
                if not existing_token:
                    token = generate_csrf_token()
                    response.set_cookie(
                        key=CSRF_COOKIE_NAME,
                        value=token,
                        max_age=CSRF_COOKIE_MAX_AGE,
                        httponly=False,  # JS must read this
                        samesite="lax",
                        secure=request.url.scheme == "https",
                        path="/",
                    )
                    logger.debug(f"Set CSRF token cookie for {path}")

            return response

        # For unsafe methods: validate CSRF token
        if method in CSRF_PROTECTED_METHODS:
            # Skip CSRF for API key authenticated requests (scripts/automation)
            if request.headers.get("X-Admin-Key"):
                api_response: Response = await call_next(request)
                return api_response

            cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
            header_token = request.headers.get(CSRF_HEADER_NAME)

            # Missing cookie
            if not cookie_token:
                logger.warning(f"CSRF validation failed: missing cookie for {method} {path}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "CSRF validation failed",
                        "message": "Missing CSRF token. Please refresh the page and try again.",
                        "type": "CSRFError",
                    },
                )

            # Missing header
            if not header_token:
                logger.warning(f"CSRF validation failed: missing header for {method} {path}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "CSRF validation failed",
                        "message": "Missing X-CSRF-Token header.",
                        "type": "CSRFError",
                    },
                )

            # Token mismatch (constant-time comparison)
            if not secrets.compare_digest(cookie_token, header_token):
                logger.warning(f"CSRF validation failed: token mismatch for {method} {path}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "CSRF validation failed",
                        "message": "Invalid CSRF token. Please refresh the page and try again.",
                        "type": "CSRFError",
                    },
                )

            logger.debug(f"CSRF validation passed for {method} {path}")

        final_response: Response = await call_next(request)
        return final_response
