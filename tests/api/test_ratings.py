"""Unit tests for ratings Pydantic models.

Tests validation logic for:
- RatingEntityType constants
- RatingCreate request model
- RatingResponse model
- RatingMetrics model
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.api.models import (
    NegativeRatingItem,
    RatingCreate,
    RatingEntityType,
    RatingMetrics,
    RatingResponse,
    RatingTrendItem,
)


class TestRatingEntityType:
    """Tests for RatingEntityType constants."""

    def test_valid_types(self):
        """Verify all valid entity types."""
        assert RatingEntityType.MEETING == "meeting"
        assert RatingEntityType.ACTION == "action"


class TestRatingCreate:
    """Tests for RatingCreate request model."""

    @pytest.fixture
    def valid_meeting_rating(self):
        """Valid meeting rating data."""
        return {
            "entity_type": "meeting",
            "entity_id": "550e8400-e29b-41d4-a716-446655440000",
            "rating": 1,
        }

    @pytest.fixture
    def valid_action_rating(self):
        """Valid action rating data."""
        return {
            "entity_type": "action",
            "entity_id": "550e8400-e29b-41d4-a716-446655440001",
            "rating": -1,
            "comment": "Action was not helpful",
        }

    def test_valid_meeting_rating(self, valid_meeting_rating):
        """Valid meeting rating should pass validation."""
        rating = RatingCreate(**valid_meeting_rating)
        assert rating.entity_type == "meeting"
        assert rating.rating == 1
        assert rating.comment is None

    def test_valid_action_rating_with_comment(self, valid_action_rating):
        """Valid action rating with comment should pass validation."""
        rating = RatingCreate(**valid_action_rating)
        assert rating.entity_type == "action"
        assert rating.rating == -1
        assert rating.comment == "Action was not helpful"

    def test_invalid_entity_type_rejected(self, valid_meeting_rating):
        """Invalid entity type should be rejected."""
        data = {**valid_meeting_rating, "entity_type": "project"}
        with pytest.raises(ValidationError) as exc_info:
            RatingCreate(**data)
        assert "Invalid entity_type" in str(exc_info.value)

    def test_invalid_rating_zero_rejected(self, valid_meeting_rating):
        """Rating of 0 should be rejected."""
        data = {**valid_meeting_rating, "rating": 0}
        with pytest.raises(ValidationError) as exc_info:
            RatingCreate(**data)
        assert "Rating must be -1" in str(exc_info.value) or "greater than or equal" in str(
            exc_info.value
        )

    def test_invalid_rating_two_rejected(self, valid_meeting_rating):
        """Rating of 2 should be rejected."""
        data = {**valid_meeting_rating, "rating": 2}
        with pytest.raises(ValidationError) as exc_info:
            RatingCreate(**data)
        assert "less than or equal" in str(exc_info.value)

    def test_thumbs_up_valid(self, valid_meeting_rating):
        """Rating of +1 (thumbs up) should be valid."""
        data = {**valid_meeting_rating, "rating": 1}
        rating = RatingCreate(**data)
        assert rating.rating == 1

    def test_thumbs_down_valid(self, valid_meeting_rating):
        """Rating of -1 (thumbs down) should be valid."""
        data = {**valid_meeting_rating, "rating": -1}
        rating = RatingCreate(**data)
        assert rating.rating == -1

    def test_comment_max_length(self, valid_meeting_rating):
        """Comment must be at most 1000 characters."""
        data = {**valid_meeting_rating, "comment": "A" * 1001}
        with pytest.raises(ValidationError) as exc_info:
            RatingCreate(**data)
        assert "String should have at most 1000 characters" in str(exc_info.value)

    def test_entity_id_required(self):
        """Entity ID is required."""
        with pytest.raises(ValidationError):
            RatingCreate(entity_type="meeting", rating=1)


class TestRatingResponse:
    """Tests for RatingResponse model."""

    def test_response_model_fields(self):
        """Verify response model has all required fields."""
        now = datetime.now(UTC)
        response = RatingResponse(
            id="rating-123",
            user_id="user-456",
            entity_type="meeting",
            entity_id="meeting-789",
            rating=1,
            comment="Great meeting!",
            created_at=now,
        )
        assert response.id == "rating-123"
        assert response.user_id == "user-456"
        assert response.entity_type == "meeting"
        assert response.rating == 1
        assert response.comment == "Great meeting!"
        assert response.created_at == now

    def test_response_model_optional_comment(self):
        """Comment should be optional (None allowed)."""
        response = RatingResponse(
            id="rating-123",
            user_id="user-456",
            entity_type="action",
            entity_id="action-789",
            rating=-1,
            comment=None,
            created_at=datetime.now(UTC),
        )
        assert response.comment is None


class TestRatingMetrics:
    """Tests for RatingMetrics model."""

    def test_metrics_model_fields(self):
        """Verify metrics model has all required fields."""
        metrics = RatingMetrics(
            period_days=30,
            total=100,
            thumbs_up=75,
            thumbs_down=25,
            thumbs_up_pct=75.0,
            by_type={
                "meeting": {"up": 50, "down": 10},
                "action": {"up": 25, "down": 15},
            },
        )
        assert metrics.period_days == 30
        assert metrics.total == 100
        assert metrics.thumbs_up == 75
        assert metrics.thumbs_down == 25
        assert metrics.thumbs_up_pct == 75.0
        assert metrics.by_type["meeting"]["up"] == 50


class TestRatingTrendItem:
    """Tests for RatingTrendItem model."""

    def test_trend_item_fields(self):
        """Verify trend item has all required fields."""
        item = RatingTrendItem(
            date="2025-12-26",
            up=10,
            down=2,
            total=12,
        )
        assert item.date == "2025-12-26"
        assert item.up == 10
        assert item.down == 2
        assert item.total == 12


class TestNegativeRatingItem:
    """Tests for NegativeRatingItem model."""

    def test_negative_rating_item_fields(self):
        """Verify negative rating item has all required fields."""
        item = NegativeRatingItem(
            id="rating-123",
            user_id="user-456",
            user_email="user@example.com",
            entity_type="meeting",
            entity_id="meeting-789",
            entity_title="Budget Planning",
            comment="Not helpful",
            created_at=datetime.now(UTC),
        )
        assert item.id == "rating-123"
        assert item.user_email == "user@example.com"
        assert item.entity_title == "Budget Planning"

    def test_negative_rating_item_optional_fields(self):
        """Verify optional fields can be None."""
        item = NegativeRatingItem(
            id="rating-123",
            user_id="user-456",
            entity_type="action",
            entity_id="action-789",
            created_at=datetime.now(UTC),
        )
        assert item.user_email is None
        assert item.entity_title is None
        assert item.comment is None
