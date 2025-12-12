"""Security headers middleware for FastAPI.

Adds essential security headers to all HTTP responses to protect against
common web vulnerabilities (XSS, clickjacking, MIME-sniffing, etc).

Headers added:
- X-Frame-Options: DENY - Prevents clickjacking attacks
- X-Content-Type-Options: nosniff - Prevents MIME-sniffing attacks
- X-XSS-Protection: 1; mode=block - Legacy XSS protection for old browsers
- Referrer-Policy: strict-origin-when-cross-origin - Controls referrer information leakage
- Permissions-Policy: Disables unnecessary browser APIs (geolocation, microphone, camera)
- Strict-Transport-Security: Force HTTPS in production (HSTS)
- Content-Security-Policy: Minimal CSP for JSON-only API (production only)

Note: Main CSP with nonce-based script loading is handled by SvelteKit frontend.
"""

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from bo1.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all HTTP responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request and add security headers to response.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response with security headers added
        """
        response = await call_next(request)
        settings = get_settings()

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS protection (legacy, but good for old browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Disable access to sensitive browser APIs
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # HSTS - Force HTTPS in production (not in dev)
        if not settings.debug:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

            # Note: CSP is handled by SvelteKit with nonce-based script loading
            # API endpoints return JSON only, so minimal CSP is sufficient
            csp_header = "default-src 'none'; frame-ancestors 'none'"
            response.headers["Content-Security-Policy"] = csp_header

        return response


def add_security_headers_middleware(app: FastAPI) -> None:
    """Add security headers middleware to FastAPI app.

    This should be added EARLY in the middleware stack, before CORS.
    Middleware is executed in reverse order of registration, so this
    should be registered AFTER CORS to run BEFORE it.
    """
    app.add_middleware(SecurityHeadersMiddleware)
