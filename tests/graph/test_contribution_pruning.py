"""Tests for contribution pruning after convergence.

Tests prune_contributions_for_phase() functionality:
- Keeps last N contributions
- Skips if not at synthesis phase
- No-op if already small
- Preserves current round contributions
- Logs pruned count
"""

import logging
from datetime import datetime

from bo1.constants import ContributionPruning
from bo1.graph.state import (
    DeliberationGraphState,
    create_initial_state,
    prune_contributions_for_phase,
)
from bo1.models.problem import Problem
from bo1.models.state import ContributionMessage, ContributionType, DeliberationPhase


def _make_contribution(
    round_number: int,
    persona_code: str = "expert_1",
    persona_name: str = "Expert One",
    content: str = "Test contribution content",
) -> ContributionMessage:
    """Create a test contribution."""
    return ContributionMessage(
        persona_code=persona_code,
        persona_name=persona_name,
        content=content,
        round_number=round_number,
        contribution_type=ContributionType.INITIAL,
        timestamp=datetime.now(),
    )


def _make_state_with_contributions(
    contributions: list[ContributionMessage],
    phase: DeliberationPhase = DeliberationPhase.SYNTHESIS,
    round_number: int = 4,
) -> DeliberationGraphState:
    """Create a state with contributions for testing."""
    problem = Problem(
        title="Test Problem",
        description="Test problem description",
        context="Test context",
        sub_problems=[],
    )
    state = create_initial_state(session_id="test-session", problem=problem)
    state["contributions"] = contributions
    state["phase"] = phase
    state["round_number"] = round_number
    return state


class TestPruneContributionsForPhase:
    """Tests for prune_contributions_for_phase function."""

    def test_prune_keeps_last_n_contributions(self):
        """Should keep only the last N contributions when pruning."""
        # Create 12 contributions across 4 rounds
        contributions = []
        for round_num in range(1, 5):
            for i in range(3):
                contributions.append(_make_contribution(round_num, f"expert_{i}"))

        state = _make_state_with_contributions(
            contributions, phase=DeliberationPhase.SYNTHESIS, round_number=4
        )

        result = prune_contributions_for_phase(state, retain_count=6)

        # Should retain 6 contributions
        assert len(result) == 6
        # Current round (4) should be preserved - 3 contributions
        current_round_count = sum(1 for c in result if c.round_number == 4)
        assert current_round_count == 3

    def test_prune_skips_if_not_convergence_phase(self):
        """Should not prune if not at synthesis phase or later."""
        contributions = [_make_contribution(i) for i in range(10)]
        state = _make_state_with_contributions(
            contributions, phase=DeliberationPhase.DISCUSSION, round_number=3
        )

        result = prune_contributions_for_phase(state, retain_count=6)

        # Should return all contributions unchanged
        assert len(result) == 10

    def test_prune_noop_if_already_small(self):
        """Should not prune if contributions <= retain_count."""
        contributions = [_make_contribution(i) for i in range(5)]
        state = _make_state_with_contributions(
            contributions, phase=DeliberationPhase.SYNTHESIS, round_number=4
        )

        result = prune_contributions_for_phase(state, retain_count=6)

        # Should return all contributions unchanged
        assert len(result) == 5

    def test_prune_preserves_current_round(self):
        """Should always preserve contributions from current round."""
        # Create 4 contributions in round 1, and 5 in current round 4
        contributions = [_make_contribution(1) for _ in range(4)]
        contributions.extend([_make_contribution(4) for _ in range(5)])

        state = _make_state_with_contributions(
            contributions, phase=DeliberationPhase.SYNTHESIS, round_number=4
        )

        # Even with retain_count=6, we should keep all 5 from current round
        result = prune_contributions_for_phase(state, retain_count=6)

        # Should keep all 5 from current round + 1 from previous
        current_round_count = sum(1 for c in result if c.round_number == 4)
        assert current_round_count == 5
        # Total should be 6 (5 current + 1 previous)
        assert len(result) == 6

    def test_prune_logs_pruned_count(self, caplog):
        """Should log the pruned count for observability."""
        contributions = [_make_contribution(i % 3 + 1) for i in range(12)]
        state = _make_state_with_contributions(
            contributions, phase=DeliberationPhase.SYNTHESIS, round_number=3
        )
        state["session_id"] = "test-log-session"

        with caplog.at_level(logging.INFO):
            prune_contributions_for_phase(state, retain_count=6)

        # Should log pruning info
        assert any("prune_contributions_for_phase" in record.message for record in caplog.records)
        assert any("pruned=" in record.message for record in caplog.records)

    def test_prune_with_default_config(self):
        """Should use ContributionPruning.RETENTION_COUNT when not specified."""
        # Create more contributions than default retention count
        num_contributions = ContributionPruning.RETENTION_COUNT + 10
        contributions = [_make_contribution(i % 4 + 1) for i in range(num_contributions)]

        state = _make_state_with_contributions(
            contributions, phase=DeliberationPhase.SYNTHESIS, round_number=4
        )

        result = prune_contributions_for_phase(state)

        # Should use default retention count
        assert len(result) <= ContributionPruning.RETENTION_COUNT + 3  # Allow for current round

    def test_prune_at_complete_phase(self):
        """Should also prune at COMPLETE phase."""
        contributions = [_make_contribution(i) for i in range(10)]
        state = _make_state_with_contributions(
            contributions, phase=DeliberationPhase.COMPLETE, round_number=4
        )

        result = prune_contributions_for_phase(state, retain_count=6)

        # Should prune at COMPLETE phase too
        assert len(result) <= 6

    def test_prune_maintains_chronological_order(self):
        """Should maintain chronological order in pruned contributions."""
        contributions = []
        for round_num in range(1, 5):
            contributions.append(_make_contribution(round_num, content=f"Round {round_num}"))

        state = _make_state_with_contributions(
            contributions, phase=DeliberationPhase.SYNTHESIS, round_number=4
        )

        result = prune_contributions_for_phase(state, retain_count=2)

        # Should be in chronological order (earlier rounds first)
        round_numbers = [c.round_number for c in result]
        assert round_numbers == sorted(round_numbers)

    def test_prune_empty_contributions(self):
        """Should handle empty contributions list."""
        state = _make_state_with_contributions(
            [], phase=DeliberationPhase.SYNTHESIS, round_number=4
        )

        result = prune_contributions_for_phase(state, retain_count=6)

        assert result == []

    def test_prune_all_current_round(self):
        """Should handle case where all contributions are from current round."""
        contributions = [_make_contribution(4) for _ in range(8)]
        state = _make_state_with_contributions(
            contributions, phase=DeliberationPhase.SYNTHESIS, round_number=4
        )

        result = prune_contributions_for_phase(state, retain_count=6)

        # Should keep all current round contributions (they're all from current round)
        assert len(result) == 8
        assert all(c.round_number == 4 for c in result)
