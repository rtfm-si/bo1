"""Unit tests for API request/response models (P1: injection validation)."""

import pytest
from pydantic import ValidationError

from backend.api.models import CreateSessionRequest


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
