"""Unit tests for deliberation logger.

Tests:
- Factory creates properly bound logger
- None rejection for mandatory fields
- Log output includes context fields
- Bind method extends context
"""

import logging
from io import StringIO

import pytest

from bo1.utils.deliberation_logger import (
    DeliberationLogger,
    get_deliberation_logger,
    validate_deliberation_log_context,
)


class TestGetDeliberationLogger:
    """Tests for get_deliberation_logger factory."""

    def test_creates_logger_with_all_fields(self) -> None:
        """Factory creates logger with bound session_id, user_id, node_name."""
        dlog = get_deliberation_logger("sess-123", "user-456", "test_node")

        assert dlog.session_id == "sess-123"
        assert dlog.user_id == "user-456"
        assert dlog.node_name == "test_node"

    def test_uses_placeholder_for_none_session_id(self) -> None:
        """Uses 'pre-session' placeholder when session_id is None."""
        dlog = get_deliberation_logger(None, "user-456", "test_node")

        assert dlog.session_id == "pre-session"

    def test_uses_placeholder_for_none_user_id(self) -> None:
        """Uses 'anonymous' placeholder when user_id is None."""
        dlog = get_deliberation_logger("sess-123", None, "test_node")

        assert dlog.user_id == "anonymous"

    def test_raises_on_empty_node_name(self) -> None:
        """Raises ValueError when node_name is empty."""
        with pytest.raises(ValueError, match="node_name is required"):
            get_deliberation_logger("sess-123", "user-456", "")

    def test_raises_on_none_node_name(self) -> None:
        """Raises ValueError when node_name is None."""
        with pytest.raises(ValueError, match="node_name is required"):
            get_deliberation_logger("sess-123", "user-456", None)  # type: ignore[arg-type]

    def test_uses_custom_logger_name(self) -> None:
        """Uses custom logger name when provided."""
        dlog = get_deliberation_logger(
            "sess-123", "user-456", "test_node", logger_name="custom.logger"
        )
        assert dlog._logger.name == "custom.logger"

    def test_uses_default_logger_name(self) -> None:
        """Uses default 'bo1.deliberation' logger name."""
        dlog = get_deliberation_logger("sess-123", "user-456", "test_node")
        assert dlog._logger.name == "bo1.deliberation"


class TestDeliberationLoggerMethods:
    """Tests for DeliberationLogger logging methods."""

    @pytest.fixture
    def capture_logger(self) -> tuple[DeliberationLogger, StringIO]:
        """Create logger that captures output to StringIO."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))

        base_logger = logging.getLogger("test.deliberation")
        base_logger.handlers = []  # Clear any existing handlers
        base_logger.addHandler(handler)
        base_logger.setLevel(logging.DEBUG)

        dlog = DeliberationLogger(base_logger, "sess-abc", "user-xyz", "test_node")
        return dlog, stream

    def test_info_includes_context_fields(self, capture_logger: tuple) -> None:
        """Info log includes session_id, user_id, node_name."""
        dlog, stream = capture_logger
        dlog.info("Test message")

        output = stream.getvalue()
        assert "session_id=sess-abc" in output
        assert "user_id=user-xyz" in output
        assert "node_name=test_node" in output
        assert "Test message" in output

    def test_info_with_extra_fields(self, capture_logger: tuple) -> None:
        """Info log includes extra context fields."""
        dlog, stream = capture_logger
        dlog.info("Test message", round_number=3, cost="$0.01")

        output = stream.getvalue()
        assert "round_number=3" in output
        assert "cost=$0.01" in output

    def test_debug_includes_context(self, capture_logger: tuple) -> None:
        """Debug log includes context fields."""
        dlog, stream = capture_logger
        dlog.debug("Debug message")

        output = stream.getvalue()
        assert "session_id=sess-abc" in output
        assert "Debug message" in output

    def test_warning_includes_context(self, capture_logger: tuple) -> None:
        """Warning log includes context fields."""
        dlog, stream = capture_logger
        dlog.warning("Warning message")

        output = stream.getvalue()
        assert "session_id=sess-abc" in output
        assert "Warning message" in output

    def test_error_includes_context(self, capture_logger: tuple) -> None:
        """Error log includes context fields."""
        dlog, stream = capture_logger
        dlog.error("Error message")

        output = stream.getvalue()
        assert "session_id=sess-abc" in output
        assert "Error message" in output

    def test_truncates_long_session_id(self) -> None:
        """Truncates session_id to 8 chars in output."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))

        base_logger = logging.getLogger("test.truncate")
        base_logger.handlers = []
        base_logger.addHandler(handler)
        base_logger.setLevel(logging.DEBUG)

        dlog = DeliberationLogger(base_logger, "very-long-session-id-12345", "user", "node")
        dlog.info("Test")

        output = stream.getvalue()
        assert "session_id=very-lon" in output
        assert "very-long-session-id-12345" not in output


class TestDeliberationLoggerBind:
    """Tests for bind method."""

    def test_bind_creates_new_logger_with_extended_context(self) -> None:
        """Bind creates new logger with extended node_name."""
        dlog = get_deliberation_logger("sess-123", "user-456", "rounds")
        bound = dlog.bind(persona="expert_1")

        assert bound.node_name == "rounds.persona=expert_1"
        # Original unchanged
        assert dlog.node_name == "rounds"

    def test_bind_preserves_session_and_user(self) -> None:
        """Bind preserves session_id and user_id."""
        dlog = get_deliberation_logger("sess-123", "user-456", "rounds")
        bound = dlog.bind(persona="expert_1")

        assert bound.session_id == "sess-123"
        assert bound.user_id == "user-456"

    def test_bind_with_multiple_fields(self) -> None:
        """Bind handles multiple context fields."""
        dlog = get_deliberation_logger("sess-123", "user-456", "rounds")
        bound = dlog.bind(round=2, phase="challenge")

        assert "round=2" in bound.node_name
        assert "phase=challenge" in bound.node_name


class TestValidateDeliberationLogContext:
    """Tests for validate_deliberation_log_context."""

    def test_returns_empty_when_all_present(self) -> None:
        """Returns empty list when all fields present."""
        missing = validate_deliberation_log_context("sess", "user", "node")
        assert missing == []

    def test_returns_session_id_when_none(self) -> None:
        """Returns 'session_id' when session_id is None."""
        missing = validate_deliberation_log_context(None, "user", "node")
        assert "session_id" in missing

    def test_returns_user_id_when_none(self) -> None:
        """Returns 'user_id' when user_id is None."""
        missing = validate_deliberation_log_context("sess", None, "node")
        assert "user_id" in missing

    def test_returns_node_name_when_none(self) -> None:
        """Returns 'node_name' when node_name is None."""
        missing = validate_deliberation_log_context("sess", "user", None)
        assert "node_name" in missing

    def test_returns_empty_string_as_missing(self) -> None:
        """Treats empty strings as missing."""
        missing = validate_deliberation_log_context("", "", "")
        assert "session_id" in missing
        assert "user_id" in missing
        assert "node_name" in missing

    def test_returns_all_missing(self) -> None:
        """Returns all three when all are None."""
        missing = validate_deliberation_log_context(None, None, None)
        assert len(missing) == 3
        assert "session_id" in missing
        assert "user_id" in missing
        assert "node_name" in missing
