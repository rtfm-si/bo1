"""Utility functions and decorators for API endpoints.

Provides:
- handle_api_errors: Decorator for standardized API error handling
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Type variable for the return type of wrapped functions
T = TypeVar("T")


def handle_api_errors(operation: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for standardized API error handling.

    Wraps endpoint functions to provide consistent error handling:
    - Passes through HTTPException (already handled by FastAPI)
    - Catches all other exceptions, logs them, and returns 500 error
    - Includes operation context in error messages

    Args:
        operation: Description of the operation (e.g., "start session", "get status")

    Returns:
        Decorator function that wraps the endpoint

    Examples:
        >>> @handle_api_errors("start session")
        ... async def start_session(session_id: str):
        ...     # ... endpoint logic
        ...     pass

        >>> @handle_api_errors("get session status")
        ... async def get_status(session_id: str):
        ...     # ... endpoint logic
        ...     pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Pass through HTTPExceptions (already handled by FastAPI)
                raise
            except Exception as e:
                # Log unexpected errors with full context
                logger.error(f"Failed to {operation}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to {operation}: {str(e)}",
                ) from e

        return wrapper

    return decorator
