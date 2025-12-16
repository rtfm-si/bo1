"""Tests for cost retry job with partitioned api_costs table.

Validates:
- Retry job uses composite ON CONFLICT (request_id, created_at)
- created_at is parsed from retry record and included in insert
- Fallback to current time if created_at missing
"""

from datetime import UTC, datetime
from unittest.mock import patch


class TestCostRetryJobPartitionedTable:
    """Test retry job compatibility with partitioned api_costs table."""

    def test_process_retry_queue_includes_created_at_in_insert(self):
        """Verify INSERT includes created_at column for partitioned table."""
        from backend.jobs.cost_retry_job import process_retry_queue
        from bo1.llm.cost_tracker import CostTracker

        # Mock retry records with created_at
        mock_records = [
            {
                "request_id": "req-123",
                "created_at": "2025-12-16T10:00:00+00:00",
                "session_id": "session-1",
                "provider": "anthropic",
                "model_name": "claude-sonnet",
                "operation_type": "completion",
                "total_cost": 0.01,
            }
        ]

        with (
            patch.object(CostTracker, "get_retry_queue_depth", return_value=1),
            patch.object(CostTracker, "pop_retry_batch", return_value=mock_records),
            patch("backend.jobs.cost_retry_job.db_session") as mock_db,
            patch.object(CostTracker, "clear_session_untracked_flag", return_value=True),
            patch("backend.jobs.cost_retry_job._check_session_in_queue", return_value=False),
        ):
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
            process_retry_queue(batch_size=10)

        # Verify executemany was called
        mock_cursor.executemany.assert_called_once()

        # Check SQL includes created_at and composite conflict target
        call_args = mock_cursor.executemany.call_args
        sql = call_args[0][0]
        assert "created_at" in sql
        assert "ON CONFLICT (request_id, created_at) DO NOTHING" in sql

    def test_process_retry_queue_parses_created_at_from_record(self):
        """Verify created_at is parsed from retry record ISO string."""
        from backend.jobs.cost_retry_job import process_retry_queue
        from bo1.llm.cost_tracker import CostTracker

        original_timestamp = "2025-12-15T14:30:45+00:00"
        mock_records = [
            {
                "request_id": "req-456",
                "created_at": original_timestamp,
                "session_id": "session-2",
                "provider": "anthropic",
                "model_name": "claude-sonnet",
                "operation_type": "completion",
                "total_cost": 0.02,
            }
        ]

        captured_insert_data = []

        with (
            patch.object(CostTracker, "get_retry_queue_depth", return_value=1),
            patch.object(CostTracker, "pop_retry_batch", return_value=mock_records),
            patch("backend.jobs.cost_retry_job.db_session") as mock_db,
            patch.object(CostTracker, "clear_session_untracked_flag", return_value=True),
            patch("backend.jobs.cost_retry_job._check_session_in_queue", return_value=False),
        ):
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value

            def capture_executemany(sql, data):
                captured_insert_data.extend(data)

            mock_cursor.executemany.side_effect = capture_executemany
            process_retry_queue(batch_size=10)

        # created_at should be parsed and in position 1 (after request_id)
        assert len(captured_insert_data) == 1
        insert_tuple = captured_insert_data[0]
        # Position 0 = request_id, position 1 = created_at
        assert insert_tuple[0] == "req-456"
        assert insert_tuple[1].year == 2025
        assert insert_tuple[1].month == 12
        assert insert_tuple[1].day == 15

    def test_process_retry_queue_fallback_to_current_time(self):
        """Verify fallback to current time when created_at missing from retry record."""
        from backend.jobs.cost_retry_job import process_retry_queue
        from bo1.llm.cost_tracker import CostTracker

        # Record without created_at (legacy data)
        mock_records = [
            {
                "request_id": "req-789",
                # No created_at field
                "session_id": "session-3",
                "provider": "anthropic",
                "model_name": "claude-sonnet",
                "operation_type": "completion",
                "total_cost": 0.03,
            }
        ]

        captured_insert_data = []

        with (
            patch.object(CostTracker, "get_retry_queue_depth", return_value=1),
            patch.object(CostTracker, "pop_retry_batch", return_value=mock_records),
            patch("backend.jobs.cost_retry_job.db_session") as mock_db,
            patch.object(CostTracker, "clear_session_untracked_flag", return_value=True),
            patch("backend.jobs.cost_retry_job._check_session_in_queue", return_value=False),
        ):
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value

            def capture_executemany(sql, data):
                captured_insert_data.extend(data)

            mock_cursor.executemany.side_effect = capture_executemany

            before = datetime.now(UTC)
            process_retry_queue(batch_size=10)
            after = datetime.now(UTC)

        # created_at should be a recent timestamp (fallback)
        assert len(captured_insert_data) == 1
        insert_tuple = captured_insert_data[0]
        created_at = insert_tuple[1]
        assert before <= created_at <= after

    def test_process_retry_queue_uses_composite_conflict_not_single_key(self):
        """Verify retry job does NOT use single-column ON CONFLICT (request_id)."""
        from backend.jobs.cost_retry_job import process_retry_queue
        from bo1.llm.cost_tracker import CostTracker

        mock_records = [
            {
                "request_id": "req-abc",
                "created_at": "2025-12-16T12:00:00+00:00",
                "provider": "anthropic",
                "total_cost": 0.01,
            }
        ]

        with (
            patch.object(CostTracker, "get_retry_queue_depth", return_value=1),
            patch.object(CostTracker, "pop_retry_batch", return_value=mock_records),
            patch("backend.jobs.cost_retry_job.db_session") as mock_db,
            patch.object(CostTracker, "clear_session_untracked_flag", return_value=True),
            patch("backend.jobs.cost_retry_job._check_session_in_queue", return_value=False),
        ):
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
            process_retry_queue(batch_size=10)

        call_args = mock_cursor.executemany.call_args
        sql = call_args[0][0]

        # Must use composite key
        assert "ON CONFLICT (request_id, created_at)" in sql
        # Should NOT have single-column conflict (except as part of composite)
        remaining = sql.replace("ON CONFLICT (request_id, created_at)", "")
        assert "ON CONFLICT (request_id)" not in remaining
