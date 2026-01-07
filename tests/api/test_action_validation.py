"""Tests for action text field validation.

Tests max_length enforcement on:
- blocking_reason (2000 chars)
- cancellation_reason (2000 chars)
- what_and_how items (1000 chars each, max 20 items)
- success_criteria items (500 chars each, max 20 items)
- kill_criteria items (500 chars each, max 20 items)
"""

import pytest
from pydantic import ValidationError

from backend.api.models import (
    ActionCreate,
    ActionStatusUpdate,
    ActionUpdate,
    BlockActionRequest,
)


class TestActionStatusUpdateValidation:
    """Test ActionStatusUpdate max_length validation."""

    def test_blocking_reason_within_limit(self):
        """Test blocking_reason at 2000 chars succeeds."""
        update = ActionStatusUpdate(
            status="blocked",
            blocking_reason="a" * 2000,
        )
        assert len(update.blocking_reason) == 2000

    def test_blocking_reason_exceeds_limit(self):
        """Test blocking_reason over 2000 chars raises 422."""
        with pytest.raises(ValidationError) as exc_info:
            ActionStatusUpdate(
                status="blocked",
                blocking_reason="a" * 2001,
            )
        assert "blocking_reason" in str(exc_info.value)

    def test_cancellation_reason_within_limit(self):
        """Test cancellation_reason at 2000 chars succeeds."""
        update = ActionStatusUpdate(
            status="cancelled",
            cancellation_reason="b" * 2000,
        )
        assert len(update.cancellation_reason) == 2000

    def test_cancellation_reason_exceeds_limit(self):
        """Test cancellation_reason over 2000 chars raises 422."""
        with pytest.raises(ValidationError) as exc_info:
            ActionStatusUpdate(
                status="cancelled",
                cancellation_reason="b" * 2001,
            )
        assert "cancellation_reason" in str(exc_info.value)


class TestBlockActionRequestValidation:
    """Test BlockActionRequest max_length validation."""

    def test_blocking_reason_within_limit(self):
        """Test blocking_reason at 2000 chars succeeds."""
        request = BlockActionRequest(blocking_reason="x" * 2000)
        assert len(request.blocking_reason) == 2000

    def test_blocking_reason_exceeds_limit(self):
        """Test blocking_reason over 2000 chars raises 422."""
        with pytest.raises(ValidationError) as exc_info:
            BlockActionRequest(blocking_reason="x" * 2001)
        assert "blocking_reason" in str(exc_info.value)


class TestActionCreateValidation:
    """Test ActionCreate list field validation."""

    def test_what_and_how_within_item_limit(self):
        """Test what_and_how item at 1000 chars succeeds."""
        action = ActionCreate(
            title="Test Action",
            description="Test description",
            what_and_how=["a" * 1000],
        )
        assert len(action.what_and_how[0]) == 1000

    def test_what_and_how_exceeds_item_limit(self):
        """Test what_and_how item over 1000 chars raises 422."""
        with pytest.raises(ValidationError) as exc_info:
            ActionCreate(
                title="Test Action",
                description="Test description",
                what_and_how=["a" * 1001],
            )
        assert "what_and_how" in str(exc_info.value)
        assert "exceeds 1000 characters" in str(exc_info.value)

    def test_what_and_how_within_list_limit(self):
        """Test what_and_how with 20 items succeeds."""
        action = ActionCreate(
            title="Test Action",
            description="Test description",
            what_and_how=["step"] * 20,
        )
        assert len(action.what_and_how) == 20

    def test_what_and_how_exceeds_list_limit(self):
        """Test what_and_how with >20 items raises 422."""
        with pytest.raises(ValidationError) as exc_info:
            ActionCreate(
                title="Test Action",
                description="Test description",
                what_and_how=["step"] * 21,
            )
        assert "what_and_how" in str(exc_info.value)
        assert "exceed 20 items" in str(exc_info.value)

    def test_success_criteria_within_item_limit(self):
        """Test success_criteria item at 500 chars succeeds."""
        action = ActionCreate(
            title="Test Action",
            description="Test description",
            success_criteria=["b" * 500],
        )
        assert len(action.success_criteria[0]) == 500

    def test_success_criteria_exceeds_item_limit(self):
        """Test success_criteria item over 500 chars raises 422."""
        with pytest.raises(ValidationError) as exc_info:
            ActionCreate(
                title="Test Action",
                description="Test description",
                success_criteria=["b" * 501],
            )
        assert "success_criteria" in str(exc_info.value)
        assert "exceeds 500 characters" in str(exc_info.value)

    def test_success_criteria_exceeds_list_limit(self):
        """Test success_criteria with >20 items raises 422."""
        with pytest.raises(ValidationError) as exc_info:
            ActionCreate(
                title="Test Action",
                description="Test description",
                success_criteria=["criteria"] * 21,
            )
        assert "success_criteria" in str(exc_info.value)
        assert "exceed 20 items" in str(exc_info.value)

    def test_kill_criteria_within_item_limit(self):
        """Test kill_criteria item at 500 chars succeeds."""
        action = ActionCreate(
            title="Test Action",
            description="Test description",
            kill_criteria=["c" * 500],
        )
        assert len(action.kill_criteria[0]) == 500

    def test_kill_criteria_exceeds_item_limit(self):
        """Test kill_criteria item over 500 chars raises 422."""
        with pytest.raises(ValidationError) as exc_info:
            ActionCreate(
                title="Test Action",
                description="Test description",
                kill_criteria=["c" * 501],
            )
        assert "kill_criteria" in str(exc_info.value)
        assert "exceeds 500 characters" in str(exc_info.value)

    def test_kill_criteria_exceeds_list_limit(self):
        """Test kill_criteria with >20 items raises 422."""
        with pytest.raises(ValidationError) as exc_info:
            ActionCreate(
                title="Test Action",
                description="Test description",
                kill_criteria=["kill"] * 21,
            )
        assert "kill_criteria" in str(exc_info.value)
        assert "exceed 20 items" in str(exc_info.value)

    def test_valid_payload_with_all_lists(self):
        """Test valid payload with reasonable data passes validation."""
        action = ActionCreate(
            title="Test Action",
            description="Test description",
            what_and_how=["Step 1: Do this", "Step 2: Do that"],
            success_criteria=["Metric A > 100", "User approval"],
            kill_criteria=["Budget exceeded", "Deadline passed"],
        )
        assert len(action.what_and_how) == 2
        assert len(action.success_criteria) == 2
        assert len(action.kill_criteria) == 2


class TestActionUpdateValidation:
    """Test ActionUpdate list field validation (Optional fields)."""

    def test_what_and_how_null_allowed(self):
        """Test what_and_how can be None (not updating)."""
        update = ActionUpdate(title="New Title")
        assert update.what_and_how is None

    def test_what_and_how_within_item_limit(self):
        """Test what_and_how item at 1000 chars succeeds."""
        update = ActionUpdate(what_and_how=["a" * 1000])
        assert len(update.what_and_how[0]) == 1000

    def test_what_and_how_exceeds_item_limit(self):
        """Test what_and_how item over 1000 chars raises 422."""
        with pytest.raises(ValidationError) as exc_info:
            ActionUpdate(what_and_how=["a" * 1001])
        assert "what_and_how" in str(exc_info.value)

    def test_what_and_how_exceeds_list_limit(self):
        """Test what_and_how with >20 items raises 422."""
        with pytest.raises(ValidationError) as exc_info:
            ActionUpdate(what_and_how=["step"] * 21)
        assert "what_and_how" in str(exc_info.value)

    def test_success_criteria_exceeds_item_limit(self):
        """Test success_criteria item over 500 chars raises 422."""
        with pytest.raises(ValidationError) as exc_info:
            ActionUpdate(success_criteria=["b" * 501])
        assert "success_criteria" in str(exc_info.value)

    def test_kill_criteria_exceeds_item_limit(self):
        """Test kill_criteria item over 500 chars raises 422."""
        with pytest.raises(ValidationError) as exc_info:
            ActionUpdate(kill_criteria=["c" * 501])
        assert "kill_criteria" in str(exc_info.value)

    def test_valid_update_with_lists(self):
        """Test valid update payload passes validation."""
        update = ActionUpdate(
            title="Updated Title",
            what_and_how=["New step 1", "New step 2"],
            success_criteria=["New metric"],
        )
        assert update.title == "Updated Title"
        assert len(update.what_and_how) == 2
        assert len(update.success_criteria) == 1
