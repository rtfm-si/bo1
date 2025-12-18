"""Deprecation utilities for API endpoints.

Provides decorator and helpers for marking endpoints as deprecated
with proper HTTP headers per RFC 8594.

See docs/adr/004-api-versioning.md for deprecation policy.
"""

import logging
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any

from fastapi import Request, Response
from fastapi.routing import APIRoute

logger = logging.getLogger(__name__)


def deprecated(
    sunset_date: str,
    message: str,
    replacement: str | None = None,
) -> Callable:
    """Mark an endpoint as deprecated.

    Adds RFC 8594 deprecation headers to responses and logs usage.

    Args:
        sunset_date: ISO date when endpoint will be removed (YYYY-MM-DD)
        message: Human-readable deprecation notice
        replacement: Optional replacement endpoint path

    Returns:
        Decorator function

    Example:
        @router.get("/old-endpoint")
        @deprecated(
            sunset_date="2025-06-01",
            message="Use /api/v2/new-endpoint instead",
            replacement="/api/v2/new-endpoint"
        )
        async def old_endpoint():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Find request and response objects from args/kwargs
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")

            # Call the original function
            result = await func(*args, **kwargs)

            # If result is a Response, add headers directly
            if isinstance(result, Response):
                _add_deprecation_headers(result, sunset_date, message)
                _log_deprecated_usage(request, func.__name__, sunset_date, replacement)
                return result

            # Otherwise, we can't add headers here - they'll be added by middleware
            # Log the usage regardless
            _log_deprecated_usage(request, func.__name__, sunset_date, replacement)
            return result

        # Mark the function as deprecated for introspection
        wrapper._deprecated = True
        wrapper._sunset_date = sunset_date
        wrapper._deprecation_message = message
        wrapper._replacement = replacement

        return wrapper

    return decorator


def _add_deprecation_headers(
    response: Response,
    sunset_date: str,
    message: str,
) -> None:
    """Add RFC 8594 deprecation headers to response.

    Args:
        response: FastAPI/Starlette Response object
        sunset_date: ISO date string (YYYY-MM-DD)
        message: Human-readable deprecation notice
    """
    # Deprecation header (RFC 8594)
    response.headers["Deprecation"] = "true"

    # Sunset header with HTTP-date format (RFC 8594)
    try:
        dt = datetime.fromisoformat(sunset_date)
        sunset_http_date = dt.strftime("%a, %d %b %Y 00:00:00 GMT")
        response.headers["Sunset"] = sunset_http_date
    except ValueError:
        logger.warning(f"Invalid sunset_date format: {sunset_date}")

    # Human-readable notice
    response.headers["X-Deprecation-Notice"] = message


def _log_deprecated_usage(
    request: Request | None,
    endpoint_name: str,
    sunset_date: str,
    replacement: str | None,
) -> None:
    """Log usage of deprecated endpoint for analytics.

    Args:
        request: HTTP request (may be None)
        endpoint_name: Name of the deprecated function
        sunset_date: When endpoint will be removed
        replacement: Suggested replacement endpoint
    """
    path = request.url.path if request else "unknown"
    user_id = None
    if request and hasattr(request.state, "user_id"):
        user_id = request.state.user_id

    logger.warning(
        "deprecated_endpoint_called",
        extra={
            "endpoint": endpoint_name,
            "path": path,
            "sunset_date": sunset_date,
            "replacement": replacement,
            "user_id": user_id,
        },
    )


class DeprecatedRoute(APIRoute):
    """Custom route class that adds deprecation headers to all responses.

    Use this when you need to deprecate an entire router or set of routes.

    Example:
        router = APIRouter(route_class=DeprecatedRoute)
        router.deprecated_config = {
            "sunset_date": "2025-06-01",
            "message": "This API version is deprecated"
        }
    """

    def get_route_handler(self) -> Callable:
        """Return custom route handler that adds deprecation headers."""
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            response = await original_route_handler(request)

            # Add deprecation headers if configured
            if hasattr(self, "deprecated_config"):
                config = self.deprecated_config
                _add_deprecation_headers(
                    response,
                    config.get("sunset_date", ""),
                    config.get("message", "This endpoint is deprecated"),
                )

            return response

        return custom_route_handler
