"""Tests for action close and clone-replan functionality.

Tests the failed/abandoned closure states and action replanning via clone.
"""

import pytest
from pydantic import ValidationError

from backend.api.models import (
    ActionCloneReplanRequest,
    ActionCloneReplanResponse,
    ActionCloseRequest,
    ActionCloseResponse,
    ActionStatusUpdate,
)
from bo1.state.repositories.action_repository import ActionRepository


class TestActionCloseModels:
    """Test close-related Pydantic models."""

    def test_action_close_request_failed(self):
        """Test ActionCloseRequest accepts failed status."""
        request = ActionCloseRequest(
            status="failed",
            reason="External API was deprecated, blocking completion.",
        )
        assert request.status == "failed"
        assert "API" in request.reason

    def test_action_close_request_abandoned(self):
        """Test ActionCloseRequest accepts abandoned status."""
        request = ActionCloseRequest(
            status="abandoned",
            reason="Business priorities shifted, no longer needed.",
        )
        assert request.status == "abandoned"
        assert "priorities" in request.reason

    def test_action_close_request_invalid_status(self):
        """Test ActionCloseRequest rejects invalid statuses."""
        with pytest.raises(ValidationError):
            ActionCloseRequest(status="done", reason="Invalid")

        with pytest.raises(ValidationError):
            ActionCloseRequest(status="cancelled", reason="Invalid")

        with pytest.raises(ValidationError):
            ActionCloseRequest(status="todo", reason="Invalid")

    def test_action_close_request_requires_reason(self):
        """Test ActionCloseRequest requires a reason."""
        with pytest.raises(ValidationError):
            ActionCloseRequest(status="failed", reason="")

    def test_action_close_response(self):
        """Test ActionCloseResponse structure."""
        response = ActionCloseResponse(
            action_id="action-123",
            status="failed",
            message="Action closed as failed",
        )
        assert response.action_id == "action-123"
        assert response.status == "failed"


class TestActionCloneReplanModels:
    """Test clone-replan related Pydantic models."""

    def test_action_clone_replan_request_empty(self):
        """Test ActionCloneReplanRequest with no modifications."""
        request = ActionCloneReplanRequest()
        assert request.new_steps is None
        assert request.new_target_date is None

    def test_action_clone_replan_request_with_steps(self):
        """Test ActionCloneReplanRequest with new steps."""
        request = ActionCloneReplanRequest(
            new_steps=["Step 1: Research alternatives", "Step 2: Implement new approach"],
        )
        assert len(request.new_steps) == 2
        assert "alternatives" in request.new_steps[0]

    def test_action_clone_replan_request_with_date(self):
        """Test ActionCloneReplanRequest with new target date."""
        request = ActionCloneReplanRequest(new_target_date="2025-01-15")
        assert request.new_target_date == "2025-01-15"

    def test_action_clone_replan_request_invalid_date(self):
        """Test ActionCloneReplanRequest rejects invalid date format."""
        with pytest.raises(ValidationError):
            ActionCloneReplanRequest(new_target_date="15/01/2025")

        with pytest.raises(ValidationError):
            ActionCloneReplanRequest(new_target_date="2025-1-15")

    def test_action_clone_replan_response(self):
        """Test ActionCloneReplanResponse structure."""
        response = ActionCloneReplanResponse(
            new_action_id="new-action-456",
            original_action_id="original-action-123",
            message="Action replanned successfully",
        )
        assert response.new_action_id == "new-action-456"
        assert response.original_action_id == "original-action-123"


class TestStatusTransitionsForClosedStates:
    """Test VALID_TRANSITIONS for new closed states."""

    def test_in_progress_to_failed_allowed(self):
        """Test in_progress -> failed is allowed."""
        repo = ActionRepository()
        is_valid, error = repo.validate_status_transition("in_progress", "failed")
        assert is_valid, f"in_progress -> failed should be allowed, got: {error}"

    def test_in_progress_to_abandoned_allowed(self):
        """Test in_progress -> abandoned is allowed."""
        repo = ActionRepository()
        is_valid, error = repo.validate_status_transition("in_progress", "abandoned")
        assert is_valid, f"in_progress -> abandoned should be allowed, got: {error}"

    def test_blocked_to_failed_allowed(self):
        """Test blocked -> failed is allowed."""
        repo = ActionRepository()
        is_valid, error = repo.validate_status_transition("blocked", "failed")
        assert is_valid, f"blocked -> failed should be allowed, got: {error}"

    def test_blocked_to_abandoned_allowed(self):
        """Test blocked -> abandoned is allowed."""
        repo = ActionRepository()
        is_valid, error = repo.validate_status_transition("blocked", "abandoned")
        assert is_valid, f"blocked -> abandoned should be allowed, got: {error}"

    def test_todo_to_abandoned_allowed(self):
        """Test todo -> abandoned is allowed (never started, no longer needed)."""
        repo = ActionRepository()
        is_valid, error = repo.validate_status_transition("todo", "abandoned")
        assert is_valid, f"todo -> abandoned should be allowed, got: {error}"

    def test_todo_to_failed_not_allowed(self):
        """Test todo -> failed is NOT allowed (can't fail if never started)."""
        repo = ActionRepository()
        is_valid, error = repo.validate_status_transition("todo", "failed")
        assert not is_valid, "todo -> failed should NOT be allowed"

    def test_failed_to_replanned_allowed(self):
        """Test failed -> replanned is allowed (via replan operation)."""
        repo = ActionRepository()
        is_valid, error = repo.validate_status_transition("failed", "replanned")
        assert is_valid, f"failed -> replanned should be allowed, got: {error}"

    def test_abandoned_to_replanned_allowed(self):
        """Test abandoned -> replanned is allowed (via replan operation)."""
        repo = ActionRepository()
        is_valid, error = repo.validate_status_transition("abandoned", "replanned")
        assert is_valid, f"abandoned -> replanned should be allowed, got: {error}"

    def test_failed_is_terminal_except_replan(self):
        """Test failed only allows transition to replanned."""
        repo = ActionRepository()
        blocked_transitions = ["todo", "in_progress", "blocked", "done", "cancelled"]

        for target in blocked_transitions:
            is_valid, error = repo.validate_status_transition("failed", target)
            assert not is_valid, f"failed -> {target} should NOT be allowed"

    def test_abandoned_is_terminal_except_replan(self):
        """Test abandoned only allows transition to replanned."""
        repo = ActionRepository()
        blocked_transitions = ["todo", "in_progress", "blocked", "done", "cancelled"]

        for target in blocked_transitions:
            is_valid, error = repo.validate_status_transition("abandoned", target)
            assert not is_valid, f"abandoned -> {target} should NOT be allowed"

    def test_replanned_is_fully_terminal(self):
        """Test replanned allows no transitions (fully terminal)."""
        repo = ActionRepository()
        all_statuses = [
            "todo",
            "in_progress",
            "blocked",
            "in_review",
            "done",
            "cancelled",
            "failed",
            "abandoned",
        ]

        for target in all_statuses:
            is_valid, _ = repo.validate_status_transition("replanned", target)
            assert not is_valid, f"replanned -> {target} should NOT be allowed"


class TestActionStatusUpdateWithNewStatuses:
    """Test ActionStatusUpdate model accepts new statuses."""

    def test_action_status_update_failed(self):
        """Test ActionStatusUpdate accepts failed status."""
        update = ActionStatusUpdate(status="failed")
        assert update.status == "failed"

    def test_action_status_update_abandoned(self):
        """Test ActionStatusUpdate accepts abandoned status."""
        update = ActionStatusUpdate(status="abandoned")
        assert update.status == "abandoned"

    def test_action_status_update_replanned(self):
        """Test ActionStatusUpdate accepts replanned status."""
        update = ActionStatusUpdate(status="replanned")
        assert update.status == "replanned"

    def test_all_valid_statuses(self):
        """Test all valid status values are accepted."""
        valid_statuses = [
            "todo",
            "in_progress",
            "blocked",
            "in_review",
            "done",
            "cancelled",
            "failed",
            "abandoned",
            "replanned",
        ]

        for status in valid_statuses:
            update = ActionStatusUpdate(status=status)
            assert update.status == status


class TestReplanBusinessLogic:
    """Test replan operation business logic."""

    def test_failed_provides_replan_context(self):
        """Test that failed actions have reason context for replanning."""
        # This tests the conceptual model - failed actions should explain
        # what went wrong so replanning can address the issue
        request = ActionCloseRequest(
            status="failed",
            reason="Integration with legacy system proved impossible due to data format incompatibility",
        )
        # The reason provides context for what to do differently
        assert "integration" in request.reason.lower()
        assert "format" in request.reason.lower()

    def test_abandoned_differs_from_failed(self):
        """Test that abandoned and failed represent different closure types."""
        # Failed = tried but couldn't complete
        failed = ActionCloseRequest(
            status="failed",
            reason="Technical blockers prevented completion",
        )

        # Abandoned = decided not to pursue
        abandoned = ActionCloseRequest(
            status="abandoned",
            reason="Business priorities changed, no longer needed",
        )

        assert failed.status == "failed"
        assert abandoned.status == "abandoned"

        # Different semantic meanings in reasons
        assert "blockers" in failed.reason.lower()
        assert "priorities" in abandoned.reason.lower()
