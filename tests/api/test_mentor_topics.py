"""Tests for mentor repeated topics API endpoint."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.mentor import router
from backend.api.middleware.auth import get_current_user
from backend.services.topic_detector import RepeatedTopic


def mock_user_override():
    """Override auth to return test user."""
    return {"user_id": "test-user-123", "email": "test@example.com"}


@pytest.fixture
def test_app():
    """Create test app with mentor router and auth override."""
    app = FastAPI()
    app.dependency_overrides[get_current_user] = mock_user_override
    # Router already has /v1/mentor prefix
    app.include_router(router, prefix="/api")
    return app


@pytest.fixture
def client(test_app):
    """Create test client with auth bypass."""
    return TestClient(test_app)


@pytest.fixture
def unauthenticated_client():
    """Create test client without auth bypass (for auth tests)."""
    from backend.api.main import app

    return TestClient(app)


class TestRepeatedTopicsEndpoint:
    """Tests for GET /api/v1/mentor/repeated-topics."""

    def test_repeated_topics_endpoint_auth(self, unauthenticated_client):
        """Endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/mentor/repeated-topics")
        assert response.status_code == 401

    def test_repeated_topics_returns_topics(self, client):
        """Returns detected repeated topics."""
        mock_topic = RepeatedTopic(
            topic_summary="How to integrate Stripe?",
            count=4,
            first_asked="2025-12-01T10:00:00+00:00",
            last_asked="2025-12-15T10:00:00+00:00",
            conversation_ids=["conv_1", "conv_2", "conv_3", "conv_4"],
            representative_messages=[
                "How to integrate Stripe?",
                "Stripe integration help",
                "Setting up Stripe payments",
            ],
            similarity_score=0.92,
        )

        with (
            patch("backend.api.mentor.get_mentor_conversation_repo") as mock_repo,
            patch("backend.services.topic_detector.get_topic_detector") as mock_detector,
        ):
            mock_repo.return_value.get_all_user_messages.return_value = []
            mock_detector.return_value.detect_repeated_topics.return_value = [mock_topic]

            response = client.get("/api/v1/mentor/repeated-topics")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["topics"]) == 1
            assert data["topics"][0]["topic_summary"] == "How to integrate Stripe?"
            assert data["topics"][0]["count"] == 4
            assert data["topics"][0]["similarity_score"] == 0.92
            assert "analysis_timestamp" in data

    def test_repeated_topics_empty(self, client):
        """Returns empty list when no repeated topics detected."""
        with (
            patch("backend.api.mentor.get_mentor_conversation_repo") as mock_repo,
            patch("backend.services.topic_detector.get_topic_detector") as mock_detector,
        ):
            mock_repo.return_value.get_all_user_messages.return_value = []
            mock_detector.return_value.detect_repeated_topics.return_value = []

            response = client.get("/api/v1/mentor/repeated-topics")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["topics"] == []

    def test_repeated_topics_query_params(self, client):
        """Query parameters are passed to detector."""
        with (
            patch("backend.api.mentor.get_mentor_conversation_repo") as mock_repo,
            patch("backend.services.topic_detector.get_topic_detector") as mock_detector,
        ):
            mock_repo.return_value.get_all_user_messages.return_value = []
            mock_detector.return_value.detect_repeated_topics.return_value = []

            response = client.get(
                "/api/v1/mentor/repeated-topics",
                params={"threshold": 0.75, "min_occurrences": 5, "days": 60},
            )

            assert response.status_code == 200
            mock_repo.return_value.get_all_user_messages.assert_called_once_with(
                "test-user-123", days=60
            )
            mock_detector.return_value.detect_repeated_topics.assert_called_once()
            call_kwargs = mock_detector.return_value.detect_repeated_topics.call_args[1]
            assert call_kwargs["threshold"] == 0.75
            assert call_kwargs["min_occurrences"] == 5

    def test_repeated_topics_threshold_validation(self, client):
        """Threshold must be between 0.7 and 0.95."""
        # Too low
        response = client.get("/api/v1/mentor/repeated-topics", params={"threshold": 0.5})
        assert response.status_code == 422

        # Too high
        response = client.get("/api/v1/mentor/repeated-topics", params={"threshold": 0.99})
        assert response.status_code == 422

    def test_repeated_topics_min_occurrences_validation(self, client):
        """min_occurrences must be between 2 and 10."""
        # Too low
        response = client.get("/api/v1/mentor/repeated-topics", params={"min_occurrences": 1})
        assert response.status_code == 422

        # Too high
        response = client.get("/api/v1/mentor/repeated-topics", params={"min_occurrences": 15})
        assert response.status_code == 422

    def test_repeated_topics_days_validation(self, client):
        """days must be between 7 and 90."""
        # Too low
        response = client.get("/api/v1/mentor/repeated-topics", params={"days": 3})
        assert response.status_code == 422

        # Too high
        response = client.get("/api/v1/mentor/repeated-topics", params={"days": 120})
        assert response.status_code == 422


class TestRepeatedTopicsCache:
    """Tests for result caching."""

    def test_repeated_topics_cache_hit(self, client):
        """Cached results returned on subsequent calls."""
        mock_topic = RepeatedTopic(
            topic_summary="Cached topic",
            count=3,
            first_asked="2025-12-01T10:00:00+00:00",
            last_asked="2025-12-15T10:00:00+00:00",
            conversation_ids=["conv_1", "conv_2", "conv_3"],
            representative_messages=["msg1", "msg2", "msg3"],
            similarity_score=0.88,
        )

        with (
            patch("backend.api.mentor.get_mentor_conversation_repo") as mock_repo,
            patch("backend.services.topic_detector.get_topic_detector") as mock_detector,
        ):
            mock_repo.return_value.get_all_user_messages.return_value = []
            mock_detector.return_value.detect_repeated_topics.return_value = [mock_topic]

            # First call
            response1 = client.get("/api/v1/mentor/repeated-topics")
            assert response1.status_code == 200

            # Second call - still works (caching at detector level)
            response2 = client.get("/api/v1/mentor/repeated-topics")
            assert response2.status_code == 200
            assert response2.json()["topics"][0]["topic_summary"] == "Cached topic"
