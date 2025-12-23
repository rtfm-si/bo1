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
from typing import Any, Literal, TypedDict, TypeVar

from fastapi import HTTPException

from bo1.logging import ErrorCode, log_error


class ErrorDetailDict(TypedDict, total=False):
    """Structured error response format for HTTPException detail.

    All API errors should use this format for consistent client-side handling.
    The error_code enables log aggregation and programmatic error handling.
    """

    error_code: str  # Required: machine-readable error code from ErrorCode enum
    message: str  # Required: human-readable error message
    detail: dict[str, Any] | None  # Optional: additional context


def http_error(
    code: ErrorCode,
    message: str,
    status: int = 400,
    **context: Any,
) -> HTTPException:
    """Create HTTPException with structured error response.

    This is the preferred way to raise HTTP errors across all API endpoints.
    It ensures consistent error format with error_code for log aggregation
    and client-side error handling.

    Args:
        code: ErrorCode enum value for machine-readable error identification
        message: Human-readable error message
        status: HTTP status code (default 400)
        **context: Additional context fields to include in detail

    Returns:
        HTTPException with structured detail dict

    Examples:
        >>> raise http_error(ErrorCode.VALIDATION_ERROR, "Invalid session ID")
        # Raises 400 with {"error_code": "VALIDATION_ERROR", "message": "Invalid session ID"}

        >>> raise http_error(
        ...     ErrorCode.AUTH_TOKEN_ERROR,
        ...     "Session expired",
        ...     status=401,
        ...     session_id="abc123"
        ... )
        # Raises 401 with {"error_code": "AUTH_TOKEN_ERROR", "message": "Session expired", "session_id": "abc123"}
    """
    detail: dict[str, Any] = {
        "error_code": code.value,
        "message": message,
    }
    if context:
        detail.update(context)

    return HTTPException(status_code=status, detail=detail)


logger = logging.getLogger(__name__)

# Type alias for error categories
ErrorType = Literal[
    "redis_unavailable",
    "session_not_found",
    "unauthorized",
    "forbidden",
    "invalid_input",
    "not_found",
    "conflict",
    "service_unavailable",
    "gone",
    "rate_limited",
    "internal_error",
]

# Standard error responses: (status_code, default_message, error_code)
ERROR_RESPONSES: dict[ErrorType, tuple[int, str, str]] = {
    "redis_unavailable": (
        500,
        "Service temporarily unavailable - please try again",
        "redis_unavailable",
    ),
    "session_not_found": (404, "Session not found", "session_not_found"),
    "unauthorized": (401, "Authentication required", "unauthorized"),
    "forbidden": (403, "Access denied", "forbidden"),
    "invalid_input": (400, "Invalid input", "invalid_input"),
    "not_found": (404, "Resource not found", "not_found"),
    "conflict": (409, "Resource conflict", "conflict"),
    "service_unavailable": (503, "Service temporarily unavailable", "service_unavailable"),
    "gone": (410, "Resource no longer available", "gone"),
    "rate_limited": (429, "Rate limit exceeded", "rate_limited"),
    "internal_error": (500, "An unexpected error occurred", "internal_error"),
}


def raise_api_error(
    error_type: ErrorType,
    detail: str | None = None,
) -> None:
    """Raise HTTPException with standardized error response.

    This provides a convenient way to raise HTTP errors with consistent
    status codes, messages, and error codes across the API.

    Args:
        error_type: Category of error (determines status code and error_code)
        detail: Optional custom error message (overrides default)

    Raises:
        HTTPException with appropriate status code, message, and error_code

    Examples:
        >>> raise_api_error("session_not_found")
        # Raises 404 with {"detail": "Session not found", "error_code": "session_not_found"}

        >>> raise_api_error("forbidden", "User lacks required permissions")
        # Raises 403 with custom message and error_code "forbidden"
    """
    status_code, default_detail, error_code = ERROR_RESPONSES[error_type]
    raise HTTPException(
        status_code=status_code,
        detail={"detail": detail or default_detail, "error_code": error_code},
    )


F = TypeVar("F", bound=Callable)


def handle_api_errors(operation: str) -> Callable[[F], F]:
    """Decorator for consistent error handling in API endpoints.

    This decorator catches all exceptions and converts them to appropriate
    HTTPExceptions with proper status codes, error codes, and logging:

    - HTTPException: Re-raised as-is (already formatted)
    - ValueError: Converted to 400 (invalid input) with error_code "validation_error"
    - KeyError: Converted to 404 (not found) with error_code "not_found"
    - Exception: Converted to 500 (internal error) with error_code "internal_error"

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

        # ValueError in implementation → 400 response with error_code "validation_error"
        # KeyError in implementation → 404 response with error_code "not_found"
        # Other exceptions → 500 response with error_code "internal_error"
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
                    detail={
                        "detail": f"Invalid input: {str(e)}",
                        "error_code": "validation_error",
                    },
                ) from e
            except KeyError as e:
                # Missing data errors → 404
                logger.warning(
                    f"Not found in {operation}: {e}",
                    extra={"operation": operation},
                )
                raise HTTPException(
                    status_code=404,
                    detail={
                        "detail": f"Resource not found: {str(e)}",
                        "error_code": "not_found",
                    },
                ) from e
            except Exception as e:
                # Unexpected errors → 500
                log_error(
                    logger,
                    ErrorCode.API_REQUEST_ERROR,
                    f"Unexpected error in {operation}: {e}",
                    exc_info=True,
                    operation=operation,
                )
                raise HTTPException(
                    status_code=500,
                    detail={
                        "detail": "An unexpected error occurred",
                        "error_code": "internal_error",
                    },
                ) from e

        return wrapper  # type: ignore[return-value]

    return decorator
