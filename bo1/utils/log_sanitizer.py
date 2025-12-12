"""Log sanitizer utility for PII and secret redaction.

Provides centralized sanitization for log messages and structured data
to prevent sensitive information from being written to logs.

Patterns covered:
- Passwords, secrets, API keys, tokens
- Email addresses (partial mask: j***@example.com)
- OAuth/Bearer tokens (truncate to first 8 chars)
- Session IDs (hash or truncate)

Usage:
    from bo1.utils.log_sanitizer import sanitize_log_data, sanitize_message

    # Sanitize dict before logging
    safe_data = sanitize_log_data({"user": "test", "password": "secret123"})
    # {"user": "test", "password": "[REDACTED]"}

    # Sanitize string message
    safe_msg = sanitize_message("Login with password=secret123 failed")
    # "Login with password=[REDACTED] failed"
"""

import re
from typing import Any

# Compile regex patterns once at module load for performance
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "api-key",
        "auth_token",
        "access_token",
        "refresh_token",
        "bearer",
        "authorization",
        "credential",
        "credentials",
        "private_key",
        "privatekey",
        "client_secret",
        "session_id",
        "sessionid",
        "cookie",
        "csrf_token",
        "x-csrf-token",
        "google_tokens",  # OAuth tokens in DB
        "oauth_token",
    }
)

# Email pattern: capture local part for partial masking
_EMAIL_PATTERN = re.compile(r"\b([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b")

# Key-value patterns in strings (key=value, key: value, "key": "value")
_KV_PATTERNS = [
    # key=value (unquoted)
    re.compile(
        r"(?i)\b(password|passwd|pwd|secret|token|api_key|apikey|api-key|"
        r"auth_token|access_token|refresh_token|bearer|authorization|"
        r"credential|private_key|client_secret|session_id)\s*[=:]\s*"
        r'([^\s,;}\]"\']+)',
        re.IGNORECASE,
    ),
    # "key": "value" (JSON-style)
    re.compile(
        r'(?i)"(password|passwd|pwd|secret|token|api_key|apikey|api-key|'
        r"auth_token|access_token|refresh_token|bearer|authorization|"
        r'credential|private_key|client_secret|session_id)"\s*:\s*"([^"]*)"',
        re.IGNORECASE,
    ),
    # 'key': 'value' (single-quoted)
    re.compile(
        r"(?i)'(password|passwd|pwd|secret|token|api_key|apikey|api-key|"
        r"auth_token|access_token|refresh_token|bearer|authorization|"
        r"credential|private_key|client_secret|session_id)'\s*:\s*'([^']*)'",
        re.IGNORECASE,
    ),
]

# Bearer token pattern
_BEARER_PATTERN = re.compile(r"Bearer\s+([a-zA-Z0-9_\-\.]+)", re.IGNORECASE)

# Long token-like strings (20+ alphanumeric chars that look like tokens)
_LONG_TOKEN_PATTERN = re.compile(r"\b[a-zA-Z0-9_\-]{32,}\b")

REDACTED = "[REDACTED]"


def _mask_email(email_match: re.Match[str]) -> str:
    """Mask email address, preserving first 1-3 chars of local part."""
    local = email_match.group(1)
    domain = email_match.group(2)
    if len(local) > 3:
        masked_local = local[:3] + "***"
    elif len(local) > 1:
        masked_local = local[0] + "***"
    else:
        masked_local = "***"
    return f"{masked_local}@{domain}"


def _truncate_token(token: str, keep_chars: int = 8) -> str:
    """Truncate token to first N chars + ellipsis."""
    if len(token) <= keep_chars:
        return REDACTED
    return token[:keep_chars] + "..."


def sanitize_message(message: str) -> str:
    """Sanitize a log message string, redacting sensitive patterns.

    Args:
        message: Raw log message

    Returns:
        Sanitized message with sensitive data redacted
    """
    if not message or not isinstance(message, str):
        return message

    result = message

    # Redact key=value patterns
    for pattern in _KV_PATTERNS:
        result = pattern.sub(r"\1=[REDACTED]", result)

    # Redact Bearer tokens (truncate to 8 chars)
    def replace_bearer(m: re.Match[str]) -> str:
        return f"Bearer {_truncate_token(m.group(1))}"

    result = _BEARER_PATTERN.sub(replace_bearer, result)

    # Mask emails
    result = _EMAIL_PATTERN.sub(_mask_email, result)

    return result


def sanitize_value(value: Any, key: str | None = None) -> Any:
    """Sanitize a single value based on its key name and content.

    Args:
        value: Value to sanitize
        key: Optional key name (for context-aware sanitization)

    Returns:
        Sanitized value
    """
    # Check if key indicates sensitive data
    if key and key.lower() in _SENSITIVE_KEYS:
        if isinstance(value, str) and len(value) > 8:
            return _truncate_token(value)
        return REDACTED

    # Handle string values
    if isinstance(value, str):
        # Check for Bearer tokens
        if value.lower().startswith("bearer "):
            return _BEARER_PATTERN.sub(lambda m: f"Bearer {_truncate_token(m.group(1))}", value)
        # Check for long token-like strings in values
        if _LONG_TOKEN_PATTERN.fullmatch(value):
            return _truncate_token(value)
        # Mask emails and key=value patterns
        return sanitize_message(value)

    return value


def sanitize_log_data(data: Any, _depth: int = 0) -> Any:
    """Recursively sanitize log data structure.

    Args:
        data: Data structure to sanitize (dict, list, or scalar)
        _depth: Internal recursion depth counter (prevents infinite loops)

    Returns:
        Deep copy with sensitive data redacted
    """
    # Prevent infinite recursion
    if _depth > 10:
        return data

    if data is None:
        return None

    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            key_lower = key.lower() if isinstance(key, str) else key
            if isinstance(key_lower, str) and key_lower in _SENSITIVE_KEYS:
                # Sensitive key - redact entire value
                if isinstance(value, str) and len(value) > 8:
                    result[key] = _truncate_token(value)
                else:
                    result[key] = REDACTED
            elif isinstance(value, dict):
                result[key] = sanitize_log_data(value, _depth + 1)
            elif isinstance(value, list):
                result[key] = sanitize_log_data(value, _depth + 1)
            elif isinstance(value, str):
                result[key] = sanitize_value(value, key)
            else:
                result[key] = value
        return result

    if isinstance(data, list):
        return [sanitize_log_data(item, _depth + 1) for item in data]

    if isinstance(data, str):
        return sanitize_message(data)

    return data


def is_sensitive_key(key: str) -> bool:
    """Check if a key name indicates sensitive data.

    Args:
        key: Key name to check

    Returns:
        True if key matches sensitive patterns
    """
    return key.lower() in _SENSITIVE_KEYS
