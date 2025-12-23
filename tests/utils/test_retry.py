"""Tests for retry utilities."""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from psycopg2 import InterfaceError, OperationalError
from psycopg2.pool import PoolError

from bo1.state.database import ConnectionTimeoutError
from bo1.utils.retry import (
    DEFAULT_TOTAL_TIMEOUT,
    RETRYABLE_PGCODES,
    is_retryable_error,
    retry_db,
    retry_db_async,
)


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

    def test_total_timeout_triggers_before_max_attempts(self):
        """Should raise TimeoutError when total timeout exceeded before max attempts."""
        # Simulate slow retries that exceed total timeout
        call_count = 0

        def slow_failing_func():
            nonlocal call_count
            call_count += 1
            time.sleep(0.15)  # Each call takes 150ms
            raise OperationalError("always fails")

        decorated = retry_db(
            max_attempts=10,  # High max attempts
            base_delay=0.1,  # 100ms delay
            total_timeout=0.3,  # 300ms total timeout
        )(slow_failing_func)

        with pytest.raises(TimeoutError) as exc_info:
            decorated()

        # Should timeout before all 10 attempts
        assert call_count < 10
        assert "total timeout exceeded" in str(exc_info.value)
        assert "0.3s" in str(exc_info.value)

    def test_timeout_error_message_includes_context(self):
        """Should include elapsed time and attempt count in TimeoutError."""
        mock_func = MagicMock(side_effect=OperationalError("fail"))
        decorated = retry_db(
            max_attempts=10,
            base_delay=0.05,
            total_timeout=0.1,
        )(mock_func)

        with pytest.raises(TimeoutError) as exc_info:
            decorated()

        msg = str(exc_info.value)
        assert "total timeout exceeded" in msg
        assert "0.1s" in msg
        assert "attempts" in msg

    def test_none_total_timeout_disables_timeout(self):
        """Should not timeout when total_timeout=None (backward compat)."""
        mock_func = MagicMock(
            side_effect=[
                OperationalError("fail 1"),
                OperationalError("fail 2"),
                "success",
            ]
        )
        decorated = retry_db(
            max_attempts=3,
            base_delay=0.05,
            total_timeout=None,  # Disabled
        )(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_default_total_timeout_is_set(self):
        """Should have default total timeout from constants."""
        assert DEFAULT_TOTAL_TIMEOUT == 30.0


class TestRetryDbAsync:
    """Tests for @retry_db_async decorator."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Should succeed without retries when no exception."""
        call_count = 0

        @retry_db_async()
        async def my_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await my_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_operational_error(self):
        """Should retry on OperationalError and succeed."""
        call_count = 0

        @retry_db_async(max_attempts=3, base_delay=0.01)
        async def my_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OperationalError("connection lost")
            return "success"

        result = await my_func()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_total_timeout_raises_asyncio_timeout_error(self):
        """Should raise asyncio.TimeoutError when total timeout exceeded."""
        call_count = 0

        @retry_db_async(max_attempts=10, base_delay=0.1, total_timeout=0.2)
        async def slow_failing_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.15)
            raise OperationalError("always fails")

        with pytest.raises(asyncio.TimeoutError) as exc_info:
            await slow_failing_func()

        assert call_count < 10
        assert "total timeout exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_none_total_timeout_disables_timeout_async(self):
        """Should not timeout when total_timeout=None (backward compat)."""
        call_count = 0

        @retry_db_async(max_attempts=3, base_delay=0.01, total_timeout=None)
        async def my_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OperationalError("fail")
            return "success"

        result = await my_func()
        assert result == "success"
        assert call_count == 3


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


class TestIsRetryableError:
    """Tests for is_retryable_error() helper function."""

    def test_deadlock_detected_is_retryable(self):
        """40P01 (deadlock_detected) should be retryable."""
        # Create mock exception with pgcode attribute
        exc = Exception("deadlock detected")
        exc.pgcode = "40P01"  # type: ignore[attr-defined]

        assert is_retryable_error(exc) is True

    def test_serialization_failure_is_retryable(self):
        """40001 (serialization_failure) should be retryable."""
        exc = Exception("could not serialize")
        exc.pgcode = "40001"  # type: ignore[attr-defined]

        assert is_retryable_error(exc) is True

    def test_unique_violation_not_retryable(self):
        """23505 (unique_violation) should NOT be retryable."""
        exc = Exception("duplicate key")
        exc.pgcode = "23505"  # type: ignore[attr-defined]

        assert is_retryable_error(exc) is False

    def test_foreign_key_violation_not_retryable(self):
        """23503 (foreign_key_violation) should NOT be retryable."""
        exc = Exception("foreign key violation")
        exc.pgcode = "23503"  # type: ignore[attr-defined]

        assert is_retryable_error(exc) is False

    def test_operational_error_is_retryable(self):
        """OperationalError should be retryable (base exception type)."""
        exc = OperationalError("connection lost")
        assert is_retryable_error(exc) is True

    def test_interface_error_is_retryable(self):
        """InterfaceError should be retryable (base exception type)."""
        exc = InterfaceError("interface error")
        assert is_retryable_error(exc) is True

    def test_pool_error_is_retryable(self):
        """PoolError should be retryable (base exception type)."""
        exc = PoolError("pool exhausted")
        assert is_retryable_error(exc) is True

    def test_value_error_not_retryable(self):
        """ValueError should NOT be retryable."""
        exc = ValueError("invalid value")
        assert is_retryable_error(exc) is False

    def test_exception_without_pgcode_attribute(self):
        """Exception without pgcode should not crash and return False."""
        exc = Exception("generic error")
        # Ensure no pgcode attribute
        assert not hasattr(exc, "pgcode")
        assert is_retryable_error(exc) is False

    def test_exception_with_none_pgcode(self):
        """Exception with pgcode=None should return False."""
        exc = Exception("error with None pgcode")
        exc.pgcode = None  # type: ignore[attr-defined]
        assert is_retryable_error(exc) is False


class TestRetryableConstants:
    """Tests for RETRYABLE_PGCODES constant."""

    def test_deadlock_in_retryable_codes(self):
        """40P01 should be in RETRYABLE_PGCODES."""
        assert "40P01" in RETRYABLE_PGCODES

    def test_serialization_in_retryable_codes(self):
        """40001 should be in RETRYABLE_PGCODES."""
        assert "40001" in RETRYABLE_PGCODES

    def test_unique_violation_not_in_retryable_codes(self):
        """23505 should NOT be in RETRYABLE_PGCODES."""
        assert "23505" not in RETRYABLE_PGCODES


class TestRetryDbWithPgcode:
    """Tests for @retry_db decorator with pgcode-based retries."""

    def test_retry_on_deadlock_pgcode(self):
        """Should retry on exception with 40P01 pgcode."""
        call_count = 0

        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                exc = Exception("deadlock detected")
                exc.pgcode = "40P01"  # type: ignore[attr-defined]
                raise exc
            return "success"

        decorated = retry_db(max_attempts=3, base_delay=0.01)(failing_func)
        result = decorated()

        assert result == "success"
        assert call_count == 2

    def test_retry_on_serialization_pgcode(self):
        """Should retry on exception with 40001 pgcode."""
        call_count = 0

        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                exc = Exception("could not serialize")
                exc.pgcode = "40001"  # type: ignore[attr-defined]
                raise exc
            return "success"

        decorated = retry_db(max_attempts=3, base_delay=0.01)(failing_func)
        result = decorated()

        assert result == "success"
        assert call_count == 2

    def test_no_retry_on_constraint_violation_pgcode(self):
        """Should NOT retry on exception with 23505 pgcode."""

        def failing_func():
            exc = Exception("duplicate key value")
            exc.pgcode = "23505"  # type: ignore[attr-defined]
            raise exc

        decorated = retry_db(max_attempts=3, base_delay=0.01)(failing_func)

        with pytest.raises(Exception, match="duplicate key value"):
            decorated()

    def test_max_attempts_on_persistent_deadlock(self):
        """Should exhaust max_attempts on persistent deadlock."""
        call_count = 0

        def always_deadlock():
            nonlocal call_count
            call_count += 1
            exc = Exception("deadlock detected")
            exc.pgcode = "40P01"  # type: ignore[attr-defined]
            raise exc

        decorated = retry_db(max_attempts=3, base_delay=0.01)(always_deadlock)

        with pytest.raises(Exception, match="deadlock detected"):
            decorated()

        assert call_count == 3


class TestRetryDbAsyncWithPgcode:
    """Tests for @retry_db_async decorator with pgcode-based retries."""

    @pytest.mark.asyncio
    async def test_retry_on_deadlock_pgcode_async(self):
        """Should retry on exception with 40P01 pgcode (async)."""
        call_count = 0

        @retry_db_async(max_attempts=3, base_delay=0.01)
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                exc = Exception("deadlock detected")
                exc.pgcode = "40P01"  # type: ignore[attr-defined]
                raise exc
            return "success"

        result = await failing_func()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_constraint_violation_pgcode_async(self):
        """Should NOT retry on exception with 23505 pgcode (async)."""

        @retry_db_async(max_attempts=3, base_delay=0.01)
        async def failing_func():
            exc = Exception("unique violation")
            exc.pgcode = "23505"  # type: ignore[attr-defined]
            raise exc

        with pytest.raises(Exception, match="unique violation"):
            await failing_func()
