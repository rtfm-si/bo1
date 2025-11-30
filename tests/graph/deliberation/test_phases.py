"""Tests for phase management."""

from bo1.graph.deliberation.phases import DeliberationPhase, PhaseManager


class TestPhaseManager:
    """Test phase calculation logic."""

    def test_determine_phase_exploration_early(self):
        """First third of rounds = exploration."""
        assert PhaseManager.determine_phase(1, 6) == "exploration"
        assert PhaseManager.determine_phase(2, 6) == "exploration"

    def test_determine_phase_challenge_middle(self):
        """Middle third = challenge."""
        assert PhaseManager.determine_phase(3, 6) == "challenge"
        assert PhaseManager.determine_phase(4, 6) == "challenge"

    def test_determine_phase_convergence_late(self):
        """Final third = convergence."""
        assert PhaseManager.determine_phase(5, 6) == "convergence"
        assert PhaseManager.determine_phase(6, 6) == "convergence"

    def test_determine_phase_short_deliberation(self):
        """3-round deliberation - with min boundaries, phases skew toward exploration.

        With max_rounds=3:
        - exploration_end = max(2, 3//3) = max(2, 1) = 2
        - challenge_end = max(4, 2*3//3) = max(4, 2) = 4

        So rounds 1-2 are exploration, 3-4 are challenge, 5+ is convergence.
        But with only 3 rounds, round 3 is still in "challenge" range.
        """
        assert PhaseManager.determine_phase(1, 3) == "exploration"
        assert (
            PhaseManager.determine_phase(2, 3) == "exploration"
        )  # Still exploration due to min boundary
        assert PhaseManager.determine_phase(3, 3) == "challenge"  # challenge range (3-4)

    def test_determine_phase_very_short_deliberation(self):
        """2-round deliberation defaults to minimum boundaries."""
        # With max_rounds=2: exploration_end=max(2, 2//3)=2, challenge_end=max(4, 2*2//3)=4
        # Round 1 <= 2 -> exploration
        # Round 2 <= 2 -> exploration (since both fit in exploration)
        assert PhaseManager.determine_phase(1, 2) == "exploration"
        assert PhaseManager.determine_phase(2, 2) == "exploration"

    def test_determine_phase_4_rounds(self):
        """4-round deliberation has phases."""
        # exploration_end = max(2, 4//3) = max(2, 1) = 2
        # challenge_end = max(4, 2*4//3) = max(4, 2) = 4
        assert PhaseManager.determine_phase(1, 4) == "exploration"
        assert PhaseManager.determine_phase(2, 4) == "exploration"
        assert PhaseManager.determine_phase(3, 4) == "challenge"
        assert PhaseManager.determine_phase(4, 4) == "challenge"

    def test_get_phase_prompt_exploration(self):
        """Exploration phase prompt contains correct keywords."""
        prompt = PhaseManager.get_phase_prompt("exploration", 1)
        assert "EXPLORATION" in prompt
        assert "Round 1" in prompt
        assert "diverse" in prompt.lower()

    def test_get_phase_prompt_challenge(self):
        """Challenge phase prompt contains correct keywords."""
        prompt = PhaseManager.get_phase_prompt("challenge", 3)
        assert "CHALLENGE" in prompt
        assert "Round 3" in prompt
        assert "critical" in prompt.lower()

    def test_get_phase_prompt_convergence(self):
        """Convergence phase prompt contains correct keywords."""
        prompt = PhaseManager.get_phase_prompt("convergence", 5)
        assert "CONVERGENCE" in prompt
        assert "Round 5" in prompt
        assert "converge" in prompt.lower()

    def test_get_phase_prompt_short(self):
        """Short phase labels are human-readable."""
        assert PhaseManager.get_phase_prompt_short("exploration") == "Exploring"
        assert PhaseManager.get_phase_prompt_short("challenge") == "Challenging"
        assert PhaseManager.get_phase_prompt_short("convergence") == "Converging"


class TestDeliberationPhase:
    """Test DeliberationPhase type."""

    def test_phase_values(self):
        """All phase values are valid."""
        phases: list[DeliberationPhase] = ["exploration", "challenge", "convergence"]
        for phase in phases:
            # Type check - this should not raise
            assert phase in ("exploration", "challenge", "convergence")
