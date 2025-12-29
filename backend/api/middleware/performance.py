"""Performance monitoring middleware for FastAPI.

Tracks request duration, counts, and error rates per endpoint.
Pushes metrics to PerformanceMonitor for trend analysis.
"""

import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Paths to exclude from performance tracking
EXCLUDED_PATHS = {
    "/health",
    "/ready",
    "/metrics",
    "/api/health",
    "/api/ready",
    "/favicon.ico",
}


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track request performance metrics.

    Records:
    - Request duration per endpoint
    - Error counts per endpoint
    - Overall error rate
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request and record metrics."""
        path = request.url.path

        # Skip excluded paths
        if path in EXCLUDED_PATHS:
            return await call_next(request)

        start_time = time.time()
        response: Response | None = None
        error_occurred = False

        try:
            response = await call_next(request)
            if response.status_code >= 500:
                error_occurred = True
            return response
        except Exception:
            error_occurred = True
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000

            # Record metrics asynchronously (non-blocking)
            try:
                self._record_metrics(path, duration_ms, error_occurred)
            except Exception as e:
                # Never let metrics recording break request handling
                logger.debug(f"Failed to record performance metrics: {e}")

    def _record_metrics(self, path: str, duration_ms: float, is_error: bool) -> None:
        """Record metrics to PerformanceMonitor.

        Args:
            path: Request path
            duration_ms: Request duration in milliseconds
            is_error: Whether request resulted in error (5xx)
        """
        # Import here to avoid circular imports
        from backend.services.performance_monitor import record_metric

        # Normalize path for low cardinality
        normalized_path = self._normalize_path(path)

        # Record response time
        record_metric(
            name="api_response_time_ms",
            value=duration_ms,
            source=normalized_path,
            labels={"endpoint": normalized_path},
        )

        # Track error/success for error rate calculation
        if is_error:
            record_metric(
                name="api_error_count",
                value=1,
                source=normalized_path,
            )
        else:
            record_metric(
                name="api_success_count",
                value=1,
                source=normalized_path,
            )

    def _normalize_path(self, path: str) -> str:
        """Normalize path to reduce cardinality.

        Replaces UUIDs and IDs with placeholders.
        """
        import re

        # Replace UUIDs
        path = re.sub(r"/[a-f0-9-]{36}", "/:id", path)
        # Replace numeric IDs
        path = re.sub(r"/\d+", "/:id", path)
        return path


def calculate_error_rate() -> float:
    """Calculate current error rate as a percentage.

    Uses the last 5 minutes of data.

    Returns:
        Error rate as percentage (0-100)
    """
    from backend.services.performance_monitor import get_performance_monitor

    monitor = get_performance_monitor()

    # Get error and success counts from last 5 minutes
    error_values = monitor.get_metric_values("api_error_count", 5)
    success_values = monitor.get_metric_values("api_success_count", 5)

    error_count = sum(v[0] for v in error_values)
    success_count = sum(v[0] for v in success_values)
    total = error_count + success_count

    if total == 0:
        return 0.0

    return (error_count / total) * 100


def push_error_rate_metric() -> None:
    """Push current error rate as a metric.

    Should be called periodically (e.g., every minute).
    """
    from backend.services.performance_monitor import record_metric

    error_rate = calculate_error_rate()
    record_metric(
        name="error_rate_percent",
        value=error_rate,
        source="calculated",
    )
