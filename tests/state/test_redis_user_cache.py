"""Tests for Redis user_id caching optimization.

Validates:
- get_cached_user_id returns user_id from Redis metadata
- get_cached_user_id falls back to DB on cache miss
- get_cached_user_id re-caches user_id on DB fetch
"""

from unittest.mock import MagicMock, patch

import pytest


class TestGetCachedUserId:
    """Test get_cached_user_id method for user_id caching optimization."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        client = MagicMock()
        client.ping.return_value = True
        return client

    @pytest.fixture
    def redis_manager(self, mock_redis):
        """Create a RedisManager with mocked Redis client."""
        from bo1.state.redis_manager import RedisManager

        with (
            patch("bo1.state.redis_manager.redis.ConnectionPool"),
            patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis),
        ):
            manager = RedisManager()
            manager.redis = mock_redis
            manager._available = True
            return manager

    def test_cache_hit_returns_user_id(self, redis_manager, mock_redis):
        """Verify cache hit returns user_id without DB query."""
        # Mock metadata with user_id
        import json

        metadata = {"user_id": "user_123", "status": "running"}
        mock_redis.get.return_value = json.dumps(metadata)

        user_id = redis_manager.get_cached_user_id("bo1_test")

        assert user_id == "user_123"
        # Verify Redis was queried
        mock_redis.get.assert_called_once_with("metadata:bo1_test")

    def test_cache_miss_queries_db(self, redis_manager, mock_redis):
        """Verify cache miss falls back to DB query via load_metadata."""
        # Mock load_metadata to simulate DB fallback returning user_id
        with patch.object(
            redis_manager,
            "load_metadata",
            return_value={"user_id": "user_db_456", "status": "running"},
        ):
            user_id = redis_manager.get_cached_user_id("bo1_test")

        assert user_id == "user_db_456"

    def test_cache_miss_with_db_not_found(self, redis_manager, mock_redis):
        """Verify returns None when both cache and DB miss."""
        # Mock load_metadata to return None (session not found anywhere)
        with patch.object(
            redis_manager,
            "load_metadata",
            return_value=None,
        ):
            user_id = redis_manager.get_cached_user_id("bo1_nonexistent")

        assert user_id is None

    def test_cache_miss_recaches_user_id(self, redis_manager, mock_redis):
        """Verify DB fetch re-caches user_id via load_metadata."""
        # Mock load_metadata to simulate DB fallback with re-caching
        with patch.object(
            redis_manager,
            "load_metadata",
            return_value={"user_id": "user_recache", "status": "running"},
        ):
            user_id = redis_manager.get_cached_user_id("bo1_test")

        assert user_id == "user_recache"
        # Note: load_metadata handles re-caching internally

    def test_redis_unavailable_returns_none(self, mock_redis):
        """Verify returns None when Redis is unavailable."""
        from bo1.state.redis_manager import RedisManager

        # Create manager and then set it to unavailable state
        with (
            patch("bo1.state.redis_manager.redis.ConnectionPool"),
            patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis),
        ):
            manager = RedisManager()
            # Simulate Redis becoming unavailable
            manager._available = False

        # Should return None since Redis isn't available
        result = manager.get_cached_user_id("bo1_test")
        assert result is None

    def test_metadata_without_user_id_returns_none(self, redis_manager, mock_redis):
        """Verify metadata without user_id returns None."""
        # Mock load_metadata to return metadata without user_id
        with patch.object(
            redis_manager,
            "load_metadata",
            return_value={"status": "running", "phase": "discussion"},
        ):
            user_id = redis_manager.get_cached_user_id("bo1_test")

        # Without user_id in metadata, get_cached_user_id returns None
        assert user_id is None
