"""Tests for topic detector service."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.services.topic_detector import (
    TopicDetector,
    get_topic_detector,
)


class TestTopicDetector:
    """Tests for TopicDetector class."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis manager."""
        mock = MagicMock()
        mock.client.get.return_value = None
        mock.client.setex.return_value = True
        return mock

    @pytest.fixture
    def detector(self, mock_redis):
        """Create a TopicDetector with mocked Redis."""
        return TopicDetector(redis_manager=mock_redis)

    def test_detect_repeated_topics_empty_history(self, detector):
        """Returns empty list when no messages provided."""
        result = detector.detect_repeated_topics(
            user_id="user_123",
            messages=[],
            threshold=0.85,
            min_occurrences=3,
        )

        assert result == []

    def test_detect_repeated_topics_no_repeats(self, detector):
        """Returns empty when no topics meet min_occurrences threshold."""
        messages = [
            {
                "content": "How do I set up billing?",
                "timestamp": datetime.now(UTC).isoformat(),
                "conversation_id": "conv_1",
            },
            {
                "content": "What is the weather today?",
                "timestamp": datetime.now(UTC).isoformat(),
                "conversation_id": "conv_2",
            },
        ]

        with patch("backend.services.topic_detector.generate_embeddings_batch") as mock_embed:
            # Return distinct embeddings
            mock_embed.return_value = [
                [1.0, 0.0, 0.0] * 341 + [1.0],  # 1024 dims
                [0.0, 1.0, 0.0] * 341 + [0.0],
            ]

            result = detector.detect_repeated_topics(
                user_id="user_123",
                messages=messages,
                threshold=0.85,
                min_occurrences=3,
            )

        assert result == []

    def test_detect_repeated_topics_finds_cluster(self, detector):
        """Finds clusters of semantically similar messages."""
        now = datetime.now(UTC).isoformat()
        messages = [
            {
                "content": "How do I integrate with Stripe?",
                "timestamp": now,
                "conversation_id": "c1",
            },
            {
                "content": "What's the process for Stripe integration?",
                "timestamp": now,
                "conversation_id": "c2",
            },
            {
                "content": "Can you help me set up Stripe payments?",
                "timestamp": now,
                "conversation_id": "c3",
            },
            {"content": "What is the weather today?", "timestamp": now, "conversation_id": "c4"},
        ]

        with patch("backend.services.topic_detector.generate_embeddings_batch") as mock_embed:
            # First 3 messages similar (high values), 4th orthogonal
            # Use distinct but similar vectors for the cluster
            similar_vec1 = [0.9, 0.1, 0.0] * 341 + [0.9]  # 1024 dims
            similar_vec2 = [0.88, 0.15, 0.0] * 341 + [0.88]
            similar_vec3 = [0.92, 0.08, 0.0] * 341 + [0.92]
            # Orthogonal vector - very different direction
            different_vec = [0.0, 0.0, 1.0] * 341 + [0.0]

            mock_embed.return_value = [similar_vec1, similar_vec2, similar_vec3, different_vec]

            result = detector.detect_repeated_topics(
                user_id="user_123",
                messages=messages,
                threshold=0.85,
                min_occurrences=3,
            )

        assert len(result) == 1
        topic = result[0]
        assert topic.count == 3
        assert "c1" in topic.conversation_ids
        assert "c2" in topic.conversation_ids
        assert "c3" in topic.conversation_ids
        assert "c4" not in topic.conversation_ids

    def test_embedding_caching(self, detector, mock_redis):
        """Uses cached embeddings when available."""
        import json

        cached_embedding = [0.5] * 1024
        mock_redis.client.get.return_value = json.dumps(cached_embedding)

        messages = [
            {
                "content": "cached question",
                "timestamp": datetime.now(UTC).isoformat(),
                "conversation_id": "c1",
            },
        ]

        with patch("backend.services.topic_detector.generate_embeddings_batch") as mock_embed:
            result = detector._get_embeddings_with_cache("user_123", messages)

            # Should not call API since cached
            mock_embed.assert_not_called()
            assert len(result) == 1
            assert result[0][1] == cached_embedding

    def test_threshold_filtering(self, detector):
        """Higher threshold filters out less similar messages."""
        now = datetime.now(UTC).isoformat()
        messages = [
            {"content": "msg1", "timestamp": now, "conversation_id": "c1"},
            {"content": "msg2", "timestamp": now, "conversation_id": "c2"},
            {"content": "msg3", "timestamp": now, "conversation_id": "c3"},
        ]

        with patch("backend.services.topic_detector.generate_embeddings_batch") as mock_embed:
            # Create vectors with known similarity
            # These will have ~0.8 cosine similarity (moderate)
            vec1 = [1.0, 0.0, 0.0] * 341 + [1.0]
            vec2 = [0.8, 0.6, 0.0] * 341 + [0.8]  # ~0.8 similarity to vec1
            vec3 = [0.7, 0.7, 0.0] * 341 + [0.7]  # ~0.7 similarity to vec1

            mock_embed.return_value = [vec1, vec2, vec3]

            # With lower threshold (0.7) - should cluster some
            result_low = detector.detect_repeated_topics(
                user_id="user_123",
                messages=messages,
                threshold=0.7,
                min_occurrences=2,
            )

        # Reset mock for second call
        with patch("backend.services.topic_detector.generate_embeddings_batch") as mock_embed2:
            # Completely orthogonal vectors - zero similarity
            vec1 = [1.0, 0.0, 0.0] * 341 + [1.0]
            vec2 = [0.0, 1.0, 0.0] * 341 + [0.0]
            vec3 = [0.0, 0.0, 1.0] * 341 + [0.0]
            mock_embed2.return_value = [vec1, vec2, vec3]

            # With high threshold and orthogonal vectors - no clusters
            result_high = detector.detect_repeated_topics(
                user_id="user_123",
                messages=messages,
                threshold=0.99,
                min_occurrences=2,
            )

        # Low threshold should find cluster, high should not
        assert len(result_low) >= 1
        assert len(result_high) == 0


class TestClusterBySimilarity:
    """Tests for clustering algorithm."""

    @pytest.fixture
    def detector(self):
        """Create detector with mock redis."""
        mock_redis = MagicMock()
        return TopicDetector(redis_manager=mock_redis)

    def test_empty_input(self, detector):
        """Empty input returns empty clusters."""
        result = detector._cluster_by_similarity([], threshold=0.85)
        assert result == []

    def test_single_item(self, detector):
        """Single item forms its own cluster."""
        messages = [({"content": "test"}, [1.0] * 1024)]
        result = detector._cluster_by_similarity(messages, threshold=0.85)
        assert len(result) == 1
        assert len(result[0]) == 1

    def test_all_similar(self, detector):
        """All similar messages form one cluster."""
        vec = [0.9] * 1024
        messages = [
            ({"content": "msg1"}, vec),
            ({"content": "msg2"}, vec),
            ({"content": "msg3"}, vec),
        ]
        result = detector._cluster_by_similarity(messages, threshold=0.85)
        assert len(result) == 1
        assert len(result[0]) == 3

    def test_all_different(self, detector):
        """All different messages form separate clusters."""
        messages = [
            ({"content": "msg1"}, [1.0, 0.0, 0.0] * 341 + [1.0]),
            ({"content": "msg2"}, [0.0, 1.0, 0.0] * 341 + [0.0]),
            ({"content": "msg3"}, [0.0, 0.0, 1.0] * 341 + [0.0]),
        ]
        result = detector._cluster_by_similarity(messages, threshold=0.85)
        assert len(result) == 3


class TestGenerateTopicSummary:
    """Tests for topic summary generation."""

    @pytest.fixture
    def detector(self):
        mock_redis = MagicMock()
        return TopicDetector(redis_manager=mock_redis)

    def test_empty_messages(self, detector):
        """Empty list returns 'Unknown topic'."""
        result = detector._generate_topic_summary([])
        assert result == "Unknown topic"

    def test_short_message(self, detector):
        """Short message used as-is."""
        result = detector._generate_topic_summary(["How to set up Stripe?"])
        assert result == "How to set up Stripe?"

    def test_long_message_truncated(self, detector):
        """Long message gets truncated."""
        long_msg = "A" * 150
        result = detector._generate_topic_summary([long_msg])
        assert len(result) == 100
        assert result.endswith("...")

    def test_shortest_selected(self, detector):
        """Shortest message selected as representative."""
        messages = [
            "This is a longer message about integrating Stripe payments",
            "Stripe setup?",
            "How do I configure Stripe for my e-commerce store",
        ]
        result = detector._generate_topic_summary(messages)
        assert result == "Stripe setup?"


class TestComputeClusterSimilarity:
    """Tests for cluster similarity computation."""

    @pytest.fixture
    def detector(self):
        mock_redis = MagicMock()
        return TopicDetector(redis_manager=mock_redis)

    def test_single_item_cluster(self, detector):
        """Single item cluster has similarity 1.0."""
        cluster = [({"content": "test"}, [1.0] * 1024)]
        result = detector._compute_cluster_similarity(cluster)
        assert result == 1.0

    def test_identical_vectors(self, detector):
        """Identical vectors have similarity 1.0."""
        vec = [0.5] * 1024
        cluster = [
            ({"content": "msg1"}, vec),
            ({"content": "msg2"}, vec),
        ]
        result = detector._compute_cluster_similarity(cluster)
        assert abs(result - 1.0) < 0.01


class TestGetTopicDetector:
    """Tests for singleton getter."""

    def test_returns_instance(self):
        """Returns TopicDetector instance."""
        with patch("backend.services.topic_detector.RedisManager"):
            detector = get_topic_detector()
            assert isinstance(detector, TopicDetector)

    def test_singleton_pattern(self):
        """Returns same instance on repeated calls."""
        with patch("backend.services.topic_detector.RedisManager"):
            detector1 = get_topic_detector()
            detector2 = get_topic_detector()
            assert detector1 is detector2
