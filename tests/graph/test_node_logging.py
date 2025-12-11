"""Tests for node logging utilities."""

import logging

import pytest

from bo1.graph.nodes.utils import log_with_session


class TestLogWithSession:
    """Test log_with_session helper function."""

    def test_log_with_session_formats_correctly(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_with_session formats message with truncated session ID."""
        logger = logging.getLogger("test_logger")

        with caplog.at_level(logging.INFO):
            log_with_session(logger, logging.INFO, "abc12345-6789-full-uuid", "Test message")

        assert "[session=abc12345]" in caplog.text
        assert "Test message" in caplog.text

    def test_log_with_session_handles_missing_session(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """log_with_session uses 'unknown' when session_id is None."""
        logger = logging.getLogger("test_logger")

        with caplog.at_level(logging.INFO):
            log_with_session(logger, logging.INFO, None, "No session test")

        assert "[session=unknown]" in caplog.text
        assert "No session test" in caplog.text

    def test_log_with_session_truncates_long_session_id(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """log_with_session truncates session_id to 8 characters."""
        logger = logging.getLogger("test_logger")
        long_session = "abcdefghijklmnopqrstuvwxyz123456789"

        with caplog.at_level(logging.INFO):
            log_with_session(logger, logging.INFO, long_session, "Truncation test")

        assert "[session=abcdefgh]" in caplog.text
        assert "ijklmnop" not in caplog.text  # Rest is truncated

    def test_log_with_session_supports_warning_level(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """log_with_session works with WARNING level."""
        logger = logging.getLogger("test_logger")

        with caplog.at_level(logging.WARNING):
            log_with_session(logger, logging.WARNING, "session123", "Warning message")

        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.WARNING
        assert "[session=session1]" in caplog.text

    def test_log_with_session_handles_empty_session_id(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """log_with_session treats empty string as falsy, using 'unknown'."""
        logger = logging.getLogger("test_logger")

        with caplog.at_level(logging.INFO):
            log_with_session(logger, logging.INFO, "", "Empty session test")

        # Empty string is falsy, so falls back to "unknown"
        assert "[session=unknown]" in caplog.text
