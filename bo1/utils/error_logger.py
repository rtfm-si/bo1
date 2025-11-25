"""Unified error logging utilities for Board of One.

Consolidates error handling, fallback logging, and error context logging
into a single ErrorLogger class for consistency across the codebase.

This module replaces:
- bo1.utils.error_handling.log_fallback()
- bo1.utils.logging_helpers.LogHelper.log_fallback_used()
- bo1.utils.logging.log_error_with_context()
"""

import logging
from typing import Any


class ErrorLogger:
    """Unified error logging for fallbacks, exceptions, and error contexts.

    Provides standardized logging methods for:
    - Fallback actions when primary operations fail
    - Error context with structured fields
    - Parsing failures with attempted strategies
    """

    @staticmethod
    def log_fallback(
        logger: logging.Logger,
        operation: str,
        reason: str,
        fallback_action: str,
        error: Exception | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log when a fallback mechanism is triggered.

        Args:
            logger: Logger instance
            operation: Operation that failed (e.g., "AI vote aggregation", "Vote JSON parsing")
            reason: Reason for fallback (e.g., "JSON parsing failed", "LLM returned invalid format")
            fallback_action: What fallback action is being taken (e.g., "Using default votes")
            error: Optional exception that triggered the fallback
            context: Additional context (e.g., {"response_preview": "..."})

        Examples:
            >>> logger = logging.getLogger(__name__)
            >>> ErrorLogger.log_fallback(
            ...     logger,
            ...     operation="Vote JSON parsing",
            ...     reason="Invalid JSON",
            ...     fallback_action="Using default votes",
            ...     error=ValueError("Invalid JSON"),
            ...     context={"response_preview": "Some text..."}
            ... )
            # Logs: "⚠️ FALLBACK: Vote JSON parsing FAILED - Invalid JSON. Falling back to: Using default votes"
        """
        # Build consistent message format
        error_str = f" Error: {error}" if error else ""
        msg = f"⚠️ FALLBACK: {operation} FAILED - {reason}.{error_str} Falling back to: {fallback_action}"

        logger.warning(msg)

        if error:
            logger.debug(f"Error details: {error}")

        if context:
            logger.debug("Context:")
            for key, value in context.items():
                # Truncate long values
                value_str = str(value)
                if len(value_str) > 200:
                    value_str = value_str[:200] + "..."
                logger.debug(f"  {key}: {value_str}")

    @staticmethod
    def log_error_with_context(
        logger: logging.Logger,
        error: Exception,
        context_msg: str,
        **context: Any,
    ) -> None:
        """Log error with structured context for debugging.

        Args:
            logger: Logger instance to use
            error: Exception that occurred
            context_msg: Contextual message explaining what was being attempted
            **context: Additional context fields (key=value pairs)

        Example:
            >>> logger = logging.getLogger(__name__)
            >>> try:
            ...     risky_operation()
            ... except ValueError as e:
            ...     ErrorLogger.log_error_with_context(
            ...         logger, e, "Failed to process session",
            ...         session_id="abc123", user_id="user456"
            ...     )
            # Logs: "Failed to process session | error_type=ValueError error=invalid input session_id=abc123 user_id=user456"
        """
        # Build structured context string
        context_parts = [f"error_type={type(error).__name__}", f"error={str(error)}"]

        for key, value in context.items():
            context_parts.append(f"{key}={value}")

        context_str = " ".join(context_parts)
        formatted_msg = f"{context_msg} | {context_str}" if context_str else context_msg

        logger.error(formatted_msg)

    @staticmethod
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
            >>> logger = logging.getLogger(__name__)
            >>> ErrorLogger.log_parsing_failure(
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
            preview = (
                content_preview[:300] + "..." if len(content_preview) > 300 else content_preview
            )
            logger.debug(f"Content preview: {preview}")
