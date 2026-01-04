"""Integration tests for insight to metrics migration.

Tests:
- Migration script extracts metrics from clarifications
- Metrics are correctly saved to business_metrics table
- Source attribution is preserved
"""

from datetime import UTC, datetime
from unittest.mock import patch

from backend.scripts.migrate_insights_to_metrics import (
    MigrationStats,
    extract_metrics_from_clarifications,
)


class TestMigrationStats:
    """Test MigrationStats tracking."""

    def test_initial_values_are_zero(self):
        """Stats start at zero."""
        stats = MigrationStats()
        assert stats.users_processed == 0
        assert stats.insights_found == 0
        assert stats.metrics_migrated == 0
        assert stats.skipped_low_confidence == 0
        assert stats.errors == 0

    def test_to_dict_returns_all_fields(self):
        """to_dict includes all stats."""
        stats = MigrationStats()
        stats.users_processed = 5
        stats.metrics_migrated = 10

        result = stats.to_dict()

        assert result["users_processed"] == 5
        assert result["metrics_migrated"] == 10
        assert "skipped_low_confidence" in result
        assert "skipped_no_metric" in result
        assert "skipped_unmappable" in result
        assert "skipped_too_old" in result
        assert "skipped_existing" in result
        assert "errors" in result


class TestExtractMetricsFromClarifications:
    """Test extract_metrics_from_clarifications function."""

    def test_empty_clarifications_returns_empty(self):
        """Empty clarifications returns empty list."""
        result = extract_metrics_from_clarifications({})
        assert result == []

    def test_none_clarifications_returns_empty(self):
        """None clarifications returns empty list."""
        result = extract_metrics_from_clarifications(None)
        assert result == []

    def test_extracts_revenue_metric(self):
        """Extracts revenue metric from clarification."""
        clarifications = {
            "What is your monthly revenue?": {
                "answer": "Our MRR is $25,000",
                "category": "revenue",
                "confidence_score": 0.9,
                "metric": {
                    "value": 25000,
                    "unit": "USD",
                    "metric_type": "MRR",
                },
                "parsed_at": datetime.now(UTC).isoformat(),
            }
        }

        result = extract_metrics_from_clarifications(clarifications)

        assert len(result) == 1
        assert result[0]["metric_key"] == "mrr"
        assert result[0]["value"] == 25000
        assert result[0]["source"] == "clarification"

    def test_extracts_team_metric(self):
        """Extracts team size metric."""
        clarifications = {
            "Team size?": {
                "answer": "10 people",
                "category": "team",
                "confidence_score": 0.85,
                "metric": {"value": 10, "unit": "count"},
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        result = extract_metrics_from_clarifications(clarifications)

        assert len(result) == 1
        assert result[0]["metric_key"] == "team_size"
        assert result[0]["value"] == 10

    def test_skips_low_confidence(self):
        """Skips insights below confidence threshold."""
        stats = MigrationStats()
        clarifications = {
            "Revenue?": {
                "answer": "Maybe $5K?",
                "category": "revenue",
                "confidence_score": 0.4,  # Below 0.6
                "metric": {"value": 5000},
            }
        }

        result = extract_metrics_from_clarifications(clarifications, stats=stats)

        assert len(result) == 0
        assert stats.skipped_low_confidence == 1

    def test_skips_no_metric_data(self):
        """Skips insights without metric data."""
        stats = MigrationStats()
        clarifications = {
            "Competitors?": {
                "answer": "We compete with Acme",
                "category": "competition",
                "confidence_score": 0.8,
                # No metric field
            }
        }

        result = extract_metrics_from_clarifications(clarifications, stats=stats)

        assert len(result) == 0
        assert stats.skipped_no_metric == 1

    def test_skips_uncategorized(self):
        """Skips uncategorized insights."""
        stats = MigrationStats()
        clarifications = {
            "What?": {
                "answer": "Something random",
                "category": "uncategorized",
                "confidence_score": 0.9,
                "metric": {"value": 42},
            }
        }

        result = extract_metrics_from_clarifications(clarifications, stats=stats)

        assert len(result) == 0
        assert stats.skipped_unmappable == 1

    def test_skips_old_insights(self):
        """Skips insights older than max_age_days."""
        stats = MigrationStats()
        old_date = "2020-01-01T00:00:00+00:00"  # Very old
        clarifications = {
            "Revenue?": {
                "answer": "$10K",
                "category": "revenue",
                "confidence_score": 0.9,
                "metric": {"value": 10000},
                "parsed_at": old_date,
            }
        }

        result = extract_metrics_from_clarifications(clarifications, max_age_days=30, stats=stats)

        assert len(result) == 0
        assert stats.skipped_too_old == 1

    def test_handles_legacy_string_format(self):
        """Handles legacy string-only clarification format."""
        stats = MigrationStats()
        clarifications = {
            "Revenue?": "We make $50K",  # Legacy string format
        }

        # Should not crash, but won't extract metrics from legacy format
        result = extract_metrics_from_clarifications(clarifications, stats=stats)
        # Legacy format without category/metric will be skipped
        assert len(result) == 0

    def test_extracts_multiple_metrics(self):
        """Extracts multiple metrics from different clarifications."""
        now = datetime.now(UTC).isoformat()
        clarifications = {
            "MRR?": {
                "answer": "$25K",
                "category": "revenue",
                "confidence_score": 0.9,
                "metric": {"value": 25000, "unit": "USD"},
                "parsed_at": now,
            },
            "Team?": {
                "answer": "10 people",
                "category": "team",
                "confidence_score": 0.85,
                "metric": {"value": 10, "unit": "count"},
                "parsed_at": now,
            },
            "Growth?": {
                "answer": "15%",
                "category": "growth",
                "confidence_score": 0.8,
                "metric": {"value": 15, "unit": "%"},
                "parsed_at": now,
            },
        }

        result = extract_metrics_from_clarifications(clarifications)

        assert len(result) == 3
        metric_keys = {m["metric_key"] for m in result}
        assert "mrr" in metric_keys
        assert "team_size" in metric_keys
        assert "growth_rate" in metric_keys

    def test_tracks_all_stats(self):
        """Tracks all statistics correctly."""
        stats = MigrationStats()
        now = datetime.now(UTC).isoformat()
        old = "2020-01-01T00:00:00+00:00"

        clarifications = {
            # Should extract
            "Revenue?": {
                "answer": "$25K",
                "category": "revenue",
                "confidence_score": 0.9,
                "metric": {"value": 25000},
                "parsed_at": now,
            },
            # Low confidence
            "Maybe revenue?": {
                "answer": "Unsure",
                "category": "revenue",
                "confidence_score": 0.3,
                "metric": {"value": 1000},
            },
            # No metric
            "Competitors?": {
                "answer": "Acme",
                "category": "competition",
                "confidence_score": 0.9,
            },
            # Too old
            "Old data": {
                "answer": "$1K",
                "category": "revenue",
                "confidence_score": 0.9,
                "metric": {"value": 1000},
                "parsed_at": old,
            },
            # Uncategorized
            "Random": {
                "answer": "42",
                "category": "uncategorized",
                "confidence_score": 0.9,
                "metric": {"value": 42},
            },
        }

        result = extract_metrics_from_clarifications(clarifications, max_age_days=30, stats=stats)

        assert stats.insights_found == 5
        assert len(result) == 1  # Only the valid revenue one
        assert stats.skipped_low_confidence == 1
        assert stats.skipped_no_metric == 1
        assert stats.skipped_too_old == 1
        assert stats.skipped_unmappable == 1


class TestMigrationIntegration:
    """Integration tests with database (mocked)."""

    @patch("backend.scripts.migrate_insights_to_metrics.metrics_repository")
    def test_migrate_user_metrics_saves_to_repository(self, mock_repo):
        """Test that metrics are saved to repository."""
        from backend.scripts.migrate_insights_to_metrics import migrate_user_metrics

        metrics = [
            {
                "metric_key": "mrr",
                "name": "Monthly Recurring Revenue",
                "value": 25000,
                "value_unit": "USD",
                "captured_at": datetime.now(UTC),
                "source": "clarification",
                "is_predefined": False,
            }
        ]

        mock_repo.get_user_metric.return_value = None  # No existing metric
        mock_repo.save_metric.return_value = {"id": "test-id"}

        migrated = migrate_user_metrics(
            user_id="user-123",
            metrics=metrics,
            dry_run=False,
        )

        assert migrated == 1
        mock_repo.save_metric.assert_called_once()
        call_kwargs = mock_repo.save_metric.call_args[1]
        assert call_kwargs["user_id"] == "user-123"
        assert call_kwargs["metric_key"] == "mrr"
        assert call_kwargs["value"] == 25000
        assert call_kwargs["source"] == "clarification"

    @patch("backend.scripts.migrate_insights_to_metrics.metrics_repository")
    def test_migrate_skips_existing_manual_metrics(self, mock_repo):
        """Test that existing manual metrics are not overwritten."""
        from backend.scripts.migrate_insights_to_metrics import migrate_user_metrics

        stats = MigrationStats()
        metrics = [
            {
                "metric_key": "mrr",
                "name": "Monthly Recurring Revenue",
                "value": 25000,
                "value_unit": "USD",
                "captured_at": datetime.now(UTC),
                "source": "clarification",
                "is_predefined": False,
            }
        ]

        # Existing manual metric
        mock_repo.get_user_metric.return_value = {
            "metric_key": "mrr",
            "value": 30000,
            "source": "manual",
        }

        migrated = migrate_user_metrics(
            user_id="user-123",
            metrics=metrics,
            force=False,  # Don't overwrite
            dry_run=False,
            stats=stats,
        )

        assert migrated == 0
        assert stats.skipped_existing == 1
        mock_repo.save_metric.assert_not_called()

    @patch("backend.scripts.migrate_insights_to_metrics.metrics_repository")
    def test_migrate_force_overwrites_existing(self, mock_repo):
        """Test that --force overwrites existing metrics."""
        from backend.scripts.migrate_insights_to_metrics import migrate_user_metrics

        metrics = [
            {
                "metric_key": "mrr",
                "name": "Monthly Recurring Revenue",
                "value": 25000,
                "value_unit": "USD",
                "captured_at": datetime.now(UTC),
                "source": "clarification",
                "is_predefined": False,
            }
        ]

        mock_repo.get_user_metric.return_value = {"source": "manual"}
        mock_repo.save_metric.return_value = {"id": "test-id"}

        migrated = migrate_user_metrics(
            user_id="user-123",
            metrics=metrics,
            force=True,  # Overwrite
            dry_run=False,
        )

        assert migrated == 1
        mock_repo.save_metric.assert_called_once()

    def test_dry_run_does_not_save(self):
        """Test that dry run doesn't save anything."""
        from backend.scripts.migrate_insights_to_metrics import migrate_user_metrics

        metrics = [
            {
                "metric_key": "mrr",
                "name": "MRR",
                "value": 25000,
            }
        ]

        with patch("backend.scripts.migrate_insights_to_metrics.metrics_repository") as mock_repo:
            migrated = migrate_user_metrics(
                user_id="user-123",
                metrics=metrics,
                dry_run=True,
            )

            # Should count as migrated but not actually call save
            assert migrated == 1
            mock_repo.save_metric.assert_not_called()
