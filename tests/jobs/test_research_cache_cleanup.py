"""Tests for research cache cleanup job.

Validates:
- cleanup_research_cache runs successfully
- cleanup_research_cache handles empty cache
- cleanup_research_cache emits metrics
- dry_run mode works correctly
"""

from unittest.mock import patch

import pytest


class TestCleanupResearchCache:
    """Test cleanup_research_cache job function."""

    @pytest.fixture
    def mock_cache_repo(self):
        """Create a mock cache repository."""
        with patch("backend.jobs.research_cache_cleanup.cache_repository") as mock_repo:
            mock_repo.delete_stale.return_value = 0
            mock_repo.get_stale.return_value = []
            mock_repo.get_stats.return_value = {"total_cached_results": 100}
            yield mock_repo

    def test_cleanup_runs_successfully(self, mock_cache_repo):
        """Verify cleanup job runs and returns stats."""
        from backend.jobs.research_cache_cleanup import cleanup_research_cache

        # side_effect with [10, 0] means first call returns 10, second returns 0 (stops loop)
        mock_cache_repo.delete_stale.side_effect = [10, 0]

        result = cleanup_research_cache()

        assert result["entries_deleted"] == 10
        assert "run_at" in result
        assert result["dry_run"] is False
        mock_cache_repo.delete_stale.assert_called()

    def test_cleanup_handles_empty_cache(self, mock_cache_repo):
        """Verify cleanup handles empty cache gracefully."""
        from backend.jobs.research_cache_cleanup import cleanup_research_cache

        mock_cache_repo.delete_stale.return_value = 0

        result = cleanup_research_cache()

        assert result["entries_deleted"] == 0
        assert result["iterations"] == 1  # One check that found nothing

    def test_cleanup_dry_run_mode(self, mock_cache_repo):
        """Verify dry_run mode doesn't actually delete."""
        from backend.jobs.research_cache_cleanup import cleanup_research_cache

        mock_cache_repo.get_stale.return_value = [
            {"id": "1", "question": "Test 1"},
            {"id": "2", "question": "Test 2"},
        ]

        result = cleanup_research_cache(dry_run=True)

        assert result["dry_run"] is True
        assert result["entries_deleted"] == 2
        mock_cache_repo.delete_stale.assert_not_called()

    def test_cleanup_respects_custom_ttl(self, mock_cache_repo):
        """Verify custom max_age_days is passed through."""
        from backend.jobs.research_cache_cleanup import cleanup_research_cache

        cleanup_research_cache(max_age_days=30, access_grace_days=3)

        mock_cache_repo.delete_stale.assert_called_with(
            max_age_days=30,
            access_grace_days=3,
        )

    def test_cleanup_uses_default_ttl(self, mock_cache_repo):
        """Verify default TTL from ResearchCacheConfig is used."""
        from backend.jobs.research_cache_cleanup import cleanup_research_cache
        from bo1.constants import ResearchCacheConfig

        cleanup_research_cache()

        call_args = mock_cache_repo.delete_stale.call_args
        assert call_args[1]["max_age_days"] == ResearchCacheConfig.CLEANUP_TTL_DAYS
        assert call_args[1]["access_grace_days"] == ResearchCacheConfig.CLEANUP_ACCESS_GRACE_DAYS

    def test_cleanup_batches_large_deletions(self, mock_cache_repo):
        """Verify cleanup iterates for large caches."""
        from backend.jobs.research_cache_cleanup import cleanup_research_cache

        # Simulate multiple batches needed
        mock_cache_repo.delete_stale.side_effect = [1000, 1000, 500, 0]

        result = cleanup_research_cache()

        assert result["entries_deleted"] == 2500
        assert result["iterations"] == 4
        assert mock_cache_repo.delete_stale.call_count == 4

    def test_cleanup_handles_error(self, mock_cache_repo):
        """Verify cleanup handles errors gracefully."""
        from backend.jobs.research_cache_cleanup import cleanup_research_cache

        mock_cache_repo.delete_stale.side_effect = Exception("Database error")

        result = cleanup_research_cache()

        assert "error" in result
        assert "Database error" in result["error"]

    def test_cleanup_updates_cache_size_metric(self, mock_cache_repo):
        """Verify cache size metric is updated after cleanup."""
        from backend.jobs.research_cache_cleanup import cleanup_research_cache

        mock_cache_repo.get_stats.return_value = {"total_cached_results": 50}

        result = cleanup_research_cache()

        assert result["cache_size_after"] == 50
        mock_cache_repo.get_stats.assert_called_once()


class TestCleanupMetrics:
    """Test Prometheus metrics for cleanup job."""

    def test_metrics_exist(self):
        """Verify required Prometheus metrics are defined."""
        from backend.jobs.research_cache_cleanup import (
            CACHE_SIZE,
            CLEANUP_DELETED,
            CLEANUP_TOTAL,
        )

        assert CLEANUP_TOTAL is not None
        assert CLEANUP_DELETED is not None
        assert CACHE_SIZE is not None

    def test_cleanup_total_has_status_label(self):
        """Verify CLEANUP_TOTAL counter has status label."""
        from backend.jobs.research_cache_cleanup import CLEANUP_TOTAL

        # Counter with labels should have _metrics dict
        assert hasattr(CLEANUP_TOTAL, "_metrics") or hasattr(CLEANUP_TOTAL, "labels")
