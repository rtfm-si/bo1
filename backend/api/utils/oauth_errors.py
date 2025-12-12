"""OAuth error sanitization utilities.

Sanitizes internal OAuth error messages to prevent information disclosure
about auth flow state, whitelist status, lockout details, etc.
"""

import logging
import uuid

logger = logging.getLogger(__name__)

# Mapping of internal error patterns to safe, user-friendly codes
# Keys are substrings to match in the original error; values are safe codes
INTERNAL_ERROR_PATTERNS: dict[str, str] = {
    # Google OAuth errors
    "access_denied": "access_denied",
    "invalid_grant": "auth_failed",
    "invalid_request": "auth_failed",
    "invalid_scope": "auth_failed",
    "unauthorized_client": "config_error",
    "unsupported_response_type": "config_error",
    "server_error": "auth_failed",
    "temporarily_unavailable": "auth_failed",
    # Internal flow errors
    "missing_params": "auth_failed",
    "invalid_state": "session_expired",
    "token_exchange_failed": "auth_failed",
    "no_access_token": "auth_failed",
    "request_failed": "auth_failed",
    # Rate limiting / lockout
    "too many": "rate_limited",
    "locked": "rate_limited",
    "lockout": "rate_limited",
    # Whitelist / access control (hide details)
    "whitelist": "access_denied",
    "not authorized": "access_denied",
    "not allowed": "access_denied",
}

# Safe error codes with user-friendly descriptions
SAFE_ERROR_CODES: dict[str, str] = {
    "auth_failed": "Authentication failed. Please try again.",
    "access_denied": "Access denied. Please contact support if you believe this is an error.",
    "config_error": "Service configuration error. Please try again later.",
    "session_expired": "Your session has expired. Please try again.",
    "rate_limited": "Too many attempts. Please try again later.",
}


def sanitize_oauth_error(error: str, log_correlation: bool = True) -> str:
    """Sanitize OAuth error message to prevent information disclosure.

    Converts internal error details to generic, user-safe error codes.
    Logs the original error with a correlation ID for debugging.

    Args:
        error: Original error message (may contain internal details)
        log_correlation: Whether to log the sanitized mapping (default True)

    Returns:
        Safe error code (one of SAFE_ERROR_CODES keys)
    """
    if not error:
        return "auth_failed"

    error_lower = error.lower()
    correlation_id = str(uuid.uuid4())[:8] if log_correlation else None

    # Check for known patterns
    for pattern, safe_code in INTERNAL_ERROR_PATTERNS.items():
        if pattern in error_lower:
            if log_correlation:
                logger.info(
                    f"OAuth error sanitized: correlation_id={correlation_id}, "
                    f"original='{error[:100]}', sanitized='{safe_code}'"
                )
            return safe_code

    # Unknown error - default to generic auth_failed
    if log_correlation:
        logger.warning(
            f"Unknown OAuth error sanitized: correlation_id={correlation_id}, "
            f"original='{error[:100]}', sanitized='auth_failed'"
        )
    return "auth_failed"


def get_user_friendly_message(error_code: str) -> str:
    """Get user-friendly message for a safe error code.

    Args:
        error_code: One of SAFE_ERROR_CODES keys

    Returns:
        Human-readable error message
    """
    return SAFE_ERROR_CODES.get(error_code, SAFE_ERROR_CODES["auth_failed"])


def sanitize_supertokens_message(message: str) -> str:
    """Sanitize SuperTokens error messages for user display.

    Replaces verbose internal messages with generic safe alternatives.

    Args:
        message: Original SuperTokens error message

    Returns:
        Safe, user-friendly message
    """
    message_lower = message.lower()

    # Whitelist rejection
    if "whitelist" in message_lower or "closed beta" in message_lower:
        return "Access denied. Contact support."

    # Account locked/deleted
    if "locked" in message_lower or "deleted" in message_lower:
        return "Account unavailable. Contact support."

    # Rate limiting / lockout
    if "too many" in message_lower or "try again" in message_lower:
        return "Too many attempts. Try again later."

    # Generic fallback
    return "Authentication failed. Please try again."
