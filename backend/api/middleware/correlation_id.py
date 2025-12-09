"""Correlation ID middleware for request tracing.

Generates or extracts X-Request-ID header for end-to-end request tracing.
Stores in request.state.request_id for downstream access.
Also sets contextvars for structured logging integration.
"""

import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from bo1.utils.logging import set_correlation_id

REQUEST_ID_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that ensures every request has a correlation ID."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process request and add correlation ID.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response with X-Request-ID header
        """
        # Extract from header or generate new UUID
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        # Store in request state for downstream access
        request.state.request_id = request_id

        # Set in contextvars for structured logging
        set_correlation_id(request_id)

        try:
            # Process request
            response = await call_next(request)

            # Add to response headers
            response.headers[REQUEST_ID_HEADER] = request_id

            return response
        finally:
            # Clear correlation ID after request
            set_correlation_id(None)
