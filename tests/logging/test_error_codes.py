"""Tests for standardized error codes and logging helper."""

import logging
import re
from unittest.mock import MagicMock

from bo1.logging import ErrorCode, log_error


class TestErrorCodeEnum:
    """Tests for ErrorCode enum values and structure."""

    def test_all_codes_are_strings(self) -> None:
        """All error codes should be string values."""
        for code in ErrorCode:
            assert isinstance(code.value, str)

    def test_all_codes_uppercase(self) -> None:
        """All error codes should be uppercase."""
        for code in ErrorCode:
            assert code.value == code.value.upper()

    def test_all_codes_use_underscores(self) -> None:
        """All error codes should use underscores (no dashes or spaces)."""
        for code in ErrorCode:
            assert "-" not in code.value
            assert " " not in code.value

    def test_code_format_matches_log_regex(self) -> None:
        """All codes should match Promtail extraction regex patterns.

        Regular codes: [A-Z_]+
        Security event codes: SECURITY:[A-Z_]+
        """
        regular_pattern = re.compile(r"^[A-Z_]+$")
        security_pattern = re.compile(r"^SECURITY:[A-Z_]+$")
        for code in ErrorCode:
            if code.value.startswith("SECURITY:"):
                assert security_pattern.match(code.value), (
                    f"{code.value} doesn't match SECURITY:[A-Z_]+ pattern"
                )
            else:
                assert regular_pattern.match(code.value), (
                    f"{code.value} doesn't match [A-Z_]+ pattern"
                )

    def test_expected_categories_exist(self) -> None:
        """Verify expected error code categories exist."""
        # LLM errors
        assert ErrorCode.LLM_API_ERROR
        assert ErrorCode.LLM_RATE_LIMIT
        assert ErrorCode.LLM_PARSE_FAILED

        # Database errors
        assert ErrorCode.DB_CONNECTION_ERROR
        assert ErrorCode.DB_WRITE_ERROR

        # Redis errors
        assert ErrorCode.REDIS_READ_ERROR
        assert ErrorCode.REDIS_WRITE_ERROR

        # Parse errors
        assert ErrorCode.PARSE_JSON_ERROR

        # Graph errors
        assert ErrorCode.GRAPH_STATE_ERROR
        assert ErrorCode.GRAPH_EXECUTION_ERROR

    def test_no_duplicate_values(self) -> None:
        """All error codes should have unique values."""
        values = [code.value for code in ErrorCode]
        assert len(values) == len(set(values)), "Duplicate error code values found"


class TestLogError:
    """Tests for log_error helper function."""

    def test_log_error_format(self) -> None:
        """log_error should produce [{code}] {message} format."""
        mock_logger = MagicMock(spec=logging.Logger)

        log_error(mock_logger, ErrorCode.LLM_API_ERROR, "Test message")

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        logged_message = call_args[0][0]

        assert logged_message == "[LLM_API_ERROR] Test message"

    def test_log_error_extra_contains_error_code(self) -> None:
        """log_error should include error_code in extra dict."""
        mock_logger = MagicMock(spec=logging.Logger)

        log_error(mock_logger, ErrorCode.DB_WRITE_ERROR, "Database error")

        call_kwargs = mock_logger.error.call_args[1]
        assert "extra" in call_kwargs
        assert call_kwargs["extra"]["error_code"] == "DB_WRITE_ERROR"

    def test_log_error_extra_includes_context(self) -> None:
        """log_error should pass additional context to extra dict."""
        mock_logger = MagicMock(spec=logging.Logger)

        log_error(
            mock_logger,
            ErrorCode.REDIS_CONNECTION_ERROR,
            "Connection failed",
            host="localhost",
            port=6379,
        )

        call_kwargs = mock_logger.error.call_args[1]
        extra = call_kwargs["extra"]
        assert extra["error_code"] == "REDIS_CONNECTION_ERROR"
        assert extra["host"] == "localhost"
        assert extra["port"] == 6379

    def test_log_error_exc_info(self) -> None:
        """log_error should pass exc_info when requested."""
        mock_logger = MagicMock(spec=logging.Logger)

        log_error(mock_logger, ErrorCode.SERVICE_EXECUTION_ERROR, "Failed", exc_info=True)

        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs["exc_info"] is True

    def test_log_error_no_exc_info_by_default(self) -> None:
        """log_error should not include exc_info by default."""
        mock_logger = MagicMock(spec=logging.Logger)

        log_error(mock_logger, ErrorCode.VALIDATION_ERROR, "Invalid")

        call_kwargs = mock_logger.error.call_args[1]
        assert call_kwargs["exc_info"] is False


class TestPromtailExtraction:
    """Tests to verify log format matches Promtail regex extraction."""

    def test_error_code_extractable_by_promtail_regex(self) -> None:
        r"""Log format should be extractable by Promtail regex.

        Promtail has two patterns:
        - Regular codes: \[(?P<error_code>[A-Z_]+)\]
        - Security events: \[SECURITY:(?P<security_event>[A-Z_]+)\]
        """
        regular_regex = re.compile(r"\[(?P<error_code>[A-Z_]+)\]")
        security_regex = re.compile(r"\[SECURITY:(?P<security_event>[A-Z_]+)\]")

        mock_logger = MagicMock(spec=logging.Logger)

        for code in ErrorCode:
            log_error(mock_logger, code, "Test message")

            logged_message = mock_logger.error.call_args[0][0]

            if code.value.startswith("SECURITY:"):
                match = security_regex.search(logged_message)
                assert match is not None, (
                    f"Code {code.value} not extractable from: {logged_message}"
                )
                expected_event = code.value.replace("SECURITY:", "")
                assert match.group("security_event") == expected_event
            else:
                match = regular_regex.search(logged_message)
                assert match is not None, (
                    f"Code {code.value} not extractable from: {logged_message}"
                )
                assert match.group("error_code") == code.value

            mock_logger.reset_mock()
