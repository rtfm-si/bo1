"""Unit tests for user context Redis caching.

Tests:
- Cache hit returns cached context without DB query
- Cache miss falls back to PostgreSQL
- Cache miss populates cache for next request
- save_context invalidates cache
- Redis unavailable gracefully falls back to DB
- TTL expiry triggers fresh fetch
"""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestUserContextCache:
    """Tests for user context caching in Redis."""

    @pytest.fixture
    def mock_redis_manager(self):
        """Create a mock RedisManager."""
        manager = MagicMock()
        manager.is_available = True
        manager.redis = MagicMock()
        return manager

    @pytest.fixture
    def sample_context(self):
        """Sample user context data."""
        return {
            "company_name": "Acme Corp",
            "business_model": "SaaS",
            "target_market": "SMBs",
            "revenue": "100000",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }

    def test_cache_hit_returns_cached_context(self, mock_redis_manager, sample_context):
        """Test that cache hit returns cached context without DB query."""
        from bo1.state.redis_manager import RedisManager

        # Setup mock Redis to return cached context
        mock_redis_manager.redis.get.return_value = json.dumps(sample_context)

        with patch.object(RedisManager, "__init__", lambda x: None):
            manager = RedisManager()
            manager._available = True
            manager.redis = mock_redis_manager.redis

            with patch("bo1.constants.UserContextCache.is_enabled", return_value=True):
                result = manager.get_cached_context("user123")

        assert result == sample_context
        mock_redis_manager.redis.get.assert_called_once()

    def test_cache_miss_returns_none(self, mock_redis_manager):
        """Test that cache miss returns None."""
        from bo1.state.redis_manager import RedisManager

        # Setup mock Redis to return None (cache miss)
        mock_redis_manager.redis.get.return_value = None

        with patch.object(RedisManager, "__init__", lambda x: None):
            manager = RedisManager()
            manager._available = True
            manager.redis = mock_redis_manager.redis

            with patch("bo1.constants.UserContextCache.is_enabled", return_value=True):
                result = manager.get_cached_context("user123")

        assert result is None

    def test_cache_context_stores_with_ttl(self, mock_redis_manager, sample_context):
        """Test that cache_context stores context with correct TTL."""
        from bo1.state.redis_manager import RedisManager

        with patch.object(RedisManager, "__init__", lambda x: None):
            manager = RedisManager()
            manager._available = True
            manager.redis = mock_redis_manager.redis

            with patch("bo1.constants.UserContextCache.is_enabled", return_value=True):
                with patch("bo1.constants.UserContextCache.TTL_SECONDS", 300):
                    with patch("bo1.constants.UserContextCache.KEY_PREFIX", "user_context:"):
                        result = manager.cache_context("user123", sample_context)

        assert result is True
        mock_redis_manager.redis.setex.assert_called_once()
        call_args = mock_redis_manager.redis.setex.call_args
        assert call_args[0][0] == "user_context:user123"
        assert call_args[0][1] == 300  # TTL

    def test_invalidate_context_deletes_key(self, mock_redis_manager):
        """Test that invalidate_context deletes the cache key."""
        from bo1.state.redis_manager import RedisManager

        mock_redis_manager.redis.delete.return_value = 1

        with patch.object(RedisManager, "__init__", lambda x: None):
            manager = RedisManager()
            manager._available = True
            manager.redis = mock_redis_manager.redis

            with patch("bo1.constants.UserContextCache.is_enabled", return_value=True):
                with patch("bo1.constants.UserContextCache.KEY_PREFIX", "user_context:"):
                    result = manager.invalidate_context("user123")

        assert result is True
        mock_redis_manager.redis.delete.assert_called_once_with("user_context:user123")

    def test_cache_disabled_returns_none(self, mock_redis_manager):
        """Test that disabled cache returns None without Redis calls."""
        from bo1.state.redis_manager import RedisManager

        with patch.object(RedisManager, "__init__", lambda x: None):
            manager = RedisManager()
            manager._available = True
            manager.redis = mock_redis_manager.redis

            with patch("bo1.constants.UserContextCache.is_enabled", return_value=False):
                result = manager.get_cached_context("user123")

        assert result is None
        mock_redis_manager.redis.get.assert_not_called()

    def test_cache_disabled_skips_write(self, mock_redis_manager, sample_context):
        """Test that disabled cache skips write operations."""
        from bo1.state.redis_manager import RedisManager

        with patch.object(RedisManager, "__init__", lambda x: None):
            manager = RedisManager()
            manager._available = True
            manager.redis = mock_redis_manager.redis

            with patch("bo1.constants.UserContextCache.is_enabled", return_value=False):
                result = manager.cache_context("user123", sample_context)

        assert result is False
        mock_redis_manager.redis.setex.assert_not_called()

    def test_redis_unavailable_returns_none(self):
        """Test that unavailable Redis returns None gracefully."""
        from bo1.state.redis_manager import RedisManager

        with patch.object(RedisManager, "__init__", lambda x: None):
            manager = RedisManager()
            manager._available = False
            manager.redis = None

            with patch("bo1.constants.UserContextCache.is_enabled", return_value=True):
                result = manager.get_cached_context("user123")

        assert result is None

    def test_redis_error_returns_none(self, mock_redis_manager):
        """Test that Redis errors return None gracefully."""
        from bo1.state.redis_manager import RedisManager

        mock_redis_manager.redis.get.side_effect = Exception("Connection refused")

        with patch.object(RedisManager, "__init__", lambda x: None):
            manager = RedisManager()
            manager._available = True
            manager.redis = mock_redis_manager.redis

            with patch("bo1.constants.UserContextCache.is_enabled", return_value=True):
                with patch("bo1.constants.UserContextCache.KEY_PREFIX", "user_context:"):
                    result = manager.get_cached_context("user123")

        assert result is None


class TestUserRepositoryCaching:
    """Tests for UserRepository caching integration."""

    @pytest.fixture
    def sample_context(self):
        """Sample user context data."""
        return {
            "company_name": "Acme Corp",
            "business_model": "SaaS",
            "target_market": "SMBs",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }

    def test_get_context_cache_hit_skips_db(self, sample_context):
        """Test that cache hit skips database query."""
        from bo1.state.repositories.user_repository import UserRepository

        mock_redis = MagicMock()
        mock_redis.get_cached_context.return_value = sample_context

        # Patch at backend.api.dependencies where the import comes from
        with patch.dict(
            "sys.modules",
            {"backend.api.dependencies": MagicMock(get_redis_manager=lambda: mock_redis)},
        ):
            with patch.object(UserRepository, "_execute_one") as mock_db:
                repo = UserRepository()
                result = repo.get_context("user123")

        assert result == sample_context
        mock_redis.get_cached_context.assert_called_once_with("user123")
        mock_db.assert_not_called()

    def test_get_context_cache_miss_queries_db(self, sample_context):
        """Test that cache miss falls back to database."""
        from bo1.state.repositories.user_repository import UserRepository

        mock_redis = MagicMock()
        mock_redis.get_cached_context.return_value = None  # Cache miss

        with patch.dict(
            "sys.modules",
            {"backend.api.dependencies": MagicMock(get_redis_manager=lambda: mock_redis)},
        ):
            with patch.object(
                UserRepository, "_execute_one", return_value=sample_context
            ) as mock_db:
                repo = UserRepository()
                result = repo.get_context("user123")

        assert result == sample_context
        mock_redis.get_cached_context.assert_called_once_with("user123")
        mock_db.assert_called_once()

    def test_get_context_cache_miss_populates_cache(self, sample_context):
        """Test that cache miss populates cache with DB result."""
        from bo1.state.repositories.user_repository import UserRepository

        mock_redis = MagicMock()
        mock_redis.get_cached_context.return_value = None  # Cache miss

        with patch.dict(
            "sys.modules",
            {"backend.api.dependencies": MagicMock(get_redis_manager=lambda: mock_redis)},
        ):
            with patch.object(UserRepository, "_execute_one", return_value=sample_context):
                repo = UserRepository()
                repo.get_context("user123")

        mock_redis.cache_context.assert_called_once_with("user123", sample_context)

    def test_save_context_invalidates_cache(self, sample_context):
        """Test that save_context invalidates the cache."""
        from bo1.state.repositories.user_repository import UserRepository

        mock_redis = MagicMock()

        with patch.dict(
            "sys.modules",
            {"backend.api.dependencies": MagicMock(get_redis_manager=lambda: mock_redis)},
        ):
            with patch.object(UserRepository, "_execute_returning", return_value=sample_context):
                repo = UserRepository()
                repo.save_context("user123", {"company_name": "New Corp"})

        mock_redis.invalidate_context.assert_called_once_with("user123")

    def test_get_context_redis_error_falls_back_to_db(self, sample_context):
        """Test that Redis errors fall back to database."""
        from bo1.state.repositories.user_repository import UserRepository

        mock_redis = MagicMock()
        mock_redis.get_cached_context.side_effect = Exception("Redis error")

        with patch.dict(
            "sys.modules",
            {"backend.api.dependencies": MagicMock(get_redis_manager=lambda: mock_redis)},
        ):
            with patch.object(
                UserRepository, "_execute_one", return_value=sample_context
            ) as mock_db:
                repo = UserRepository()
                result = repo.get_context("user123")

        assert result == sample_context
        mock_db.assert_called_once()


class TestUserContextCacheConfig:
    """Tests for UserContextCache configuration."""

    def test_default_ttl_is_300_seconds(self):
        """Test that default TTL is 5 minutes."""
        from bo1.constants import UserContextCache

        assert UserContextCache.TTL_SECONDS == 300

    def test_key_prefix_format(self):
        """Test that key prefix is correct."""
        from bo1.constants import UserContextCache

        assert UserContextCache.KEY_PREFIX == "user_context:"

    def test_is_enabled_default_true(self):
        """Test that caching is enabled by default."""
        from bo1.constants import UserContextCache

        with patch.dict("os.environ", {}, clear=True):
            # Clear env var to test default
            import os

            os.environ.pop("USER_CONTEXT_CACHE_ENABLED", None)
            assert UserContextCache.is_enabled() is True

    def test_is_enabled_can_be_disabled(self):
        """Test that caching can be disabled via env var."""
        from bo1.constants import UserContextCache

        with patch.dict("os.environ", {"USER_CONTEXT_CACHE_ENABLED": "false"}):
            assert UserContextCache.is_enabled() is False
