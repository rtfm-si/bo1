"""Tests for benchmark value timestamp tracking.

Verifies:
- Setting a metric value records timestamp
- Unchanged value doesn't update timestamp
- Multiple metrics tracked independently
- Timestamps included in API response
"""

from datetime import UTC, datetime

from backend.api.context.services import (
    BENCHMARK_METRIC_FIELDS,
    update_benchmark_timestamps,
)


class TestUpdateBenchmarkTimestamps:
    """Tests for update_benchmark_timestamps function."""

    def test_setting_new_metric_records_timestamp(self):
        """Setting a metric value for the first time records timestamp."""
        new_context = {"revenue": "50000"}
        existing_context = None

        result = update_benchmark_timestamps(new_context, existing_context)

        assert "revenue" in result
        # Timestamp should be a valid ISO format string
        ts = datetime.fromisoformat(result["revenue"].replace("Z", "+00:00"))
        assert ts.date() == datetime.now(UTC).date()

    def test_unchanged_value_keeps_existing_timestamp(self):
        """Unchanged value doesn't update timestamp."""
        old_timestamp = "2025-01-01T12:00:00+00:00"
        new_context = {"revenue": "50000"}
        existing_context = {
            "revenue": "50000",
            "benchmark_timestamps": {"revenue": old_timestamp},
        }

        result = update_benchmark_timestamps(new_context, existing_context)

        # Should keep the existing timestamp
        assert result["revenue"] == old_timestamp

    def test_changed_value_updates_timestamp(self):
        """Changed value updates timestamp."""
        old_timestamp = "2025-01-01T12:00:00+00:00"
        new_context = {"revenue": "75000"}  # Changed from 50000
        existing_context = {
            "revenue": "50000",
            "benchmark_timestamps": {"revenue": old_timestamp},
        }

        result = update_benchmark_timestamps(new_context, existing_context)

        # Should have a new timestamp
        assert result["revenue"] != old_timestamp
        ts = datetime.fromisoformat(result["revenue"].replace("Z", "+00:00"))
        assert ts.date() == datetime.now(UTC).date()

    def test_multiple_metrics_tracked_independently(self):
        """Multiple metrics tracked independently."""
        old_timestamp = "2025-01-01T12:00:00+00:00"
        new_context = {
            "revenue": "75000",  # Changed
            "customers": "100",  # Unchanged
            "growth_rate": "15",  # New
        }
        existing_context = {
            "revenue": "50000",
            "customers": "100",
            "benchmark_timestamps": {
                "revenue": old_timestamp,
                "customers": old_timestamp,
            },
        }

        result = update_benchmark_timestamps(new_context, existing_context)

        # revenue: changed → new timestamp
        assert result["revenue"] != old_timestamp

        # customers: unchanged → keep old timestamp
        assert result["customers"] == old_timestamp

        # growth_rate: new → new timestamp
        assert "growth_rate" in result
        ts = datetime.fromisoformat(result["growth_rate"].replace("Z", "+00:00"))
        assert ts.date() == datetime.now(UTC).date()

    def test_empty_value_not_tracked(self):
        """Empty or null values don't get tracked."""
        new_context = {"revenue": "", "customers": None}
        existing_context = None

        result = update_benchmark_timestamps(new_context, existing_context)

        assert "revenue" not in result
        assert "customers" not in result

    def test_non_benchmark_fields_ignored(self):
        """Non-benchmark fields are not tracked."""
        new_context = {
            "business_model": "SaaS",  # Not a benchmark metric
            "industry": "Technology",  # Not a benchmark metric
            "revenue": "50000",  # This is a benchmark metric
        }
        existing_context = None

        result = update_benchmark_timestamps(new_context, existing_context)

        # Only revenue should be tracked
        assert "revenue" in result
        assert "business_model" not in result
        assert "industry" not in result

    def test_preserves_existing_timestamps_for_unmodified_fields(self):
        """Existing timestamps for unmodified fields are preserved."""
        old_timestamps = {
            "revenue": "2025-01-01T12:00:00+00:00",
            "customers": "2025-01-02T12:00:00+00:00",
            "team_size": "2025-01-03T12:00:00+00:00",
        }
        new_context = {"revenue": "75000"}  # Only changing revenue
        existing_context = {
            "revenue": "50000",
            "customers": "100",
            "team_size": "10",
            "benchmark_timestamps": old_timestamps,
        }

        result = update_benchmark_timestamps(new_context, existing_context)

        # revenue: changed → new timestamp
        assert result["revenue"] != old_timestamps["revenue"]

        # customers and team_size: not in new_context but should keep timestamps
        assert result["customers"] == old_timestamps["customers"]
        assert result["team_size"] == old_timestamps["team_size"]


class TestBenchmarkMetricFields:
    """Tests for BENCHMARK_METRIC_FIELDS constant."""

    def test_expected_fields_present(self):
        """Expected benchmark fields are present."""
        expected = {
            "revenue",
            "customers",
            "growth_rate",
            "team_size",
            "mau_bucket",
            "revenue_stage",
            "traffic_range",
            # Extended metrics (z25 migration)
            "dau",
            "mau",
            "dau_mau_ratio",
            "arpu",
            "arr_growth_rate",
            "grr",
            "active_churn",
            "revenue_churn",
            "nps",
            "quick_ratio",
        }
        assert expected == BENCHMARK_METRIC_FIELDS

    def test_is_frozen_set(self):
        """BENCHMARK_METRIC_FIELDS is immutable."""
        assert isinstance(BENCHMARK_METRIC_FIELDS, frozenset)


class TestContextDataToModel:
    """Tests for context_data_to_model including benchmark_timestamps."""

    def test_includes_benchmark_timestamps(self):
        """context_data_to_model includes benchmark_timestamps."""
        from backend.api.context.services import context_data_to_model

        timestamps = {
            "revenue": "2025-01-01T00:00:00+00:00",
            "customers": "2025-01-02T00:00:00+00:00",
        }
        context_data = {
            "revenue": "50000",
            "customers": "100",
            "benchmark_timestamps": timestamps,
        }

        result = context_data_to_model(context_data)

        # Pydantic parses ISO strings to datetime objects
        assert result.benchmark_timestamps is not None
        assert "revenue" in result.benchmark_timestamps
        assert "customers" in result.benchmark_timestamps
        # Check the values are datetime objects with correct dates
        assert result.benchmark_timestamps["revenue"].year == 2025
        assert result.benchmark_timestamps["revenue"].month == 1
        assert result.benchmark_timestamps["revenue"].day == 1

    def test_handles_missing_benchmark_timestamps(self):
        """context_data_to_model handles missing benchmark_timestamps."""
        from backend.api.context.services import context_data_to_model

        context_data = {
            "revenue": "50000",
            "customers": "100",
        }

        result = context_data_to_model(context_data)

        assert result.benchmark_timestamps is None


class TestContextModelToDict:
    """Tests for context_model_to_dict including benchmark_timestamps."""

    def test_includes_benchmark_timestamps(self):
        """context_model_to_dict includes benchmark_timestamps."""
        from backend.api.context.models import BusinessContext
        from backend.api.context.services import context_model_to_dict

        timestamps = {
            "revenue": datetime(2025, 1, 1, tzinfo=UTC),
            "customers": datetime(2025, 1, 2, tzinfo=UTC),
        }
        context = BusinessContext(
            revenue="50000",
            customers="100",
            benchmark_timestamps=timestamps,
        )

        result = context_model_to_dict(context)

        # Should have the timestamps dict
        assert result["benchmark_timestamps"] is not None
        assert "revenue" in result["benchmark_timestamps"]
        assert "customers" in result["benchmark_timestamps"]

    def test_handles_none_benchmark_timestamps(self):
        """context_model_to_dict handles None benchmark_timestamps."""
        from backend.api.context.models import BusinessContext
        from backend.api.context.services import context_model_to_dict

        context = BusinessContext(revenue="50000", customers="100")

        result = context_model_to_dict(context)

        assert result["benchmark_timestamps"] is None
