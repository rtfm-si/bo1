"""Centralized error code registry and structured logging helper.

Provides consistent error codes for log aggregation via Loki/Grafana.
Format: [{error_code}] {message} with extra={"error_code": code, ...context}
"""

import logging
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Standardized error codes for log aggregation.

    Categories:
    - LLM_*: LLM/AI provider errors
    - DB_*: Database (PostgreSQL) errors
    - REDIS_*: Redis errors
    - PARSE_*: Parsing/validation errors
    - SERVICE_*: Service/business logic errors
    - GRAPH_*: Graph execution errors
    - AUTH_*: Authentication/authorization errors
    - API_*: API/HTTP errors
    """

    # LLM errors
    LLM_API_ERROR = "LLM_API_ERROR"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_RETRIES_EXHAUSTED = "LLM_RETRIES_EXHAUSTED"
    LLM_PARSE_FAILED = "LLM_PARSE_FAILED"
    LLM_CACHE_ERROR = "LLM_CACHE_ERROR"
    LLM_CIRCUIT_OPEN = "LLM_CIRCUIT_OPEN"
    LLM_EMBEDDING_FAILED = "LLM_EMBEDDING_FAILED"

    # Database errors
    DB_CONNECTION_ERROR = "DB_CONNECTION_ERROR"
    DB_QUERY_ERROR = "DB_QUERY_ERROR"
    DB_WRITE_ERROR = "DB_WRITE_ERROR"
    DB_PARTITION_ERROR = "DB_PARTITION_ERROR"

    # Redis errors
    REDIS_CONNECTION_ERROR = "REDIS_CONNECTION_ERROR"
    REDIS_READ_ERROR = "REDIS_READ_ERROR"
    REDIS_WRITE_ERROR = "REDIS_WRITE_ERROR"

    # Parsing/validation errors
    PARSE_JSON_ERROR = "PARSE_JSON_ERROR"
    PARSE_XML_ERROR = "PARSE_XML_ERROR"
    PARSE_RESPONSE_ERROR = "PARSE_RESPONSE_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"

    # Service errors
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    SERVICE_CONFIG_ERROR = "SERVICE_CONFIG_ERROR"
    SERVICE_DEPENDENCY_ERROR = "SERVICE_DEPENDENCY_ERROR"
    SERVICE_EXECUTION_ERROR = "SERVICE_EXECUTION_ERROR"

    # Graph execution errors
    GRAPH_STATE_ERROR = "GRAPH_STATE_ERROR"
    GRAPH_EXECUTION_ERROR = "GRAPH_EXECUTION_ERROR"
    GRAPH_NODE_ERROR = "GRAPH_NODE_ERROR"
    GRAPH_CHECKPOINT_ERROR = "GRAPH_CHECKPOINT_ERROR"

    # Authentication/authorization errors
    AUTH_TOKEN_ERROR = "AUTH_TOKEN_ERROR"  # noqa: S105 (not a password, it's an error code)
    AUTH_OAUTH_ERROR = "AUTH_OAUTH_ERROR"
    AUTH_LOCKOUT_ERROR = "AUTH_LOCKOUT_ERROR"

    # API errors
    API_REQUEST_ERROR = "API_REQUEST_ERROR"
    API_AUDIT_ERROR = "API_AUDIT_ERROR"
    API_NOT_FOUND = "API_NOT_FOUND"
    API_FORBIDDEN = "API_FORBIDDEN"
    API_UNAUTHORIZED = "API_UNAUTHORIZED"
    API_CONFLICT = "API_CONFLICT"
    API_RATE_LIMIT = "API_RATE_LIMIT"
    API_BAD_REQUEST = "API_BAD_REQUEST"
    API_SESSION_ERROR = "API_SESSION_ERROR"
    API_ACTION_ERROR = "API_ACTION_ERROR"

    # External service errors
    EXT_STRIPE_ERROR = "EXT_STRIPE_ERROR"
    EXT_EMAIL_ERROR = "EXT_EMAIL_ERROR"
    EXT_CALENDAR_ERROR = "EXT_CALENDAR_ERROR"
    EXT_SPACES_ERROR = "EXT_SPACES_ERROR"
    EXT_SHEETS_ERROR = "EXT_SHEETS_ERROR"
    EXT_NTFY_ERROR = "EXT_NTFY_ERROR"
    EXT_OAUTH_ERROR = "EXT_OAUTH_ERROR"

    # API errors (additional)
    API_SSE_ERROR = "API_SSE_ERROR"
    API_WORKSPACE_ERROR = "API_WORKSPACE_ERROR"

    # Service errors (additional)
    SERVICE_ANALYSIS_ERROR = "SERVICE_ANALYSIS_ERROR"
    SERVICE_BILLING_ERROR = "SERVICE_BILLING_ERROR"
    SERVICE_ONBOARDING_ERROR = "SERVICE_ONBOARDING_ERROR"

    # Security errors
    SECURITY_ALERT_ERROR = "SECURITY_ALERT_ERROR"

    # Security events (for SIEM aggregation - prefixed with SECURITY:)
    # These use special format for Loki label extraction
    SECURITY_AUTH_FAILURE = "SECURITY:AUTH_FAILURE"
    SECURITY_RATE_LIMIT = "SECURITY:RATE_LIMIT"
    SECURITY_LOCKOUT = "SECURITY:LOCKOUT"
    SECURITY_PROMPT_INJECTION = "SECURITY:PROMPT_INJECTION"
    SECURITY_WAF_BLOCK = "SECURITY:WAF_BLOCK"

    # Cost tracking errors
    COST_FLUSH_ERROR = "COST_FLUSH_ERROR"
    COST_RETRY_ERROR = "COST_RETRY_ERROR"


def log_error(
    logger: logging.Logger,
    code: ErrorCode,
    message: str,
    exc_info: bool = False,
    **context: Any,
) -> None:
    """Log error with standardized format for Loki aggregation.

    Format: [{error_code}] {message}
    Extra: {"error_code": code.value, ...context}

    Args:
        logger: Logger instance
        code: ErrorCode enum value
        message: Error description
        exc_info: Include exception traceback (default False)
        **context: Additional context fields for extra dict
    """
    logger.error(
        f"[{code.value}] {message}",
        exc_info=exc_info,
        extra={"error_code": code.value, **context},
    )


def log_security_event(
    logger: logging.Logger,
    code: ErrorCode,
    message: str,
    client_ip: str | None = None,
    **context: Any,
) -> None:
    """Log security event with structured format for SIEM aggregation.

    Format: [{security_event_code}] {message}
    Extra includes client_ip and security_event label for Loki filtering.

    Args:
        logger: Logger instance
        code: ErrorCode enum value (should be SECURITY_* type)
        message: Event description
        client_ip: Client IP address for correlation
        **context: Additional context fields
    """
    extra = {
        "error_code": code.value,
        "security_event": code.value.replace("SECURITY:", ""),
        **context,
    }
    if client_ip:
        extra["client_ip"] = client_ip

    logger.warning(
        f"[{code.value}] {message}",
        extra=extra,
    )
