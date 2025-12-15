"""Tests for partition management service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from backend.services.partition_manager import (
    PARTITIONED_TABLES,
    PartitionInfo,
    PartitionResult,
    create_partition,
    drop_old_partitions,
    ensure_future_partitions,
    get_all_partition_stats,
    get_partition_stats,
    run_maintenance,
)


class TestPartitionResult:
    """Tests for PartitionResult dataclass."""

    def test_created_status(self) -> None:
        """Test PartitionResult with created status."""
        result = PartitionResult(
            table="api_costs",
            partition_name="api_costs_2024_12",
            status="created",
        )
        assert result.table == "api_costs"
        assert result.partition_name == "api_costs_2024_12"
        assert result.status == "created"
        assert result.message is None

    def test_error_status_with_message(self) -> None:
        """Test PartitionResult with error status and message."""
        result = PartitionResult(
            table="api_costs",
            partition_name="api_costs_2024_12",
            status="error",
            message="Partition already exists",
        )
        assert result.status == "error"
        assert result.message == "Partition already exists"


class TestPartitionInfo:
    """Tests for PartitionInfo dataclass."""

    def test_partition_info_fields(self) -> None:
        """Test PartitionInfo contains all expected fields."""
        now = datetime.now(UTC)
        info = PartitionInfo(
            partition_name="api_costs_2024_12",
            table_name="api_costs",
            start_date=now,
            end_date=now + timedelta(days=30),
            row_count=1000,
            total_size="10 MB",
            table_size="8 MB",
            indexes_size="2 MB",
        )
        assert info.partition_name == "api_costs_2024_12"
        assert info.row_count == 1000
        assert info.total_size == "10 MB"


class TestCreatePartition:
    """Tests for create_partition function."""

    def test_invalid_table_returns_error(self) -> None:
        """Test that invalid table name returns error result."""
        result = create_partition(
            table="invalid_table",
            start_date=datetime.now(UTC),
            end_date=datetime.now(UTC) + timedelta(days=30),
        )
        assert result.status == "error"
        assert "not a partitioned table" in result.message

    @patch("backend.services.partition_manager.db_session")
    def test_already_exists_returns_skipped(self, mock_db_session: MagicMock) -> None:
        """Test that existing partition returns already_exists status."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"exists": 1}  # Partition exists
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

        now = datetime.now(UTC)
        result = create_partition(
            table="api_costs",
            start_date=now,
            end_date=now + timedelta(days=30),
        )
        assert result.status == "already_exists"

    @patch("backend.services.partition_manager.db_session")
    def test_creates_valid_partition(self, mock_db_session: MagicMock) -> None:
        """Test that new partition is created successfully."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # Partition doesn't exist
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

        start_date = datetime(2024, 12, 1, tzinfo=UTC)
        end_date = datetime(2025, 1, 1, tzinfo=UTC)

        result = create_partition(
            table="api_costs",
            start_date=start_date,
            end_date=end_date,
        )

        assert result.status == "created"
        assert result.partition_name == "api_costs_2024_12"


class TestDropOldPartitions:
    """Tests for drop_old_partitions function."""

    def test_invalid_table_returns_error(self) -> None:
        """Test that invalid table name returns error result."""
        results = drop_old_partitions(table="invalid_table", retention_days=90)
        assert len(results) == 1
        assert results[0].status == "error"

    @patch("backend.services.partition_manager.db_session")
    def test_respects_retention_period(self, mock_db_session: MagicMock) -> None:
        """Test that only partitions older than retention are dropped."""
        # Test only old partitions (more than 365 days ago to be safe)
        # Using partitions from 2023 which will be dropped with any retention < 365 days
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"partition_name": "api_costs_2023_01"},  # Very old, should drop
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

        # With 90 day retention, 2023_01 should definitely be dropped
        results = drop_old_partitions(table="api_costs", retention_days=90)

        # Verify DROP was called
        dropped = [r for r in results if r.status == "dropped"]
        assert len(dropped) == 1
        assert "2023_01" in dropped[0].partition_name

    @patch("backend.services.partition_manager.db_session")
    def test_keeps_recent_partitions(self, mock_db_session: MagicMock) -> None:
        """Test that recent partitions are not dropped."""
        # Use future partitions that should never be dropped
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"partition_name": "api_costs_2026_01"},  # Future, should keep
            {"partition_name": "api_costs_2026_06"},  # Future, should keep
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

        results = drop_old_partitions(table="api_costs", retention_days=90)

        # No partitions should be dropped (future dates)
        dropped = [r for r in results if r.status == "dropped"]
        assert len(dropped) == 0


class TestEnsureFuturePartitions:
    """Tests for ensure_future_partitions function."""

    def test_invalid_table_returns_error(self) -> None:
        """Test that invalid table name returns error result."""
        results = ensure_future_partitions(table="invalid_table", months_ahead=3)
        assert len(results) == 1
        assert results[0].status == "error"

    @patch("backend.services.partition_manager.create_partition")
    def test_creates_correct_number_of_partitions(self, mock_create: MagicMock) -> None:
        """Test that correct number of future partitions are created."""
        mock_create.return_value = PartitionResult(
            table="api_costs",
            partition_name="api_costs_2025_01",
            status="created",
        )

        results = ensure_future_partitions(table="api_costs", months_ahead=3)

        # Should create current month + 3 ahead = 4 partitions
        assert len(results) == 4
        assert mock_create.call_count == 4


class TestGetPartitionStats:
    """Tests for get_partition_stats function."""

    def test_invalid_table_returns_empty(self) -> None:
        """Test that invalid table name returns empty list."""
        results = get_partition_stats(table="invalid_table")
        assert results == []

    @patch("backend.services.partition_manager.db_session")
    def test_returns_partition_sizes(self, mock_db_session: MagicMock) -> None:
        """Test that partition stats are returned correctly."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "partition_name": "api_costs_2024_11",
                "row_count": 5000,
                "total_size": "50 MB",
                "table_size": "40 MB",
                "indexes_size": "10 MB",
            },
            {
                "partition_name": "api_costs_2024_12",
                "row_count": 3000,
                "total_size": "30 MB",
                "table_size": "25 MB",
                "indexes_size": "5 MB",
            },
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

        stats = get_partition_stats(table="api_costs")

        assert len(stats) == 2
        assert stats[0].partition_name == "api_costs_2024_11"
        assert stats[0].row_count == 5000
        assert stats[0].total_size == "50 MB"


class TestGetAllPartitionStats:
    """Tests for get_all_partition_stats function."""

    @patch("backend.services.partition_manager.get_partition_stats")
    def test_returns_stats_for_all_tables(self, mock_get_stats: MagicMock) -> None:
        """Test that stats are returned for all partitioned tables."""
        mock_get_stats.return_value = []

        stats = get_all_partition_stats()

        # Should call get_partition_stats for each table
        assert mock_get_stats.call_count == len(PARTITIONED_TABLES)
        assert set(stats.keys()) == set(PARTITIONED_TABLES)


class TestRunMaintenance:
    """Tests for run_maintenance function."""

    @patch("backend.services.partition_manager.ensure_future_partitions")
    @patch("backend.services.partition_manager.drop_old_partitions")
    def test_runs_both_operations(
        self,
        mock_drop: MagicMock,
        mock_ensure: MagicMock,
    ) -> None:
        """Test that maintenance runs both create and drop operations."""
        mock_ensure.return_value = []
        mock_drop.return_value = []

        results = run_maintenance(create_future=True, drop_expired=True)

        # Should run for each partitioned table
        assert mock_ensure.call_count == len(PARTITIONED_TABLES)
        assert mock_drop.call_count == len(PARTITIONED_TABLES)
        assert set(results.keys()) == set(PARTITIONED_TABLES)

    @patch("backend.services.partition_manager.ensure_future_partitions")
    @patch("backend.services.partition_manager.drop_old_partitions")
    def test_skips_drop_when_disabled(
        self,
        mock_drop: MagicMock,
        mock_ensure: MagicMock,
    ) -> None:
        """Test that drop is skipped when drop_expired=False."""
        mock_ensure.return_value = []

        run_maintenance(create_future=True, drop_expired=False)

        assert mock_ensure.call_count == len(PARTITIONED_TABLES)
        assert mock_drop.call_count == 0

    @patch("backend.services.partition_manager.ensure_future_partitions")
    @patch("backend.services.partition_manager.drop_old_partitions")
    def test_skips_create_when_disabled(
        self,
        mock_drop: MagicMock,
        mock_ensure: MagicMock,
    ) -> None:
        """Test that create is skipped when create_future=False."""
        mock_drop.return_value = []

        run_maintenance(create_future=False, drop_expired=True)

        assert mock_ensure.call_count == 0
        assert mock_drop.call_count == len(PARTITIONED_TABLES)
