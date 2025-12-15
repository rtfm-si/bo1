"""Tests for partition retention job."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from backend.jobs.partition_retention_job import (
    _categorize_result,
    _get_month_suffix,
    run_retention_job,
)
from backend.services.partition_manager import PartitionResult


class TestRunRetentionJob:
    """Tests for run_retention_job function."""

    @patch("backend.jobs.partition_retention_job.ensure_future_partitions")
    @patch("backend.jobs.partition_retention_job.drop_old_partitions")
    def test_job_creates_future_partitions(
        self,
        mock_drop: MagicMock,
        mock_ensure: MagicMock,
    ) -> None:
        """Test that job creates future partitions for all tables."""
        mock_ensure.return_value = [
            PartitionResult(
                table="api_costs",
                partition_name="api_costs_2025_01",
                status="created",
            )
        ]
        mock_drop.return_value = []

        result = run_retention_job(months_ahead=3, dry_run=False)

        # Should create partitions for all 3 tables
        assert mock_ensure.call_count == 3
        assert result["summary"]["partitions_created"] >= 1

    @patch("backend.jobs.partition_retention_job.ensure_future_partitions")
    @patch("backend.jobs.partition_retention_job.drop_old_partitions")
    def test_job_drops_expired_partitions(
        self,
        mock_drop: MagicMock,
        mock_ensure: MagicMock,
    ) -> None:
        """Test that job drops expired partitions."""
        mock_ensure.return_value = []
        mock_drop.return_value = [
            PartitionResult(
                table="api_costs",
                partition_name="api_costs_2024_01",
                status="dropped",
            )
        ]

        result = run_retention_job(months_ahead=3, dry_run=False)

        # Should drop partitions for all 3 tables
        assert mock_drop.call_count == 3
        assert result["summary"]["partitions_dropped"] >= 1

    @patch("backend.jobs.partition_retention_job.ensure_future_partitions")
    @patch("backend.jobs.partition_retention_job.drop_old_partitions")
    def test_job_handles_empty_table(
        self,
        mock_drop: MagicMock,
        mock_ensure: MagicMock,
    ) -> None:
        """Test that job handles tables with no existing partitions."""
        mock_ensure.return_value = [
            PartitionResult(
                table="api_costs",
                partition_name="api_costs_2024_12",
                status="created",
            )
        ]
        mock_drop.return_value = []  # No partitions to drop

        result = run_retention_job(months_ahead=3, dry_run=False)

        assert result["summary"]["partitions_dropped"] == 0
        assert result["summary"]["errors"] == 0

    @patch("backend.jobs.partition_retention_job.get_all_partition_stats")
    def test_dry_run_does_not_modify(
        self,
        mock_stats: MagicMock,
    ) -> None:
        """Test that dry_run=True does not create or drop partitions."""
        mock_stats.return_value = {"api_costs": [], "session_events": [], "contributions": []}

        result = run_retention_job(months_ahead=3, dry_run=True)

        assert result["dry_run"] is True
        # Should include current_stats in dry run mode
        assert "current_stats" in result
        # Should indicate what would be done
        for table_data in result["tables"].values():
            assert "would_create" in table_data or "would_drop_older_than" in table_data

    @patch("backend.jobs.partition_retention_job.ensure_future_partitions")
    @patch("backend.jobs.partition_retention_job.drop_old_partitions")
    def test_job_tracks_errors(
        self,
        mock_drop: MagicMock,
        mock_ensure: MagicMock,
    ) -> None:
        """Test that job tracks and reports errors."""
        mock_ensure.return_value = [
            PartitionResult(
                table="api_costs",
                partition_name="api_costs_2025_01",
                status="error",
                message="Permission denied",
            )
        ]
        mock_drop.return_value = []

        result = run_retention_job(months_ahead=3, dry_run=False)

        assert result["summary"]["errors"] >= 1
        # Check that error is recorded in table results
        api_costs_results = result["tables"]["api_costs"]
        assert len(api_costs_results["errors"]) >= 1

    @patch("backend.jobs.partition_retention_job.ensure_future_partitions")
    @patch("backend.jobs.partition_retention_job.drop_old_partitions")
    def test_job_includes_timing(
        self,
        mock_drop: MagicMock,
        mock_ensure: MagicMock,
    ) -> None:
        """Test that job result includes timing information."""
        mock_ensure.return_value = []
        mock_drop.return_value = []

        result = run_retention_job(months_ahead=3, dry_run=False)

        assert "started_at" in result
        assert "completed_at" in result
        assert "duration_ms" in result
        assert isinstance(result["duration_ms"], int)


class TestCategorizeResult:
    """Tests for _categorize_result helper function."""

    def test_categorizes_created(self) -> None:
        """Test categorization of created partition."""
        table_results = {"created": [], "dropped": [], "skipped": [], "errors": []}
        summary = {
            "partitions_created": 0,
            "partitions_dropped": 0,
            "partitions_skipped": 0,
            "errors": 0,
        }

        result = PartitionResult(table="api_costs", partition_name="test_2024_12", status="created")
        _categorize_result(result, table_results, summary)

        assert "test_2024_12" in table_results["created"]
        assert summary["partitions_created"] == 1

    def test_categorizes_dropped(self) -> None:
        """Test categorization of dropped partition."""
        table_results = {"created": [], "dropped": [], "skipped": [], "errors": []}
        summary = {
            "partitions_created": 0,
            "partitions_dropped": 0,
            "partitions_skipped": 0,
            "errors": 0,
        }

        result = PartitionResult(table="api_costs", partition_name="test_2024_01", status="dropped")
        _categorize_result(result, table_results, summary)

        assert "test_2024_01" in table_results["dropped"]
        assert summary["partitions_dropped"] == 1

    def test_categorizes_already_exists(self) -> None:
        """Test categorization of already existing partition."""
        table_results = {"created": [], "dropped": [], "skipped": [], "errors": []}
        summary = {
            "partitions_created": 0,
            "partitions_dropped": 0,
            "partitions_skipped": 0,
            "errors": 0,
        }

        result = PartitionResult(
            table="api_costs", partition_name="test_2024_12", status="already_exists"
        )
        _categorize_result(result, table_results, summary)

        assert "test_2024_12" in table_results["skipped"]
        assert summary["partitions_skipped"] == 1

    def test_categorizes_error(self) -> None:
        """Test categorization of error."""
        table_results = {"created": [], "dropped": [], "skipped": [], "errors": []}
        summary = {
            "partitions_created": 0,
            "partitions_dropped": 0,
            "partitions_skipped": 0,
            "errors": 0,
        }

        result = PartitionResult(
            table="api_costs", partition_name="test_2024_12", status="error", message="Failed"
        )
        _categorize_result(result, table_results, summary)

        assert len(table_results["errors"]) == 1
        assert table_results["errors"][0]["message"] == "Failed"
        assert summary["errors"] == 1


class TestGetMonthSuffix:
    """Tests for _get_month_suffix helper function."""

    @patch("backend.jobs.partition_retention_job.datetime")
    def test_current_month(self, mock_datetime: MagicMock) -> None:
        """Test suffix for current month."""
        mock_datetime.now.return_value = datetime(2024, 12, 15, tzinfo=UTC)

        suffix = _get_month_suffix(0)

        assert suffix == "2024_12"

    @patch("backend.jobs.partition_retention_job.datetime")
    def test_next_month(self, mock_datetime: MagicMock) -> None:
        """Test suffix for next month."""
        mock_datetime.now.return_value = datetime(2024, 12, 15, tzinfo=UTC)

        suffix = _get_month_suffix(1)

        assert suffix == "2025_01"

    @patch("backend.jobs.partition_retention_job.datetime")
    def test_year_boundary(self, mock_datetime: MagicMock) -> None:
        """Test suffix handles year boundary correctly."""
        mock_datetime.now.return_value = datetime(2024, 11, 15, tzinfo=UTC)

        suffix_plus_2 = _get_month_suffix(2)

        assert suffix_plus_2 == "2025_01"
