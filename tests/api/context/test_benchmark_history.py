"""Tests for benchmark history tracking.

Verifies:
- History appended when benchmark values change
- History trimmed to max 6 entries per metric
- Same-day updates replace rather than append
- API returns history in comparison response
- Stale benchmark detection works correctly
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from backend.api.context.services import (
    MAX_BENCHMARK_HISTORY_ENTRIES,
    append_benchmark_history,
)


class TestAppendBenchmarkHistory:
    """Tests for append_benchmark_history function."""

    def test_setting_new_metric_appends_to_history(self):
        """Setting a new metric value creates history entry."""
        new_context = {"revenue": 50000}
        existing_context = None

        result = append_benchmark_history(new_context, existing_context)

        assert "revenue" in result
        assert len(result["revenue"]) == 1
        assert result["revenue"][0]["value"] == 50000
        assert result["revenue"][0]["date"] == datetime.now(UTC).strftime("%Y-%m-%d")

    def test_unchanged_value_no_new_entry(self):
        """Unchanged value doesn't append to history."""
        new_context = {"revenue": 50000}
        existing_context = {
            "revenue": 50000,  # Same value
            "benchmark_history": {"revenue": [{"value": 50000, "date": "2025-01-01"}]},
        }

        result = append_benchmark_history(new_context, existing_context)

        # Should still have only 1 entry (unchanged)
        assert len(result["revenue"]) == 1
        assert result["revenue"][0]["date"] == "2025-01-01"

    def test_changed_value_appends_to_history(self):
        """Changed value appends new entry to history."""
        new_context = {"revenue": 75000}  # Changed from 50000
        existing_context = {
            "revenue": 50000,
            "benchmark_history": {"revenue": [{"value": 50000, "date": "2025-01-01"}]},
        }

        result = append_benchmark_history(new_context, existing_context)

        # Should have 2 entries now, newest first
        assert len(result["revenue"]) == 2
        assert result["revenue"][0]["value"] == 75000  # New value first
        assert result["revenue"][1]["value"] == 50000  # Old value second

    def test_same_day_update_replaces_entry(self):
        """Multiple updates on same day replace rather than append."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        new_context = {"revenue": 80000}  # Third value today
        existing_context = {
            "revenue": 75000,
            "benchmark_history": {
                "revenue": [
                    {"value": 75000, "date": today},  # Already recorded today
                    {"value": 50000, "date": "2025-01-01"},
                ]
            },
        }

        result = append_benchmark_history(new_context, existing_context)

        # Should still have 2 entries, but today's value updated
        assert len(result["revenue"]) == 2
        assert result["revenue"][0]["value"] == 80000  # Updated to newest
        assert result["revenue"][0]["date"] == today
        assert result["revenue"][1]["value"] == 50000

    def test_history_trimmed_to_max_entries(self):
        """History trimmed to MAX_BENCHMARK_HISTORY_ENTRIES (6)."""
        yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        new_context = {"revenue": 100000}  # New value
        existing_context = {
            "revenue": 95000,
            "benchmark_history": {
                "revenue": [
                    {"value": 95000, "date": yesterday},
                    {"value": 90000, "date": "2025-06-01"},
                    {"value": 85000, "date": "2025-05-01"},
                    {"value": 80000, "date": "2025-04-01"},
                    {"value": 75000, "date": "2025-03-01"},
                    {"value": 70000, "date": "2025-02-01"},  # 6th entry, will be dropped
                ]
            },
        }

        result = append_benchmark_history(new_context, existing_context)

        # Should have exactly 6 entries (max)
        assert len(result["revenue"]) == MAX_BENCHMARK_HISTORY_ENTRIES
        # Newest first
        assert result["revenue"][0]["value"] == 100000
        # Oldest (70000) should be dropped
        assert 70000 not in [e["value"] for e in result["revenue"]]

    def test_multiple_metrics_tracked_independently(self):
        """Multiple metrics tracked independently."""
        new_context = {
            "revenue": 75000,  # Changed
            "customers": 100,  # Unchanged
            "growth_rate": 15,  # New metric
        }
        existing_context = {
            "revenue": 50000,
            "customers": 100,
            "benchmark_history": {
                "revenue": [{"value": 50000, "date": "2025-01-01"}],
                "customers": [{"value": 100, "date": "2025-01-01"}],
            },
        }

        result = append_benchmark_history(new_context, existing_context)

        # revenue: changed → new entry
        assert len(result["revenue"]) == 2

        # customers: unchanged → no new entry
        assert len(result["customers"]) == 1

        # growth_rate: new → new entry
        assert "growth_rate" in result
        assert len(result["growth_rate"]) == 1
        assert result["growth_rate"][0]["value"] == 15

    def test_empty_value_not_tracked(self):
        """Empty or null values don't get tracked."""
        new_context = {"revenue": "", "customers": None}
        existing_context = None

        result = append_benchmark_history(new_context, existing_context)

        assert "revenue" not in result
        assert "customers" not in result

    def test_preserves_existing_history_for_unmodified_fields(self):
        """Existing history for unmodified fields is preserved."""
        new_context = {"revenue": 75000}  # Only changing revenue
        existing_context = {
            "revenue": 50000,
            "customers": 100,
            "benchmark_history": {
                "revenue": [{"value": 50000, "date": "2025-01-01"}],
                "customers": [{"value": 100, "date": "2025-01-02"}],
            },
        }

        result = append_benchmark_history(new_context, existing_context)

        # revenue: changed → new entry
        assert len(result["revenue"]) == 2

        # customers: not in new_context but should keep existing history
        assert "customers" in result
        assert len(result["customers"]) == 1


class TestGetStaleBenchmarks:
    """Tests for get_stale_benchmarks function."""

    def test_no_context_returns_empty(self):
        """No context returns empty result."""
        from backend.services.insight_staleness import get_stale_benchmarks

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = None
            result = get_stale_benchmarks("user-123")

        assert result.has_stale_benchmarks is False
        assert result.stale_benchmarks == []

    def test_all_benchmarks_fresh(self):
        """All fresh benchmarks return empty result."""
        from backend.services.insight_staleness import get_stale_benchmarks

        recent = datetime.now(UTC).isoformat()
        context = {
            "revenue": 50000,
            "customers": 100,
            "benchmark_timestamps": {
                "revenue": recent,
                "customers": recent,
            },
        }

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = context
            result = get_stale_benchmarks("user-123")

        assert result.has_stale_benchmarks is False
        assert result.stale_benchmarks == []

    def test_stale_benchmarks_detected(self):
        """Stale benchmarks detected correctly."""
        from backend.services.insight_staleness import get_stale_benchmarks

        old_timestamp = (datetime.now(UTC) - timedelta(days=60)).isoformat()
        context = {
            "revenue": 50000,
            "customers": 100,
            "benchmark_timestamps": {
                "revenue": old_timestamp,  # 60 days old = stale
                "customers": datetime.now(UTC).isoformat(),  # Fresh
            },
        }

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = context
            result = get_stale_benchmarks("user-123")

        assert result.has_stale_benchmarks is True
        assert len(result.stale_benchmarks) == 1
        assert result.stale_benchmarks[0].field_name == "revenue"
        assert result.stale_benchmarks[0].days_since_update >= 60

    def test_no_timestamp_treated_as_stale(self):
        """Benchmark without timestamp treated as stale."""
        from backend.services.insight_staleness import get_stale_benchmarks

        context = {
            "revenue": 50000,  # No timestamp
            "benchmark_timestamps": {},
        }

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = context
            result = get_stale_benchmarks("user-123")

        assert result.has_stale_benchmarks is True
        assert len(result.stale_benchmarks) == 1
        assert result.stale_benchmarks[0].field_name == "revenue"
        assert result.stale_benchmarks[0].days_since_update == 999  # Never confirmed

    def test_sorted_by_staleness(self):
        """Stale benchmarks sorted by days_since_update (most stale first)."""
        from backend.services.insight_staleness import get_stale_benchmarks

        context = {
            "revenue": 50000,
            "customers": 100,
            "growth_rate": 15,
            "benchmark_timestamps": {
                "revenue": (datetime.now(UTC) - timedelta(days=60)).isoformat(),  # 60 days
                "customers": (datetime.now(UTC) - timedelta(days=90)).isoformat(),  # 90 days
                "growth_rate": (datetime.now(UTC) - timedelta(days=45)).isoformat(),  # 45 days
            },
        }

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = context
            result = get_stale_benchmarks("user-123")

        assert result.has_stale_benchmarks is True
        # Should be sorted by staleness (most stale first)
        days = [b.days_since_update for b in result.stale_benchmarks]
        assert days == sorted(days, reverse=True)

    def test_display_names_correct(self):
        """Display names are human-friendly."""
        from backend.services.insight_staleness import get_stale_benchmarks

        context = {
            "revenue": 50000,
            "mau_bucket": "10k-50k",
            "benchmark_timestamps": {},  # All stale
        }

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = context
            result = get_stale_benchmarks("user-123")

        names = {b.field_name: b.display_name for b in result.stale_benchmarks}
        assert names.get("revenue") == "Revenue"
        assert names.get("mau_bucket") == "Monthly active users"


class TestMaxBenchmarkHistoryEntries:
    """Tests for MAX_BENCHMARK_HISTORY_ENTRIES constant."""

    def test_max_is_six(self):
        """Max entries is 6."""
        assert MAX_BENCHMARK_HISTORY_ENTRIES == 6
