"""Tests for expert selection logic."""

import pytest

from bo1.graph.deliberation.experts import select_experts_for_round


class MockPersona:
    """Mock PersonaProfile for testing."""

    def __init__(self, code: str):
        self.code = code


class MockContribution:
    """Mock ContributionMessage for testing."""

    def __init__(self, persona_code: str):
        self.persona_code = persona_code


class MockMetrics:
    """Mock DeliberationMetrics for testing."""

    def __init__(self, recommended_experts: int = 4):
        self.recommended_experts = recommended_experts


class TestSelectExpertsForRound:
    """Test expert selection logic."""

    @pytest.fixture
    def personas(self):
        """Create 5 mock personas."""
        return [MockPersona(f"expert_{i}") for i in range(5)]

    @pytest.fixture
    def empty_state(self, personas):
        """State with personas but no contributions."""
        return {
            "personas": personas,
            "contributions": [],
            "experts_per_round": [],
            "metrics": MockMetrics(recommended_experts=4),
        }

    @pytest.mark.asyncio
    async def test_exploration_selects_recommended_count(self, empty_state):
        """Exploration phase selects recommended_experts count."""
        selected = await select_experts_for_round(empty_state, "exploration", 1)
        assert len(selected) == 4  # recommended_experts = 4

    @pytest.mark.asyncio
    async def test_exploration_prioritizes_unheard_voices(self, personas):
        """Exploration prioritizes experts with fewer contributions."""
        contributions = [
            MockContribution("expert_0"),
            MockContribution("expert_0"),
            MockContribution("expert_0"),
            MockContribution("expert_1"),
            MockContribution("expert_1"),
        ]
        state = {
            "personas": personas,
            "contributions": contributions,
            "experts_per_round": [],
            "metrics": MockMetrics(recommended_experts=3),
        }
        selected = await select_experts_for_round(state, "exploration", 2)

        # Should select experts with fewest contributions first
        selected_codes = [p.code for p in selected]
        # expert_2, expert_3, expert_4 have 0 contributions
        assert "expert_2" in selected_codes
        assert "expert_3" in selected_codes
        assert "expert_4" in selected_codes

    @pytest.mark.asyncio
    async def test_challenge_selects_fewer_experts(self, empty_state):
        """Challenge phase selects fewer experts (recommended - 1)."""
        selected = await select_experts_for_round(empty_state, "challenge", 3)
        assert len(selected) == 3  # max(2, 4-1) = 3

    @pytest.mark.asyncio
    async def test_challenge_filters_recent_speakers(self, personas):
        """Challenge phase filters out recent speakers."""
        state = {
            "personas": personas,
            "contributions": [],
            "experts_per_round": [
                ["expert_0", "expert_1"],  # Round 1
                ["expert_0", "expert_2"],  # Round 2
            ],
            "metrics": MockMetrics(recommended_experts=4),
        }
        selected = await select_experts_for_round(state, "challenge", 3)
        selected_codes = [p.code for p in selected]

        # expert_0 spoke in both recent rounds (count=2), should be filtered
        assert "expert_0" not in selected_codes

    @pytest.mark.asyncio
    async def test_challenge_fallback_when_all_spoke_recently(self, personas):
        """Challenge phase uses all personas when all spoke recently."""
        # All experts spoke in recent rounds
        state = {
            "personas": personas[:3],  # Only 3 personas
            "contributions": [],
            "experts_per_round": [
                ["expert_0", "expert_1", "expert_2"],
                ["expert_0", "expert_1", "expert_2"],
            ],
            "metrics": MockMetrics(recommended_experts=4),
        }
        selected = await select_experts_for_round(state, "challenge", 3)
        # Should still select some experts (fallback to all)
        assert len(selected) >= 2

    @pytest.mark.asyncio
    async def test_convergence_selects_fewer_experts(self, empty_state):
        """Convergence phase selects fewer experts (recommended - 1)."""
        selected = await select_experts_for_round(empty_state, "convergence", 5)
        assert len(selected) == 3  # max(2, 4-1) = 3

    @pytest.mark.asyncio
    async def test_convergence_balances_contributions(self, personas):
        """Convergence selects least-contributing experts."""
        contributions = [
            MockContribution("expert_0"),
            MockContribution("expert_0"),
            MockContribution("expert_1"),
        ]
        state = {
            "personas": personas,
            "contributions": contributions,
            "experts_per_round": [],
            "metrics": MockMetrics(recommended_experts=4),
        }
        selected = await select_experts_for_round(state, "convergence", 5)
        selected_codes = [p.code for p in selected]

        # Should select experts with fewer contributions
        assert "expert_2" in selected_codes
        assert "expert_3" in selected_codes
        assert "expert_4" in selected_codes

    @pytest.mark.asyncio
    async def test_empty_personas_returns_empty(self):
        """Empty personas list returns empty selection."""
        state = {
            "personas": [],
            "contributions": [],
            "experts_per_round": [],
            "metrics": MockMetrics(),
        }
        selected = await select_experts_for_round(state, "exploration", 1)
        assert selected == []

    @pytest.mark.asyncio
    async def test_missing_personas_returns_empty(self):
        """Missing personas key returns empty selection."""
        state = {
            "contributions": [],
            "experts_per_round": [],
        }
        selected = await select_experts_for_round(state, "exploration", 1)
        assert selected == []

    @pytest.mark.asyncio
    async def test_adaptive_complexity_simple(self, personas):
        """Simple problems use fewer experts."""
        state = {
            "personas": personas,
            "contributions": [],
            "experts_per_round": [],
            "metrics": MockMetrics(recommended_experts=3),
        }
        selected = await select_experts_for_round(state, "exploration", 1)
        assert len(selected) == 3

    @pytest.mark.asyncio
    async def test_adaptive_complexity_complex(self, personas):
        """Complex problems use more experts."""
        state = {
            "personas": personas,
            "contributions": [],
            "experts_per_round": [],
            "metrics": MockMetrics(recommended_experts=5),
        }
        selected = await select_experts_for_round(state, "exploration", 1)
        assert len(selected) == 5

    @pytest.mark.asyncio
    async def test_default_fallback_without_metrics(self, personas):
        """Falls back to 4 experts when metrics unavailable."""
        state = {
            "personas": personas,
            "contributions": [],
            "experts_per_round": [],
            "metrics": None,
        }
        selected = await select_experts_for_round(state, "exploration", 1)
        assert len(selected) == 4

    @pytest.mark.asyncio
    async def test_unknown_phase_uses_default(self, empty_state):
        """Unknown phase uses default selection."""
        selected = await select_experts_for_round(empty_state, "unknown_phase", 1)
        assert len(selected) == 4  # recommended_experts default

    @pytest.mark.asyncio
    async def test_minimum_experts_respected(self, personas):
        """Minimum of 2 experts is respected."""
        state = {
            "personas": personas[:2],  # Only 2 personas
            "contributions": [],
            "experts_per_round": [],
            "metrics": MockMetrics(recommended_experts=1),  # Would be 0 after -1
        }
        selected = await select_experts_for_round(state, "challenge", 3)
        assert len(selected) >= 2

    @pytest.mark.asyncio
    async def test_respects_persona_count_limit(self, personas):
        """Selection respects available persona count."""
        state = {
            "personas": personas[:2],  # Only 2 personas
            "contributions": [],
            "experts_per_round": [],
            "metrics": MockMetrics(recommended_experts=5),
        }
        selected = await select_experts_for_round(state, "exploration", 1)
        assert len(selected) == 2  # Can't select more than available
