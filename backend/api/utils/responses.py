"""Reusable OpenAPI response definitions for consistent API documentation.

This module provides pre-configured response schemas that can be added to
FastAPI route decorators via the `responses` parameter.

Usage:
    from backend.api.utils.responses import (
        ERROR_400_RESPONSE,
        ERROR_404_RESPONSE,
        ERROR_403_RESPONSE,
        RATE_LIMIT_RESPONSE,
    )

    @router.get(
        "/sessions/{session_id}",
        responses={
            404: ERROR_404_RESPONSE,
            403: ERROR_403_RESPONSE,
        }
    )
    async def get_session(session_id: str):
        ...

    @router.post("/endpoint", responses={429: RATE_LIMIT_RESPONSE})
    @limiter.limit("10/minute")
    async def my_endpoint():
        ...
"""

from typing import Any

from backend.api.models import (
    BadRequestErrorResponse,
    ConflictErrorResponse,
    ForbiddenErrorResponse,
    GoneErrorResponse,
    InternalErrorResponse,
    NotFoundErrorResponse,
    RateLimitResponse,
    UnauthorizedErrorResponse,
)

# Pre-configured error responses for OpenAPI documentation
# Use these in `responses={status: RESPONSE}` on route decorators

ERROR_400_RESPONSE: dict[str, Any] = {
    "model": BadRequestErrorResponse,
    "description": "Bad request - validation failed or invalid parameters",
}

ERROR_401_RESPONSE: dict[str, Any] = {
    "model": UnauthorizedErrorResponse,
    "description": "Unauthorized - authentication required or invalid",
}

ERROR_403_RESPONSE: dict[str, Any] = {
    "model": ForbiddenErrorResponse,
    "description": "Forbidden - user lacks permission to access this resource",
}

ERROR_404_RESPONSE: dict[str, Any] = {
    "model": NotFoundErrorResponse,
    "description": "Not found - the requested resource does not exist",
}

ERROR_409_RESPONSE: dict[str, Any] = {
    "model": ConflictErrorResponse,
    "description": "Conflict - request conflicts with current resource state",
}

ERROR_410_RESPONSE: dict[str, Any] = {
    "model": GoneErrorResponse,
    "description": "Gone - resource no longer available (e.g., expired invitation)",
}

ERROR_500_RESPONSE: dict[str, Any] = {
    "model": InternalErrorResponse,
    "description": "Internal server error - an unexpected error occurred",
}

# Pre-configured 429 response for OpenAPI documentation
# Add to any endpoint decorated with @limiter.limit()
RATE_LIMIT_RESPONSE: dict[str, Any] = {
    "model": RateLimitResponse,
    "description": "Rate limit exceeded. The Retry-After header indicates when to retry.",
    "headers": {
        "Retry-After": {
            "description": "Number of seconds until the rate limit window resets",
            "schema": {"type": "integer", "example": 60},
        }
    },
}
