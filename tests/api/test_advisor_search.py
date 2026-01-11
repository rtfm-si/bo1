"""Tests for advisor conversation search endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.advisor import router
from backend.api.middleware.auth import get_current_user
from backend.services.topic_detector import SimilarMessage, TopicDetector


def mock_user_override():
    """Override auth to return test user."""
    return {"user_id": "test-user-123", "email": "test@example.com"}


@pytest.fixture
def test_app():
    """Create test app with advisor router and auth override."""
    app = FastAPI()
    app.dependency_overrides[get_current_user] = mock_user_override
    app.include_router(router, prefix="/api")
    return app


@pytest.fixture
def client(test_app):
    """Create test client with auth bypass."""
    return TestClient(test_app)


class TestSearchEndpoint:
    """Tests for GET /api/v1/advisor/search."""

    @pytest.fixture
    def mock_messages(self):
        """Create mock conversation messages."""
        return [
            {
                "content": "How do I improve my sales pipeline?",
                "timestamp": "2026-01-01T10:00:00Z",
                "conversation_id": "conv-1",
            },
            {
                "content": "What marketing strategy should I use?",
                "timestamp": "2026-01-02T10:00:00Z",
                "conversation_id": "conv-2",
            },
            {
                "content": "Help with customer retention strategies",
                "timestamp": "2026-01-03T10:00:00Z",
                "conversation_id": "conv-3",
            },
        ]

    @pytest.fixture
    def mock_similar_results(self):
        """Create mock similar message results."""
        return [
            SimilarMessage(
                conversation_id="conv-1",
                content="How do I improve my sales pipeline?",
                preview="How do I improve my sales pipeline?",
                similarity=0.85,
                timestamp="2026-01-01T10:00:00Z",
            ),
            SimilarMessage(
                conversation_id="conv-2",
                content="What marketing strategy should I use?",
                preview="What marketing strategy should I use?",
                similarity=0.72,
                timestamp="2026-01-02T10:00:00Z",
            ),
        ]

    def test_search_returns_matches_for_known_topics(
        self, client, mock_messages, mock_similar_results
    ):
        """Search returns matching conversations for related queries."""
        with (
            patch("backend.api.advisor.get_mentor_conversation_repo") as mock_repo_getter,
            patch("backend.services.topic_detector.get_topic_detector") as mock_detector_getter,
        ):
            mock_repo = MagicMock()
            mock_repo.get_all_user_messages.return_value = mock_messages
            mock_repo_getter.return_value = mock_repo

            mock_detector = MagicMock()
            mock_detector.find_similar_messages.return_value = mock_similar_results
            mock_detector_getter.return_value = mock_detector

            response = client.get("/api/v1/advisor/search?q=sales+strategy")
            assert response.status_code == 200

            data = response.json()
            assert data["total"] == 2
            assert len(data["matches"]) == 2
            assert data["matches"][0]["conversation_id"] == "conv-1"
            assert data["matches"][0]["similarity"] == 0.85
            assert data["matches"][1]["conversation_id"] == "conv-2"

    def test_search_returns_empty_for_no_matches(self, client, mock_messages):
        """Search returns empty list when no matches found."""
        with (
            patch("backend.api.advisor.get_mentor_conversation_repo") as mock_repo_getter,
            patch("backend.services.topic_detector.get_topic_detector") as mock_detector_getter,
        ):
            mock_repo = MagicMock()
            mock_repo.get_all_user_messages.return_value = mock_messages
            mock_repo_getter.return_value = mock_repo

            mock_detector = MagicMock()
            mock_detector.find_similar_messages.return_value = []  # No matches
            mock_detector_getter.return_value = mock_detector

            response = client.get("/api/v1/advisor/search?q=completely+unrelated+topic")
            assert response.status_code == 200

            data = response.json()
            assert data["total"] == 0
            assert data["matches"] == []

    def test_search_respects_user_ownership(self, client, mock_messages):
        """Search only returns conversations owned by the requesting user."""
        with (
            patch("backend.api.advisor.get_mentor_conversation_repo") as mock_repo_getter,
            patch("backend.services.topic_detector.get_topic_detector") as mock_detector_getter,
        ):
            mock_repo = MagicMock()
            mock_repo.get_all_user_messages.return_value = mock_messages
            mock_repo_getter.return_value = mock_repo

            mock_detector = MagicMock()
            mock_detector.find_similar_messages.return_value = []
            mock_detector_getter.return_value = mock_detector

            response = client.get("/api/v1/advisor/search?q=test")
            assert response.status_code == 200

            # Verify user_id was passed to repo
            mock_repo.get_all_user_messages.assert_called_once()
            call_args = mock_repo.get_all_user_messages.call_args
            assert call_args[0][0] == "test-user-123"

    def test_search_handles_empty_query_gracefully(self, client):
        """Search rejects queries shorter than 3 characters."""
        # Query too short
        response = client.get("/api/v1/advisor/search?q=ab")
        assert response.status_code == 422  # Validation error

    def test_search_filters_by_threshold(self, client, mock_messages):
        """Search respects the similarity threshold parameter."""
        with (
            patch("backend.api.advisor.get_mentor_conversation_repo") as mock_repo_getter,
            patch("backend.services.topic_detector.get_topic_detector") as mock_detector_getter,
        ):
            mock_repo = MagicMock()
            mock_repo.get_all_user_messages.return_value = mock_messages
            mock_repo_getter.return_value = mock_repo

            mock_detector = MagicMock()
            mock_detector.find_similar_messages.return_value = []
            mock_detector_getter.return_value = mock_detector

            response = client.get("/api/v1/advisor/search?q=sales&threshold=0.8")
            assert response.status_code == 200

            # Verify threshold was passed to detector
            mock_detector.find_similar_messages.assert_called_once()
            call_kwargs = mock_detector.find_similar_messages.call_args[1]
            assert call_kwargs["threshold"] == 0.8

    def test_search_returns_empty_for_new_user(self, client):
        """Search returns empty gracefully for users with no conversations."""
        with (
            patch("backend.api.advisor.get_mentor_conversation_repo") as mock_repo_getter,
        ):
            mock_repo = MagicMock()
            mock_repo.get_all_user_messages.return_value = []  # No messages
            mock_repo_getter.return_value = mock_repo

            response = client.get("/api/v1/advisor/search?q=anything")
            assert response.status_code == 200

            data = response.json()
            assert data["total"] == 0
            assert data["matches"] == []


class TestTopicDetectorFindSimilar:
    """Tests for TopicDetector.find_similar_messages method."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis manager."""
        mock = MagicMock()
        mock.client = MagicMock()
        mock.client.get.return_value = None  # No cache hits
        return mock

    def test_returns_empty_for_empty_query(self, mock_redis):
        """Returns empty list for empty or whitespace query."""
        detector = TopicDetector(redis_manager=mock_redis)
        messages = [{"content": "Test message", "timestamp": "2026-01-01", "conversation_id": "c1"}]

        result = detector.find_similar_messages("test-user", "", messages)
        assert result == []

        result = detector.find_similar_messages("test-user", "   ", messages)
        assert result == []

    def test_returns_empty_for_no_messages(self, mock_redis):
        """Returns empty list when no messages provided."""
        detector = TopicDetector(redis_manager=mock_redis)

        result = detector.find_similar_messages("test-user", "query", [])
        assert result == []

    def test_filters_by_threshold(self, mock_redis):
        """Only returns results above the similarity threshold."""
        detector = TopicDetector(redis_manager=mock_redis)
        messages = [
            {
                "content": "Sales pipeline management",
                "timestamp": "2026-01-01",
                "conversation_id": "c1",
            },
        ]

        with patch.object(detector, "_get_embeddings_with_cache") as mock_embed:
            # Return message with embedding
            mock_embed.return_value = [(messages[0], [0.1, 0.2, 0.3])]

            with patch("backend.services.topic_detector.generate_embeddings_batch") as mock_gen:
                mock_gen.return_value = [[0.5, 0.6, 0.7]]  # Different embedding

                with patch("backend.services.topic_detector.cosine_similarity") as mock_cos:
                    # Return low similarity
                    mock_cos.return_value = 0.5

                    result = detector.find_similar_messages(
                        "test-user", "query", messages, threshold=0.7
                    )
                    assert result == []  # Below threshold

                    # Return high similarity
                    mock_cos.return_value = 0.85
                    result = detector.find_similar_messages(
                        "test-user", "query", messages, threshold=0.7
                    )
                    assert len(result) == 1

    def test_respects_limit(self, mock_redis):
        """Returns at most 'limit' results."""
        detector = TopicDetector(redis_manager=mock_redis)
        messages = [
            {"content": f"Message {i}", "timestamp": "2026-01-01", "conversation_id": f"c{i}"}
            for i in range(10)
        ]

        with patch.object(detector, "_get_embeddings_with_cache") as mock_embed:
            mock_embed.return_value = [(m, [0.1, 0.2, 0.3]) for m in messages]

            with patch("backend.services.topic_detector.generate_embeddings_batch") as mock_gen:
                mock_gen.return_value = [[0.1, 0.2, 0.3]]

                with patch("backend.services.topic_detector.cosine_similarity") as mock_cos:
                    mock_cos.return_value = 0.9  # All match

                    result = detector.find_similar_messages("test-user", "query", messages, limit=3)
                    assert len(result) == 3

    def test_sorts_by_similarity_descending(self, mock_redis):
        """Results are sorted by similarity score (highest first)."""
        detector = TopicDetector(redis_manager=mock_redis)
        messages = [
            {"content": "Low match", "timestamp": "2026-01-01", "conversation_id": "c1"},
            {"content": "High match", "timestamp": "2026-01-02", "conversation_id": "c2"},
            {"content": "Medium match", "timestamp": "2026-01-03", "conversation_id": "c3"},
        ]

        with patch.object(detector, "_get_embeddings_with_cache") as mock_embed:
            mock_embed.return_value = [(m, [0.1 * i, 0.2, 0.3]) for i, m in enumerate(messages)]

            with patch("backend.services.topic_detector.generate_embeddings_batch") as mock_gen:
                mock_gen.return_value = [[0.5, 0.5, 0.5]]

                with patch("backend.services.topic_detector.cosine_similarity") as mock_cos:

                    def get_similarity(q_emb, m_emb):
                        # Return different similarity based on embedding index
                        idx = int(m_emb[0] * 10)
                        return [0.7, 0.95, 0.8][idx]

                    mock_cos.side_effect = get_similarity

                    result = detector.find_similar_messages(
                        "test-user", "query", messages, threshold=0.6
                    )
                    assert len(result) == 3
                    # Highest similarity first
                    assert result[0].similarity == 0.95
                    assert result[1].similarity == 0.8
                    assert result[2].similarity == 0.7

    def test_truncates_preview(self, mock_redis):
        """Preview is truncated for long messages."""
        detector = TopicDetector(redis_manager=mock_redis)
        long_content = "A" * 200  # Very long message
        messages = [
            {"content": long_content, "timestamp": "2026-01-01", "conversation_id": "c1"},
        ]

        with patch.object(detector, "_get_embeddings_with_cache") as mock_embed:
            mock_embed.return_value = [(messages[0], [0.1, 0.2, 0.3])]

            with patch("backend.services.topic_detector.generate_embeddings_batch") as mock_gen:
                mock_gen.return_value = [[0.1, 0.2, 0.3]]

                with patch("backend.services.topic_detector.cosine_similarity") as mock_cos:
                    mock_cos.return_value = 0.9

                    result = detector.find_similar_messages(
                        "test-user", "query", messages, threshold=0.7
                    )
                    assert len(result) == 1
                    assert len(result[0].preview) == 103  # 100 + "..."
                    assert result[0].preview.endswith("...")
                    assert result[0].content == long_content  # Full content preserved
