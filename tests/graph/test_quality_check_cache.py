"""Unit tests for quality check cache."""

import pytest

from bo1.graph.quality.contribution_check import (
    QualityCheckCache,
    QualityCheckResult,
)


class TestQualityCheckCache:
    """Tests for QualityCheckCache class."""

    @pytest.fixture
    def cache(self) -> QualityCheckCache:
        """Fresh cache instance."""
        return QualityCheckCache()

    @pytest.fixture
    def sample_result(self) -> QualityCheckResult:
        """Sample quality check result."""
        return QualityCheckResult(
            is_shallow=False,
            weak_aspects=["evidence"],
            quality_score=0.65,
            feedback="Good contribution, add more evidence",
            specificity_score=0.7,
            evidence_score=0.5,
            actionability_score=0.75,
        )

    def test_cache_miss_returns_none(self, cache: QualityCheckCache):
        """Cache miss should return None and increment miss counter."""
        result = cache.get("new content", "problem context")

        assert result is None
        assert cache.stats["misses"] == 1
        assert cache.stats["hits"] == 0

    def test_cache_hit_returns_result(
        self, cache: QualityCheckCache, sample_result: QualityCheckResult
    ):
        """Cache hit should return stored result."""
        content = "We should focus on enterprise customers."
        context = "Should we expand our sales strategy?"

        # Store result
        cache.put(content, context, sample_result, round_number=1)

        # Retrieve - should hit
        result = cache.get(content, context)

        assert result is not None
        assert result.quality_score == sample_result.quality_score
        assert result.is_shallow == sample_result.is_shallow
        assert cache.stats["hits"] == 1

    def test_different_content_different_keys(
        self, cache: QualityCheckCache, sample_result: QualityCheckResult
    ):
        """Different content should produce different cache keys."""
        context = "Problem context"

        # Store for content A
        cache.put("Content A", context, sample_result, round_number=1)

        # Retrieve for content B - should miss
        result = cache.get("Content B", context)

        assert result is None
        assert cache.stats["misses"] == 1

    def test_different_context_different_keys(
        self, cache: QualityCheckCache, sample_result: QualityCheckResult
    ):
        """Different problem context should produce different cache keys."""
        content = "Same contribution content"

        # Store with context A
        cache.put(content, "Context A", sample_result, round_number=1)

        # Retrieve with context B - should miss
        result = cache.get(content, "Context B")

        assert result is None
        assert cache.stats["misses"] == 1

    def test_invalidate_before_round(
        self, cache: QualityCheckCache, sample_result: QualityCheckResult
    ):
        """invalidate_before_round should remove old entries."""
        context = "Problem context"

        # Store entries from rounds 1, 2, 3
        cache.put("Content round 1", context, sample_result, round_number=1)
        cache.put("Content round 2", context, sample_result, round_number=2)
        cache.put("Content round 3", context, sample_result, round_number=3)

        assert cache.stats["size"] == 3

        # Invalidate rounds < 3
        removed = cache.invalidate_before_round(round_number=3)

        assert removed == 2
        assert cache.stats["size"] == 1

        # Round 3 entry should still be accessible
        result = cache.get("Content round 3", context)
        assert result is not None

        # Round 1 and 2 entries should be gone
        assert cache.get("Content round 1", context) is None
        assert cache.get("Content round 2", context) is None

    def test_clear(self, cache: QualityCheckCache, sample_result: QualityCheckResult):
        """clear() should remove all entries."""
        cache.put("Content 1", "Context", sample_result, round_number=1)
        cache.put("Content 2", "Context", sample_result, round_number=2)

        assert cache.stats["size"] == 2

        cache.clear()

        assert cache.stats["size"] == 0

    def test_stats_tracking(self, cache: QualityCheckCache, sample_result: QualityCheckResult):
        """Stats should accurately track hits, misses, and size."""
        context = "Context"

        # 2 misses
        cache.get("Miss 1", context)
        cache.get("Miss 2", context)

        # Store 2 entries
        cache.put("Content 1", context, sample_result, round_number=1)
        cache.put("Content 2", context, sample_result, round_number=1)

        # 2 hits
        cache.get("Content 1", context)
        cache.get("Content 2", context)

        stats = cache.stats
        assert stats["size"] == 2
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 0.5

    def test_whitespace_normalization(
        self, cache: QualityCheckCache, sample_result: QualityCheckResult
    ):
        """Content with leading/trailing whitespace should match."""
        context = "Context"

        # Store with extra whitespace
        cache.put("  Content with spaces  ", context, sample_result, round_number=1)

        # Retrieve with different whitespace - should hit due to strip()
        result = cache.get("Content with spaces", context)

        assert result is not None
