"""Standardized logging utilities for Board of One.

Provides:
- Consistent logger creation with structured formatting
- Structured logging context helpers
- Standard log format across all modules
"""

import logging
import sys
from typing import Any

# Standard log format: timestamp, level, module, message
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a configured logger with standardized formatting.

    Args:
        name: Logger name (typically __name__ from calling module)
        level: Log level (default: INFO)

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting process")
        2025-01-23 10:30:45 - INFO - bo1.module - Starting process
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)

    return logger


def log_with_context(logger: logging.Logger, level: int, msg: str, **context: Any) -> None:
    """Log message with structured context for better observability.

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
        2025-01-23 10:30:45 - INFO - bo1.module - Session started | session_id=abc123 user_id=user456 problem_type=investment
    """
    if context:
        context_str = " ".join(f"{k}={v}" for k, v in context.items())
        formatted_msg = f"{msg} | {context_str}"
    else:
        formatted_msg = msg

    logger.log(level, formatted_msg)


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
        2025-01-23 10:30:45 - INFO - bo1.llm - LLM call complete | model=claude-sonnet-4.5 prompt_tokens=1500 completion_tokens=300 cost=$0.0045 duration_ms=2340.5 agent=persona_selector phase=selection
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
        2025-01-23 10:30:45 - INFO - bo1.cache - Cache HIT | operation=get cache_type=persona key=persona_selector_abc123
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
        2025-01-23 10:30:45 - ERROR - bo1.module - Failed to process session | error_type=ValueError error=invalid input session_id=abc123 user_id=user456
    """
    log_with_context(
        logger,
        logging.ERROR,
        context_msg,
        error_type=type(error).__name__,
        error=str(error),
        **context,
    )
