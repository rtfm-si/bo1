"""Integration tests for console adapter with input validation and error handling.

These tests validate:
- Input validation (session_id, problem statements)
- Error handling (corrupted checkpoints, missing sessions)
- Security (injection attempts, malicious input)
- Pause/resume functionality
"""

import pytest

from bo1.interfaces.console import (
    run_console_deliberation,
    sanitize_problem_statement,
    validate_session_id,
    validate_user_input,
)
from tests.utils.factories import create_test_problem


class TestInputValidation:
    """Test input validation functions."""

    def test_validate_session_id_valid_uuid(self):
        """Test that valid UUIDs are accepted."""
        valid_uuids = [
            "123e4567-e89b-12d3-a456-426614174000",
            "550e8400-e29b-41d4-a716-446655440000",
            "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        ]
        for uuid_str in valid_uuids:
            assert validate_session_id(uuid_str) is True

    def test_validate_session_id_invalid(self):
        """Test that invalid session IDs are rejected."""
        invalid_ids = [
            "not-a-uuid",
            "12345",
            "",
            "123e4567-e89b-12d3-a456",  # Incomplete UUID
            "'; DROP TABLE sessions; --",  # SQL injection attempt
            "../../../etc/passwd",  # Path traversal
            "<script>alert('xss')</script>",  # XSS attempt
        ]
        for invalid_id in invalid_ids:
            assert validate_session_id(invalid_id) is False

    def test_sanitize_problem_statement_basic(self):
        """Test basic sanitization."""
        statement = "  Should we invest in AI?  "
        result = sanitize_problem_statement(statement)
        assert result == "Should we invest in AI?"

    def test_sanitize_problem_statement_null_bytes(self):
        """Test that null bytes are removed."""
        statement = "Problem\x00with\x00null\x00bytes"
        result = sanitize_problem_statement(statement)
        assert "\x00" not in result
        assert result == "Problemwithnullbytes"

    def test_sanitize_problem_statement_control_chars(self):
        """Test that control characters are removed (except newlines/tabs)."""
        statement = "Problem\x01with\x02control\x03chars"
        result = sanitize_problem_statement(statement)
        # Control chars should be removed
        assert "\x01" not in result
        assert "\x02" not in result
        assert "\x03" not in result

    def test_sanitize_problem_statement_preserves_newlines(self):
        """Test that newlines and tabs are preserved."""
        statement = "Line 1\nLine 2\tTabbed"
        result = sanitize_problem_statement(statement)
        assert "\n" in result
        assert "\t" in result

    def test_sanitize_problem_statement_length_limit(self):
        """Test that overly long statements are truncated."""
        statement = "A" * 20000
        result = sanitize_problem_statement(statement)
        assert len(result) == 10000

    def test_sanitize_problem_statement_sql_injection(self):
        """Test that SQL injection attempts are handled."""
        statement = "'; DROP TABLE problems; --"
        result = sanitize_problem_statement(statement)
        # Should preserve the text but strip dangerous whitespace
        assert result == "'; DROP TABLE problems; --"
        # Note: Actual SQL injection protection happens at the database layer

    def test_validate_user_input_valid(self):
        """Test valid user input."""
        assert validate_user_input("y", ["y", "n"]) is True
        assert validate_user_input("Y", ["y", "n"]) is True
        assert validate_user_input("  y  ", ["y", "n"]) is True
        assert validate_user_input("pause", ["y", "n", "pause"]) is True

    def test_validate_user_input_invalid(self):
        """Test invalid user input."""
        assert validate_user_input("invalid", ["y", "n"]) is False
        assert validate_user_input("", ["y", "n"]) is False
        assert validate_user_input("yes", ["y", "n"]) is False


class TestConsoleAdapterErrorHandling:
    """Test error handling in console adapter."""

    @pytest.mark.asyncio
    async def test_invalid_session_id_format(self):
        """Test that invalid session ID format raises ValueError."""
        problem = create_test_problem(
            title="Test",
            description="Test problem",
            context="Test context",
        )

        with pytest.raises(ValueError, match="Invalid session ID format"):
            await run_console_deliberation(
                problem=problem,
                session_id="not-a-valid-uuid",
                max_rounds=1,
            )

    @pytest.mark.asyncio
    async def test_empty_problem_description(self):
        """Test that empty problem description raises ValueError."""
        problem = create_test_problem(
            title="Test",
            description="",
            context="Test context",
        )

        with pytest.raises(ValueError, match="Problem description cannot be empty"):
            await run_console_deliberation(
                problem=problem,
                session_id=None,
                max_rounds=1,
            )

    @pytest.mark.asyncio
    async def test_whitespace_only_problem(self):
        """Test that whitespace-only problem raises ValueError."""
        problem = create_test_problem(
            title="Test",
            description="   \n\t  ",
            context="Test context",
        )

        with pytest.raises(ValueError, match="Problem description cannot be empty"):
            await run_console_deliberation(
                problem=problem,
                session_id=None,
                max_rounds=1,
            )

    @pytest.mark.skip(reason="Checkpointing not yet enabled (Week 5 feature)")
    @pytest.mark.asyncio
    async def test_missing_checkpoint(self):
        """Test that resuming from non-existent session raises ValueError.

        When a session_id is provided, console.py enables Redis checkpointing.
        This test verifies that trying to resume from a non-existent session
        raises an appropriate error.
        """
        problem = create_test_problem(
            title="Test",
            description="Test problem",
            context="Test context",
        )

        # Use a valid UUID that doesn't exist
        fake_session_id = "550e8400-e29b-41d4-a716-446655440000"

        with pytest.raises(
            ValueError, match="No checkpoint found|Corrupted checkpoint|Error loading checkpoint"
        ):
            await run_console_deliberation(
                problem=problem,
                session_id=fake_session_id,
                max_rounds=1,
            )


class TestSecurityValidation:
    """Test security-related validations."""

    @pytest.mark.requires_llm
    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="RedisSaver.aget_tuple() not implemented in langgraph-checkpoint-redis 0.1.2"
    )
    async def test_script_injection_in_problem(self):
        """Test that script injection attempts in problem are sanitized."""
        problem = create_test_problem(
            title="<script>alert('xss')</script>",
            description="<script>alert('xss')</script>Should we invest?",
            context="<img src=x onerror=alert('xss')>",
        )

        # Should not raise an error, just sanitize
        state = await run_console_deliberation(
            problem=problem,
            session_id=None,
            max_rounds=1,
            debug=True,
        )

        # Problem should be sanitized
        assert state is not None
        assert state["problem"].description != ""

    @pytest.mark.requires_llm
    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="RedisSaver.aget_tuple() not implemented in langgraph-checkpoint-redis 0.1.2"
    )
    async def test_sql_injection_in_problem(self):
        """Test that SQL injection attempts are handled."""
        problem = create_test_problem(
            title="Test",
            description="'; DROP TABLE problems; --",
            context="Test context",
        )

        # Should not raise an error, just sanitize
        state = await run_console_deliberation(
            problem=problem,
            session_id=None,
            max_rounds=1,
            debug=True,
        )

        assert state is not None

    @pytest.mark.asyncio
    async def test_path_traversal_in_session_id(self):
        """Test that path traversal attempts in session ID are rejected."""
        problem = create_test_problem(
            title="Test",
            description="Test problem",
            context="Test context",
        )

        with pytest.raises(ValueError, match="Invalid session ID format"):
            await run_console_deliberation(
                problem=problem,
                session_id="../../../etc/passwd",
                max_rounds=1,
            )


class TestPauseResume:
    """Test pause/resume functionality (requires checkpointing enabled).

    Note: These tests are placeholders for Week 5 when Redis checkpointing is enabled.
    Currently, checkpointing is disabled in console.py.
    """

    @pytest.mark.skip(reason="Checkpointing not yet enabled (Week 5 feature)")
    @pytest.mark.asyncio
    async def test_pause_and_resume_cycle(self):
        """Test full pause/resume cycle."""
        # This will be implemented in Week 5
        pass

    @pytest.mark.skip(reason="Checkpointing not yet enabled (Week 5 feature)")
    @pytest.mark.asyncio
    async def test_resume_validates_checkpoint_integrity(self):
        """Test that resume validates checkpoint integrity."""
        # This will be implemented in Week 5
        pass
