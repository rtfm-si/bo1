"""Standardized API error handling utilities.

This module provides consistent error handling across all API endpoints with:
- Decorator for automatic exception handling
- Standard error responses with appropriate HTTP status codes
- Comprehensive error logging with context
- No stack trace leakage to clients
- Graceful degradation on failures

Usage:
    @router.post("/sessions")
    @handle_api_errors("create session")
    async def create_session(...):
        # Implementation - no try/except needed
        pass
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Literal, TypeVar

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Type alias for error categories
ErrorType = Literal[
    "redis_unavailable",
    "session_not_found",
    "unauthorized",
    "forbidden",
    "invalid_input",
    "not_found",
]

# Standard error responses (status_code, message)
ERROR_RESPONSES: dict[ErrorType, tuple[int, str]] = {
    "redis_unavailable": (
        500,
        "Service temporarily unavailable - please try again",
    ),
    "session_not_found": (404, "Session not found"),
    "unauthorized": (401, "Authentication required"),
    "forbidden": (403, "Access denied"),
    "invalid_input": (400, "Invalid input"),
    "not_found": (404, "Resource not found"),
}


def raise_api_error(
    error_type: ErrorType,
    detail: str | None = None,
) -> None:
    """Raise HTTPException with standardized error response.

    This provides a convenient way to raise HTTP errors with consistent
    status codes and messages across the API.

    Args:
        error_type: Category of error (determines status code)
        detail: Optional custom error message (overrides default)

    Raises:
        HTTPException with appropriate status code and message

    Examples:
        >>> raise_api_error("session_not_found")
        # Raises 404 with "Session not found"

        >>> raise_api_error("forbidden", "User lacks required permissions")
        # Raises 403 with custom message
    """
    status_code, default_detail = ERROR_RESPONSES[error_type]
    raise HTTPException(
        status_code=status_code,
        detail=detail or default_detail,
    )


F = TypeVar("F", bound=Callable)


def handle_api_errors(operation: str) -> Callable[[F], F]:
    """Decorator for consistent error handling in API endpoints.

    This decorator catches all exceptions and converts them to appropriate
    HTTPExceptions with proper status codes and logging:

    - HTTPException: Re-raised as-is (already formatted)
    - ValueError: Converted to 400 (invalid input)
    - KeyError: Converted to 404 (not found)
    - Exception: Converted to 500 (internal error)

    All errors are logged with context for debugging, but stack traces
    are never leaked to clients.

    Args:
        operation: Description of operation for logging (e.g., "create session")

    Returns:
        Decorated function with error handling

    Examples:
        @router.post("/sessions")
        @handle_api_errors("create session")
        async def create_session(request: CreateSessionRequest):
            # Implementation - exceptions automatically handled
            session_id = await create_new_session(request)
            return {"session_id": session_id}

        # ValueError in implementation → 400 response
        # KeyError in implementation → 404 response
        # Other exceptions → 500 response
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]  # noqa: ANN202, ANN002, ANN003
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTPException as-is (already formatted)
                raise
            except ValueError as e:
                # Business logic validation errors → 400
                logger.warning(
                    f"Validation error in {operation}: {e}",
                    extra={"operation": operation},
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid input: {str(e)}",
                ) from e
            except KeyError as e:
                # Missing data errors → 404
                logger.warning(
                    f"Not found in {operation}: {e}",
                    extra={"operation": operation},
                )
                raise HTTPException(
                    status_code=404,
                    detail=f"Resource not found: {str(e)}",
                ) from e
            except Exception as e:
                # Unexpected errors → 500
                logger.error(
                    f"Unexpected error in {operation}: {e}",
                    exc_info=True,
                    extra={"operation": operation},
                )
                raise HTTPException(
                    status_code=500,
                    detail="An unexpected error occurred",
                ) from e

        return wrapper  # type: ignore[return-value]

    return decorator
