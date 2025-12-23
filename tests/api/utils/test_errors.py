"""Unit tests for http_error() helper and ErrorDetailDict."""

import pytest
from fastapi import HTTPException

from backend.api.utils.errors import ErrorDetailDict, http_error
from bo1.logging.errors import ErrorCode


class TestHttpError:
    """Tests for http_error() helper function."""

    def test_returns_http_exception(self):
        """http_error should return an HTTPException."""
        result = http_error(ErrorCode.VALIDATION_ERROR, "Test error")
        assert isinstance(result, HTTPException)

    def test_default_status_code(self):
        """Default status code should be 400."""
        result = http_error(ErrorCode.VALIDATION_ERROR, "Test error")
        assert result.status_code == 400

    def test_custom_status_code(self):
        """Should support custom status codes."""
        result = http_error(ErrorCode.API_NOT_FOUND, "Not found", status=404)
        assert result.status_code == 404

        result = http_error(ErrorCode.API_UNAUTHORIZED, "Unauthorized", status=401)
        assert result.status_code == 401

        result = http_error(ErrorCode.API_FORBIDDEN, "Forbidden", status=403)
        assert result.status_code == 403

        result = http_error(ErrorCode.GRAPH_EXECUTION_ERROR, "Server error", status=500)
        assert result.status_code == 500

    def test_error_code_in_detail(self):
        """Detail should contain error_code field with ErrorCode value."""
        result = http_error(ErrorCode.API_SESSION_ERROR, "Session error")
        assert result.detail["error_code"] == "API_SESSION_ERROR"

    def test_message_in_detail(self):
        """Detail should contain message field."""
        result = http_error(ErrorCode.VALIDATION_ERROR, "Invalid input provided")
        assert result.detail["message"] == "Invalid input provided"

    def test_additional_context(self):
        """Should include additional context in detail."""
        result = http_error(
            ErrorCode.API_SESSION_ERROR,
            "Session failed",
            status=500,
            session_id="bo1_abc123",
            user_id="user_123",
        )
        assert result.detail["error_code"] == "API_SESSION_ERROR"
        assert result.detail["message"] == "Session failed"
        assert result.detail["session_id"] == "bo1_abc123"
        assert result.detail["user_id"] == "user_123"

    def test_rate_limit_context(self):
        """Should support rate limit error context."""
        result = http_error(
            ErrorCode.API_RATE_LIMIT,
            "Meeting cap exceeded",
            status=429,
            reset_time="2024-01-01T12:00:00Z",
            limit=10,
            remaining=0,
        )
        assert result.status_code == 429
        assert result.detail["error_code"] == "API_RATE_LIMIT"
        assert result.detail["reset_time"] == "2024-01-01T12:00:00Z"
        assert result.detail["limit"] == 10
        assert result.detail["remaining"] == 0

    def test_conflict_error(self):
        """Should support conflict errors."""
        result = http_error(
            ErrorCode.API_CONFLICT,
            "Session is already running",
            status=409,
        )
        assert result.status_code == 409
        assert result.detail["error_code"] == "API_CONFLICT"

    def test_gone_error(self):
        """Should support 410 Gone errors."""
        result = http_error(
            ErrorCode.API_SESSION_ERROR,
            "Session checkpoint expired",
            status=410,
        )
        assert result.status_code == 410

    def test_raises_correctly(self):
        """Should be raiseable as an exception."""
        with pytest.raises(HTTPException) as exc_info:
            raise http_error(ErrorCode.API_BAD_REQUEST, "Invalid request")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "API_BAD_REQUEST"
        assert exc_info.value.detail["message"] == "Invalid request"

    def test_all_api_error_codes(self):
        """All API error codes should work with http_error."""
        api_codes = [
            ErrorCode.API_REQUEST_ERROR,
            ErrorCode.API_AUDIT_ERROR,
            ErrorCode.API_NOT_FOUND,
            ErrorCode.API_FORBIDDEN,
            ErrorCode.API_UNAUTHORIZED,
            ErrorCode.API_CONFLICT,
            ErrorCode.API_RATE_LIMIT,
            ErrorCode.API_BAD_REQUEST,
            ErrorCode.API_SESSION_ERROR,
            ErrorCode.API_ACTION_ERROR,
            ErrorCode.API_SSE_ERROR,
            ErrorCode.API_WORKSPACE_ERROR,
        ]

        for code in api_codes:
            result = http_error(code, f"Test message for {code.value}")
            assert result.detail["error_code"] == code.value
            assert "Test message" in result.detail["message"]


class TestErrorDetailDict:
    """Tests for ErrorDetailDict TypedDict structure."""

    def test_error_detail_dict_fields(self):
        """ErrorDetailDict should have expected fields."""
        # This is a TypedDict so we test its structure at runtime
        detail: ErrorDetailDict = {
            "error_code": "TEST_ERROR",
            "message": "Test message",
        }
        assert detail["error_code"] == "TEST_ERROR"
        assert detail["message"] == "Test message"

    def test_error_detail_dict_with_detail(self):
        """ErrorDetailDict should support optional detail field."""
        detail: ErrorDetailDict = {
            "error_code": "TEST_ERROR",
            "message": "Test message",
            "detail": {"extra": "info"},
        }
        assert detail["detail"] == {"extra": "info"}


class TestHttpErrorIntegration:
    """Integration tests for http_error with real ErrorCodes."""

    def test_validation_error_workflow(self):
        """Test validation error workflow."""
        err = http_error(ErrorCode.VALIDATION_ERROR, "Field 'name' is required")
        assert err.status_code == 400
        assert err.detail["error_code"] == "VALIDATION_ERROR"

    def test_auth_error_workflow(self):
        """Test authentication error workflow."""
        err = http_error(
            ErrorCode.AUTH_TOKEN_ERROR,
            "Session expired",
            status=401,
        )
        assert err.status_code == 401
        assert err.detail["error_code"] == "AUTH_TOKEN_ERROR"

    def test_service_error_workflow(self):
        """Test service error workflow."""
        err = http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR,
            "Failed to start deliberation",
            status=500,
            session_id="bo1_test",
        )
        assert err.status_code == 500
        assert err.detail["error_code"] == "SERVICE_EXECUTION_ERROR"
        assert err.detail["session_id"] == "bo1_test"
