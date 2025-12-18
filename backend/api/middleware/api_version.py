"""API version middleware for FastAPI.

Adds API-Version header to all responses for client version awareness.
Supports version negotiation via Accept-Version or X-API-Version headers.

See docs/adr/004-api-versioning.md for versioning strategy.
"""

import logging
import re

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Current API version
API_VERSION = "1.0"

# Supported versions (for validation)
SUPPORTED_VERSIONS = {"1.0"}

# Version pattern: major.minor (e.g., "1.0", "2.1")
VERSION_PATTERN = re.compile(r"^\d+\.\d+$")


def parse_version_header(request: Request) -> str | None:
    """Extract API version from request headers.

    Checks Accept-Version first, then X-API-Version as fallback.

    Args:
        request: Incoming HTTP request

    Returns:
        Version string if found and valid format, None otherwise
    """
    version = request.headers.get("Accept-Version") or request.headers.get("X-API-Version")
    if version and VERSION_PATTERN.match(version):
        return version
    return None


class ApiVersionMiddleware(BaseHTTPMiddleware):
    """Add API-Version header to all responses and log version usage."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request and add API-Version header to response.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response with API-Version header added
        """
        # Parse requested version from headers
        requested_version = parse_version_header(request)

        # Store version in request state for downstream use
        request.state.api_version = requested_version or API_VERSION

        # Log version usage for analytics (only for API requests)
        if request.url.path.startswith("/api/"):
            logger.debug(
                "api_version_request",
                extra={
                    "requested_version": requested_version,
                    "effective_version": request.state.api_version,
                    "path": request.url.path,
                },
            )

        response = await call_next(request)

        # Add version header to response
        response.headers["API-Version"] = API_VERSION

        return response
