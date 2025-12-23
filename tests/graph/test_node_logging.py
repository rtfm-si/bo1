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

    def test_log_with_session_includes_sub_problem_index(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """log_with_session includes sub_problem_index in log prefix."""
        logger = logging.getLogger("test_logger")

        with caplog.at_level(logging.INFO):
            log_with_session(logger, logging.INFO, "session1", "SP test", sub_problem_index=2)

        assert "[session=session1]" in caplog.text
        assert "[sp=2]" in caplog.text
        assert "SP test" in caplog.text

    def test_log_with_session_includes_round_number(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_with_session includes round_number in log prefix."""
        logger = logging.getLogger("test_logger")

        with caplog.at_level(logging.INFO):
            log_with_session(logger, logging.INFO, "session1", "Round test", round_number=3)

        assert "[session=session1]" in caplog.text
        assert "[round=3]" in caplog.text
        assert "Round test" in caplog.text

    def test_log_with_session_includes_all_context(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_with_session includes session, request, sp, and round in order."""
        logger = logging.getLogger("test_logger")

        with caplog.at_level(logging.INFO):
            log_with_session(
                logger,
                logging.INFO,
                "session1",
                "Full context test",
                request_id="request1",
                sub_problem_index=1,
                round_number=4,
            )

        # Check all parts appear in log
        assert "[session=session1]" in caplog.text
        assert "[request=request1]" in caplog.text
        assert "[sp=1]" in caplog.text
        assert "[round=4]" in caplog.text
        assert "Full context test" in caplog.text

        # Check order: session, request, sp, round
        log_text = caplog.text
        session_pos = log_text.find("[session=")
        request_pos = log_text.find("[request=")
        sp_pos = log_text.find("[sp=")
        round_pos = log_text.find("[round=")
        assert session_pos < request_pos < sp_pos < round_pos

    def test_log_with_session_none_optional_params_omitted(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """log_with_session omits None optional params from prefix."""
        logger = logging.getLogger("test_logger")

        with caplog.at_level(logging.INFO):
            log_with_session(
                logger,
                logging.INFO,
                "session1",
                "Partial context",
                request_id=None,
                sub_problem_index=None,
                round_number=None,
            )

        assert "[session=session1]" in caplog.text
        assert "[request=" not in caplog.text
        assert "[sp=" not in caplog.text
        assert "[round=" not in caplog.text

    def test_log_with_session_zero_values_included(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_with_session includes zero values (they are valid indexes/rounds)."""
        logger = logging.getLogger("test_logger")

        with caplog.at_level(logging.INFO):
            log_with_session(
                logger,
                logging.INFO,
                "session1",
                "Zero test",
                sub_problem_index=0,
                round_number=0,
            )

        assert "[sp=0]" in caplog.text
        assert "[round=0]" in caplog.text
