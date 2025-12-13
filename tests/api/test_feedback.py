"""Unit tests for feedback Pydantic models.

Tests validation logic for:
- FeedbackType constants
- FeedbackStatus constants
- FeedbackCreate request model
- FeedbackResponse model
- FeedbackStatusUpdate model
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.api.models import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackStatus,
    FeedbackStatusUpdate,
    FeedbackType,
)


class TestFeedbackType:
    """Tests for FeedbackType constants."""

    def test_valid_types(self):
        """Verify all valid feedback types."""
        assert FeedbackType.FEATURE_REQUEST == "feature_request"
        assert FeedbackType.PROBLEM_REPORT == "problem_report"


class TestFeedbackStatus:
    """Tests for FeedbackStatus constants."""

    def test_valid_statuses(self):
        """Verify all valid feedback statuses."""
        assert FeedbackStatus.NEW == "new"
        assert FeedbackStatus.REVIEWING == "reviewing"
        assert FeedbackStatus.RESOLVED == "resolved"
        assert FeedbackStatus.CLOSED == "closed"


class TestFeedbackCreate:
    """Tests for FeedbackCreate request model."""

    @pytest.fixture
    def valid_feature_request(self):
        """Valid feature request data."""
        return {
            "type": "feature_request",
            "title": "Add dark mode support",
            "description": "It would be great to have a dark mode option.",
            "include_context": False,
        }

    @pytest.fixture
    def valid_problem_report(self):
        """Valid problem report data."""
        return {
            "type": "problem_report",
            "title": "Page not loading",
            "description": "When I click on a meeting, the page shows a spinner but never loads.",
            "include_context": True,
        }

    def test_valid_feature_request(self, valid_feature_request):
        """Valid feature request should pass validation."""
        feedback = FeedbackCreate(**valid_feature_request)
        assert feedback.type == "feature_request"
        assert feedback.title == "Add dark mode support"
        assert feedback.include_context is False

    def test_valid_problem_report(self, valid_problem_report):
        """Valid problem report should pass validation."""
        feedback = FeedbackCreate(**valid_problem_report)
        assert feedback.type == "problem_report"
        assert feedback.include_context is True

    def test_invalid_type_rejected(self, valid_feature_request):
        """Invalid feedback type should be rejected."""
        data = {**valid_feature_request, "type": "invalid_type"}
        with pytest.raises(ValidationError) as exc_info:
            FeedbackCreate(**data)
        assert "Invalid feedback type" in str(exc_info.value)

    def test_title_min_length(self, valid_feature_request):
        """Title must be at least 5 characters."""
        data = {**valid_feature_request, "title": "Hi"}
        with pytest.raises(ValidationError) as exc_info:
            FeedbackCreate(**data)
        assert "String should have at least 5 characters" in str(exc_info.value)

    def test_title_max_length(self, valid_feature_request):
        """Title must be at most 200 characters."""
        data = {**valid_feature_request, "title": "A" * 201}
        with pytest.raises(ValidationError) as exc_info:
            FeedbackCreate(**data)
        assert "String should have at most 200 characters" in str(exc_info.value)

    def test_description_min_length(self, valid_feature_request):
        """Description must be at least 10 characters."""
        data = {**valid_feature_request, "description": "Short"}
        with pytest.raises(ValidationError) as exc_info:
            FeedbackCreate(**data)
        assert "String should have at least 10 characters" in str(exc_info.value)

    def test_description_max_length(self, valid_feature_request):
        """Description must be at most 5000 characters."""
        data = {**valid_feature_request, "description": "A" * 5001}
        with pytest.raises(ValidationError) as exc_info:
            FeedbackCreate(**data)
        assert "String should have at most 5000 characters" in str(exc_info.value)

    def test_include_context_default(self, valid_feature_request):
        """include_context should default to True."""
        del valid_feature_request["include_context"]
        feedback = FeedbackCreate(**valid_feature_request)
        assert feedback.include_context is True


class TestFeedbackResponse:
    """Tests for FeedbackResponse model."""

    @pytest.fixture
    def valid_response_data(self):
        """Valid feedback response data."""
        return {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": "660e8400-e29b-41d4-a716-446655440001",
            "type": "feature_request",
            "title": "Add dark mode support",
            "description": "It would be great to have a dark mode option.",
            "context": None,
            "status": "new",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

    def test_valid_response(self, valid_response_data):
        """Valid response data should pass validation."""
        response = FeedbackResponse(**valid_response_data)
        assert response.id == "550e8400-e29b-41d4-a716-446655440000"
        assert response.type == "feature_request"
        assert response.status == "new"

    def test_response_with_context(self, valid_response_data):
        """Response with context should include context data."""
        data = {
            **valid_response_data,
            "context": {
                "user_tier": "free",
                "page_url": "https://app.boardofone.ai/meeting/123",
                "user_agent": "Mozilla/5.0",
                "timestamp": "2025-12-13T10:00:00Z",
            },
        }
        response = FeedbackResponse(**data)
        assert response.context is not None
        assert response.context["user_tier"] == "free"


class TestFeedbackStatusUpdate:
    """Tests for FeedbackStatusUpdate request model."""

    def test_valid_statuses(self):
        """All valid statuses should pass validation."""
        for status in ["new", "reviewing", "resolved", "closed"]:
            update = FeedbackStatusUpdate(status=status)
            assert update.status == status

    def test_invalid_status_rejected(self):
        """Invalid status should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FeedbackStatusUpdate(status="invalid_status")
        assert "Invalid status" in str(exc_info.value)
