"""Tests for CostTracker token budget and cost budget tracking.

Validates:
- Token budget warning is logged when input tokens exceed threshold
- No warning when under budget
- Prompt name is included in warning
- Cost budget warnings at 80% threshold
- Cost budget exceeded at 100%
- No duplicate warnings per session
"""

import logging
from unittest.mock import patch

from bo1.llm.cost_tracker import CostRecord, CostTracker


class TestTokenBudgetTracking:
    """Test _check_token_budget method."""

    def test_token_budget_warning_logged_when_exceeded(self, caplog):
        """Verify warning is logged when input tokens exceed threshold."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            input_tokens=60_000,  # Exceeds default 50k threshold
            output_tokens=500,
            node_name="parallel_round_node",
            phase="deliberation",
            metadata={"prompt_name": "contribution_prompt"},
        )

        with patch("bo1.config.get_settings") as mock_settings:
            mock_settings.return_value.token_budget_warning_threshold = 50_000
            with caplog.at_level(logging.WARNING):
                CostTracker._check_token_budget(record)

        assert "Token budget exceeded" in caplog.text
        assert "60,000 tokens" in caplog.text
        assert "threshold: 50,000" in caplog.text
        assert "contribution_prompt" in caplog.text
        assert "parallel_round_node" in caplog.text

    def test_no_warning_when_under_budget(self, caplog):
        """Verify no warning when input tokens are under threshold."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            input_tokens=30_000,  # Under 50k threshold
            output_tokens=500,
            node_name="synthesis_node",
            phase="synthesis",
        )

        with patch("bo1.config.get_settings") as mock_settings:
            mock_settings.return_value.token_budget_warning_threshold = 50_000
            with caplog.at_level(logging.WARNING):
                CostTracker._check_token_budget(record)

        assert "Token budget exceeded" not in caplog.text

    def test_prompt_name_included_in_warning(self, caplog):
        """Verify prompt_name from metadata is included in warning."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-haiku-4-5-20251001",
            operation_type="completion",
            input_tokens=100_000,
            node_name="facilitator_node",
            phase="orchestration",
            metadata={"prompt_name": "facilitator_decision_prompt"},
        )

        with patch("bo1.config.get_settings") as mock_settings:
            mock_settings.return_value.token_budget_warning_threshold = 50_000
            with caplog.at_level(logging.WARNING):
                CostTracker._check_token_budget(record)

        assert "facilitator_decision_prompt" in caplog.text

    def test_unknown_prompt_name_when_not_provided(self, caplog):
        """Verify 'unknown' is used when prompt_name not in metadata."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            input_tokens=75_000,
            metadata={},  # No prompt_name
        )

        with patch("bo1.config.get_settings") as mock_settings:
            mock_settings.return_value.token_budget_warning_threshold = 50_000
            with caplog.at_level(logging.WARNING):
                CostTracker._check_token_budget(record)

        assert "prompt=unknown" in caplog.text

    def test_configurable_threshold(self, caplog):
        """Verify threshold is read from config."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            input_tokens=25_000,  # Under custom threshold
        )

        with patch("bo1.config.get_settings") as mock_settings:
            # Set threshold lower than input tokens
            mock_settings.return_value.token_budget_warning_threshold = 20_000
            with caplog.at_level(logging.WARNING):
                CostTracker._check_token_budget(record)

        # Should warn because 25k > 20k threshold
        assert "Token budget exceeded" in caplog.text
        assert "threshold: 20,000" in caplog.text


class TestCostBudgetTracking:
    """Test check_budget method for cost budget alerts."""

    def setup_method(self):
        """Reset budget state before each test."""
        # Clear any tracked sessions from previous tests
        CostTracker._warned_sessions.clear()
        CostTracker._exceeded_sessions.clear()

    def test_warning_triggered_at_80_percent(self, caplog):
        """Verify warning is triggered at 80% of budget."""
        session_id = "test_session_80"

        with caplog.at_level(logging.WARNING):
            warning, exceeded = CostTracker.check_budget(
                session_id=session_id,
                current_cost=0.40,  # 80% of $0.50
                budget=0.50,
                warning_threshold=0.80,
            )

        assert warning is True
        assert exceeded is False
        assert "Cost budget warning" in caplog.text
        assert session_id in caplog.text
        assert "$0.40" in caplog.text

    def test_exceeded_triggered_at_100_percent(self, caplog):
        """Verify exceeded is triggered at 100% of budget."""
        session_id = "test_session_100"

        with caplog.at_level(logging.WARNING):
            warning, exceeded = CostTracker.check_budget(
                session_id=session_id,
                current_cost=0.55,  # 110% of $0.50
                budget=0.50,
                warning_threshold=0.80,
            )

        # Both should trigger on first call
        assert warning is True
        assert exceeded is True
        assert "Cost budget EXCEEDED" in caplog.text

    def test_no_duplicate_warnings(self, caplog):
        """Verify warnings are not emitted twice for same session."""
        session_id = "test_session_no_dup"

        # First call - should trigger warning
        with caplog.at_level(logging.WARNING):
            warning1, _ = CostTracker.check_budget(
                session_id=session_id,
                current_cost=0.42,
                budget=0.50,
                warning_threshold=0.80,
            )

        assert warning1 is True
        assert "Cost budget warning" in caplog.text

        # Clear log and call again with higher cost
        caplog.clear()

        with caplog.at_level(logging.WARNING):
            warning2, _ = CostTracker.check_budget(
                session_id=session_id,
                current_cost=0.48,
                budget=0.50,
                warning_threshold=0.80,
            )

        # Should not trigger again
        assert warning2 is False
        assert "Cost budget warning" not in caplog.text

    def test_no_warning_under_threshold(self, caplog):
        """Verify no warning when under 80% threshold."""
        session_id = "test_session_under"

        with caplog.at_level(logging.WARNING):
            warning, exceeded = CostTracker.check_budget(
                session_id=session_id,
                current_cost=0.30,  # 60% of $0.50
                budget=0.50,
                warning_threshold=0.80,
            )

        assert warning is False
        assert exceeded is False
        assert "Cost budget" not in caplog.text

    def test_uses_settings_defaults(self, caplog):
        """Verify settings defaults are used when not provided."""
        session_id = "test_session_defaults"

        with patch("bo1.config.get_settings") as mock_settings:
            mock_settings.return_value.session_cost_budget = 0.50
            mock_settings.return_value.cost_warning_threshold = 0.80

            with caplog.at_level(logging.WARNING):
                warning, _ = CostTracker.check_budget(
                    session_id=session_id,
                    current_cost=0.45,  # 90% > 80%
                )

        assert warning is True

    def test_reset_session_budget_state(self):
        """Verify reset_session_budget_state clears tracking."""
        session_id = "test_session_reset"

        # Trigger warning
        CostTracker.check_budget(session_id, 0.45, 0.50, 0.80)
        assert session_id in CostTracker._warned_sessions

        # Reset
        CostTracker.reset_session_budget_state(session_id)
        assert session_id not in CostTracker._warned_sessions

        # Can trigger warning again
        warning, _ = CostTracker.check_budget(session_id, 0.45, 0.50, 0.80)
        assert warning is True


class TestGetSubproblemCosts:
    """Test get_subproblem_costs method."""

    def test_get_subproblem_costs_returns_breakdown(self):
        """Test that get_subproblem_costs returns per-sub-problem breakdown."""
        session_id = "test_session_sp_costs"

        # Mock the database query response
        mock_rows = [
            # sub_problem_index, api_calls, total_cost, total_tokens, anthropic, voyage, brave, tavily, decomp, delib, synth
            (None, 5, 0.05, 1000, 0.05, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0),  # Overhead
            (0, 10, 0.15, 5000, 0.12, 0.01, 0.01, 0.01, 0.0, 0.10, 0.05),  # Sub-problem 0
            (1, 8, 0.12, 4000, 0.10, 0.01, 0.005, 0.005, 0.0, 0.08, 0.04),  # Sub-problem 1
        ]

        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
            mock_cursor.fetchall.return_value = mock_rows

            results = CostTracker.get_subproblem_costs(session_id)

        assert len(results) == 3

        # Check overhead (null sub_problem_index)
        assert results[0]["sub_problem_index"] is None
        assert results[0]["label"] == "Overhead"
        assert results[0]["total_cost"] == 0.05
        assert results[0]["api_calls"] == 5
        assert results[0]["by_provider"]["anthropic"] == 0.05
        assert results[0]["by_phase"]["decomposition"] == 0.05

        # Check sub-problem 0
        assert results[1]["sub_problem_index"] == 0
        assert results[1]["label"] == "Sub-problem 0"
        assert results[1]["total_cost"] == 0.15
        assert results[1]["total_tokens"] == 5000
        assert results[1]["by_phase"]["deliberation"] == 0.10

        # Check sub-problem 1
        assert results[2]["sub_problem_index"] == 1
        assert results[2]["label"] == "Sub-problem 1"

    def test_get_subproblem_costs_handles_null_index(self):
        """Test that NULL sub_problem_index is labeled as Overhead."""
        session_id = "test_session_null_idx"

        mock_rows = [
            (None, 3, 0.03, 500, 0.03, 0.0, 0.0, 0.0, 0.03, 0.0, 0.0),
        ]

        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
            mock_cursor.fetchall.return_value = mock_rows

            results = CostTracker.get_subproblem_costs(session_id)

        assert len(results) == 1
        assert results[0]["sub_problem_index"] is None
        assert results[0]["label"] == "Overhead"

    def test_get_subproblem_costs_empty_session(self):
        """Test that empty session returns empty list."""
        session_id = "test_session_empty"

        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
            mock_cursor.fetchall.return_value = []

            results = CostTracker.get_subproblem_costs(session_id)

        assert results == []

    def test_get_subproblem_costs_handles_none_values(self):
        """Test that None values in aggregation are handled gracefully."""
        session_id = "test_session_none_vals"

        # Simulate a row with None for some aggregated values
        mock_rows = [
            (0, None, None, None, None, None, None, None, None, None, None),
        ]

        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
            mock_cursor.fetchall.return_value = mock_rows

            results = CostTracker.get_subproblem_costs(session_id)

        assert len(results) == 1
        assert results[0]["total_cost"] == 0.0
        assert results[0]["api_calls"] == 0
        assert results[0]["total_tokens"] == 0
        assert results[0]["by_provider"]["anthropic"] == 0.0


class TestCostTrackerBatching:
    """Test batch buffer functionality for cost tracking."""

    def setup_method(self):
        """Clear buffer before each test."""
        CostTracker._clear_buffer_for_testing()

    def teardown_method(self):
        """Clear buffer after each test."""
        CostTracker._clear_buffer_for_testing()

    def test_log_cost_buffers_records(self):
        """Verify log_cost adds records to buffer instead of immediate DB write."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            input_tokens=1000,
            output_tokens=200,
            total_cost=0.006,
            session_id="test_batch_1",
        )

        with patch("bo1.llm.cost_tracker.db_session"):
            request_id = CostTracker.log_cost(record)

        # Should have a request_id
        assert request_id is not None
        assert len(request_id) == 36  # UUID format

        # Buffer should have 1 record
        stats = CostTracker.get_buffer_stats()
        assert stats["buffer_size"] == 1

    def test_flush_writes_all_buffered_records(self):
        """Verify flush writes all buffered records to database."""
        # Add multiple records to buffer
        for i in range(5):
            record = CostRecord(
                provider="anthropic",
                model_name="claude-sonnet-4-5-20250929",
                operation_type="completion",
                input_tokens=1000,
                output_tokens=200,
                total_cost=0.006,
                session_id=f"test_flush_{i}",
            )
            # Mock db_session during log_cost to prevent auto-flush
            with patch("bo1.llm.cost_tracker.db_session"):
                CostTracker.log_cost(record)

        # Verify buffer has 5 records
        stats = CostTracker.get_buffer_stats()
        assert stats["buffer_size"] == 5

        # Flush with mocked DB
        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
            flushed = CostTracker.flush("test_session")

        assert flushed == 5
        # Verify executemany was called
        mock_cursor.executemany.assert_called_once()
        # Buffer should be empty
        assert CostTracker.get_buffer_stats()["buffer_size"] == 0

    def test_flush_idempotent_when_empty(self):
        """Verify flush is no-op when buffer is empty."""
        # Buffer should be empty after setup
        assert CostTracker.get_buffer_stats()["buffer_size"] == 0

        # Flush should return 0
        flushed = CostTracker.flush("empty_session")
        assert flushed == 0

    def test_auto_flush_on_batch_size(self):
        """Verify auto-flush when buffer exceeds BATCH_SIZE."""
        from bo1.llm.cost_tracker import BATCH_SIZE

        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value

            # Add BATCH_SIZE records - should trigger auto-flush
            for i in range(BATCH_SIZE):
                record = CostRecord(
                    provider="anthropic",
                    model_name="claude-sonnet-4-5-20250929",
                    operation_type="completion",
                    input_tokens=1000,
                    output_tokens=200,
                    total_cost=0.006,
                    session_id=f"test_auto_{i}",
                )
                CostTracker.log_cost(record)

        # executemany should have been called (auto-flush triggered)
        assert mock_cursor.executemany.call_count >= 1
        # Buffer should be empty or nearly empty after auto-flush
        assert CostTracker.get_buffer_stats()["buffer_size"] < BATCH_SIZE

    def test_buffer_preserved_on_db_failure(self):
        """Verify buffer is preserved (re-added) on DB write failure."""
        # Add records to buffer
        for i in range(3):
            record = CostRecord(
                provider="anthropic",
                model_name="claude-sonnet-4-5-20250929",
                operation_type="completion",
                input_tokens=1000,
                output_tokens=200,
                total_cost=0.006,
                session_id=f"test_fail_{i}",
            )
            with patch("bo1.llm.cost_tracker.db_session"):
                CostTracker.log_cost(record)

        assert CostTracker.get_buffer_stats()["buffer_size"] == 3

        # Flush with DB error AND Redis error (to test buffer re-add fallback)
        with (
            patch("bo1.llm.cost_tracker.db_session") as mock_db,
            patch.object(
                CostTracker, "_push_to_retry_queue", return_value=0
            ),  # Simulate Redis also failing
        ):
            mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.executemany.side_effect = Exception(
                "DB connection failed"
            )
            flushed = CostTracker.flush("fail_session")

        # Should return 0 (failure)
        assert flushed == 0
        # Records should be back in buffer (only if Redis also failed)
        assert CostTracker.get_buffer_stats()["buffer_size"] == 3

    def test_get_buffer_stats_returns_correct_info(self):
        """Verify get_buffer_stats returns accurate statistics."""
        # Initially empty
        stats = CostTracker.get_buffer_stats()
        assert stats["buffer_size"] == 0
        assert "last_flush_time" in stats
        assert "seconds_since_flush" in stats

        # Add a record
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            input_tokens=1000,
            total_cost=0.003,
        )
        with patch("bo1.llm.cost_tracker.db_session"):
            CostTracker.log_cost(record)

        stats = CostTracker.get_buffer_stats()
        assert stats["buffer_size"] == 1
        assert stats["seconds_since_flush"] >= 0

    def test_thread_safety_concurrent_logging(self):
        """Verify buffer is thread-safe under concurrent writes."""
        import threading

        errors = []
        record_count = 20

        def log_records():
            try:
                for _ in range(record_count):
                    record = CostRecord(
                        provider="anthropic",
                        model_name="claude-sonnet-4-5-20250929",
                        operation_type="completion",
                        input_tokens=100,
                        total_cost=0.001,
                    )
                    with patch("bo1.llm.cost_tracker.db_session"):
                        CostTracker.log_cost(record)
            except Exception as e:
                errors.append(e)

        # Run 3 threads concurrently
        threads = [threading.Thread(target=log_records) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors
        assert len(errors) == 0
        # All records should be in buffer (3 threads * 20 records = 60)
        # Note: some may have auto-flushed due to BATCH_SIZE
        stats = CostTracker.get_buffer_stats()
        assert stats["buffer_size"] <= 60  # Could be less if auto-flush triggered


class TestCostRetryQueue:
    """Test retry queue functionality for resilience."""

    def setup_method(self):
        """Clear buffer before each test."""
        CostTracker._clear_buffer_for_testing()

    def teardown_method(self):
        """Clear buffer after each test."""
        CostTracker._clear_buffer_for_testing()

    def test_push_to_retry_queue_on_db_failure(self):
        """Test that failed DB flush pushes to Redis retry queue."""
        from unittest.mock import MagicMock

        # Add records to buffer
        records = []
        for i in range(3):
            record = CostRecord(
                provider="anthropic",
                model_name="claude-sonnet-4-5-20250929",
                operation_type="completion",
                input_tokens=1000,
                output_tokens=200,
                total_cost=0.006,
                session_id=f"test_retry_{i}",
            )
            records.append(record)
            with patch("bo1.llm.cost_tracker.db_session"):
                CostTracker.log_cost(record)

        # Mock Redis and DB
        mock_redis = MagicMock()
        mock_redis.rpush.return_value = 1
        mock_redis.llen.return_value = 3

        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            # DB fails
            mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.executemany.side_effect = Exception(
                "DB connection failed"
            )

            with patch("redis.Redis.from_url", return_value=mock_redis):
                with patch.object(CostTracker, "_mark_sessions_untracked_costs"):
                    flushed = CostTracker.flush("fail_session")

        # Flush returns 0 (DB failed)
        assert flushed == 0

        # Redis rpush should have been called for each record
        assert mock_redis.rpush.call_count == 3

    def test_get_retry_queue_depth(self):
        """Test getting retry queue depth."""
        from unittest.mock import MagicMock

        mock_redis = MagicMock()
        mock_redis.llen.return_value = 42

        with patch("redis.Redis.from_url", return_value=mock_redis):
            depth = CostTracker.get_retry_queue_depth()

        assert depth == 42
        mock_redis.llen.assert_called_once_with("cost_retry_queue")

    def test_pop_retry_batch(self):
        """Test popping batch from retry queue."""
        import json
        from unittest.mock import MagicMock

        mock_redis = MagicMock()
        # Simulate 2 records in queue
        mock_redis.lpop.side_effect = [
            json.dumps({"request_id": "req1", "session_id": "s1", "total_cost": 0.01}),
            json.dumps({"request_id": "req2", "session_id": "s2", "total_cost": 0.02}),
            None,  # Queue empty
        ]

        with patch("redis.Redis.from_url", return_value=mock_redis):
            records = CostTracker.pop_retry_batch(batch_size=10)

        assert len(records) == 2
        assert records[0]["request_id"] == "req1"
        assert records[1]["request_id"] == "req2"

    def test_clear_session_untracked_flag(self):
        """Test clearing untracked costs flag for a session."""
        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
            mock_cursor.rowcount = 1

            result = CostTracker.clear_session_untracked_flag("test_session")

        assert result is True
        # Verify UPDATE query was called
        call_args = mock_cursor.execute.call_args
        assert "UPDATE sessions" in call_args[0][0]
        assert "has_untracked_costs = FALSE" in call_args[0][0]

    def test_mark_sessions_untracked_costs(self):
        """Test marking sessions as having untracked costs."""
        records = [
            CostRecord(
                provider="anthropic",
                model_name="claude-sonnet",
                operation_type="completion",
                session_id="session_1",
            ),
            CostRecord(
                provider="anthropic",
                model_name="claude-sonnet",
                operation_type="completion",
                session_id="session_2",
            ),
            CostRecord(
                provider="anthropic",
                model_name="claude-sonnet",
                operation_type="completion",
                session_id="session_1",  # Duplicate - should dedupe
            ),
        ]

        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
            mock_cursor.rowcount = 2

            CostTracker._mark_sessions_untracked_costs(records)

        # Verify UPDATE was called with unique session IDs
        call_args = mock_cursor.execute.call_args
        assert "has_untracked_costs = TRUE" in call_args[0][0]
        # Should have 2 unique sessions
        session_ids = call_args[0][1][0]
        assert len(session_ids) == 2
        assert "session_1" in session_ids
        assert "session_2" in session_ids


class TestDuplicateHandling:
    """Test idempotent insert handling with composite unique constraint.

    The api_costs table is partitioned by created_at, so the unique constraint
    is (request_id, created_at). These tests verify:
    - Duplicate inserts with same request_id + created_at are silently ignored
    - Same request_id with different created_at is allowed (edge case)
    - CostRecord includes created_at for consistent conflict resolution
    """

    def setup_method(self):
        """Clear buffer before each test."""
        CostTracker._clear_buffer_for_testing()

    def teardown_method(self):
        """Clear buffer after each test."""
        CostTracker._clear_buffer_for_testing()

    def test_cost_record_has_created_at_field(self):
        """Verify CostRecord includes created_at for partitioned table conflict resolution."""
        from datetime import datetime

        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
        )

        # Should have created_at set automatically
        assert hasattr(record, "created_at")
        assert isinstance(record.created_at, datetime)
        assert record.created_at.tzinfo is not None  # Should be timezone-aware

    def test_created_at_is_consistent_across_retries(self):
        """Verify created_at is set at record creation time, not flush time."""
        import time

        record1 = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
        )
        created_at_1 = record1.created_at

        # Wait a tiny bit
        time.sleep(0.01)

        # Access created_at again - should be the same
        assert record1.created_at == created_at_1

    def test_flush_includes_created_at_in_insert(self):
        """Verify flush includes created_at column in INSERT statement."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=0.01,
        )

        with patch("bo1.llm.cost_tracker.db_session"):
            CostTracker.log_cost(record)

        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
            CostTracker.flush("test_session")

        # Check the SQL includes created_at
        call_args = mock_cursor.executemany.call_args
        sql = call_args[0][0]
        assert "created_at" in sql
        # Verify it's in the conflict target
        assert "ON CONFLICT (request_id, created_at) DO NOTHING" in sql

    def test_flush_uses_composite_conflict_target(self):
        """Verify ON CONFLICT uses both request_id AND created_at for partitioned table."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=0.01,
        )

        with patch("bo1.llm.cost_tracker.db_session"):
            CostTracker.log_cost(record)

        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
            CostTracker.flush("test_session")

        call_args = mock_cursor.executemany.call_args
        sql = call_args[0][0]

        # Must use composite key for partitioned table
        assert "ON CONFLICT (request_id, created_at)" in sql
        # Old non-partitioned syntax should NOT be present
        assert "ON CONFLICT (request_id)" not in sql.replace(
            "ON CONFLICT (request_id, created_at)", ""
        )

    def test_retry_queue_preserves_created_at(self):
        """Verify retry records include created_at for consistent conflict resolution."""
        import json
        from unittest.mock import MagicMock

        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=0.01,
            session_id="test_retry_session",
        )
        original_created_at = record.created_at

        with patch("bo1.llm.cost_tracker.db_session"):
            CostTracker.log_cost(record)

        # Mock Redis and simulate DB failure + Redis push
        mock_redis = MagicMock()
        pushed_data = []

        def capture_rpush(key, data):
            pushed_data.append(json.loads(data))
            return 1

        mock_redis.rpush.side_effect = capture_rpush
        mock_redis.llen.return_value = 1

        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.executemany.side_effect = Exception(
                "DB failed"
            )
            with patch("redis.Redis.from_url", return_value=mock_redis):
                with patch.object(CostTracker, "_mark_sessions_untracked_costs"):
                    CostTracker.flush("test_session")

        # Verify created_at was preserved in retry data
        assert len(pushed_data) == 1
        assert "created_at" in pushed_data[0]
        # Should be ISO format string of the original timestamp
        assert original_created_at.isoformat() == pushed_data[0]["created_at"]


class TestLatencyMetricEmission:
    """Test LLM latency Prometheus metric emission."""

    def setup_method(self):
        """Clear buffer before each test."""
        CostTracker._clear_buffer_for_testing()

    def teardown_method(self):
        """Clear buffer after each test."""
        CostTracker._clear_buffer_for_testing()

    def test_record_cost_emits_latency_metric(self):
        """Verify histogram observation is called when latency_ms is present."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            input_tokens=1000,
            output_tokens=200,
            total_cost=0.006,
            latency_ms=2500,  # 2.5 seconds
        )

        with patch("backend.api.metrics.prom_metrics") as mock_prom:
            CostTracker._emit_prometheus_metrics(record)

        mock_prom.observe_llm_request.assert_called_once_with(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            operation="completion",
            duration_seconds=2.5,
            node=None,
        )

    def test_record_cost_handles_missing_latency(self):
        """Verify graceful handling when latency_ms is None."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            input_tokens=1000,
            output_tokens=200,
            total_cost=0.006,
            latency_ms=None,  # No latency
        )

        with patch("backend.api.metrics.prom_metrics") as mock_prom:
            CostTracker._emit_prometheus_metrics(record)

        # Should not call observe_llm_request when latency is None
        mock_prom.observe_llm_request.assert_not_called()

    def test_latency_metric_labels_correct(self):
        """Verify correct model/provider/operation labels are used."""
        record = CostRecord(
            provider="voyage",
            model_name="voyage-3",
            operation_type="embedding",
            input_tokens=500,
            total_cost=0.00003,
            latency_ms=150,
        )

        with patch("backend.api.metrics.prom_metrics") as mock_prom:
            CostTracker._emit_prometheus_metrics(record)

        mock_prom.observe_llm_request.assert_called_once_with(
            provider="voyage",
            model="voyage-3",
            operation="embedding",
            duration_seconds=0.15,
            node=None,
        )

    def test_latency_metric_with_node_context(self):
        """Verify node name is passed for context attribution."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-haiku-4-5-20251001",
            operation_type="completion",
            input_tokens=500,
            output_tokens=100,
            total_cost=0.0007,
            latency_ms=800,
            node_name="parallel_round_node",
        )

        with patch("backend.api.metrics.prom_metrics") as mock_prom:
            CostTracker._emit_prometheus_metrics(record)

        mock_prom.observe_llm_request.assert_called_once_with(
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
            operation="completion",
            duration_seconds=0.8,
            node="parallel_round_node",
        )

    def test_latency_conversion_ms_to_seconds(self):
        """Verify milliseconds are correctly converted to seconds."""
        test_cases = [
            (1000, 1.0),
            (500, 0.5),
            (2500, 2.5),
            (100, 0.1),
            (10000, 10.0),
        ]

        for latency_ms, expected_seconds in test_cases:
            record = CostRecord(
                provider="anthropic",
                model_name="claude-sonnet-4-5-20250929",
                operation_type="completion",
                latency_ms=latency_ms,
            )

            with patch("backend.api.metrics.prom_metrics") as mock_prom:
                CostTracker._emit_prometheus_metrics(record)

            call_args = mock_prom.observe_llm_request.call_args
            assert call_args.kwargs["duration_seconds"] == expected_seconds, (
                f"Expected {expected_seconds}s for {latency_ms}ms"
            )
