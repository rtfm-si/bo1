"""Standardized logging utilities for Board of One.

Provides:
- Consistent logger creation with structured formatting
- Structured logging context helpers
- JSON logging format for production observability
- Standard log format across all modules
- Automatic PII/secret sanitization in logs
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from bo1.utils.log_sanitizer import sanitize_log_data, sanitize_message

# Context variable for correlation ID (set by middleware, read by logger)
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)

# Standard log format: timestamp, level, module, message
TEXT_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# For backward compatibility
LOG_FORMAT = TEXT_LOG_FORMAT


class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging.

    Outputs logs as JSON objects with consistent fields:
    - timestamp: ISO 8601 format
    - level: Log level name
    - logger: Logger name
    - message: Log message
    - trace_id: Correlation ID (if available)
    - context: Additional context fields (if provided via extra)
    """

    def __init__(self, indent: int | None = None) -> None:
        """Initialize JSON formatter.

        Args:
            indent: JSON indentation level (None for compact, 2 for pretty)
        """
        super().__init__()
        self.indent = indent

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with PII/secret sanitization.

        Args:
            record: Log record to format

        Returns:
            JSON string representation of log record with sensitive data redacted
        """
        # Sanitize the message before including in log
        raw_message = record.getMessage()
        safe_message = sanitize_message(raw_message)

        # Base log structure
        log_dict: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": safe_message,
        }

        # Add correlation ID if available
        trace_id = correlation_id_var.get()
        if trace_id:
            log_dict["trace_id"] = trace_id

        # Add structured context if provided via extra (sanitized)
        if hasattr(record, "log_context") and record.log_context:
            log_dict["context"] = sanitize_log_data(record.log_context)

        # Add exception info if present (sanitize stack trace)
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            log_dict["exception"] = sanitize_message(exc_text)

        return json.dumps(log_dict, default=str, indent=self.indent)


def _get_log_format() -> str:
    """Get configured log format from settings.

    Returns:
        'text' or 'json'
    """
    try:
        from bo1.config import get_settings

        return get_settings().log_format
    except Exception:
        return "text"


def _get_json_indent() -> int | None:
    """Get configured JSON indent from settings.

    Returns:
        Indent value or None for compact
    """
    try:
        from bo1.config import get_settings

        return get_settings().log_json_indent
    except Exception:
        return None


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a configured logger with standardized formatting.

    Uses JSON formatter when LOG_FORMAT=json, otherwise text formatter.

    Args:
        name: Logger name (typically __name__ from calling module)
        level: Log level (default: INFO)

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting process")
        # Text mode: 2025-01-23 10:30:45 - INFO - bo1.module - Starting process
        # JSON mode: {"timestamp": "...", "level": "INFO", "logger": "bo1.module", "message": "Starting process"}
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)

        # Select formatter based on config
        log_format = _get_log_format()
        formatter: logging.Formatter
        if log_format == "json":
            formatter = JsonFormatter(indent=_get_json_indent())
        else:
            formatter = logging.Formatter(TEXT_LOG_FORMAT, datefmt=DATE_FORMAT)

        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)

    return logger


def log_with_context(logger: logging.Logger, level: int, msg: str, **context: Any) -> None:
    """Log message with structured context for better observability.

    In text mode, appends context as key=value pairs.
    In JSON mode, includes context as a nested object.

    Args:
        logger: Logger instance to use
        level: Log level (logging.INFO, logging.WARNING, etc.)
        msg: Primary log message
        **context: Additional context fields (key=value pairs)

    Example:
        >>> logger = get_logger(__name__)
        >>> log_with_context(
        ...     logger, logging.INFO, "Session started",
        ...     session_id="abc123", user_id="user456", problem_type="investment"
        ... )
        # Text: 2025-01-23 10:30:45 - INFO - bo1.module - Session started | session_id=abc123 user_id=user456
        # JSON: {"timestamp": "...", "message": "Session started", "context": {"session_id": "abc123", ...}}
    """
    log_format = _get_log_format()

    if log_format == "json":
        # In JSON mode, pass context via extra for formatter to handle
        logger.log(level, msg, extra={"log_context": context} if context else {})
    else:
        # In text mode, format as key=value pairs
        if context:
            context_str = " ".join(f"{k}={v}" for k, v in context.items())
            formatted_msg = f"{msg} | {context_str}"
        else:
            formatted_msg = msg
        logger.log(level, formatted_msg)


def set_correlation_id(trace_id: str | None) -> None:
    """Set correlation ID for current context.

    Should be called by middleware at request start.

    Args:
        trace_id: Correlation ID (typically from X-Request-ID header)
    """
    correlation_id_var.set(trace_id)


def get_correlation_id() -> str | None:
    """Get current correlation ID.

    Returns:
        Correlation ID if set, None otherwise
    """
    return correlation_id_var.get()


def log_llm_call(
    logger: logging.Logger,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost: float,
    duration_ms: float,
    **extra: Any,
) -> None:
    """Log LLM API call with standardized metrics.

    Args:
        logger: Logger instance to use
        model: Model name (e.g., "claude-sonnet-4.5")
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        cost: Total cost in USD
        duration_ms: Call duration in milliseconds
        **extra: Additional context (agent_name, phase, etc.)

    Example:
        >>> logger = get_logger(__name__)
        >>> log_llm_call(
        ...     logger, model="claude-sonnet-4.5",
        ...     prompt_tokens=1500, completion_tokens=300,
        ...     cost=0.0045, duration_ms=2340.5,
        ...     agent="persona_selector", phase="selection"
        ... )
    """
    log_with_context(
        logger,
        logging.INFO,
        "LLM call complete",
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost=f"${cost:.4f}",
        duration_ms=f"{duration_ms:.1f}",
        **extra,
    )


def log_cache_operation(
    logger: logging.Logger,
    operation: str,
    cache_type: str,
    hit: bool,
    key: str | None = None,
    **extra: Any,
) -> None:
    """Log cache operation with standardized format.

    Args:
        logger: Logger instance to use
        operation: Operation type (get, set, delete)
        cache_type: Cache type (persona, research, etc.)
        hit: Whether operation was a cache hit (for get operations)
        key: Optional cache key for debugging
        **extra: Additional context

    Example:
        >>> logger = get_logger(__name__)
        >>> log_cache_operation(
        ...     logger, operation="get", cache_type="persona",
        ...     hit=True, key="persona_selector_abc123"
        ... )
    """
    result = "HIT" if hit else "MISS"
    context = {"operation": operation, "cache_type": cache_type, **extra}
    if key:
        context["key"] = key

    log_with_context(logger, logging.INFO, f"Cache {result}", **context)


def log_error_with_context(
    logger: logging.Logger, error: Exception, context_msg: str, **context: Any
) -> None:
    """Log error with structured context for debugging.

    Args:
        logger: Logger instance to use
        error: Exception that occurred
        context_msg: Contextual message explaining what was being attempted
        **context: Additional context fields

    Example:
        >>> logger = get_logger(__name__)
        >>> try:
        ...     risky_operation()
        ... except ValueError as e:
        ...     log_error_with_context(
        ...         logger, e, "Failed to process session",
        ...         session_id="abc123", user_id="user456"
        ...     )
    """
    log_with_context(
        logger,
        logging.ERROR,
        context_msg,
        error_type=type(error).__name__,
        error=str(error),
        **context,
    )
