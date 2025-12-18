"""Tests for standardized API error handling.

This module tests the error handling utilities to ensure:
- Consistent HTTP status codes across the API
- Proper exception-to-status-code mapping
- Error logging with context
- No stack trace leakage to clients
"""

import pytest
from fastapi import HTTPException

from backend.api.utils.errors import handle_api_errors, raise_api_error


class TestRaiseAPIError:
    """Test standardized error raising."""

    def test_raise_api_error_session_not_found(self) -> None:
        """Test session not found error."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("session_not_found")

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail["detail"].lower()
        assert exc_info.value.detail["error_code"] == "session_not_found"

    def test_raise_api_error_unauthorized(self) -> None:
        """Test unauthorized error."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("unauthorized")

        assert exc_info.value.status_code == 401
        assert "authentication" in exc_info.value.detail["detail"].lower()
        assert exc_info.value.detail["error_code"] == "unauthorized"

    def test_raise_api_error_forbidden(self) -> None:
        """Test forbidden error."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("forbidden")

        assert exc_info.value.status_code == 403
        assert "denied" in exc_info.value.detail["detail"].lower()
        assert exc_info.value.detail["error_code"] == "forbidden"

    def test_raise_api_error_redis_unavailable(self) -> None:
        """Test Redis unavailable error."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("redis_unavailable")

        assert exc_info.value.status_code == 500
        assert "unavailable" in exc_info.value.detail["detail"].lower()
        assert exc_info.value.detail["error_code"] == "redis_unavailable"

    def test_raise_api_error_custom_detail(self) -> None:
        """Test error with custom message."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("forbidden", "Custom message")

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["detail"] == "Custom message"
        assert exc_info.value.detail["error_code"] == "forbidden"


@pytest.mark.asyncio
class TestErrorDecorator:
    """Test error handling decorator."""

    async def test_error_decorator_success(self) -> None:
        """Test decorator allows successful execution."""

        @handle_api_errors("test operation")
        async def success_func() -> str:
            return "success"

        result = await success_func()
        assert result == "success"

    async def test_error_decorator_http_exception_passthrough(self) -> None:
        """Test decorator re-raises HTTPException as-is."""

        @handle_api_errors("test operation")
        async def http_error_func() -> None:
            raise HTTPException(status_code=418, detail="I'm a teapot")

        with pytest.raises(HTTPException) as exc_info:
            await http_error_func()

        assert exc_info.value.status_code == 418
        assert exc_info.value.detail == "I'm a teapot"

    async def test_error_decorator_value_error(self) -> None:
        """Test decorator converts ValueError to 400."""

        @handle_api_errors("test operation")
        async def value_error_func() -> None:
            raise ValueError("Invalid value")

        with pytest.raises(HTTPException) as exc_info:
            await value_error_func()

        assert exc_info.value.status_code == 400
        assert "Invalid input" in exc_info.value.detail["detail"]
        assert "Invalid value" in exc_info.value.detail["detail"]
        assert exc_info.value.detail["error_code"] == "validation_error"

    async def test_error_decorator_key_error(self) -> None:
        """Test decorator converts KeyError to 404."""

        @handle_api_errors("test operation")
        async def key_error_func() -> None:
            raise KeyError("missing_key")

        with pytest.raises(HTTPException) as exc_info:
            await key_error_func()

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail["detail"].lower()
        assert exc_info.value.detail["error_code"] == "not_found"

    async def test_error_decorator_unexpected_exception(self) -> None:
        """Test decorator converts unexpected errors to 500."""

        @handle_api_errors("test operation")
        async def runtime_error_func() -> None:
            raise RuntimeError("Unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            await runtime_error_func()

        assert exc_info.value.status_code == 500
        assert "unexpected error" in exc_info.value.detail["detail"].lower()
        assert exc_info.value.detail["error_code"] == "internal_error"
        # Should NOT contain stack trace details
        assert "RuntimeError" not in exc_info.value.detail["detail"]
        assert "Traceback" not in exc_info.value.detail["detail"]

    async def test_error_decorator_preserves_function_metadata(self) -> None:
        """Test decorator preserves original function metadata."""

        @handle_api_errors("test operation")
        async def documented_func() -> str:
            """This is a documented function."""
            return "result"

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is a documented function."
