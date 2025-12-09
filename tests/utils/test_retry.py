"""Tests for retry utilities."""

import time
from unittest.mock import MagicMock, patch

import pytest
from psycopg2 import InterfaceError, OperationalError
from psycopg2.pool import PoolError

from bo1.state.database import ConnectionTimeoutError
from bo1.utils.retry import retry_db


class TestRetryDb:
    """Tests for @retry_db decorator."""

    def test_success_on_first_attempt(self):
        """Should succeed without retries when no exception."""
        mock_func = MagicMock(return_value="success")
        decorated = retry_db()(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_on_operational_error(self):
        """Should retry on OperationalError and succeed."""
        mock_func = MagicMock(side_effect=[OperationalError("connection lost"), "success"])
        decorated = retry_db(max_attempts=3, base_delay=0.01)(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_on_interface_error(self):
        """Should retry on InterfaceError and succeed."""
        mock_func = MagicMock(side_effect=[InterfaceError("interface error"), "success"])
        decorated = retry_db(max_attempts=3, base_delay=0.01)(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_on_pool_error(self):
        """Should retry on PoolError and succeed."""
        mock_func = MagicMock(side_effect=[PoolError("pool exhausted"), "success"])
        decorated = retry_db(max_attempts=3, base_delay=0.01)(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_max_attempts_exceeded(self):
        """Should raise after max_attempts exceeded."""
        mock_func = MagicMock(side_effect=OperationalError("always fails"))
        decorated = retry_db(max_attempts=3, base_delay=0.01)(mock_func)

        with pytest.raises(OperationalError, match="always fails"):
            decorated()

        assert mock_func.call_count == 3

    def test_non_retryable_exception_not_retried(self):
        """Should not retry non-retryable exceptions."""
        mock_func = MagicMock(side_effect=ValueError("not retryable"))
        decorated = retry_db(max_attempts=3, base_delay=0.01)(mock_func)

        with pytest.raises(ValueError, match="not retryable"):
            decorated()

        assert mock_func.call_count == 1

    def test_exponential_backoff_timing(self):
        """Should apply exponential backoff between retries."""
        mock_func = MagicMock(
            side_effect=[
                OperationalError("fail 1"),
                OperationalError("fail 2"),
                "success",
            ]
        )
        decorated = retry_db(max_attempts=3, base_delay=0.1, max_delay=10.0)(mock_func)

        start = time.monotonic()
        result = decorated()
        elapsed = time.monotonic() - start

        assert result == "success"
        # First delay ~0.1s, second delay ~0.2s (exponential)
        # With jitter, total should be roughly 0.3s (but allow variance)
        assert elapsed >= 0.2  # At least base delays occurred
        assert elapsed < 1.0  # But not too long

    def test_preserves_function_metadata(self):
        """Should preserve decorated function's name and docstring."""

        @retry_db()
        def my_function():
            """My docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    def test_passes_args_and_kwargs(self):
        """Should pass arguments correctly to decorated function."""
        mock_func = MagicMock(return_value="success")
        decorated = retry_db()(mock_func)

        result = decorated("arg1", "arg2", kwarg1="value1")

        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
        assert result == "success"

    def test_logs_retry_attempts(self):
        """Should log retry attempts with correlation ID."""
        mock_func = MagicMock(side_effect=[OperationalError("fail"), "success"])
        decorated = retry_db(max_attempts=3, base_delay=0.01)(mock_func)

        with patch("bo1.utils.retry.logger") as mock_logger:
            result = decorated()

        assert result == "success"
        # Should have logged a warning for the retry
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "attempt 1/3" in warning_call
        assert "Retrying" in warning_call


class TestConnectionTimeoutError:
    """Tests for ConnectionTimeoutError exception."""

    def test_exception_message(self):
        """Should include timeout info in message."""
        error = ConnectionTimeoutError("Pool exhausted after 5s")
        assert "Pool exhausted" in str(error)
        assert "5s" in str(error)

    def test_exception_is_exception_subclass(self):
        """Should be a standard Exception subclass."""
        error = ConnectionTimeoutError("test")
        assert isinstance(error, Exception)
