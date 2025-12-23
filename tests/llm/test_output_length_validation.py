"""Tests for PromptBroker output length validation."""

import os
from datetime import datetime
from unittest.mock import patch

from bo1.constants import OutputLengthConfig
from bo1.llm.broker import PromptBroker
from bo1.llm.client import TokenUsage
from bo1.llm.response import LLMResponse


def create_mock_response(
    output_tokens: int,
    input_tokens: int = 100,
) -> LLMResponse:
    """Create a mock LLMResponse for testing."""
    return LLMResponse(
        content="Test content",
        model="claude-sonnet-4-20250514",
        token_usage=TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=0,
            cache_read_tokens=0,
        ),
        duration_ms=500,
        retry_count=0,
        timestamp=datetime.now(),
        request_id="test-request-123",
        phase="test",
        agent_type="TestAgent",
    )


class TestOutputLengthConfig:
    """Tests for OutputLengthConfig class."""

    def test_default_thresholds(self):
        """Verify default threshold values."""
        assert OutputLengthConfig.VERBOSE_THRESHOLD == 0.5
        assert OutputLengthConfig.TRUNCATION_THRESHOLD == 0.9

    def test_is_enabled_default_true(self):
        """Verify validation is enabled by default."""
        # Clear env var if set
        with patch.dict(os.environ, {}, clear=True):
            assert OutputLengthConfig.is_enabled() is True

    def test_is_enabled_respects_env_var_false(self):
        """Verify env var can disable validation."""
        with patch.dict(os.environ, {"OUTPUT_LENGTH_VALIDATION_ENABLED": "false"}):
            assert OutputLengthConfig.is_enabled() is False

    def test_is_enabled_respects_env_var_true(self):
        """Verify env var can explicitly enable validation."""
        with patch.dict(os.environ, {"OUTPUT_LENGTH_VALIDATION_ENABLED": "true"}):
            assert OutputLengthConfig.is_enabled() is True


class TestValidateOutputLengthVerbose:
    """Tests for verbose response detection (< 50% of max_tokens)."""

    def test_verbose_warning_triggered_at_49_percent(self):
        """Verify verbose warning triggers below 50% threshold."""
        broker = PromptBroker()
        max_tokens = 1000
        output_tokens = 490  # 49% of max_tokens

        response = create_mock_response(output_tokens=output_tokens)

        warning_type = broker._validate_output_length(
            response=response,
            max_tokens=max_tokens,
            request_id="test-123",
            model="claude-sonnet-4",
            phase="test",
        )

        assert warning_type == "verbose"

    def test_no_warning_at_50_percent(self):
        """Verify no warning at exactly 50% threshold."""
        broker = PromptBroker()
        max_tokens = 1000
        output_tokens = 500  # Exactly 50%

        response = create_mock_response(output_tokens=output_tokens)

        warning_type = broker._validate_output_length(
            response=response,
            max_tokens=max_tokens,
            request_id="test-123",
            model="claude-sonnet-4",
            phase="test",
        )

        assert warning_type is None

    def test_verbose_warning_at_very_low_output(self):
        """Verify verbose warning for very short responses."""
        broker = PromptBroker()
        max_tokens = 2000
        output_tokens = 100  # 5% of max_tokens

        response = create_mock_response(output_tokens=output_tokens)

        warning_type = broker._validate_output_length(
            response=response,
            max_tokens=max_tokens,
            request_id="test-123",
            model="claude-sonnet-4",
            phase="synthesis",
        )

        assert warning_type == "verbose"


class TestValidateOutputLengthTruncated:
    """Tests for truncated response detection (> 90% of max_tokens)."""

    def test_truncated_warning_triggered_at_91_percent(self):
        """Verify truncated warning triggers above 90% threshold."""
        broker = PromptBroker()
        max_tokens = 1000
        output_tokens = 910  # 91% of max_tokens

        response = create_mock_response(output_tokens=output_tokens)

        warning_type = broker._validate_output_length(
            response=response,
            max_tokens=max_tokens,
            request_id="test-123",
            model="claude-sonnet-4",
            phase="test",
        )

        assert warning_type == "truncated"

    def test_no_warning_at_90_percent(self):
        """Verify no warning at exactly 90% threshold."""
        broker = PromptBroker()
        max_tokens = 1000
        output_tokens = 900  # Exactly 90%

        response = create_mock_response(output_tokens=output_tokens)

        warning_type = broker._validate_output_length(
            response=response,
            max_tokens=max_tokens,
            request_id="test-123",
            model="claude-sonnet-4",
            phase="test",
        )

        assert warning_type is None

    def test_truncated_warning_at_max_tokens(self):
        """Verify truncated warning when output equals max_tokens."""
        broker = PromptBroker()
        max_tokens = 1000
        output_tokens = 1000  # 100% of max_tokens

        response = create_mock_response(output_tokens=output_tokens)

        warning_type = broker._validate_output_length(
            response=response,
            max_tokens=max_tokens,
            request_id="test-123",
            model="claude-sonnet-4",
            phase="contribution",
        )

        assert warning_type == "truncated"


class TestValidateOutputLengthNormal:
    """Tests for normal output length (50-90% of max_tokens)."""

    def test_no_warning_at_70_percent(self):
        """Verify no warning in normal range."""
        broker = PromptBroker()
        max_tokens = 1000
        output_tokens = 700  # 70% - well within normal range

        response = create_mock_response(output_tokens=output_tokens)

        warning_type = broker._validate_output_length(
            response=response,
            max_tokens=max_tokens,
            request_id="test-123",
            model="claude-sonnet-4",
            phase="test",
        )

        assert warning_type is None

    def test_no_warning_at_51_percent(self):
        """Verify no warning just above verbose threshold."""
        broker = PromptBroker()
        max_tokens = 1000
        output_tokens = 510

        response = create_mock_response(output_tokens=output_tokens)

        warning_type = broker._validate_output_length(
            response=response,
            max_tokens=max_tokens,
            request_id="test-123",
            model="claude-sonnet-4",
            phase="test",
        )

        assert warning_type is None

    def test_no_warning_at_89_percent(self):
        """Verify no warning just below truncation threshold."""
        broker = PromptBroker()
        max_tokens = 1000
        output_tokens = 890

        response = create_mock_response(output_tokens=output_tokens)

        warning_type = broker._validate_output_length(
            response=response,
            max_tokens=max_tokens,
            request_id="test-123",
            model="claude-sonnet-4",
            phase="test",
        )

        assert warning_type is None


class TestValidateOutputLengthDisabled:
    """Tests for disabled validation."""

    def test_no_warning_when_disabled(self):
        """Verify no warning when validation disabled via env var."""
        broker = PromptBroker()
        max_tokens = 1000
        output_tokens = 100  # Would trigger verbose warning if enabled

        response = create_mock_response(output_tokens=output_tokens)

        with patch.dict(os.environ, {"OUTPUT_LENGTH_VALIDATION_ENABLED": "false"}):
            warning_type = broker._validate_output_length(
                response=response,
                max_tokens=max_tokens,
                request_id="test-123",
                model="claude-sonnet-4",
                phase="test",
            )

        assert warning_type is None

    def test_no_warning_when_max_tokens_zero(self):
        """Verify no warning when max_tokens is zero (avoid division by zero)."""
        broker = PromptBroker()
        response = create_mock_response(output_tokens=100)

        warning_type = broker._validate_output_length(
            response=response,
            max_tokens=0,
            request_id="test-123",
            model="claude-sonnet-4",
            phase="test",
        )

        assert warning_type is None

    def test_no_warning_when_max_tokens_negative(self):
        """Verify no warning when max_tokens is negative."""
        broker = PromptBroker()
        response = create_mock_response(output_tokens=100)

        warning_type = broker._validate_output_length(
            response=response,
            max_tokens=-1,
            request_id="test-123",
            model="claude-sonnet-4",
            phase="test",
        )

        assert warning_type is None


class TestOutputLengthWarningLogged:
    """Tests for structured warning logs."""

    def test_verbose_warning_logged_with_context(self):
        """Verify verbose warning includes structured context."""
        broker = PromptBroker()
        max_tokens = 1000
        output_tokens = 200  # 20% of max_tokens

        response = create_mock_response(output_tokens=output_tokens)

        with patch("bo1.llm.broker.logger") as mock_logger:
            warning_type = broker._validate_output_length(
                response=response,
                max_tokens=max_tokens,
                request_id="test-123",
                model="claude-sonnet-4",
                phase="synthesis",
            )

        assert warning_type == "verbose"
        mock_logger.warning.assert_called_once()
        log_message = mock_logger.warning.call_args[0][0]

        # Verify structured context in log
        assert "test-123" in log_message
        assert "20.0%" in log_message or "20%" in log_message
        assert "200" in log_message
        assert "1000" in log_message
        assert "claude-sonnet-4" in log_message
        assert "synthesis" in log_message

    def test_truncated_warning_logged_with_context(self):
        """Verify truncated warning includes structured context."""
        broker = PromptBroker()
        max_tokens = 1000
        output_tokens = 950  # 95% of max_tokens

        response = create_mock_response(output_tokens=output_tokens)

        with patch("bo1.llm.broker.logger") as mock_logger:
            warning_type = broker._validate_output_length(
                response=response,
                max_tokens=max_tokens,
                request_id="test-456",
                model="claude-haiku-3",
                phase="contribution",
            )

        assert warning_type == "truncated"
        mock_logger.warning.assert_called_once()
        log_message = mock_logger.warning.call_args[0][0]

        # Verify structured context in log
        assert "test-456" in log_message
        assert "95.0%" in log_message or "95%" in log_message
        assert "truncation" in log_message
        assert "claude-haiku-3" in log_message
        assert "contribution" in log_message

    def test_no_log_when_normal_output(self):
        """Verify no warning logged for normal output length."""
        broker = PromptBroker()
        max_tokens = 1000
        output_tokens = 700  # 70% - normal range

        response = create_mock_response(output_tokens=output_tokens)

        with patch("bo1.llm.broker.logger") as mock_logger:
            warning_type = broker._validate_output_length(
                response=response,
                max_tokens=max_tokens,
                request_id="test-123",
                model="claude-sonnet-4",
                phase="test",
            )

        assert warning_type is None
        mock_logger.warning.assert_not_called()
