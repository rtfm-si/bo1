"""API version middleware for FastAPI.

Adds API-Version header to all responses for client version awareness.
Supports future API versioning and deprecation strategies.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Current API version
API_VERSION = "1.0"


class ApiVersionMiddleware(BaseHTTPMiddleware):
    """Add API-Version header to all responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request and add API-Version header to response.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response with API-Version header added
        """
        response = await call_next(request)
        response.headers["API-Version"] = API_VERSION
        return response
