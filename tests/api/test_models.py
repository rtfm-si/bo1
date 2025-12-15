"""Unit tests for API request/response models (P1: injection validation)."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.api.models import (
    CreateSessionRequest,
    MessageResponse,
    TerminationResponse,
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
