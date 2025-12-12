"""Tests for action cancellation functionality.

Tests the "What went wrong?" prompt and cancellation_reason field.
"""

import pytest
from pydantic import ValidationError

from backend.api.models import ActionDetailResponse, ActionStatusUpdate


class TestActionCancellationModels:
    """Test cancellation-related Pydantic models."""

    def test_action_status_update_with_cancellation_reason(self):
        """Test ActionStatusUpdate accepts cancellation_reason."""
        update = ActionStatusUpdate(
            status="cancelled",
            cancellation_reason="Budget constraints forced us to deprioritize this.",
        )
        assert update.status == "cancelled"
        assert update.cancellation_reason == "Budget constraints forced us to deprioritize this."

    def test_action_status_update_cancelled_without_reason(self):
        """Test ActionStatusUpdate allows cancelled without reason (validation at API level)."""
        # Model doesn't enforce this - API endpoint does
        update = ActionStatusUpdate(status="cancelled")
        assert update.status == "cancelled"
        assert update.cancellation_reason is None

    def test_action_status_update_blocked_with_blocking_reason(self):
        """Test blocking_reason is separate from cancellation_reason."""
        update = ActionStatusUpdate(
            status="blocked",
            blocking_reason="Waiting for external dependency",
        )
        assert update.status == "blocked"
        assert update.blocking_reason == "Waiting for external dependency"
        assert update.cancellation_reason is None

    def test_action_detail_response_with_cancellation_fields(self):
        """Test ActionDetailResponse includes cancellation fields."""
        response = ActionDetailResponse(
            id="test-123",
            title="Test Action",
            description="A test action",
            session_id="session-456",
            problem_statement="Test problem",
            status="cancelled",
            cancellation_reason="Project pivot made this irrelevant",
            cancelled_at="2025-12-12T10:00:00Z",
        )
        assert response.status == "cancelled"
        assert response.cancellation_reason == "Project pivot made this irrelevant"
        assert response.cancelled_at == "2025-12-12T10:00:00Z"

    def test_action_detail_response_cancellation_defaults(self):
        """Test cancellation fields default to None."""
        response = ActionDetailResponse(
            id="test-123",
            title="Test Action",
            description="A test action",
            session_id="session-456",
            problem_statement="Test problem",
        )
        assert response.cancellation_reason is None
        assert response.cancelled_at is None

    def test_action_status_update_invalid_status(self):
        """Test ActionStatusUpdate rejects invalid status."""
        with pytest.raises(ValidationError):
            ActionStatusUpdate(status="invalid_status")


class TestCancellationBusinessLogic:
    """Test cancellation business logic."""

    def test_cancelled_action_has_reason_context(self):
        """Test that cancelled actions provide context about what went wrong."""
        # This tests the conceptual model - cancelled actions should explain why
        response = ActionDetailResponse(
            id="action-789",
            title="Launch marketing campaign",
            description="Run Q4 marketing campaign",
            session_id="session-abc",
            problem_statement="How to increase brand awareness",
            status="cancelled",
            cancellation_reason="Market conditions changed - competitor launched similar product",
            cancelled_at="2025-12-12T15:30:00Z",
        )
        # Verify the reason provides actionable insight
        assert "competitor" in response.cancellation_reason.lower()
        assert response.cancelled_at is not None

    def test_cancelled_differs_from_blocked(self):
        """Test that cancelled and blocked are distinct states with different metadata."""
        blocked = ActionDetailResponse(
            id="blocked-1",
            title="Blocked action",
            description="Something blocking",
            session_id="s1",
            problem_statement="P1",
            status="blocked",
            blocking_reason="API rate limited",
            blocked_at="2025-12-12T10:00:00Z",
        )

        cancelled = ActionDetailResponse(
            id="cancelled-1",
            title="Cancelled action",
            description="Something cancelled",
            session_id="s2",
            problem_statement="P2",
            status="cancelled",
            cancellation_reason="No longer needed",
            cancelled_at="2025-12-12T11:00:00Z",
        )

        # Blocked = temporary, can be unblocked
        assert blocked.status == "blocked"
        assert blocked.blocking_reason is not None
        assert blocked.cancellation_reason is None

        # Cancelled = final, captures what went wrong
        assert cancelled.status == "cancelled"
        assert cancelled.cancellation_reason is not None
        assert cancelled.blocking_reason is None

    def test_status_transitions_to_cancelled(self):
        """Test valid status transitions to cancelled."""
        # All non-terminal statuses can transition to cancelled
        valid_from_statuses = ["todo", "in_progress", "blocked", "in_review"]

        for from_status in valid_from_statuses:
            update = ActionStatusUpdate(
                status="cancelled",
                cancellation_reason=f"Cancelled from {from_status} state",
            )
            assert update.status == "cancelled"

    def test_action_status_patterns(self):
        """Test the full set of valid action statuses."""
        valid_statuses = ["todo", "in_progress", "blocked", "in_review", "done", "cancelled"]

        for status in valid_statuses:
            update = ActionStatusUpdate(status=status)
            assert update.status == status
