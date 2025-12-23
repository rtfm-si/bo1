"""Unit tests for API request/response models (P1: injection validation)."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.api.models import (
    BadRequestErrorResponse,
    ConflictErrorResponse,
    CreateSessionRequest,
    ErrorResponse,
    ForbiddenErrorResponse,
    InternalErrorResponse,
    MessageResponse,
    NotFoundErrorResponse,
    RateLimitResponse,
    TerminationResponse,
    UnauthorizedErrorResponse,
    WhitelistCheckResponse,
)


class TestCreateSessionRequestValidation:
    """Test security validation for CreateSessionRequest."""

    def test_valid_problem_statement(self):
        """Test that valid problem statements are accepted."""
        request = CreateSessionRequest(
            problem_statement="Should we invest $500K in expanding to the European market?"
        )
        assert "invest" in request.problem_statement

    def test_rejects_script_tags(self):
        """Test that XSS script tags are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CreateSessionRequest(
                problem_statement="<script>alert('xss')</script>What should we do?"
            )

        errors = exc_info.value.errors()
        assert any("script tags" in str(e["msg"]).lower() for e in errors)

    def test_rejects_script_tag_variations(self):
        """Test that script tag variations are rejected."""
        xss_attempts = [
            "<SCRIPT>alert('xss')</SCRIPT>What should we do?",
            "<script src='evil.js'>What should we do?",
            "<script type='text/javascript'>What should we do?",
        ]

        for attempt in xss_attempts:
            with pytest.raises(ValidationError):
                CreateSessionRequest(problem_statement=attempt)

    def test_rejects_drop_table_injection(self):
        """Test that SQL DROP TABLE injection is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CreateSessionRequest(problem_statement="What should we do?; DROP TABLE sessions;--")

        errors = exc_info.value.errors()
        assert any("sql" in str(e["msg"]).lower() for e in errors)

    def test_rejects_delete_from_injection(self):
        """Test that SQL DELETE FROM injection is rejected."""
        with pytest.raises(ValidationError):
            CreateSessionRequest(
                problem_statement="What should we do?; DELETE FROM users WHERE 1=1;--"
            )

    def test_rejects_union_select_injection(self):
        """Test that SQL UNION SELECT injection is rejected."""
        with pytest.raises(ValidationError):
            CreateSessionRequest(
                problem_statement="What should we do? UNION SELECT * FROM passwords"
            )

    def test_rejects_truncate_table_injection(self):
        """Test that SQL TRUNCATE TABLE injection is rejected."""
        with pytest.raises(ValidationError):
            CreateSessionRequest(problem_statement="What should we do?; TRUNCATE TABLE sessions;--")

    def test_rejects_insert_into_injection(self):
        """Test that SQL INSERT INTO injection is rejected."""
        with pytest.raises(ValidationError):
            CreateSessionRequest(
                problem_statement="What should we do? INSERT INTO users VALUES ('hacker')"
            )

    def test_problem_statement_min_length(self):
        """Test that short problem statements are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CreateSessionRequest(problem_statement="Too short")

        errors = exc_info.value.errors()
        assert any("at least 10" in str(e["msg"]).lower() for e in errors)

    def test_problem_statement_max_length(self):
        """Test that overly long problem statements are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CreateSessionRequest(problem_statement="x" * 10001)

        errors = exc_info.value.errors()
        assert any("at most 10000" in str(e["msg"]).lower() for e in errors)

    def test_context_size_limit(self):
        """Test that problem_context exceeding 50KB is rejected."""
        # Create a context > 50KB
        large_context = {"data": "x" * 60000}

        with pytest.raises(ValidationError) as exc_info:
            CreateSessionRequest(
                problem_statement="Should we expand to Europe?",
                problem_context=large_context,
            )

        errors = exc_info.value.errors()
        assert any("50kb" in str(e["msg"]).lower() for e in errors)

    def test_empty_problem_statement_rejected(self):
        """Test that empty (whitespace-only) problem statements are rejected."""
        with pytest.raises(ValidationError):
            CreateSessionRequest(problem_statement="          ")


class TestMessageResponseSerialization:
    """Test MessageResponse model serialization."""

    def test_message_response_serialization(self):
        """Test that MessageResponse serializes correctly."""
        response = MessageResponse(status="success", message="Operation completed")
        data = response.model_dump()
        assert data == {"status": "success", "message": "Operation completed"}

    def test_message_response_json(self):
        """Test that MessageResponse generates valid JSON."""
        response = MessageResponse(status="error", message="Something went wrong")
        json_str = response.model_dump_json()
        assert '"status":"error"' in json_str
        assert '"message":"Something went wrong"' in json_str

    def test_message_response_required_fields(self):
        """Test that MessageResponse requires both fields."""
        with pytest.raises(ValidationError):
            MessageResponse(status="success")  # missing message
        with pytest.raises(ValidationError):
            MessageResponse(message="test")  # missing status


class TestWhitelistCheckResponseSerialization:
    """Test WhitelistCheckResponse model serialization."""

    def test_whitelist_check_response_true(self):
        """Test WhitelistCheckResponse with is_whitelisted=True."""
        response = WhitelistCheckResponse(is_whitelisted=True)
        assert response.model_dump() == {"is_whitelisted": True}

    def test_whitelist_check_response_false(self):
        """Test WhitelistCheckResponse with is_whitelisted=False."""
        response = WhitelistCheckResponse(is_whitelisted=False)
        assert response.model_dump() == {"is_whitelisted": False}

    def test_whitelist_check_required_field(self):
        """Test that is_whitelisted is required."""
        with pytest.raises(ValidationError):
            WhitelistCheckResponse()


class TestTerminationResponseSerialization:
    """Test TerminationResponse model serialization."""

    def test_termination_response_serialization(self):
        """Test that TerminationResponse serializes correctly."""
        now = datetime.now(UTC)
        response = TerminationResponse(
            session_id="bo1_test123",
            status="terminated",
            terminated_at=now,
            termination_type="user_cancelled",
            billable_portion=0.5,
            completed_sub_problems=2,
            total_sub_problems=4,
            synthesis_available=False,
        )
        data = response.model_dump()
        assert data["session_id"] == "bo1_test123"
        assert data["status"] == "terminated"
        assert data["termination_type"] == "user_cancelled"
        assert data["billable_portion"] == 0.5
        assert data["completed_sub_problems"] == 2
        assert data["total_sub_problems"] == 4
        assert data["synthesis_available"] is False

    def test_termination_response_billable_portion_bounds(self):
        """Test that billable_portion must be between 0 and 1."""
        now = datetime.now(UTC)
        base_args = {
            "session_id": "bo1_test",
            "status": "terminated",
            "terminated_at": now,
            "termination_type": "user_cancelled",
            "completed_sub_problems": 0,
            "total_sub_problems": 1,
            "synthesis_available": False,
        }

        # Valid bounds
        TerminationResponse(billable_portion=0.0, **base_args)
        TerminationResponse(billable_portion=1.0, **base_args)
        TerminationResponse(billable_portion=0.5, **base_args)

        # Invalid bounds
        with pytest.raises(ValidationError):
            TerminationResponse(billable_portion=-0.1, **base_args)
        with pytest.raises(ValidationError):
            TerminationResponse(billable_portion=1.1, **base_args)


class TestRateLimitResponse:
    """Test RateLimitResponse model for 429 responses."""

    def test_model_serialization(self):
        """Test RateLimitResponse serializes correctly."""
        response = RateLimitResponse(retry_after=60)
        data = response.model_dump()

        assert data["detail"] == "Too many requests. Please try again later."
        assert data["error_code"] == "rate_limited"
        assert data["retry_after"] == 60

    def test_model_with_custom_values(self):
        """Test RateLimitResponse with custom values."""
        response = RateLimitResponse(
            detail="Custom rate limit message",
            error_code="custom_rate_limit",
            retry_after=120,
        )
        data = response.model_dump()

        assert data["detail"] == "Custom rate limit message"
        assert data["error_code"] == "custom_rate_limit"
        assert data["retry_after"] == 120

    def test_retry_after_required(self):
        """Test that retry_after is required."""
        # Default values allow constructing without detail/error_code
        response = RateLimitResponse(retry_after=30)
        assert response.retry_after == 30

    def test_json_schema_example(self):
        """Test that model has expected JSON schema example."""
        schema = RateLimitResponse.model_json_schema()
        assert "examples" in schema
        assert len(schema["examples"]) > 0

        example = schema["examples"][0]
        assert example["detail"] == "Too many requests. Please try again later."
        assert example["error_code"] == "rate_limited"
        assert example["retry_after"] == 60


class TestErrorResponse:
    """Test ErrorResponse model and its variants."""

    def test_error_response_serialization(self):
        """Test ErrorResponse serializes with error_code and message."""
        response = ErrorResponse(
            error_code="API_NOT_FOUND",
            message="Session not found",
        )
        data = response.model_dump()

        assert data["error_code"] == "API_NOT_FOUND"
        assert data["message"] == "Session not found"

    def test_error_response_schema_has_examples(self):
        """Test ErrorResponse has proper JSON schema examples."""
        schema = ErrorResponse.model_json_schema()
        assert "examples" in schema
        assert len(schema["examples"]) >= 1

        # Verify examples have the correct structure
        for example in schema["examples"]:
            assert "error_code" in example
            assert "message" in example

    def test_not_found_error_response(self):
        """Test NotFoundErrorResponse has correct defaults."""
        response = NotFoundErrorResponse()
        data = response.model_dump()

        assert data["error_code"] == "API_NOT_FOUND"
        assert "not found" in data["message"].lower()

    def test_not_found_error_response_custom_message(self):
        """Test NotFoundErrorResponse with custom message."""
        response = NotFoundErrorResponse(
            message="Custom not found message",
        )
        data = response.model_dump()

        assert data["error_code"] == "API_NOT_FOUND"
        assert data["message"] == "Custom not found message"

    def test_forbidden_error_response(self):
        """Test ForbiddenErrorResponse has correct defaults."""
        response = ForbiddenErrorResponse()
        data = response.model_dump()

        assert data["error_code"] == "API_FORBIDDEN"
        assert "denied" in data["message"].lower() or "access" in data["message"].lower()

    def test_unauthorized_error_response(self):
        """Test UnauthorizedErrorResponse has correct defaults."""
        response = UnauthorizedErrorResponse()
        data = response.model_dump()

        assert data["error_code"] == "API_UNAUTHORIZED"
        assert "authentication" in data["message"].lower() or "required" in data["message"].lower()

    def test_bad_request_error_response(self):
        """Test BadRequestErrorResponse has correct defaults."""
        response = BadRequestErrorResponse()
        data = response.model_dump()

        assert data["error_code"] == "API_BAD_REQUEST"
        assert "invalid" in data["message"].lower() or "request" in data["message"].lower()

    def test_conflict_error_response(self):
        """Test ConflictErrorResponse has correct defaults."""
        response = ConflictErrorResponse()
        data = response.model_dump()

        assert data["error_code"] == "API_CONFLICT"
        assert "conflict" in data["message"].lower()

    def test_internal_error_response(self):
        """Test InternalErrorResponse has correct defaults."""
        response = InternalErrorResponse()
        data = response.model_dump()

        assert data["error_code"] == "API_REQUEST_ERROR"
        assert "error" in data["message"].lower()

    def test_all_error_variants_inherit_from_error_response(self):
        """Test all error variants are subclasses of ErrorResponse."""
        variants = [
            NotFoundErrorResponse,
            ForbiddenErrorResponse,
            UnauthorizedErrorResponse,
            BadRequestErrorResponse,
            ConflictErrorResponse,
            InternalErrorResponse,
        ]

        for variant in variants:
            assert issubclass(variant, ErrorResponse)
            instance = variant()
            assert isinstance(instance, ErrorResponse)

    def test_error_response_required_fields(self):
        """Test ErrorResponse requires both error_code and message."""
        with pytest.raises(ValidationError):
            ErrorResponse()  # type: ignore

        with pytest.raises(ValidationError):
            ErrorResponse(error_code="TEST")  # type: ignore

        with pytest.raises(ValidationError):
            ErrorResponse(message="Test message")  # type: ignore


class TestErrorResponseHelpers:
    """Test error response helpers in responses.py."""

    def test_error_400_response_structure(self):
        """Test ERROR_400_RESPONSE has correct structure."""
        from backend.api.utils.responses import ERROR_400_RESPONSE

        assert "model" in ERROR_400_RESPONSE
        assert ERROR_400_RESPONSE["model"] == BadRequestErrorResponse
        assert "description" in ERROR_400_RESPONSE
        assert (
            "400" in ERROR_400_RESPONSE["description"].lower()
            or "bad" in ERROR_400_RESPONSE["description"].lower()
        )

    def test_error_401_response_structure(self):
        """Test ERROR_401_RESPONSE has correct structure."""
        from backend.api.utils.responses import ERROR_401_RESPONSE

        assert "model" in ERROR_401_RESPONSE
        assert ERROR_401_RESPONSE["model"] == UnauthorizedErrorResponse
        assert "description" in ERROR_401_RESPONSE

    def test_error_403_response_structure(self):
        """Test ERROR_403_RESPONSE has correct structure."""
        from backend.api.utils.responses import ERROR_403_RESPONSE

        assert "model" in ERROR_403_RESPONSE
        assert ERROR_403_RESPONSE["model"] == ForbiddenErrorResponse
        assert "description" in ERROR_403_RESPONSE

    def test_error_404_response_structure(self):
        """Test ERROR_404_RESPONSE has correct structure."""
        from backend.api.utils.responses import ERROR_404_RESPONSE

        assert "model" in ERROR_404_RESPONSE
        assert ERROR_404_RESPONSE["model"] == NotFoundErrorResponse
        assert "description" in ERROR_404_RESPONSE

    def test_error_409_response_structure(self):
        """Test ERROR_409_RESPONSE has correct structure."""
        from backend.api.utils.responses import ERROR_409_RESPONSE

        assert "model" in ERROR_409_RESPONSE
        assert ERROR_409_RESPONSE["model"] == ConflictErrorResponse
        assert "description" in ERROR_409_RESPONSE

    def test_error_500_response_structure(self):
        """Test ERROR_500_RESPONSE has correct structure."""
        from backend.api.utils.responses import ERROR_500_RESPONSE

        assert "model" in ERROR_500_RESPONSE
        assert ERROR_500_RESPONSE["model"] == InternalErrorResponse
        assert "description" in ERROR_500_RESPONSE

    def test_all_error_helpers_are_dict(self):
        """Test all error response helpers are dictionaries."""
        from backend.api.utils.responses import (
            ERROR_400_RESPONSE,
            ERROR_401_RESPONSE,
            ERROR_403_RESPONSE,
            ERROR_404_RESPONSE,
            ERROR_409_RESPONSE,
            ERROR_500_RESPONSE,
        )

        helpers = [
            ERROR_400_RESPONSE,
            ERROR_401_RESPONSE,
            ERROR_403_RESPONSE,
            ERROR_404_RESPONSE,
            ERROR_409_RESPONSE,
            ERROR_500_RESPONSE,
        ]

        for helper in helpers:
            assert isinstance(helper, dict)
            assert "model" in helper
            assert "description" in helper
