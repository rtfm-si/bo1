"""Tests for Redis metadata PostgreSQL fallback in RedisManager.

Validates:
- load_metadata returns DB data when Redis empty
- load_metadata returns None when both fail
- Re-cache writes to Redis on DB hit
- recache_ttl_seconds=0 disables re-cache
- Fallback metric incremented
"""

from unittest.mock import MagicMock, patch

import pytest

from bo1.state.redis_manager import RedisManager

# Patch path for session_repository singleton instance
SESSION_REPO_PATCH = "bo1.state.repositories.session_repository"


class TestMetadataFallback:
    """Test load_metadata PostgreSQL fallback behavior."""

    @pytest.fixture
    def connected_manager(self):
        """Create a connected RedisManager with mocked Redis."""
        with patch("bo1.state.redis_manager.redis.ConnectionPool"):
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True
            mock_redis.get.return_value = None  # Default: cache miss

            with patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis):
                manager = RedisManager(host="localhost", port=6379)
                yield manager, mock_redis

    @pytest.fixture
    def disconnected_manager(self):
        """Create a disconnected RedisManager."""
        import redis

        with patch("bo1.state.redis_manager.redis.ConnectionPool"):
            mock_redis = MagicMock()
            mock_redis.ping.side_effect = redis.ConnectionError("Connection refused")

            with patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis):
                manager = RedisManager(host="localhost", port=6379)
                yield manager

    def test_load_metadata_returns_redis_data_when_available(self, connected_manager):
        """load_metadata returns Redis data when cache hit."""
        manager, mock_redis = connected_manager
        cached_data = '{"status": "running", "user_id": "user123"}'
        mock_redis.get.return_value = cached_data

        result = manager.load_metadata("bo1_test123")

        assert result is not None
        assert result["status"] == "running"
        assert result["user_id"] == "user123"
        mock_redis.get.assert_called_once_with("metadata:bo1_test123")

    def test_load_metadata_falls_back_to_db_when_redis_empty(self, connected_manager):
        """load_metadata returns DB data when Redis cache miss."""
        manager, mock_redis = connected_manager
        mock_redis.get.return_value = None  # Cache miss

        db_metadata = {
            "status": "completed",
            "phase": "synthesis",
            "user_id": "user456",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T01:00:00",
            "problem_statement": "Test problem",
            "problem_context": {},
        }

        mock_repo = MagicMock()
        mock_repo.get_metadata.return_value = db_metadata

        with patch(SESSION_REPO_PATCH, mock_repo):
            result = manager.load_metadata("bo1_test456")

        assert result is not None
        assert result["status"] == "completed"
        assert result["user_id"] == "user456"
        mock_repo.get_metadata.assert_called_once_with("bo1_test456")

    def test_load_metadata_returns_none_when_both_fail(self, connected_manager):
        """load_metadata returns None when both Redis and DB have no data."""
        manager, mock_redis = connected_manager
        mock_redis.get.return_value = None

        mock_repo = MagicMock()
        mock_repo.get_metadata.return_value = None

        with patch(SESSION_REPO_PATCH, mock_repo):
            result = manager.load_metadata("bo1_nonexistent")

        assert result is None

    def test_load_metadata_recaches_on_db_hit(self, connected_manager):
        """load_metadata re-caches metadata in Redis after DB hit."""
        manager, mock_redis = connected_manager
        mock_redis.get.return_value = None  # Cache miss

        db_metadata = {
            "status": "running",
            "user_id": "user789",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T01:00:00",
            "problem_statement": "Test",
            "problem_context": {},
            "phase": "rounds",
        }

        mock_repo = MagicMock()
        mock_repo.get_metadata.return_value = db_metadata

        with patch(SESSION_REPO_PATCH, mock_repo):
            result = manager.load_metadata("bo1_test789", recache_ttl_seconds=3600)

        assert result is not None
        # Verify setex was called to re-cache
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "metadata:bo1_test789"
        assert call_args[0][1] == 3600  # TTL

    def test_load_metadata_skips_recache_when_ttl_zero(self, connected_manager):
        """load_metadata skips re-caching when recache_ttl_seconds=0."""
        manager, mock_redis = connected_manager
        mock_redis.get.return_value = None

        db_metadata = {
            "status": "running",
            "user_id": "user_no_cache",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T01:00:00",
            "problem_statement": "Test",
            "problem_context": {},
            "phase": "rounds",
        }

        mock_repo = MagicMock()
        mock_repo.get_metadata.return_value = db_metadata

        with patch(SESSION_REPO_PATCH, mock_repo):
            result = manager.load_metadata("bo1_test_no_cache", recache_ttl_seconds=0)

        assert result is not None
        # Verify setex was NOT called
        mock_redis.setex.assert_not_called()

    def test_load_metadata_falls_back_when_redis_unavailable(self, disconnected_manager):
        """load_metadata falls back to DB when Redis is unavailable."""
        manager = disconnected_manager
        assert manager.is_available is False

        db_metadata = {
            "status": "running",
            "user_id": "user_db_only",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T01:00:00",
            "problem_statement": "Test",
            "problem_context": {},
            "phase": "init",
        }

        mock_repo = MagicMock()
        mock_repo.get_metadata.return_value = db_metadata

        with patch(SESSION_REPO_PATCH, mock_repo):
            result = manager.load_metadata("bo1_db_only")

        assert result is not None
        assert result["user_id"] == "user_db_only"

    def test_load_metadata_increments_success_metric_on_db_hit(self, connected_manager):
        """Fallback metric incremented with result=success on DB hit."""
        manager, mock_redis = connected_manager
        mock_redis.get.return_value = None

        db_metadata = {"status": "running", "user_id": "user_metric"}

        mock_repo = MagicMock()
        mock_repo.get_metadata.return_value = db_metadata

        mock_counter = MagicMock()
        mock_prom = MagicMock()
        mock_prom.redis_metadata_fallback_total.labels.return_value = mock_counter

        with patch(SESSION_REPO_PATCH, mock_repo):
            with patch("backend.api.metrics.prom_metrics", mock_prom):
                result = manager.load_metadata("bo1_metric_test")

        assert result is not None
        mock_prom.redis_metadata_fallback_total.labels.assert_called_with(result="success")
        mock_counter.inc.assert_called_once()

    def test_load_metadata_increments_failure_metric_on_db_miss(self, connected_manager):
        """Fallback metric incremented with result=failure when DB also misses."""
        manager, mock_redis = connected_manager
        mock_redis.get.return_value = None

        mock_repo = MagicMock()
        mock_repo.get_metadata.return_value = None

        mock_counter = MagicMock()
        mock_prom = MagicMock()
        mock_prom.redis_metadata_fallback_total.labels.return_value = mock_counter

        with patch(SESSION_REPO_PATCH, mock_repo):
            with patch("backend.api.metrics.prom_metrics", mock_prom):
                result = manager.load_metadata("bo1_nonexistent")

        assert result is None
        mock_prom.redis_metadata_fallback_total.labels.assert_called_with(result="failure")
        mock_counter.inc.assert_called_once()


class TestGetCachedUserId:
    """Test get_cached_user_id with improved fallback."""

    @pytest.fixture
    def connected_manager(self):
        """Create a connected RedisManager with mocked Redis."""
        with patch("bo1.state.redis_manager.redis.ConnectionPool"):
            mock_redis = MagicMock()
            mock_redis.ping.return_value = True
            mock_redis.get.return_value = None

            with patch("bo1.state.redis_manager.redis.Redis", return_value=mock_redis):
                manager = RedisManager(host="localhost", port=6379)
                yield manager, mock_redis

    def test_get_cached_user_id_from_redis(self, connected_manager):
        """get_cached_user_id returns user_id from Redis cache."""
        manager, mock_redis = connected_manager
        mock_redis.get.return_value = '{"user_id": "cached_user"}'

        result = manager.get_cached_user_id("bo1_test")

        assert result == "cached_user"

    def test_get_cached_user_id_from_db_fallback(self, connected_manager):
        """get_cached_user_id returns user_id from DB fallback."""
        manager, mock_redis = connected_manager
        mock_redis.get.return_value = None

        db_metadata = {"status": "running", "user_id": "db_user"}

        mock_repo = MagicMock()
        mock_repo.get_metadata.return_value = db_metadata

        with patch(SESSION_REPO_PATCH, mock_repo):
            result = manager.get_cached_user_id("bo1_db_test")

        assert result == "db_user"

    def test_get_cached_user_id_returns_none_when_not_found(self, connected_manager):
        """get_cached_user_id returns None when user_id not in metadata."""
        manager, mock_redis = connected_manager
        mock_redis.get.return_value = None

        mock_repo = MagicMock()
        mock_repo.get_metadata.return_value = None

        with patch(SESSION_REPO_PATCH, mock_repo):
            result = manager.get_cached_user_id("bo1_missing")

        assert result is None
