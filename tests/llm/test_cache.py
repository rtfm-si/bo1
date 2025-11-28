"""Tests for LLM response caching functionality.

This module tests the Redis-backed LLM response cache to ensure:
- Deterministic cache key generation
- Proper cache hits and misses
- TTL-based expiration
- Statistics tracking
- Graceful degradation on errors
"""

import pytest

from bo1.llm.broker import PromptRequest
from bo1.llm.cache import LLMResponseCache, generate_cache_key, get_llm_cache
from bo1.llm.client import TokenUsage
from bo1.llm.response import LLMResponse


class TestCacheKeyGeneration:
    """Test deterministic cache key generation."""

    def test_cache_key_deterministic(self) -> None:
        """Test that identical prompts generate identical keys."""
        key1 = generate_cache_key("system", "user", "model")
        key2 = generate_cache_key("system", "user", "model")
        assert key1 == key2

    def test_cache_key_different_prompts(self) -> None:
        """Test that different prompts generate different keys."""
        key1 = generate_cache_key("system", "user", "model")
        key2 = generate_cache_key("system", "different", "model")
        assert key1 != key2

    def test_cache_key_different_models(self) -> None:
        """Test that different models generate different keys."""
        key1 = generate_cache_key("system", "user", "model1")
        key2 = generate_cache_key("system", "user", "model2")
        assert key1 != key2

    def test_cache_key_includes_max_tokens(self) -> None:
        """Test that max_tokens affects cache key."""
        key1 = generate_cache_key("system", "user", "model", max_tokens=1000)
        key2 = generate_cache_key("system", "user", "model", max_tokens=2000)
        assert key1 != key2

    def test_cache_key_format(self) -> None:
        """Test cache key has expected format."""
        key = generate_cache_key("system", "user", "model")
        assert key.startswith("llm:cache:")
        assert len(key) == 10 + 16  # "llm:cache:" + 16 hex chars


@pytest.mark.integration
class TestLLMResponseCache:
    """Test LLM response cache with Redis backend."""

    @pytest.fixture
    def mock_redis_manager(self) -> object:
        """Create a mock Redis manager for testing."""
        from unittest.mock import MagicMock

        manager = MagicMock()
        manager.redis = MagicMock()
        return manager

    @pytest.fixture
    def cache(self, mock_redis_manager: object) -> LLMResponseCache:
        """Create cache instance with mock Redis."""
        from unittest.mock import MagicMock, patch

        with patch("bo1.llm.cache.get_settings") as mock_settings:
            # Create mock cache config with proper attribute access
            mock_cache_config = MagicMock()
            mock_cache_config.llm_cache_enabled = True
            mock_cache_config.llm_cache_ttl_seconds = 3600

            # Set up settings mock to return the cache config
            mock_settings_instance = MagicMock()
            mock_settings_instance.cache = mock_cache_config
            mock_settings.return_value = mock_settings_instance

            return LLMResponseCache(mock_redis_manager)

    @pytest.fixture
    def sample_request(self) -> PromptRequest:
        """Create sample prompt request."""
        return PromptRequest(
            system="test system",
            user_message="test message",
            model="claude-sonnet-4.5",
            max_tokens=1000,
        )

    @pytest.fixture
    def sample_response(self) -> LLMResponse:
        """Create sample LLM response."""
        return LLMResponse(
            content="test response",
            model="claude-sonnet-4-5-20250929",
            token_usage=TokenUsage(
                input_tokens=100,
                output_tokens=50,
                cache_creation_tokens=0,
                cache_read_tokens=0,
            ),
            duration_ms=1000,
            retry_count=0,
        )

    @pytest.mark.asyncio
    async def test_cache_hit(
        self,
        cache: LLMResponseCache,
        sample_request: PromptRequest,
        sample_response: LLMResponse,
    ) -> None:
        """Test cache hit returns cached response."""
        # Setup mock to return cached data
        cache.redis.get.return_value = sample_response.model_dump_json()

        # Get cached response (using get() method)
        cached = await cache.get(sample_request)

        # Verify
        assert cached is not None
        assert cached.content == "test response"
        assert cache.hit_rate == 1.0
        assert cache._hits == 1
        assert cache._misses == 0

    @pytest.mark.asyncio
    async def test_cache_miss(
        self,
        cache: LLMResponseCache,
        sample_request: PromptRequest,
    ) -> None:
        """Test cache miss returns None."""
        # Setup mock to return no data
        cache.redis.get.return_value = None

        # Get cached response (using get() method)
        cached = await cache.get(sample_request)

        # Verify
        assert cached is None
        assert cache.hit_rate == 0.0
        assert cache._hits == 0
        assert cache._misses == 1

    @pytest.mark.asyncio
    async def test_cache_response(
        self,
        cache: LLMResponseCache,
        sample_request: PromptRequest,
        sample_response: LLMResponse,
    ) -> None:
        """Test caching response stores in Redis with TTL."""
        # Cache response (using set() method)
        await cache.set(sample_request, sample_response)

        # Verify setex was called with correct parameters
        cache.redis.setex.assert_called_once()
        call_args = cache.redis.setex.call_args

        # Check TTL
        assert call_args[0][1] == 3600  # TTL in seconds

        # Check data is JSON
        assert "test response" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_cache_disabled(
        self,
        mock_redis_manager: object,
        sample_request: PromptRequest,
    ) -> None:
        """Test cache is bypassed when disabled."""
        from unittest.mock import MagicMock, patch

        with patch("bo1.llm.cache.get_settings") as mock_settings:
            # Create mock cache config with cache disabled
            mock_cache_config = MagicMock()
            mock_cache_config.llm_cache_enabled = False
            mock_cache_config.llm_cache_ttl_seconds = 3600

            # Set up settings mock to return the cache config
            mock_settings_instance = MagicMock()
            mock_settings_instance.cache = mock_cache_config
            mock_settings.return_value = mock_settings_instance

            cache = LLMResponseCache(mock_redis_manager)

            # Get should return None without checking Redis (using get() method)
            cached = await cache.get(sample_request)
            assert cached is None
            cache.redis.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_read_error_graceful(
        self,
        cache: LLMResponseCache,
        sample_request: PromptRequest,
    ) -> None:
        """Test cache read errors don't break execution."""
        # Setup mock to raise error
        cache.redis.get.side_effect = Exception("Redis connection failed")

        # Get should return None (cache miss) (using get() method)
        cached = await cache.get(sample_request)
        assert cached is None
        assert cache._misses == 1

    @pytest.mark.asyncio
    async def test_cache_write_error_graceful(
        self,
        cache: LLMResponseCache,
        sample_request: PromptRequest,
        sample_response: LLMResponse,
    ) -> None:
        """Test cache write errors don't break execution."""
        # Setup mock to raise error
        cache.redis.setex.side_effect = Exception("Redis connection failed")

        # Cache should not raise exception (using set() method)
        await cache.set(sample_request, sample_response)
        # No assertion needed - just verify no exception raised

    def test_hit_rate_calculation(self, cache: LLMResponseCache) -> None:
        """Test hit rate calculation is correct."""
        # Initially 0
        assert cache.hit_rate == 0.0

        # After 2 hits, 1 miss
        cache._hits = 2
        cache._misses = 1
        assert cache.hit_rate == 2 / 3

        # After 10 hits, 0 misses
        cache._hits = 10
        cache._misses = 0
        assert cache.hit_rate == 1.0

    def test_get_stats(self, cache: LLMResponseCache) -> None:
        """Test statistics collection."""
        cache._hits = 6
        cache._misses = 4

        stats = cache.get_stats()

        assert stats["enabled"] is True
        assert stats["hits"] == 6
        assert stats["misses"] == 4
        assert stats["hit_rate"] == 0.6
        assert stats["ttl_seconds"] == 3600


class TestCacheSingleton:
    """Test global cache instance management."""

    def test_get_llm_cache_singleton(self) -> None:
        """Test that get_llm_cache returns singleton instance."""
        from unittest.mock import MagicMock, patch

        # Reset global cache instance for clean test
        import bo1.llm.cache

        bo1.llm.cache._cache_instance = None

        mock_redis_manager = MagicMock()
        with patch("bo1.state.redis_manager.RedisManager", return_value=mock_redis_manager):
            with patch("bo1.llm.cache.get_settings") as mock_settings:
                # Create mock cache config with proper attribute access
                mock_cache_config = MagicMock()
                mock_cache_config.llm_cache_enabled = True
                mock_cache_config.llm_cache_ttl_seconds = 3600

                # Set up settings mock to return the cache config
                mock_settings_instance = MagicMock()
                mock_settings_instance.cache = mock_cache_config
                mock_settings.return_value = mock_settings_instance

                cache1 = get_llm_cache()
                cache2 = get_llm_cache()

                # Should be same instance
                assert cache1 is cache2

        # Reset after test
        bo1.llm.cache._cache_instance = None
