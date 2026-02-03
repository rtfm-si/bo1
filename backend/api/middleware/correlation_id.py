"""Correlation ID middleware for request tracing.

Generates or extracts X-Request-ID header for end-to-end request tracing.
Stores in request.state.request_id for downstream access.
Also sets contextvars for structured logging integration.

When OpenTelemetry tracing is enabled, uses the trace ID as correlation ID
to unify distributed tracing with request correlation.
"""

import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from bo1.utils.logging import set_correlation_id

REQUEST_ID_HEADER = "X-Request-ID"


def _get_otel_trace_id() -> str | None:
    """Extract current OpenTelemetry trace ID if tracing is enabled.

    Returns:
        Trace ID as hex string, or None if tracing disabled or no active span
    """
    try:
        from bo1.observability.tracing import is_tracing_enabled

        if not is_tracing_enabled():
            return None

        from opentelemetry import trace

        span = trace.get_current_span()
        if span is None:
            return None

        ctx = span.get_span_context()
        if ctx.trace_id == 0:
            return None

        # Format as 32-char hex string (standard OTEL format)
        return format(ctx.trace_id, "032x")
    except Exception:
        return None


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that ensures every request has a correlation ID.

    When OpenTelemetry is enabled, prefers the trace ID to unify
    distributed tracing with request correlation.
    """

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
        # Prefer OTEL trace ID when tracing enabled, then header, then generate
        otel_trace_id = _get_otel_trace_id()
        if otel_trace_id:
            request_id = otel_trace_id
        else:
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
