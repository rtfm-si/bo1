"""Utilities for consistent error handling and logging.

This module provides standardized functions for logging fallback actions
and parsing failures across the codebase.
"""

import logging
from typing import Any


def log_fallback(
    logger: logging.Logger,
    operation: str,
    error: Exception,
    fallback_action: str,
    context: dict[str, Any] | None = None,
) -> None:
    """Log fallback action with consistent formatting.

    Args:
        logger: Logger instance
        operation: What was being attempted (e.g., "Vote JSON parsing")
        error: The exception that occurred
        fallback_action: What fallback is being used (e.g., "Using default votes")
        context: Additional context (e.g., {"response_preview": "..."})

    Examples:
        >>> import logging
        >>> logger = logging.getLogger(__name__)
        >>> log_fallback(
        ...     logger,
        ...     "Vote JSON parsing",
        ...     ValueError("Invalid JSON"),
        ...     "Using default votes",
        ...     {"response_preview": "Some text..."}
        ... )
        # Logs: "⚠️ FALLBACK: Vote JSON parsing failed. Using default votes."
    """
    msg = f"⚠️ FALLBACK: {operation} failed. {fallback_action}."
    logger.error(msg)
    logger.debug(f"Error details: {error}")

    if context:
        logger.debug("Context:")
        for key, value in context.items():
            # Truncate long values
            value_str = str(value)
            if len(value_str) > 200:
                value_str = value_str[:200] + "..."
            logger.debug(f"  {key}: {value_str}")


def log_parsing_failure(
    logger: logging.Logger,
    content_type: str,
    strategies_attempted: list[str],
    error: Exception,
    content_preview: str | None = None,
) -> None:
    """Log parsing failure with strategies attempted.

    Args:
        logger: Logger instance
        content_type: What was being parsed (e.g., "JSON", "XML vote")
        strategies_attempted: List of strategy names tried
        error: Final error that caused failure
        content_preview: Preview of content that failed to parse

    Examples:
        >>> import logging
        >>> logger = logging.getLogger(__name__)
        >>> log_parsing_failure(
        ...     logger,
        ...     "JSON",
        ...     ["direct parse", "markdown extraction", "regex"],
        ...     ValueError("No valid JSON found"),
        ...     "Some invalid content here..."
        ... )
        # Logs: "❌ PARSING FAILED: JSON parsing exhausted all strategies"
    """
    msg = f"❌ PARSING FAILED: {content_type} parsing exhausted all strategies"
    logger.error(msg)
    logger.debug(f"Strategies attempted: {', '.join(strategies_attempted)}")
    logger.debug(f"Final error: {error}")

    if content_preview:
        preview = content_preview[:300] + "..." if len(content_preview) > 300 else content_preview
        logger.debug(f"Content preview: {preview}")
