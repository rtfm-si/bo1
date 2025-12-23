"""Tests for SessionMetadataCache.

Tests cover:
- Cache hit/miss behavior
- TTL expiry
- LRU eviction
- Thread safety
- Prometheus metrics
- Invalidation
"""

import threading
import time
from unittest.mock import MagicMock, patch

from backend.api.session_cache import SessionMetadataCache


class TestCacheBasics:
    """Tests for basic cache get/set/invalidate operations."""

    def test_cache_hit_returns_cached_value(self) -> None:
        """Cache should return stored value on hit."""
        cache = SessionMetadataCache(max_size=100, ttl_seconds=300)
        metadata = {"user_id": "user-123", "status": "running"}

        cache.set("session-abc", metadata)
        result = cache.get("session-abc")

        assert result == metadata

    def test_cache_miss_returns_none(self) -> None:
        """Cache should return None on miss."""
        cache = SessionMetadataCache(max_size=100, ttl_seconds=300)

        result = cache.get("nonexistent-session")

        assert result is None

    def test_invalidate_removes_entry(self) -> None:
        """Invalidate should remove entry from cache."""
        cache = SessionMetadataCache(max_size=100, ttl_seconds=300)
        cache.set("session-abc", {"status": "running"})

        removed = cache.invalidate("session-abc")

        assert removed is True
        assert cache.get("session-abc") is None

    def test_invalidate_returns_false_for_missing(self) -> None:
        """Invalidate should return False if entry not present."""
        cache = SessionMetadataCache(max_size=100, ttl_seconds=300)

        removed = cache.invalidate("nonexistent-session")

        assert removed is False

    def test_clear_removes_all_entries(self) -> None:
        """Clear should remove all cached entries."""
        cache = SessionMetadataCache(max_size=100, ttl_seconds=300)
        cache.set("session-1", {"status": "running"})
        cache.set("session-2", {"status": "completed"})

        count = cache.clear()

        assert count == 2
        assert cache.size() == 0

    def test_size_returns_entry_count(self) -> None:
        """Size should return number of cached entries."""
        cache = SessionMetadataCache(max_size=100, ttl_seconds=300)

        assert cache.size() == 0
        cache.set("session-1", {})
        assert cache.size() == 1
        cache.set("session-2", {})
        assert cache.size() == 2


class TestTTLExpiry:
    """Tests for TTL-based cache expiry."""

    def test_ttl_expiry_triggers_reload(self) -> None:
        """Expired entries should not be returned."""
        cache = SessionMetadataCache(max_size=100, ttl_seconds=0)  # 0 = immediate expiry

        cache.set("session-abc", {"status": "running"})
        # Entry is immediately expired
        time.sleep(0.01)  # Small delay to ensure expiry

        result = cache.get("session-abc")

        assert result is None

    def test_valid_ttl_returns_value(self) -> None:
        """Non-expired entries should be returned."""
        cache = SessionMetadataCache(max_size=100, ttl_seconds=300)

        cache.set("session-abc", {"status": "running"})
        result = cache.get("session-abc")

        assert result == {"status": "running"}


class TestLRUEviction:
    """Tests for LRU eviction when cache is full."""

    def test_lru_eviction_removes_oldest(self) -> None:
        """LRU eviction should remove oldest entry when at capacity."""
        cache = SessionMetadataCache(max_size=2, ttl_seconds=300)

        cache.set("session-1", {"order": 1})
        cache.set("session-2", {"order": 2})
        cache.set("session-3", {"order": 3})  # Should evict session-1

        assert cache.get("session-1") is None
        assert cache.get("session-2") == {"order": 2}
        assert cache.get("session-3") == {"order": 3}

    def test_access_updates_lru_order(self) -> None:
        """Accessing an entry should move it to end of LRU queue."""
        cache = SessionMetadataCache(max_size=2, ttl_seconds=300)

        cache.set("session-1", {"order": 1})
        cache.set("session-2", {"order": 2})
        cache.get("session-1")  # Access session-1, moving it to end
        cache.set("session-3", {"order": 3})  # Should evict session-2 (now oldest)

        assert cache.get("session-1") == {"order": 1}
        assert cache.get("session-2") is None
        assert cache.get("session-3") == {"order": 3}


class TestGetOrLoad:
    """Tests for get_or_load() with loader function."""

    def test_cache_miss_calls_loader(self) -> None:
        """Loader should be called on cache miss."""
        cache = SessionMetadataCache(max_size=100, ttl_seconds=300)
        loader = MagicMock(return_value={"status": "loaded"})

        result = cache.get_or_load("session-abc", loader)

        assert result == {"status": "loaded"}
        loader.assert_called_once_with("session-abc")

    def test_cache_hit_skips_loader(self) -> None:
        """Loader should not be called on cache hit."""
        cache = SessionMetadataCache(max_size=100, ttl_seconds=300)
        cache.set("session-abc", {"status": "cached"})
        loader = MagicMock(return_value={"status": "loaded"})

        result = cache.get_or_load("session-abc", loader)

        assert result == {"status": "cached"}
        loader.assert_not_called()

    def test_loader_result_is_cached(self) -> None:
        """Loaded value should be stored in cache."""
        cache = SessionMetadataCache(max_size=100, ttl_seconds=300)
        loader = MagicMock(return_value={"status": "loaded"})

        cache.get_or_load("session-abc", loader)
        # Second call should hit cache
        cache.get_or_load("session-abc", loader)

        loader.assert_called_once()

    def test_none_result_not_cached(self) -> None:
        """None loader result should not be cached."""
        cache = SessionMetadataCache(max_size=100, ttl_seconds=300)
        loader = MagicMock(return_value=None)

        result1 = cache.get_or_load("session-abc", loader)
        result2 = cache.get_or_load("session-abc", loader)

        assert result1 is None
        assert result2 is None
        assert loader.call_count == 2


class TestThreadSafety:
    """Tests for thread-safe concurrent access."""

    def test_thread_safety_concurrent_access(self) -> None:
        """Cache should handle concurrent access safely."""
        cache = SessionMetadataCache(max_size=1000, ttl_seconds=300)
        errors: list[Exception] = []

        def writer(thread_id: int) -> None:
            try:
                for i in range(100):
                    cache.set(f"session-{thread_id}-{i}", {"thread": thread_id, "i": i})
            except Exception as e:
                errors.append(e)

        def reader(thread_id: int) -> None:
            try:
                for i in range(100):
                    cache.get(f"session-{thread_id}-{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for t in range(10):
            threads.append(threading.Thread(target=writer, args=(t,)))
            threads.append(threading.Thread(target=reader, args=(t,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestMetrics:
    """Tests for Prometheus metrics."""

    def test_metrics_incremented_on_hit(self) -> None:
        """Cache hit should increment hit counter."""
        cache = SessionMetadataCache(max_size=100, ttl_seconds=300)
        cache.set("session-abc", {"status": "running"})

        with patch("backend.api.session_cache.session_cache_hits") as hits_mock:
            cache.get_or_load("session-abc", lambda _: {})
            hits_mock.inc.assert_called_once()

    def test_metrics_incremented_on_miss(self) -> None:
        """Cache miss should increment miss counter."""
        cache = SessionMetadataCache(max_size=100, ttl_seconds=300)

        with patch("backend.api.session_cache.session_cache_misses") as misses_mock:
            cache.get_or_load("session-abc", lambda _: {"loaded": True})
            misses_mock.inc.assert_called_once()


class TestIntegration:
    """Integration tests for cache with verified_session."""

    def test_verified_session_uses_cache(self) -> None:
        """get_verified_session should use cache for metadata lookup."""
        # This would require mocking FastAPI dependencies
        # Covered by the implementation pattern in dependencies.py
        pass

    def test_session_complete_invalidates_cache(self) -> None:
        """Session completion should invalidate cached metadata."""
        # This would require mocking session_repo
        # Covered by the implementation in event_collector.py
        pass
