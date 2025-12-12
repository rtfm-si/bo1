"""Tests for JSON structured logging."""

import json
import logging
from io import StringIO
from unittest.mock import patch

from bo1.utils.logging import (
    JsonFormatter,
    get_correlation_id,
    log_with_context,
    set_correlation_id,
)


class TestJsonFormatter:
    """Test JsonFormatter output structure."""

    def test_json_formatter_output_structure(self) -> None:
        """JSON formatter produces valid JSON with expected fields."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "timestamp" in parsed
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.logger"
        assert parsed["message"] == "Test message"

    def test_json_formatter_with_indent(self) -> None:
        """JSON formatter respects indent setting."""
        formatter = JsonFormatter(indent=2)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        # Indented JSON has newlines
        assert "\n" in output
        # Still valid JSON
        parsed = json.loads(output)
        assert parsed["message"] == "Test"

    def test_json_formatter_compact(self) -> None:
        """JSON formatter produces compact output by default."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        # Compact JSON has no newlines in the base structure
        assert output.count("\n") == 0

    def test_json_formatter_with_context(self) -> None:
        """JSON formatter includes context from extra (sensitive fields are redacted)."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.log_context = {"session_id": "abc123", "user_id": "user456", "action": "test"}

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "context" in parsed
        # session_id is redacted by log sanitizer for security
        assert parsed["context"]["session_id"] == "[REDACTED]"
        # user_id and non-sensitive fields are preserved
        assert parsed["context"]["user_id"] == "user456"
        assert parsed["context"]["action"] == "test"


class TestCorrelationId:
    """Test correlation ID integration."""

    def test_correlation_id_included_in_json(self) -> None:
        """Correlation ID appears in JSON output when set."""
        formatter = JsonFormatter()

        # Set correlation ID
        set_correlation_id("trace-abc-123")
        try:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test",
                args=(),
                exc_info=None,
            )

            output = formatter.format(record)
            parsed = json.loads(output)

            assert "trace_id" in parsed
            assert parsed["trace_id"] == "trace-abc-123"
        finally:
            set_correlation_id(None)

    def test_correlation_id_not_included_when_not_set(self) -> None:
        """trace_id field omitted when correlation ID not set."""
        formatter = JsonFormatter()

        # Ensure correlation ID is not set
        set_correlation_id(None)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "trace_id" not in parsed

    def test_set_and_get_correlation_id(self) -> None:
        """set_correlation_id and get_correlation_id work correctly."""
        assert get_correlation_id() is None

        set_correlation_id("test-id-123")
        assert get_correlation_id() == "test-id-123"

        set_correlation_id(None)
        assert get_correlation_id() is None


class TestTextFormatter:
    """Test text format remains unchanged."""

    @patch("bo1.utils.logging._get_log_format", return_value="text")
    def test_text_formatter_unchanged(self, mock_format: object) -> None:
        """Text mode produces pipe-delimited key=value format."""
        # Create a fresh logger for testing
        logger = logging.getLogger("test.text.formatter")
        logger.handlers.clear()

        # Capture output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        log_with_context(
            logger,
            logging.INFO,
            "Session started",
            session_id="abc123",
            user_id="user456",
        )

        output = stream.getvalue()

        assert "Session started" in output
        assert "session_id=abc123" in output
        assert "user_id=user456" in output
        assert "|" in output


class TestLogWithContextJsonMode:
    """Test log_with_context in JSON mode."""

    @patch("bo1.utils.logging._get_log_format", return_value="json")
    def test_log_with_context_json_mode(self, mock_format: object) -> None:
        """log_with_context produces JSON with context object."""
        # Create a fresh logger for testing
        logger = logging.getLogger("test.json.context")
        logger.handlers.clear()

        # Capture output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        log_with_context(
            logger,
            logging.INFO,
            "Session started",
            session_id="abc123",
            user_id="user456",
        )

        output = stream.getvalue()
        parsed = json.loads(output)

        assert parsed["message"] == "Session started"
        # session_id is redacted by log sanitizer for security
        assert parsed["context"]["session_id"] == "[REDACTED]"
        assert parsed["context"]["user_id"] == "user456"

    @patch("bo1.utils.logging._get_log_format", return_value="json")
    def test_log_with_context_no_context(self, mock_format: object) -> None:
        """log_with_context without context omits context field."""
        logger = logging.getLogger("test.json.no.context")
        logger.handlers.clear()

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        log_with_context(logger, logging.INFO, "Simple message")

        output = stream.getvalue()
        parsed = json.loads(output)

        assert parsed["message"] == "Simple message"
        assert "context" not in parsed or not parsed.get("context")
