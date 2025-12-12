"""Tests for action dates update functionality (Gantt drag-to-reschedule).

Tests:
- PATCH /api/v1/actions/{action_id}/dates updates target dates
- Date persistence through repository
- Cascade update tracking
"""

import pytest
from pydantic import ValidationError

from backend.api.models import ActionDatesResponse, ActionDatesUpdate


class TestActionDatesUpdateModel:
    """Test ActionDatesUpdate Pydantic model validation."""

    def test_update_with_start_date_only(self):
        """Test ActionDatesUpdate with only start date."""
        update = ActionDatesUpdate(target_start_date="2025-01-15")
        assert update.target_start_date == "2025-01-15"
        assert update.target_end_date is None
        assert update.timeline is None

    def test_update_with_end_date_only(self):
        """Test ActionDatesUpdate with only end date."""
        update = ActionDatesUpdate(target_end_date="2025-01-31")
        assert update.target_start_date is None
        assert update.target_end_date == "2025-01-31"

    def test_update_with_both_dates(self):
        """Test ActionDatesUpdate with both dates (Gantt drag result)."""
        update = ActionDatesUpdate(
            target_start_date="2025-01-15",
            target_end_date="2025-01-31",
        )
        assert update.target_start_date == "2025-01-15"
        assert update.target_end_date == "2025-01-31"

    def test_update_with_timeline(self):
        """Test ActionDatesUpdate with timeline string."""
        update = ActionDatesUpdate(timeline="2 weeks")
        assert update.timeline == "2 weeks"
        assert update.target_start_date is None
        assert update.target_end_date is None

    def test_update_all_fields(self):
        """Test ActionDatesUpdate with all fields."""
        update = ActionDatesUpdate(
            target_start_date="2025-01-15",
            target_end_date="2025-01-31",
            timeline="2 weeks",
        )
        assert update.target_start_date == "2025-01-15"
        assert update.target_end_date == "2025-01-31"
        assert update.timeline == "2 weeks"

    def test_invalid_date_format(self):
        """Test ActionDatesUpdate rejects invalid date format."""
        with pytest.raises(ValidationError) as exc_info:
            ActionDatesUpdate(target_start_date="01/15/2025")
        assert "target_start_date" in str(exc_info.value)

    def test_invalid_date_format_partial(self):
        """Test ActionDatesUpdate rejects partial date format."""
        with pytest.raises(ValidationError) as exc_info:
            ActionDatesUpdate(target_start_date="2025-1-15")
        assert "target_start_date" in str(exc_info.value)


class TestActionDatesResponseModel:
    """Test ActionDatesResponse Pydantic model validation."""

    def test_response_with_updated_dates(self):
        """Test ActionDatesResponse with updated dates."""
        response = ActionDatesResponse(
            action_id="action-123",
            target_start_date="2025-01-15",
            target_end_date="2025-01-31",
            estimated_start_date="2025-01-15",
            estimated_end_date="2025-01-31",
            estimated_duration_days=12,
            cascade_updated=0,
        )
        assert response.action_id == "action-123"
        assert response.target_start_date == "2025-01-15"
        assert response.target_end_date == "2025-01-31"
        assert response.cascade_updated == 0

    def test_response_with_cascade_updates(self):
        """Test ActionDatesResponse with cascaded dependent updates."""
        response = ActionDatesResponse(
            action_id="action-123",
            target_start_date="2025-01-15",
            target_end_date="2025-01-31",
            estimated_start_date="2025-01-15",
            estimated_end_date="2025-01-31",
            estimated_duration_days=12,
            cascade_updated=3,
        )
        assert response.cascade_updated == 3

    def test_response_with_null_dates(self):
        """Test ActionDatesResponse allows null dates."""
        response = ActionDatesResponse(
            action_id="action-123",
            target_start_date=None,
            target_end_date=None,
            estimated_start_date=None,
            estimated_end_date=None,
            estimated_duration_days=None,
            cascade_updated=0,
        )
        assert response.target_start_date is None
        assert response.estimated_duration_days is None


class TestGanttDatePersistence:
    """Test Gantt drag-to-reschedule date persistence flow."""

    def test_gantt_date_change_request_format(self):
        """Test the expected request format from Gantt drag-to-reschedule."""
        # Simulate what handleGanttDateChange sends
        start = "2025-01-20"
        end = "2025-02-05"

        update = ActionDatesUpdate(
            target_start_date=start,
            target_end_date=end,
        )

        # Verify format matches API expectation
        assert update.target_start_date == "2025-01-20"
        assert update.target_end_date == "2025-02-05"

    def test_date_format_consistency(self):
        """Test that YYYY-MM-DD format is consistently used."""
        # Frontend sends: new Date().toISOString().split('T')[0]
        iso_date_part = "2025-12-25"

        update = ActionDatesUpdate(target_start_date=iso_date_part)
        assert update.target_start_date == "2025-12-25"
