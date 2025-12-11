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
