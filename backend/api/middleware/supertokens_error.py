"""SuperTokens error handling utilities.

Provides enhanced logging and graceful degradation for SuperTokens session operations.
Returns 503 when SuperTokens Core is unavailable instead of 500.
"""

import logging

from fastapi import Request
from starlette.responses import JSONResponse

from bo1.logging.errors import ErrorCode, log_error

logger = logging.getLogger(__name__)

# SuperTokens Core unavailability indicators
SUPERTOKENS_CONNECTION_ERRORS = (
    "connection refused",
    "connection reset",
    "network unreachable",
    "host not found",
    "timeout",
    "connection error",
    "failed to connect",
    "could not connect",
    "httpx",  # httpx connection errors
    "aiohttp",  # aiohttp connection errors
)

# SuperTokens auth paths that should have enhanced error handling
SUPERTOKENS_PATHS = ("/api/auth/session/refresh", "/api/auth/signout")


def is_supertokens_connection_error(exc: Exception) -> bool:
    """Check if exception indicates SuperTokens Core connectivity issue.

    Args:
        exc: Exception to check

    Returns:
        True if this is a connection error, False otherwise
    """
    error_str = str(exc).lower()
    exc_type = type(exc).__name__.lower()

    return any(
        indicator in error_str or indicator in exc_type
        for indicator in SUPERTOKENS_CONNECTION_ERRORS
    )


def is_supertokens_path(path: str) -> bool:
    """Check if path is a SuperTokens auth path.

    Args:
        path: Request path

    Returns:
        True if path should have SuperTokens error handling
    """
    return any(path.startswith(p) for p in SUPERTOKENS_PATHS)


def handle_supertokens_error(request: Request, exc: Exception) -> JSONResponse | None:
    """Handle SuperTokens errors with graceful degradation.

    If the exception is a SuperTokens Core connectivity issue on an auth path,
    returns a 503 response. Otherwise returns None to let normal error handling apply.

    Args:
        request: FastAPI request
        exc: Exception that occurred

    Returns:
        JSONResponse with 503 if connection error on auth path, None otherwise
    """
    path = request.url.path

    # Only apply to SuperTokens auth paths
    if not is_supertokens_path(path):
        return None

    # Check if this is a connection error
    if not is_supertokens_connection_error(exc):
        # Log non-connection errors on auth paths
        log_error(
            logger,
            ErrorCode.SERVICE_DEPENDENCY_ERROR,
            f"SuperTokens error on {path}: {type(exc).__name__}: {exc}",
            path=path,
            method=request.method,
            exc_info=True,
        )
        return None

    # Log connection error
    log_error(
        logger,
        ErrorCode.SERVICE_DEPENDENCY_ERROR,
        f"SuperTokens Core unavailable: {exc}",
        path=path,
        method=request.method,
        client_ip=request.client.host if request.client else "unknown",
        exc_info=True,
    )

    # Return 503 Service Unavailable (graceful degradation)
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Authentication service temporarily unavailable",
            "error_code": "SERVICE_UNAVAILABLE",
            "message": "Please try again in a few moments",
        },
        headers={"Retry-After": "10"},
    )
