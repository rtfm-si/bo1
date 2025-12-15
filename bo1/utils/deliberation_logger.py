"""Deliberation logging context helper for consistent field binding.

Provides a factory to create loggers with mandatory context fields:
- session_id: Unique session identifier
- user_id: User who initiated the session
- node_name: Name of the graph node or orchestration component

These fields enable better log filtering/searching in Grafana Loki.
"""

import logging
from typing import Any

from bo1.utils.logging import log_with_context


class DeliberationLogger:
    """Logger wrapper with bound context fields for deliberation pipeline.

    Provides consistent structured logging with mandatory context fields:
    - session_id: Truncated to 8 chars for readability
    - user_id: Truncated to 8 chars for readability
    - node_name: Full node/component name

    Example:
        >>> dlog = get_deliberation_logger("sess-123", "user-456", "rounds")
        >>> dlog.info("Starting round", round_number=1)
        # Text: Starting round | session_id=sess-123 user_id=user-456 node_name=rounds round_number=1
        # JSON: {"message": "Starting round", "context": {"session_id": "sess-123", ...}}
    """

    def __init__(
        self,
        base_logger: logging.Logger,
        session_id: str,
        user_id: str,
        node_name: str,
    ) -> None:
        """Initialize deliberation logger with bound context.

        Args:
            base_logger: Base Python logger to wrap
            session_id: Session identifier (required, non-empty)
            user_id: User identifier (required, non-empty)
            node_name: Graph node or component name (required, non-empty)
        """
        self._logger = base_logger
        self._session_id = session_id
        self._user_id = user_id
        self._node_name = node_name

    @property
    def session_id(self) -> str:
        """Get bound session ID."""
        return self._session_id

    @property
    def user_id(self) -> str:
        """Get bound user ID."""
        return self._user_id

    @property
    def node_name(self) -> str:
        """Get bound node name."""
        return self._node_name

    def _log(self, level: int, msg: str, **extra: Any) -> None:
        """Internal log method with bound context.

        Args:
            level: Logging level (logging.INFO, etc.)
            msg: Log message
            **extra: Additional context fields
        """
        log_with_context(
            self._logger,
            level,
            msg,
            session_id=self._session_id[:8] if len(self._session_id) > 8 else self._session_id,
            user_id=self._user_id[:8] if len(self._user_id) > 8 else self._user_id,
            node_name=self._node_name,
            **extra,
        )

    def debug(self, msg: str, **extra: Any) -> None:
        """Log debug message with bound context."""
        self._log(logging.DEBUG, msg, **extra)

    def info(self, msg: str, **extra: Any) -> None:
        """Log info message with bound context."""
        self._log(logging.INFO, msg, **extra)

    def warning(self, msg: str, **extra: Any) -> None:
        """Log warning message with bound context."""
        self._log(logging.WARNING, msg, **extra)

    def error(self, msg: str, **extra: Any) -> None:
        """Log error message with bound context."""
        self._log(logging.ERROR, msg, **extra)

    def exception(self, msg: str, **extra: Any) -> None:
        """Log exception message with bound context and stack trace."""
        # Use standard logger for exception to capture traceback
        sid = self._session_id[:8] if len(self._session_id) > 8 else self._session_id
        uid = self._user_id[:8] if len(self._user_id) > 8 else self._user_id
        context_str = f"session_id={sid} user_id={uid} node_name={self._node_name}"
        if extra:
            extra_str = " ".join(f"{k}={v}" for k, v in extra.items())
            context_str = f"{context_str} {extra_str}"
        self._logger.exception(f"{msg} | {context_str}")

    def bind(self, **extra: Any) -> "DeliberationLogger":
        """Create a new logger with additional bound context.

        Useful for adding sub-context within a node (e.g., persona_code).

        Args:
            **extra: Additional context to bind (stored in node_name suffix)

        Returns:
            New DeliberationLogger with extended context
        """
        # Extend node_name with extra context for sub-scoping
        extra_str = ".".join(f"{k}={v}" for k, v in extra.items()) if extra else ""
        new_node_name = f"{self._node_name}.{extra_str}" if extra_str else self._node_name
        return DeliberationLogger(
            self._logger,
            self._session_id,
            self._user_id,
            new_node_name,
        )


def get_deliberation_logger(
    session_id: str | None,
    user_id: str | None,
    node_name: str,
    logger_name: str | None = None,
) -> DeliberationLogger:
    """Factory to create a deliberation logger with mandatory context fields.

    Args:
        session_id: Unique session identifier (uses "pre-session" if None)
        user_id: User identifier (uses "anonymous" if None)
        node_name: Graph node or component name (required)
        logger_name: Optional base logger name (defaults to "bo1.deliberation")

    Returns:
        DeliberationLogger with bound context fields

    Raises:
        ValueError: If node_name is empty

    Example:
        >>> dlog = get_deliberation_logger("abc-123", "user-456", "decompose_node")
        >>> dlog.info("Decomposing problem", sub_problems=3)
        # Logs with session_id, user_id, node_name always included
    """
    if not node_name:
        raise ValueError("node_name is required for deliberation logger")

    # Use placeholders for early-stage logs (pre-session creation)
    effective_session_id = session_id or "pre-session"
    effective_user_id = user_id or "anonymous"

    base_logger = logging.getLogger(logger_name or "bo1.deliberation")
    return DeliberationLogger(
        base_logger,
        effective_session_id,
        effective_user_id,
        node_name,
    )


def validate_deliberation_log_context(
    session_id: str | None,
    user_id: str | None,
    node_name: str | None,
) -> list[str]:
    """Validate that mandatory context fields are present.

    Useful for runtime validation in debug mode to detect missing fields.

    Args:
        session_id: Session ID to validate
        user_id: User ID to validate
        node_name: Node name to validate

    Returns:
        List of missing field names (empty if all present)

    Example:
        >>> missing = validate_deliberation_log_context(None, "user", "node")
        >>> if missing:
        ...     logger.warning(f"Missing deliberation log fields: {missing}")
    """
    missing: list[str] = []
    if not session_id:
        missing.append("session_id")
    if not user_id:
        missing.append("user_id")
    if not node_name:
        missing.append("node_name")
    return missing
