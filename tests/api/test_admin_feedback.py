"""Unit tests for admin feedback API endpoints.

Tests:
- GET /api/admin/feedback (with sentiment/theme filters)
- GET /api/admin/feedback/analysis-summary
- GET /api/admin/feedback/by-theme/{theme}
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.admin.feedback import router
from backend.api.middleware.admin import require_admin_any


def mock_admin_override():
    """Override admin auth to always succeed."""
    return "admin-user-id"


@pytest.fixture
def client():
    """Create test client with admin auth override and disabled rate limiter."""
    from backend.api.middleware.rate_limit import limiter

    original_enabled = limiter.enabled
    limiter.enabled = False

    app = FastAPI()
    app.dependency_overrides[require_admin_any] = mock_admin_override
    app.include_router(router, prefix="/api/admin")

    yield TestClient(app)

    limiter.enabled = original_enabled


@pytest.fixture
def sample_feedback():
    """Sample feedback data with analysis."""
    return {
        "id": "feedback-123",
        "user_id": "user-456",
        "type": "feature_request",
        "title": "Add dark mode",
        "description": "Would be great to have a dark theme.",
        "context": None,
        "analysis": {
            "sentiment": "neutral",
            "sentiment_confidence": 0.8,
            "themes": ["design", "usability"],
            "analyzed_at": "2025-12-13T10:00:00Z",
        },
        "status": "new",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }


class TestListFeedback:
    """Tests for GET /api/admin/feedback."""

    def test_list_feedback_with_sentiment_filter(self, client, sample_feedback):
        """Should filter by sentiment."""
        with patch("backend.api.admin.feedback.feedback_repository") as mock_repo:
            mock_repo.list_feedback.return_value = [sample_feedback]
            mock_repo.count_feedback.return_value = 1

            response = client.get("/api/admin/feedback?sentiment=neutral")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        mock_repo.list_feedback.assert_called_once()
        call_args = mock_repo.list_feedback.call_args
        assert call_args.kwargs["sentiment"] == "neutral"

    def test_list_feedback_with_theme_filter(self, client, sample_feedback):
        """Should filter by theme."""
        with patch("backend.api.admin.feedback.feedback_repository") as mock_repo:
            mock_repo.list_feedback.return_value = [sample_feedback]
            mock_repo.count_feedback.return_value = 1

            response = client.get("/api/admin/feedback?theme=usability")

        assert response.status_code == 200
        mock_repo.list_feedback.assert_called_once()
        call_args = mock_repo.list_feedback.call_args
        assert call_args.kwargs["theme"] == "usability"

    def test_list_feedback_invalid_sentiment(self, client):
        """Should reject invalid sentiment filter."""
        with patch("backend.api.admin.feedback.feedback_repository"):
            response = client.get("/api/admin/feedback?sentiment=invalid")

        assert response.status_code == 400
        detail = response.json()["detail"]
        message = detail["message"] if isinstance(detail, dict) else detail
        assert "Invalid sentiment filter" in message

    def test_list_feedback_includes_analysis(self, client, sample_feedback):
        """Should include analysis in response."""
        with patch("backend.api.admin.feedback.feedback_repository") as mock_repo:
            mock_repo.list_feedback.return_value = [sample_feedback]
            mock_repo.count_feedback.return_value = 1

            response = client.get("/api/admin/feedback")

        assert response.status_code == 200
        data = response.json()
        item = data["items"][0]
        assert item["analysis"] is not None
        assert item["analysis"]["sentiment"] == "neutral"
        assert "design" in item["analysis"]["themes"]


class TestAnalysisSummary:
    """Tests for GET /api/admin/feedback/analysis-summary."""

    def test_get_analysis_summary(self, client):
        """Should return aggregated analysis stats."""
        with patch("backend.api.admin.feedback.feedback_repository") as mock_repo:
            mock_repo.get_analysis_summary.return_value = {
                "analyzed_count": 100,
                "sentiment_counts": {
                    "positive": 40,
                    "negative": 20,
                    "neutral": 30,
                    "mixed": 10,
                },
                "top_themes": [
                    {"theme": "usability", "count": 25},
                    {"theme": "features", "count": 20},
                    {"theme": "performance", "count": 15},
                ],
            }

            response = client.get("/api/admin/feedback/analysis-summary")

        assert response.status_code == 200
        data = response.json()
        assert data["analyzed_count"] == 100
        assert data["sentiment_counts"]["positive"] == 40
        assert len(data["top_themes"]) == 3
        assert data["top_themes"][0]["theme"] == "usability"

    def test_get_analysis_summary_empty(self, client):
        """Should handle no analyzed feedback."""
        with patch("backend.api.admin.feedback.feedback_repository") as mock_repo:
            mock_repo.get_analysis_summary.return_value = {
                "analyzed_count": 0,
                "sentiment_counts": {},
                "top_themes": [],
            }

            response = client.get("/api/admin/feedback/analysis-summary")

        assert response.status_code == 200
        data = response.json()
        assert data["analyzed_count"] == 0


class TestFeedbackByTheme:
    """Tests for GET /api/admin/feedback/by-theme/{theme}."""

    def test_get_feedback_by_theme(self, client, sample_feedback):
        """Should return feedback items with theme."""
        with patch("backend.api.admin.feedback.feedback_repository") as mock_repo:
            mock_repo.get_feedback_by_theme.return_value = [sample_feedback]

            response = client.get("/api/admin/feedback/by-theme/usability")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        mock_repo.get_feedback_by_theme.assert_called_once_with("usability", limit=50)

    def test_get_feedback_by_theme_with_limit(self, client, sample_feedback):
        """Should respect limit parameter."""
        with patch("backend.api.admin.feedback.feedback_repository") as mock_repo:
            mock_repo.get_feedback_by_theme.return_value = [sample_feedback]

            response = client.get("/api/admin/feedback/by-theme/usability?limit=10")

        assert response.status_code == 200
        mock_repo.get_feedback_by_theme.assert_called_once_with("usability", limit=10)

    def test_get_feedback_by_theme_empty(self, client):
        """Should handle no feedback with theme."""
        with patch("backend.api.admin.feedback.feedback_repository") as mock_repo:
            mock_repo.get_feedback_by_theme.return_value = []

            response = client.get("/api/admin/feedback/by-theme/nonexistent")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0


class TestFeedbackAnalysisInResponse:
    """Tests for analysis field in feedback responses."""

    def test_feedback_response_with_analysis(self, client, sample_feedback):
        """GET single feedback should include analysis."""
        with patch("backend.api.admin.feedback.feedback_repository") as mock_repo:
            mock_repo.get_feedback_by_id.return_value = sample_feedback

            response = client.get("/api/admin/feedback/feedback-123")

        assert response.status_code == 200
        data = response.json()
        assert data["analysis"]["sentiment"] == "neutral"
        assert data["analysis"]["sentiment_confidence"] == 0.8
        assert "design" in data["analysis"]["themes"]

    def test_feedback_response_without_analysis(self, client, sample_feedback):
        """Should handle feedback without analysis."""
        feedback_no_analysis = {**sample_feedback, "analysis": None}
        with patch("backend.api.admin.feedback.feedback_repository") as mock_repo:
            mock_repo.get_feedback_by_id.return_value = feedback_no_analysis

            response = client.get("/api/admin/feedback/feedback-123")

        assert response.status_code == 200
        data = response.json()
        assert data["analysis"] is None
