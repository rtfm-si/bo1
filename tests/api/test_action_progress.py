"""Tests for action progress tracking functionality.

Tests:
- Update progress by percentage (0-100)
- Update progress by points (0-N)
- Variance calculation: early, on-time, late
- Progress model validation
- Variance model validation
"""

from datetime import datetime, timedelta

import pytest

from backend.api.models import (
    ActionProgressUpdate,
    ActionVariance,
)


# Model validation tests
class TestActionProgressUpdateModel:
    """Test ActionProgressUpdate Pydantic model validation."""

    def test_progress_update_percentage(self):
        """Test ActionProgressUpdate with percentage type."""
        update = ActionProgressUpdate(
            progress_type="percentage",
            progress_value=75,
        )

        assert update.progress_type == "percentage"
        assert update.progress_value == 75
        assert update.actual_start_date is None
        assert update.actual_finish_date is None

    def test_progress_update_points(self):
        """Test ActionProgressUpdate with points type."""
        update = ActionProgressUpdate(
            progress_type="points",
            progress_value=8,
            estimated_effort_points=13,
        )

        assert update.progress_type == "points"
        assert update.progress_value == 8
        assert update.estimated_effort_points == 13

    def test_progress_update_status_only(self):
        """Test ActionProgressUpdate with status_only type."""
        update = ActionProgressUpdate(
            progress_type="status_only",
            progress_value=None,
        )

        assert update.progress_type == "status_only"
        assert update.progress_value is None

    def test_progress_update_with_dates(self):
        """Test ActionProgressUpdate with actual dates."""
        start = datetime.now().isoformat()
        end = (datetime.now() + timedelta(days=5)).isoformat()

        update = ActionProgressUpdate(
            progress_type="percentage",
            progress_value=100,
            actual_start_date=start,
            actual_finish_date=end,
        )

        assert update.actual_start_date == start
        assert update.actual_finish_date == end

    def test_progress_update_percentage_zero(self):
        """Test progress percentage of 0."""
        update = ActionProgressUpdate(
            progress_type="percentage",
            progress_value=0,
        )

        assert update.progress_value == 0

    def test_progress_update_percentage_100(self):
        """Test progress percentage of 100."""
        update = ActionProgressUpdate(
            progress_type="percentage",
            progress_value=100,
        )

        assert update.progress_value == 100


class TestActionVarianceModel:
    """Test ActionVariance Pydantic model validation."""

    def test_variance_on_time(self):
        """Test ActionVariance with ON_TIME status."""
        variance = ActionVariance(
            action_id="action-1",
            planned_duration_days=10,
            actual_duration_days=10,
            variance_days=0,
            risk_level="ON_TIME",
            progress_percent=75,
        )

        assert variance.action_id == "action-1"
        assert variance.risk_level == "ON_TIME"
        assert variance.variance_days == 0

    def test_variance_early(self):
        """Test ActionVariance with EARLY status."""
        variance = ActionVariance(
            action_id="action-1",
            planned_duration_days=10,
            actual_duration_days=8,
            variance_days=-2,
            risk_level="EARLY",
        )

        assert variance.risk_level == "EARLY"
        assert variance.variance_days == -2

    def test_variance_late(self):
        """Test ActionVariance with LATE status."""
        variance = ActionVariance(
            action_id="action-1",
            planned_duration_days=10,
            actual_duration_days=15,
            variance_days=5,
            risk_level="LATE",
        )

        assert variance.risk_level == "LATE"
        assert variance.variance_days == 5

    def test_variance_no_dates(self):
        """Test ActionVariance with no date data."""
        variance = ActionVariance(
            action_id="action-1",
            planned_duration_days=None,
            actual_duration_days=None,
            variance_days=None,
            risk_level="ON_TIME",
        )

        assert variance.actual_duration_days is None
        assert variance.variance_days is None
        assert variance.risk_level == "ON_TIME"

    def test_variance_with_progress(self):
        """Test ActionVariance includes progress percentage."""
        variance = ActionVariance(
            action_id="action-1",
            risk_level="ON_TIME",
            progress_percent=50,
        )

        assert variance.progress_percent == 50

    def test_variance_no_progress(self):
        """Test ActionVariance without progress."""
        variance = ActionVariance(
            action_id="action-1",
            risk_level="ON_TIME",
        )

        assert variance.progress_percent is None


class TestProgressRequestValidation:
    """Test request validation for progress updates."""

    def test_invalid_progress_type(self):
        """Test that invalid progress_type is rejected."""
        with pytest.raises(ValueError):
            ActionProgressUpdate(
                progress_type="invalid_type",
                progress_value=50,
            )

    def test_valid_progress_types(self):
        """Test all valid progress_type values."""
        valid_types = ["percentage", "points", "status_only"]

        for progress_type in valid_types:
            update = ActionProgressUpdate(
                progress_type=progress_type,
                progress_value=None if progress_type == "status_only" else 50,
            )
            assert update.progress_type == progress_type

    def test_negative_progress_value_rejected(self):
        """Test that negative progress values are rejected."""
        with pytest.raises(ValueError):
            ActionProgressUpdate(
                progress_type="percentage",
                progress_value=-10,
            )

    def test_effort_points_must_be_positive(self):
        """Test that effort points must be >= 1."""
        with pytest.raises(ValueError):
            ActionProgressUpdate(
                progress_type="points",
                progress_value=5,
                estimated_effort_points=0,  # Invalid: must be >= 1
            )

    def test_valid_effort_points(self):
        """Test valid effort points values."""
        update = ActionProgressUpdate(
            progress_type="points",
            progress_value=5,
            estimated_effort_points=13,
        )

        assert update.estimated_effort_points == 13
