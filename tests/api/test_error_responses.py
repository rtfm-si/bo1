"""Tests for error response documentation and structured error responses.

Verifies:
- ErrorResponse model exists with required fields
- 401/404 responses are in endpoint decorator
- All API error responses include 'error_code' field
"""

import pytest
from fastapi import HTTPException

from backend.api.utils.errors import (
    ERROR_RESPONSES,
    ErrorType,
    handle_api_errors,
    raise_api_error,
)


class TestRaiseApiError:
    """Tests for raise_api_error function."""

    def test_raise_api_error_includes_error_code(self) -> None:
        """Verify raise_api_error returns structured error with error_code."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("not_found")

        exc = exc_info.value
        assert exc.status_code == 404
        assert isinstance(exc.detail, dict)
        assert "error_code" in exc.detail
        assert exc.detail["error_code"] == "not_found"
        assert "detail" in exc.detail
        assert exc.detail["detail"] == "Resource not found"

    def test_raise_api_error_custom_detail(self) -> None:
        """Verify custom detail message is preserved."""
        custom_msg = "User with ID 123 not found"
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error("not_found", custom_msg)

        exc = exc_info.value
        assert exc.detail["detail"] == custom_msg
        assert exc.detail["error_code"] == "not_found"

    @pytest.mark.parametrize(
        "error_type",
        [
            "redis_unavailable",
            "session_not_found",
            "unauthorized",
            "forbidden",
            "invalid_input",
            "not_found",
            "conflict",
            "service_unavailable",
            "gone",
            "rate_limited",
            "internal_error",
        ],
    )
    def test_all_error_types_have_error_code(self, error_type: ErrorType) -> None:
        """Verify all error types return structured response with error_code."""
        with pytest.raises(HTTPException) as exc_info:
            raise_api_error(error_type)

        exc = exc_info.value
        assert isinstance(exc.detail, dict)
        assert "error_code" in exc.detail
        assert "detail" in exc.detail

    def test_error_responses_mapping_has_three_tuple(self) -> None:
        """Verify ERROR_RESPONSES mapping has (status_code, message, error_code)."""
        for error_type, response_tuple in ERROR_RESPONSES.items():
            assert len(response_tuple) == 3, f"{error_type} should have 3 elements"
            status_code, message, error_code = response_tuple
            assert isinstance(status_code, int)
            assert isinstance(message, str)
            assert isinstance(error_code, str)


class TestHandleApiErrors:
    """Tests for handle_api_errors decorator."""

    @pytest.mark.asyncio
    async def test_decorator_value_error_includes_error_code(self) -> None:
        """Verify ValueError is converted to 400 with error_code."""

        @handle_api_errors("test operation")
        async def raise_value_error() -> None:
            raise ValueError("invalid value")

        with pytest.raises(HTTPException) as exc_info:
            await raise_value_error()

        exc = exc_info.value
        assert exc.status_code == 400
        assert isinstance(exc.detail, dict)
        assert exc.detail["error_code"] == "validation_error"
        assert "invalid value" in exc.detail["detail"]

    @pytest.mark.asyncio
    async def test_decorator_key_error_includes_error_code(self) -> None:
        """Verify KeyError is converted to 404 with error_code."""

        @handle_api_errors("test operation")
        async def raise_key_error() -> None:
            raise KeyError("missing_key")

        with pytest.raises(HTTPException) as exc_info:
            await raise_key_error()

        exc = exc_info.value
        assert exc.status_code == 404
        assert isinstance(exc.detail, dict)
        assert exc.detail["error_code"] == "not_found"
        assert "missing_key" in exc.detail["detail"]

    @pytest.mark.asyncio
    async def test_decorator_generic_exception_includes_error_code(self) -> None:
        """Verify generic Exception is converted to 500 with error_code."""

        @handle_api_errors("test operation")
        async def raise_generic_error() -> None:
            raise RuntimeError("something went wrong")

        with pytest.raises(HTTPException) as exc_info:
            await raise_generic_error()

        exc = exc_info.value
        assert exc.status_code == 500
        assert isinstance(exc.detail, dict)
        assert exc.detail["error_code"] == "internal_error"
        # Should NOT leak the actual error message
        assert "something went wrong" not in exc.detail["detail"]

    @pytest.mark.asyncio
    async def test_decorator_passes_through_http_exception(self) -> None:
        """Verify HTTPException is passed through as-is."""
        original_detail = {"detail": "Custom error", "error_code": "custom_error"}

        @handle_api_errors("test operation")
        async def raise_http_exception() -> None:
            raise HTTPException(status_code=418, detail=original_detail)

        with pytest.raises(HTTPException) as exc_info:
            await raise_http_exception()

        exc = exc_info.value
        assert exc.status_code == 418
        assert exc.detail == original_detail


class TestErrorResponseModel:
    """Test ErrorResponse model structure."""

    def test_error_response_model_exists(self):
        """ErrorResponse model should exist."""
        from backend.api.models import ErrorResponse

        assert ErrorResponse is not None

    def test_error_response_has_required_fields(self):
        """ErrorResponse should have error_code and message fields."""
        from backend.api.models import ErrorResponse

        # Create instance to verify structure
        error = ErrorResponse(error_code="TEST_ERROR", message="Test error message")
        assert error.error_code == "TEST_ERROR"
        assert error.message == "Test error message"

    def test_error_response_structure(self):
        """ErrorResponse should have proper structure for API consistency."""
        from backend.api.models import ErrorResponse

        error = ErrorResponse(
            error_code="API_NOT_FOUND",
            message="Session not found",
        )
        assert error.error_code == "API_NOT_FOUND"
        assert error.message == "Session not found"


class TestActionsEndpointResponses:
    """Test actions endpoint has error responses in decorator."""

    def test_actions_list_has_401_response(self):
        """Actions list endpoint should have 401 in responses."""
        from backend.api.actions import router

        # Find the route
        for route in router.routes:
            if hasattr(route, "path") and route.path == "" and "GET" in route.methods:
                responses = getattr(route, "responses", {})
                assert 401 in responses or "401" in responses, "401 should be documented"
                break

    def test_action_detail_has_404_response(self):
        """Action detail endpoint should have 404 in responses."""
        from backend.api.actions import router

        for route in router.routes:
            if hasattr(route, "path") and route.path == "/{action_id}" and "GET" in route.methods:
                responses = getattr(route, "responses", {})
                assert 404 in responses or "404" in responses, "404 should be documented"
                break
