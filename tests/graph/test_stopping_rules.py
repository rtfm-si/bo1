"""Tests for stopping rules evaluator and early exit conditions.

This module tests the StoppingRulesEvaluator and related functions,
particularly the should_exit_early() function for cost savings.
"""

import pytest

from bo1.graph.quality.stopping_rules import (
    HARD_CAP_ROUNDS,
    StoppingDecision,
    StoppingRulesEvaluator,
    should_exit_early,
)
from bo1.graph.state import create_initial_state
from bo1.models.problem import Problem
from bo1.models.state import DeliberationMetrics


@pytest.fixture
def sample_problem() -> Problem:
    """Create a sample problem for testing."""
    return Problem(
        title="Test Problem",
        description="Should we invest in feature X?",
        context="SaaS startup with $500K budget",
    )


@pytest.fixture
def evaluator() -> StoppingRulesEvaluator:
    """Create a StoppingRulesEvaluator instance."""
    return StoppingRulesEvaluator()


# ============================================================================
# should_exit_early() Unit Tests
# ============================================================================


class TestShouldExitEarly:
    """Tests for should_exit_early() function."""

    def test_returns_false_when_round_less_than_2(self, sample_problem: Problem):
        """Early exit requires minimum 2 rounds of exploration."""
        state = create_initial_state(
            session_id="test-early-round",
            problem=sample_problem,
            max_rounds=6,
        )
        # Round 0 - should not exit early
        state["round_number"] = 0
        state["metrics"] = DeliberationMetrics(convergence_score=0.95, novelty_score=0.10)
        assert should_exit_early(state) is False

        # Round 1 - should not exit early
        state["round_number"] = 1
        assert should_exit_early(state) is False

    def test_returns_false_when_metrics_missing(self, sample_problem: Problem):
        """Early exit requires metrics to be available."""
        state = create_initial_state(
            session_id="test-no-metrics",
            problem=sample_problem,
            max_rounds=6,
        )
        state["round_number"] = 3
        state["metrics"] = None  # No metrics

        assert should_exit_early(state) is False

    def test_returns_false_when_convergence_low(self, sample_problem: Problem):
        """Early exit requires convergence > 0.85."""
        state = create_initial_state(
            session_id="test-low-convergence",
            problem=sample_problem,
            max_rounds=6,
        )
        state["round_number"] = 3
        state["metrics"] = DeliberationMetrics(
            convergence_score=0.80,  # Below threshold
            novelty_score=0.20,
        )

        assert should_exit_early(state) is False

    def test_returns_false_when_novelty_high(self, sample_problem: Problem):
        """Early exit requires novelty < 0.30 (agents repeating themselves)."""
        state = create_initial_state(
            session_id="test-high-novelty",
            problem=sample_problem,
            max_rounds=6,
        )
        state["round_number"] = 3
        state["metrics"] = DeliberationMetrics(
            convergence_score=0.90,
            novelty_score=0.40,  # Above threshold
        )

        assert should_exit_early(state) is False

    def test_returns_true_when_all_conditions_met(self, sample_problem: Problem):
        """Early exit when convergence > 0.85 AND novelty < 0.30 AND round >= 2."""
        state = create_initial_state(
            session_id="test-early-exit",
            problem=sample_problem,
            max_rounds=6,
        )
        state["round_number"] = 3
        state["metrics"] = DeliberationMetrics(
            convergence_score=0.90,  # > 0.85
            novelty_score=0.20,  # < 0.30
        )

        assert should_exit_early(state) is True

    def test_edge_case_convergence_exactly_threshold(self, sample_problem: Problem):
        """Edge case: convergence exactly at 0.85 should NOT trigger early exit."""
        state = create_initial_state(
            session_id="test-exact-convergence",
            problem=sample_problem,
            max_rounds=6,
        )
        state["round_number"] = 3
        state["metrics"] = DeliberationMetrics(
            convergence_score=0.85,  # Exactly at threshold (uses > not >=)
            novelty_score=0.20,
        )

        assert should_exit_early(state) is False

    def test_edge_case_novelty_exactly_threshold(self, sample_problem: Problem):
        """Edge case: novelty exactly at 0.30 should NOT trigger early exit."""
        state = create_initial_state(
            session_id="test-exact-novelty",
            problem=sample_problem,
            max_rounds=6,
        )
        state["round_number"] = 3
        state["metrics"] = DeliberationMetrics(
            convergence_score=0.90,
            novelty_score=0.30,  # Exactly at threshold (uses < not <=)
        )

        assert should_exit_early(state) is False

    def test_edge_case_round_exactly_2(self, sample_problem: Problem):
        """Edge case: round 2 is minimum for early exit (should work)."""
        state = create_initial_state(
            session_id="test-round-2",
            problem=sample_problem,
            max_rounds=6,
        )
        state["round_number"] = 2  # Exactly at minimum
        state["metrics"] = DeliberationMetrics(
            convergence_score=0.90,
            novelty_score=0.20,
        )

        assert should_exit_early(state) is True

    def test_handles_none_convergence_score(self, sample_problem: Problem):
        """Handles metrics with None convergence_score gracefully."""
        state = create_initial_state(
            session_id="test-none-convergence",
            problem=sample_problem,
            max_rounds=6,
        )
        state["round_number"] = 3
        state["metrics"] = DeliberationMetrics(
            convergence_score=None,  # Not calculated yet
            novelty_score=0.20,
        )

        # Should default to 0.0 for convergence and not trigger early exit
        assert should_exit_early(state) is False

    def test_handles_none_novelty_score(self, sample_problem: Problem):
        """Handles metrics with None novelty_score gracefully."""
        state = create_initial_state(
            session_id="test-none-novelty",
            problem=sample_problem,
            max_rounds=6,
        )
        state["round_number"] = 3
        state["metrics"] = DeliberationMetrics(
            convergence_score=0.90,
            novelty_score=None,  # Not calculated yet
        )

        # Should default to 1.0 for novelty and not trigger early exit
        assert should_exit_early(state) is False


# ============================================================================
# StoppingRulesEvaluator.check_early_exit() Tests
# ============================================================================


class TestCheckEarlyExit:
    """Tests for StoppingRulesEvaluator.check_early_exit() method."""

    def test_returns_stopping_decision_when_early_exit_triggered(
        self, evaluator: StoppingRulesEvaluator, sample_problem: Problem
    ):
        """Returns StoppingDecision(should_stop=True, stop_reason='early_convergence')."""
        state = create_initial_state(
            session_id="test-check-early",
            problem=sample_problem,
            max_rounds=6,
        )
        state["round_number"] = 3
        state["metrics"] = DeliberationMetrics(
            convergence_score=0.90,
            novelty_score=0.20,
        )

        result = evaluator.check_early_exit(state)

        assert result is not None
        assert isinstance(result, StoppingDecision)
        assert result.should_stop is True
        assert result.stop_reason == "early_convergence"

    def test_returns_none_when_conditions_not_met(
        self, evaluator: StoppingRulesEvaluator, sample_problem: Problem
    ):
        """Returns None when early exit conditions are not met."""
        state = create_initial_state(
            session_id="test-no-early",
            problem=sample_problem,
            max_rounds=6,
        )
        state["round_number"] = 3
        state["metrics"] = DeliberationMetrics(
            convergence_score=0.50,  # Low convergence
            novelty_score=0.60,  # High novelty
        )

        result = evaluator.check_early_exit(state)

        assert result is None


# ============================================================================
# StoppingRulesEvaluator.evaluate() Integration Tests
# ============================================================================


class TestEvaluatorEarlyExitIntegration:
    """Integration tests for early exit in the full evaluate() flow."""

    def test_early_exit_returns_before_round_3_max_rounds(
        self, evaluator: StoppingRulesEvaluator, sample_problem: Problem
    ):
        """Early exit can stop before max_rounds when conditions met."""
        state = create_initial_state(
            session_id="test-early-before-max",
            problem=sample_problem,
            max_rounds=6,
        )
        state["round_number"] = 2  # Before max_rounds
        state["metrics"] = DeliberationMetrics(
            convergence_score=0.90,
            novelty_score=0.15,
        )

        result = evaluator.evaluate(state)

        assert result.should_stop is True
        assert result.stop_reason == "early_convergence"

    def test_hard_cap_checked_before_early_exit(
        self, evaluator: StoppingRulesEvaluator, sample_problem: Problem
    ):
        """Hard cap is checked before early exit conditions."""
        state = create_initial_state(
            session_id="test-hard-cap-first",
            problem=sample_problem,
            max_rounds=10,  # High max_rounds
        )
        state["round_number"] = HARD_CAP_ROUNDS  # At hard cap
        state["metrics"] = DeliberationMetrics(
            convergence_score=0.90,
            novelty_score=0.15,
        )

        result = evaluator.evaluate(state)

        assert result.should_stop is True
        # Hard cap triggers first
        assert result.stop_reason == f"hard_cap_{HARD_CAP_ROUNDS}_rounds"

    def test_early_exit_checked_before_convergence_threshold(
        self, evaluator: StoppingRulesEvaluator, sample_problem: Problem
    ):
        """Early exit (0.85) is checked before convergence threshold (0.90)."""
        state = create_initial_state(
            session_id="test-early-first",
            problem=sample_problem,
            max_rounds=6,
        )
        state["round_number"] = 2
        # High convergence (> 0.85 for early, > 0.90 for threshold)
        # Low novelty (< 0.30 for early)
        state["metrics"] = DeliberationMetrics(
            convergence_score=0.88,  # Above early (0.85) but below threshold (0.90)
            novelty_score=0.10,
        )

        result = evaluator.evaluate(state)

        assert result.should_stop is True
        # Early exit triggers, not consensus (which requires round >= 3)
        assert result.stop_reason == "early_convergence"

    def test_early_exit_prevents_additional_rounds(
        self, evaluator: StoppingRulesEvaluator, sample_problem: Problem
    ):
        """Early exit prevents additional persona calls by stopping early."""
        # Start at round 2 with high convergence
        state = create_initial_state(
            session_id="test-prevent-rounds",
            problem=sample_problem,
            max_rounds=5,
        )
        state["round_number"] = 2
        state["metrics"] = DeliberationMetrics(
            convergence_score=0.90,
            novelty_score=0.20,
        )

        result = evaluator.evaluate(state)

        # Should stop at round 2, preventing rounds 3, 4, 5
        assert result.should_stop is True
        assert result.stop_reason == "early_convergence"

    def test_continue_when_no_stopping_conditions_met(
        self, evaluator: StoppingRulesEvaluator, sample_problem: Problem
    ):
        """Continue deliberation when no stopping conditions are met."""
        state = create_initial_state(
            session_id="test-continue",
            problem=sample_problem,
            max_rounds=6,
        )
        state["round_number"] = 2
        state["metrics"] = DeliberationMetrics(
            convergence_score=0.50,  # Low convergence
            novelty_score=0.60,  # High novelty
        )

        result = evaluator.evaluate(state)

        assert result.should_stop is False
        assert result.stop_reason is None


# ============================================================================
# Prometheus Metric Tests
# ============================================================================


class TestEarlyExitMetrics:
    """Tests for Prometheus metrics tracking early exits."""

    def test_metric_exists(self):
        """Verify bo1_early_exit_total metric is defined."""
        from backend.api.middleware.metrics import bo1_early_exit_total

        # Verify metric exists and has correct structure
        assert bo1_early_exit_total is not None
        # Counter internal name doesn't include _total suffix
        assert "early_exit" in bo1_early_exit_total._name

    def test_record_early_exit_function_exists(self):
        """Verify record_early_exit function is available."""
        from backend.api.middleware.metrics import record_early_exit

        # Function should be callable
        assert callable(record_early_exit)

    def test_record_early_exit_increments_counter(self):
        """Test that record_early_exit increments the counter."""
        from backend.api.middleware.metrics import (
            bo1_early_exit_total,
            record_early_exit,
        )

        # Get initial value (handle case where metric hasn't been used yet)
        try:
            initial = bo1_early_exit_total.labels(reason="convergence_high")._value.get()
        except (KeyError, AttributeError):
            initial = 0.0

        # Record an early exit
        record_early_exit(reason="convergence_high")

        # Verify increment
        new_value = bo1_early_exit_total.labels(reason="convergence_high")._value.get()
        assert new_value == initial + 1
