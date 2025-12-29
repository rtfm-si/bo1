"""Tests for heatmap history depth API models.

Tests:
- Validate HeatmapHistoryDepth model (valid depths, defaults)
- Validate HeatmapHistoryDepthUpdate (valid values only)
- Validate HeatmapHistoryDepthResponse structure
"""

import pytest

from backend.api.context.models import (
    HeatmapHistoryDepth,
    HeatmapHistoryDepthResponse,
    HeatmapHistoryDepthUpdate,
)


class TestHeatmapHistoryDepthModel:
    """Test HeatmapHistoryDepth Pydantic model validation."""

    def test_default_depth_is_three_months(self):
        """Default should be 3 months."""
        depth = HeatmapHistoryDepth()
        assert depth.history_months == 3

    def test_valid_depth_one_month(self):
        """1 month should be accepted."""
        depth = HeatmapHistoryDepth(history_months=1)
        assert depth.history_months == 1

    def test_valid_depth_three_months(self):
        """3 months should be accepted."""
        depth = HeatmapHistoryDepth(history_months=3)
        assert depth.history_months == 3

    def test_valid_depth_six_months(self):
        """6 months should be accepted."""
        depth = HeatmapHistoryDepth(history_months=6)
        assert depth.history_months == 6

    def test_invalid_depth_two_rejected(self):
        """2 months should be rejected (not in Literal[1, 3, 6])."""
        with pytest.raises(ValueError):
            HeatmapHistoryDepth(history_months=2)

    def test_invalid_depth_twelve_rejected(self):
        """12 months should be rejected."""
        with pytest.raises(ValueError):
            HeatmapHistoryDepth(history_months=12)

    def test_invalid_depth_zero_rejected(self):
        """0 months should be rejected."""
        with pytest.raises(ValueError):
            HeatmapHistoryDepth(history_months=0)


class TestHeatmapHistoryDepthUpdateModel:
    """Test HeatmapHistoryDepthUpdate request model validation."""

    def test_valid_update_one_month(self):
        """Valid update request with 1 month should pass."""
        update = HeatmapHistoryDepthUpdate(history_months=1)
        assert update.history_months == 1

    def test_valid_update_three_months(self):
        """Valid update request with 3 months should pass."""
        update = HeatmapHistoryDepthUpdate(history_months=3)
        assert update.history_months == 3

    def test_valid_update_six_months(self):
        """Valid update request with 6 months should pass."""
        update = HeatmapHistoryDepthUpdate(history_months=6)
        assert update.history_months == 6

    def test_invalid_update_two_months(self):
        """2 months should be rejected."""
        with pytest.raises(ValueError):
            HeatmapHistoryDepthUpdate(history_months=2)

    def test_invalid_update_negative(self):
        """Negative months should be rejected."""
        with pytest.raises(ValueError):
            HeatmapHistoryDepthUpdate(history_months=-1)


class TestHeatmapHistoryDepthResponseModel:
    """Test HeatmapHistoryDepthResponse model."""

    def test_success_response(self):
        """Success response should include depth."""
        resp = HeatmapHistoryDepthResponse(
            success=True, depth=HeatmapHistoryDepth(history_months=3)
        )
        assert resp.success is True
        assert resp.depth.history_months == 3
        assert resp.error is None

    def test_success_response_with_six_months(self):
        """Success response should correctly report 6 months."""
        resp = HeatmapHistoryDepthResponse(
            success=True, depth=HeatmapHistoryDepth(history_months=6)
        )
        assert resp.success is True
        assert resp.depth.history_months == 6

    def test_error_response(self):
        """Error response should include error message."""
        resp = HeatmapHistoryDepthResponse(
            success=False, depth=HeatmapHistoryDepth(), error="Something went wrong"
        )
        assert resp.success is False
        assert resp.error == "Something went wrong"

    def test_default_depth_in_response(self):
        """Response with default depth should be 3 months."""
        resp = HeatmapHistoryDepthResponse(success=True, depth=HeatmapHistoryDepth())
        assert resp.depth.history_months == 3
