"""Degraded mode middleware.

Returns 503 for write operations when LLM providers are unavailable.
Allows read-only operations to continue.
"""

import logging
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.services.service_monitor import ServiceStatus, get_service_monitor
from backend.services.vendor_health import HealthStatus, get_vendor_health_tracker

logger = logging.getLogger(__name__)

# Paths that require LLM providers (write operations)
LLM_REQUIRED_PATHS = [
    "/api/v1/sessions",  # POST to create new meeting
    "/api/v1/datasets/{dataset_id}/ask",  # POST for dataset Q&A
]

# Methods that are read-only (always allowed)
READ_ONLY_METHODS = {"GET", "HEAD", "OPTIONS"}

# Paths always allowed (health, status, auth)
ALWAYS_ALLOWED_PATHS = [
    "/api/health",
    "/api/ready",
    "/api/v1/status",
    "/api/admin",
    "/auth",
    "/docs",
    "/openapi.json",
]


def _is_llm_required(request: Request) -> bool:
    """Check if request requires LLM providers."""
    # Read-only methods always allowed
    if request.method in READ_ONLY_METHODS:
        return False

    # Check path patterns
    path = request.url.path

    # Always allowed paths
    for allowed in ALWAYS_ALLOWED_PATHS:
        if path.startswith(allowed):
            return False

    # Check LLM-required paths
    for pattern in LLM_REQUIRED_PATHS:
        # Simple pattern matching (no regex for performance)
        if "{" in pattern:
            # Path with parameter - check prefix
            prefix = pattern.split("{")[0]
            if path.startswith(prefix):
                return True
        elif path == pattern or path.startswith(pattern + "/"):
            return True

    # POST/PUT/PATCH to sessions or datasets Q&A require LLM
    if request.method in {"POST", "PUT", "PATCH"}:
        if "/sessions" in path or "/ask" in path:
            return True

    return False


def _check_llm_availability() -> tuple[bool, str | None]:
    """Check if LLM providers are available.

    Returns:
        (is_available, error_message)
    """
    tracker = get_vendor_health_tracker()
    monitor = get_service_monitor()

    # Check vendor health
    vendor_status = tracker.get_overall_status()
    if vendor_status == HealthStatus.UNHEALTHY:
        return False, "LLM providers are currently unavailable"

    # Check service monitor for critical services
    service_status = monitor.get_overall_status()
    if service_status == ServiceStatus.OUTAGE:
        return False, "Critical services are experiencing an outage"

    return True, None


class DegradedModeMiddleware(BaseHTTPMiddleware):
    """Middleware to handle degraded mode.

    When LLM providers are unavailable:
    - Returns 503 for operations requiring LLM
    - Allows read-only operations
    - Adds X-Service-Status header to all responses
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request with degraded mode checks."""
        # Get current status for header
        monitor = get_service_monitor()
        service_status = monitor.get_overall_status()

        # Check if this request requires LLM
        if _is_llm_required(request):
            is_available, error_message = _check_llm_availability()

            if not is_available:
                logger.warning(
                    f"Degraded mode: Rejecting {request.method} {request.url.path} - {error_message}"
                )
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": error_message,
                        "status": "service_unavailable",
                        "retry_after": 60,
                    },
                    headers={
                        "X-Service-Status": service_status.value,
                        "Retry-After": "60",
                    },
                )

        # Process request normally
        response = await call_next(request)

        # Add service status header
        response.headers["X-Service-Status"] = service_status.value

        return response
