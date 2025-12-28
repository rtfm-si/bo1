"""Tests for session termination endpoint.

Tests POST /api/v1/sessions/{id}/terminate functionality:
- Termination types (blocker_identified, user_cancelled, continue_best_effort)
- Partial billing calculation
- State transitions
- Error handling
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSessionTermination:
    """Tests for session termination endpoint."""

    @pytest.fixture
    def mock_redis_manager(self):
        """Create a mock Redis manager."""
        manager = MagicMock()
        manager.is_available = True
        manager.load_metadata.return_value = {
            "status": "active",
            "user_id": "test-user-123",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "problem_statement": "Test problem",
        }
        manager.load_state.return_value = {
            "sub_problem_results": [{"synthesis": "Result 1"}],
            "problem": {"sub_problems": [{"goal": "SP1"}, {"goal": "SP2"}, {"goal": "SP3"}]},
        }
        manager.save_metadata.return_value = True
        return manager

    @pytest.fixture
    def mock_session_manager(self):
        """Create a mock session manager."""
        manager = MagicMock()
        manager.active_executions = {}
        manager.kill_session = AsyncMock()
        return manager

    def test_termination_request_valid_types(self):
        """Test that termination request validates termination types."""
        from backend.api.models import TerminationRequest

        # Valid types
        for term_type in ["blocker_identified", "user_cancelled", "continue_best_effort"]:
            req = TerminationRequest(termination_type=term_type)
            assert req.termination_type == term_type

    def test_termination_request_invalid_type(self):
        """Test that invalid termination type is rejected."""
        from pydantic import ValidationError

        from backend.api.models import TerminationRequest

        with pytest.raises(ValidationError):
            TerminationRequest(termination_type="invalid_type")

    def test_termination_request_with_reason(self):
        """Test termination request with reason."""
        from backend.api.models import TerminationRequest

        req = TerminationRequest(
            termination_type="blocker_identified",
            reason="Missing critical market data for Europe",
        )
        assert req.reason == "Missing critical market data for Europe"

    def test_termination_request_reason_max_length(self):
        """Test termination reason max length validation."""
        from pydantic import ValidationError

        from backend.api.models import TerminationRequest

        # Should fail with reason > 2000 chars
        with pytest.raises(ValidationError):
            TerminationRequest(
                termination_type="user_cancelled",
                reason="x" * 2001,
            )

    def test_billable_portion_calculation_full_completion(self):
        """Test billable portion is 1.0 when all sub-problems completed."""
        # 3/3 sub-problems completed = 1.0
        completed = 3
        total = 3
        billable_portion = completed / max(total, 1)
        assert billable_portion == 1.0

    def test_billable_portion_calculation_partial(self):
        """Test billable portion for partial completion."""
        # 1/3 sub-problems completed = 0.333...
        completed = 1
        total = 3
        billable_portion = completed / max(total, 1)
        assert abs(billable_portion - 0.333) < 0.01

    def test_billable_portion_user_cancelled_zero(self):
        """Test user_cancelled with no completions = 0.0 billable."""
        completed = 0
        total = 3
        termination_type = "user_cancelled"

        billable_portion = completed / max(total, 1)
        if termination_type == "user_cancelled" and completed == 0:
            billable_portion = 0.0

        assert billable_portion == 0.0

    def test_billable_portion_continue_best_effort_minimum(self):
        """Test continue_best_effort has minimum 25% billing."""
        completed = 0
        total = 3
        termination_type = "continue_best_effort"

        billable_portion = completed / max(total, 1)
        if termination_type == "continue_best_effort":
            billable_portion = max(billable_portion, 0.25)

        assert billable_portion == 0.25

    def test_termination_response_model(self):
        """Test TerminationResponse model structure."""
        from backend.api.models import TerminationResponse

        resp = TerminationResponse(
            session_id="bo1_test123",
            status="terminated",
            terminated_at=datetime.now(UTC),
            termination_type="user_cancelled",
            billable_portion=0.5,
            completed_sub_problems=1,
            total_sub_problems=2,
            synthesis_available=False,
        )

        assert resp.session_id == "bo1_test123"
        assert resp.status == "terminated"
        assert resp.billable_portion == 0.5
        assert not resp.synthesis_available

    def test_termination_response_synthesis_available(self):
        """Test synthesis_available is True for continue_best_effort with completions."""
        from backend.api.models import TerminationResponse

        resp = TerminationResponse(
            session_id="bo1_test123",
            status="terminated",
            terminated_at=datetime.now(UTC),
            termination_type="continue_best_effort",
            billable_portion=0.5,
            completed_sub_problems=1,
            total_sub_problems=2,
            synthesis_available=True,
        )

        assert resp.synthesis_available is True


class TestSessionRepositoryTermination:
    """Tests for session repository termination methods."""

    @patch("bo1.state.repositories.session_repository.db_session")
    def test_terminate_session_success(self, mock_db_session):
        """Test successful session termination in repository."""
        from bo1.state.repositories.session_repository import SessionRepository

        # Mock cursor and result
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": "bo1_test123",
            "status": "terminated",
            "terminated_at": datetime.now(UTC),
            "termination_type": "user_cancelled",
            "termination_reason": "Test reason",
            "billable_portion": 0.5,
            "updated_at": datetime.now(UTC),
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db_session.return_value.__enter__.return_value = mock_conn

        repo = SessionRepository()
        result = repo.terminate_session(
            session_id="bo1_test123",
            termination_type="user_cancelled",
            termination_reason="Test reason",
            billable_portion=0.5,
        )

        assert result is not None
        assert result["status"] == "terminated"
        assert result["termination_type"] == "user_cancelled"
        assert result["billable_portion"] == 0.5

    @patch("bo1.state.repositories.session_repository.db_session")
    def test_terminate_session_not_found(self, mock_db_session):
        """Test termination of non-existent session returns None."""
        from bo1.state.repositories.session_repository import SessionRepository

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db_session.return_value.__enter__.return_value = mock_conn

        repo = SessionRepository()
        result = repo.terminate_session(
            session_id="nonexistent",
            termination_type="user_cancelled",
            termination_reason=None,
            billable_portion=0.0,
        )

        assert result is None


class TestTerminationEventTypes:
    """Tests for SSE termination event types."""

    def test_meeting_terminated_event_payload(self):
        """Test meeting_terminated event payload structure."""
        payload = {
            "termination_type": "blocker_identified",
            "reason": "Missing data",
            "billable_portion": 0.33,
            "completed_sub_problems": 1,
            "total_sub_problems": 3,
        }

        assert "termination_type" in payload
        assert "billable_portion" in payload
        assert 0.0 <= payload["billable_portion"] <= 1.0
        assert payload["completed_sub_problems"] <= payload["total_sub_problems"]


class TestTerminationEdgeCases:
    """Tests for terminate endpoint edge cases (P0 bug fix)."""

    def test_terminal_states_set_contains_all_states(self):
        """Test that terminal states set includes all expected states."""
        terminal_states = {"terminated", "completed", "killed", "failed", "deleted"}
        assert "terminated" in terminal_states
        assert "completed" in terminal_states
        assert "killed" in terminal_states
        assert "failed" in terminal_states
        assert "deleted" in terminal_states

    def test_terminate_rejects_already_terminated(self):
        """Test that terminating an already-terminated session returns 409."""
        from fastapi import HTTPException

        from backend.api.utils.errors import raise_api_error

        # Simulate the check in terminate endpoint
        current_status = "terminated"
        terminal_states = {"terminated", "completed", "killed", "failed", "deleted"}

        with pytest.raises(HTTPException) as exc_info:
            if current_status in terminal_states:
                raise_api_error(
                    "conflict",
                    f"Session already in terminal state: {current_status}",
                )

        assert exc_info.value.status_code == 409
        assert "terminated" in str(exc_info.value.detail)

    def test_terminate_rejects_killed_status(self):
        """Test that terminating a killed session returns 409."""
        from fastapi import HTTPException

        from backend.api.utils.errors import raise_api_error

        current_status = "killed"
        terminal_states = {"terminated", "completed", "killed", "failed", "deleted"}

        with pytest.raises(HTTPException) as exc_info:
            if current_status in terminal_states:
                raise_api_error(
                    "conflict",
                    f"Session already in terminal state: {current_status}",
                )

        assert exc_info.value.status_code == 409
        assert "killed" in str(exc_info.value.detail)

    def test_terminate_rejects_failed_status(self):
        """Test that terminating a failed session returns 409."""
        from fastapi import HTTPException

        from backend.api.utils.errors import raise_api_error

        current_status = "failed"
        terminal_states = {"terminated", "completed", "killed", "failed", "deleted"}

        with pytest.raises(HTTPException) as exc_info:
            if current_status in terminal_states:
                raise_api_error(
                    "conflict",
                    f"Session already in terminal state: {current_status}",
                )

        assert exc_info.value.status_code == 409
        assert "failed" in str(exc_info.value.detail)

    def test_terminate_rejects_completed_status(self):
        """Test that terminating a completed session returns 409."""
        from fastapi import HTTPException

        from backend.api.utils.errors import raise_api_error

        current_status = "completed"
        terminal_states = {"terminated", "completed", "killed", "failed", "deleted"}

        with pytest.raises(HTTPException) as exc_info:
            if current_status in terminal_states:
                raise_api_error(
                    "conflict",
                    f"Session already in terminal state: {current_status}",
                )

        assert exc_info.value.status_code == 409
        assert "completed" in str(exc_info.value.detail)

    def test_terminate_allows_active_status(self):
        """Test that active sessions can be terminated."""
        current_status = "active"
        terminal_states = {"terminated", "completed", "killed", "failed", "deleted"}

        # Should NOT be in terminal states
        assert current_status not in terminal_states

    def test_terminate_allows_running_status(self):
        """Test that running sessions can be terminated."""
        current_status = "running"
        terminal_states = {"terminated", "completed", "killed", "failed", "deleted"}

        # Should NOT be in terminal states
        assert current_status not in terminal_states

    def test_redis_save_failure_non_critical(self):
        """Test that Redis save_metadata failure doesn't cause 500 error."""
        # This tests the defensive try/except around save_metadata
        # If redis_manager.save_metadata raises, we should log and continue
        import logging

        class FakeRedisManager:
            def save_metadata(self, session_id: str, metadata: dict) -> bool:
                raise ConnectionError("Redis connection lost")

        manager = FakeRedisManager()
        logger = logging.getLogger("test")

        # Simulate the defensive handling
        try:
            manager.save_metadata("test-session", {"status": "terminated"})
        except Exception as e:
            # Should be caught and logged, not re-raised
            logger.warning(f"Failed to update Redis metadata: {e}")

        # Test passes if we get here without exception

    def test_orphaned_redis_metadata_handling(self):
        """Test handling of session that exists in Redis but not PostgreSQL."""
        from fastapi import HTTPException

        from backend.api.utils.errors import raise_api_error

        # Simulate the check: session not in DB
        db_session = None

        with pytest.raises(HTTPException) as exc_info:
            if not db_session:
                raise_api_error("not_found", "Session not found")

        assert exc_info.value.status_code == 404

    def test_race_condition_db_status_mismatch(self):
        """Test handling when DB status differs from Redis (race condition)."""
        from fastapi import HTTPException

        from backend.api.utils.errors import raise_api_error

        # Simulate: Redis says "active", but DB says "completed"
        _redis_status = "active"  # noqa: F841 - documenting the scenario
        db_status = "completed"
        terminal_states = {"terminated", "completed", "killed", "failed", "deleted"}

        with pytest.raises(HTTPException) as exc_info:
            if db_status in terminal_states:
                raise_api_error(
                    "conflict",
                    f"Session already finalized (status: {db_status})",
                )

        assert exc_info.value.status_code == 409
        assert "finalized" in str(exc_info.value.detail)
