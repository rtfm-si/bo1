"""Tests for stalled disagreement detection and resolution.

Tests the productive disagreement fix:
- detect_stalled_disagreement()
- update_stalled_disagreement_counter()
- StoppingRulesEvaluator.check_stalled_disagreement()
"""

import pytest

from bo1.graph.quality.stopping_rules import (
    STALLED_CONFLICT_THRESHOLD,
    STALLED_NOVELTY_THRESHOLD,
    STALLED_ROUNDS_FOR_GUIDANCE,
    STALLED_ROUNDS_FOR_SYNTHESIS,
    StoppingRulesEvaluator,
    detect_stalled_disagreement,
    update_stalled_disagreement_counter,
)
from bo1.graph.state import DeliberationGraphState, create_initial_state
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
def base_state(sample_problem: Problem) -> DeliberationGraphState:
    """Create base state for testing."""
    return create_initial_state(
        session_id="test-session",
        problem=sample_problem,
        max_rounds=6,
    )


# ============================================================================
# detect_stalled_disagreement Tests
# ============================================================================


def test_detect_stalled_disagreement_no_metrics(base_state: DeliberationGraphState):
    """Test detection returns not stalled when no metrics available."""
    state = dict(base_state)
    state["metrics"] = None

    result = detect_stalled_disagreement(state)

    assert result["stalled"] is False
    assert result["rounds_stuck"] == 0
    assert result["resolution"] is None


def test_detect_stalled_disagreement_low_conflict(base_state: DeliberationGraphState):
    """Test detection returns not stalled when conflict is low."""
    state = dict(base_state)
    state["metrics"] = DeliberationMetrics(
        conflict_score=0.50,  # Below threshold (0.70)
        novelty_score=0.30,  # Below threshold (0.40)
    )
    state["high_conflict_low_novelty_rounds"] = 3

    result = detect_stalled_disagreement(state)

    assert result["stalled"] is False
    assert result["resolution"] is None


def test_detect_stalled_disagreement_high_novelty(base_state: DeliberationGraphState):
    """Test detection returns not stalled when novelty is high."""
    state = dict(base_state)
    state["metrics"] = DeliberationMetrics(
        conflict_score=0.80,  # Above threshold
        novelty_score=0.50,  # Above threshold (0.40)
    )
    state["high_conflict_low_novelty_rounds"] = 3

    result = detect_stalled_disagreement(state)

    assert result["stalled"] is False
    assert result["resolution"] is None


def test_detect_stalled_disagreement_triggers_guidance_at_2_rounds(
    base_state: DeliberationGraphState,
):
    """Test detection triggers guidance after 2 consecutive rounds."""
    state = dict(base_state)
    state["metrics"] = DeliberationMetrics(
        conflict_score=0.80,  # Above threshold
        novelty_score=0.30,  # Below threshold
    )
    state["high_conflict_low_novelty_rounds"] = STALLED_ROUNDS_FOR_GUIDANCE  # 2

    result = detect_stalled_disagreement(state)

    assert result["stalled"] is True
    assert result["rounds_stuck"] == STALLED_ROUNDS_FOR_GUIDANCE
    assert result["resolution"] == "guidance"
    assert result["conflict_score"] == 0.80
    assert result["novelty_score"] == 0.30


def test_detect_stalled_disagreement_forces_synthesis_at_3_rounds(
    base_state: DeliberationGraphState,
):
    """Test detection forces synthesis after 3 consecutive rounds."""
    state = dict(base_state)
    state["metrics"] = DeliberationMetrics(
        conflict_score=0.80,
        novelty_score=0.30,
    )
    state["high_conflict_low_novelty_rounds"] = STALLED_ROUNDS_FOR_SYNTHESIS  # 3

    result = detect_stalled_disagreement(state)

    assert result["stalled"] is True
    assert result["rounds_stuck"] == STALLED_ROUNDS_FOR_SYNTHESIS
    assert result["resolution"] == "force_synthesis"


def test_detect_stalled_disagreement_not_stalled_at_1_round(
    base_state: DeliberationGraphState,
):
    """Test detection returns not stalled at only 1 round (below threshold)."""
    state = dict(base_state)
    state["metrics"] = DeliberationMetrics(
        conflict_score=0.80,
        novelty_score=0.30,
    )
    state["high_conflict_low_novelty_rounds"] = 1  # Below guidance threshold

    result = detect_stalled_disagreement(state)

    # Pattern detected but not enough rounds yet
    assert result["stalled"] is False
    assert result["rounds_stuck"] == 1
    assert result["resolution"] is None


# ============================================================================
# update_stalled_disagreement_counter Tests
# ============================================================================


def test_update_counter_increments_on_stalled_pattern(base_state: DeliberationGraphState):
    """Test counter increments when stalled pattern detected."""
    state = dict(base_state)
    state["metrics"] = DeliberationMetrics(
        conflict_score=0.80,  # Above threshold
        novelty_score=0.30,  # Below threshold
    )
    state["high_conflict_low_novelty_rounds"] = 1

    new_count = update_stalled_disagreement_counter(state)

    assert new_count == 2  # Incremented from 1


def test_update_counter_resets_on_novelty_improvement(base_state: DeliberationGraphState):
    """Test counter resets when novelty improves."""
    state = dict(base_state)
    state["metrics"] = DeliberationMetrics(
        conflict_score=0.80,  # Still high conflict
        novelty_score=0.50,  # Novelty improved above threshold
    )
    state["high_conflict_low_novelty_rounds"] = 2

    new_count = update_stalled_disagreement_counter(state)

    assert new_count == 0  # Reset because pattern broken


def test_update_counter_resets_on_conflict_drop(base_state: DeliberationGraphState):
    """Test counter resets when conflict drops."""
    state = dict(base_state)
    state["metrics"] = DeliberationMetrics(
        conflict_score=0.50,  # Conflict dropped below threshold
        novelty_score=0.30,  # Still low novelty
    )
    state["high_conflict_low_novelty_rounds"] = 2

    new_count = update_stalled_disagreement_counter(state)

    assert new_count == 0  # Reset because pattern broken


def test_update_counter_returns_zero_without_metrics(base_state: DeliberationGraphState):
    """Test counter returns 0 when no metrics available."""
    state = dict(base_state)
    state["metrics"] = None
    state["high_conflict_low_novelty_rounds"] = 3

    new_count = update_stalled_disagreement_counter(state)

    assert new_count == 0


# ============================================================================
# StoppingRulesEvaluator.check_stalled_disagreement Tests
# ============================================================================


def test_evaluator_check_returns_none_when_not_stalled(base_state: DeliberationGraphState):
    """Test evaluator returns None when not stalled."""
    state = dict(base_state)
    state["metrics"] = DeliberationMetrics(
        conflict_score=0.50,  # Low conflict
        novelty_score=0.60,  # High novelty
    )
    state["high_conflict_low_novelty_rounds"] = 0

    evaluator = StoppingRulesEvaluator()
    result = evaluator.check_stalled_disagreement(state)

    assert result is None


def test_evaluator_check_returns_guidance_decision(base_state: DeliberationGraphState):
    """Test evaluator returns guidance decision when stuck 2 rounds."""
    state = dict(base_state)
    state["round_number"] = 4
    state["metrics"] = DeliberationMetrics(
        conflict_score=0.80,
        novelty_score=0.30,
    )
    state["high_conflict_low_novelty_rounds"] = STALLED_ROUNDS_FOR_GUIDANCE

    evaluator = StoppingRulesEvaluator()
    result = evaluator.check_stalled_disagreement(state)

    assert result is not None
    assert result.should_stop is False
    assert result.facilitator_guidance is not None
    assert result.facilitator_guidance["type"] == "impasse_intervention"
    assert "resolution_options" in result.facilitator_guidance
    assert len(result.facilitator_guidance["resolution_options"]) == 3


def test_evaluator_check_returns_stop_decision_at_3_rounds(base_state: DeliberationGraphState):
    """Test evaluator returns stop decision when stuck 3+ rounds."""
    state = dict(base_state)
    state["round_number"] = 5
    state["metrics"] = DeliberationMetrics(
        conflict_score=0.80,
        novelty_score=0.30,
    )
    state["high_conflict_low_novelty_rounds"] = STALLED_ROUNDS_FOR_SYNTHESIS

    evaluator = StoppingRulesEvaluator()
    result = evaluator.check_stalled_disagreement(state)

    assert result is not None
    assert result.should_stop is True
    assert result.stop_reason == "stalled_disagreement"


# ============================================================================
# Threshold Constants Tests
# ============================================================================


def test_threshold_constants():
    """Test that threshold constants are set correctly."""
    assert STALLED_CONFLICT_THRESHOLD == 0.70
    assert STALLED_NOVELTY_THRESHOLD == 0.40
    assert STALLED_ROUNDS_FOR_GUIDANCE == 2
    assert STALLED_ROUNDS_FOR_SYNTHESIS == 3
