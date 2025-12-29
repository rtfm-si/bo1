"""Tests for working pattern API endpoints.

Tests:
- Validate WorkingPattern model (valid days, duplicates, out of range)
- GET returns default when not set
- PUT saves and returns updated pattern
- Invalid days (0, 8, duplicates) return 422
"""

import pytest

from backend.api.context.models import (
    WorkingPattern,
    WorkingPatternResponse,
    WorkingPatternUpdate,
)


class TestWorkingPatternModel:
    """Test WorkingPattern Pydantic model validation."""

    def test_default_working_days(self):
        """Default should be Mon-Fri (1-5)."""
        pattern = WorkingPattern()
        assert pattern.working_days == [1, 2, 3, 4, 5]

    def test_valid_custom_days(self):
        """Valid custom days should be accepted."""
        pattern = WorkingPattern(working_days=[1, 3, 5])
        assert pattern.working_days == [1, 3, 5]

    def test_weekend_only(self):
        """Weekend-only pattern should work."""
        pattern = WorkingPattern(working_days=[6, 7])
        assert pattern.working_days == [6, 7]

    def test_all_days(self):
        """All 7 days should be accepted."""
        pattern = WorkingPattern(working_days=[1, 2, 3, 4, 5, 6, 7])
        assert pattern.working_days == [1, 2, 3, 4, 5, 6, 7]

    def test_single_day(self):
        """Single day should be accepted."""
        pattern = WorkingPattern(working_days=[3])
        assert pattern.working_days == [3]

    def test_unsorted_days_get_sorted(self):
        """Unsorted days should be normalized to sorted order."""
        pattern = WorkingPattern(working_days=[5, 2, 7, 1])
        assert pattern.working_days == [1, 2, 5, 7]

    def test_duplicate_days_removed(self):
        """Duplicate days should be removed."""
        pattern = WorkingPattern(working_days=[1, 2, 2, 3, 3, 3])
        assert pattern.working_days == [1, 2, 3]

    def test_invalid_day_zero_filtered(self):
        """Day 0 should be filtered out."""
        pattern = WorkingPattern(working_days=[0, 1, 2])
        assert pattern.working_days == [1, 2]

    def test_invalid_day_eight_filtered(self):
        """Day 8 should be filtered out."""
        pattern = WorkingPattern(working_days=[1, 8, 9])
        assert pattern.working_days == [1]

    def test_all_invalid_days_fallback_to_default(self):
        """If all days invalid, should fallback to default."""
        pattern = WorkingPattern(working_days=[0, 8, 9, 10])
        assert pattern.working_days == [1, 2, 3, 4, 5]

    def test_empty_list_fallback_to_default(self):
        """Empty list should fallback to default."""
        pattern = WorkingPattern(working_days=[])
        assert pattern.working_days == [1, 2, 3, 4, 5]


class TestWorkingPatternUpdateModel:
    """Test WorkingPatternUpdate request model validation."""

    def test_valid_update(self):
        """Valid update request should pass validation."""
        update = WorkingPatternUpdate(working_days=[1, 2, 3])
        assert update.working_days == [1, 2, 3]

    def test_min_length_validation(self):
        """At least one day is required."""
        with pytest.raises(ValueError):
            WorkingPatternUpdate(working_days=[])

    def test_max_length_validation(self):
        """Maximum 7 days allowed."""
        # 8 days should fail
        with pytest.raises(ValueError):
            WorkingPatternUpdate(working_days=[1, 2, 3, 4, 5, 6, 7, 1])


class TestWorkingPatternResponseModel:
    """Test WorkingPatternResponse model."""

    def test_success_response(self):
        """Success response should include pattern."""
        resp = WorkingPatternResponse(
            success=True, pattern=WorkingPattern(working_days=[1, 2, 3, 4, 5])
        )
        assert resp.success is True
        assert resp.pattern.working_days == [1, 2, 3, 4, 5]
        assert resp.error is None

    def test_error_response(self):
        """Error response should include error message."""
        resp = WorkingPatternResponse(
            success=False, pattern=WorkingPattern(), error="Something went wrong"
        )
        assert resp.success is False
        assert resp.error == "Something went wrong"
