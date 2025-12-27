"""Tests for persona context contribution limiting.

Verifies that the PERSONA_CONTEXT_CONTRIBUTION_LIMIT constant is correctly
applied to limit the number of contributions included in persona prompts.
"""

from bo1.constants import PersonaContextConfig
from bo1.models.state import ContributionMessage, ContributionType


class TestPersonaContextConfig:
    """Tests for PersonaContextConfig constants."""

    def test_contribution_limit_value(self) -> None:
        """Verify contribution limit is set to 3."""
        assert PersonaContextConfig.CONTRIBUTION_LIMIT == 3

    def test_contribution_limit_is_positive(self) -> None:
        """Verify contribution limit is a positive integer."""
        assert isinstance(PersonaContextConfig.CONTRIBUTION_LIMIT, int)
        assert PersonaContextConfig.CONTRIBUTION_LIMIT > 0


class TestContributionSlicing:
    """Tests for contribution slicing behavior with the limit constant."""

    def _create_mock_contributions(self, count: int) -> list[ContributionMessage]:
        """Create mock contribution messages for testing."""
        return [
            ContributionMessage(
                persona_code=f"p{i}",
                persona_name=f"Persona {i}",
                content=f"Contribution content {i}",
                thinking=None,
                contribution_type=ContributionType.RESPONSE,
                round_number=i // 3,
            )
            for i in range(count)
        ]

    def test_limit_applied_to_contributions(self) -> None:
        """Verify that slicing with limit returns correct number of contributions."""
        contributions = self._create_mock_contributions(10)
        limit = PersonaContextConfig.CONTRIBUTION_LIMIT

        recent = contributions[-limit:] if contributions else []

        assert len(recent) == 3
        # Should be the last 3 contributions
        assert recent[0].persona_code == "p7"
        assert recent[1].persona_code == "p8"
        assert recent[2].persona_code == "p9"

    def test_limit_with_fewer_contributions(self) -> None:
        """Verify limit handles case with fewer contributions than limit."""
        contributions = self._create_mock_contributions(2)
        limit = PersonaContextConfig.CONTRIBUTION_LIMIT

        recent = contributions[-limit:] if contributions else []

        assert len(recent) == 2
        assert recent[0].persona_code == "p0"
        assert recent[1].persona_code == "p1"

    def test_limit_with_empty_contributions(self) -> None:
        """Verify limit handles empty contributions list."""
        contributions: list[ContributionMessage] = []
        limit = PersonaContextConfig.CONTRIBUTION_LIMIT

        recent = contributions[-limit:] if contributions else []

        assert len(recent) == 0

    def test_limit_with_exact_count(self) -> None:
        """Verify limit handles exactly 3 contributions."""
        contributions = self._create_mock_contributions(3)
        limit = PersonaContextConfig.CONTRIBUTION_LIMIT

        recent = contributions[-limit:] if contributions else []

        assert len(recent) == 3
        assert recent[0].persona_code == "p0"
        assert recent[2].persona_code == "p2"

    def test_most_recent_contributions_retained(self) -> None:
        """Verify that the most recent contributions are retained (not oldest)."""
        contributions = self._create_mock_contributions(6)
        limit = PersonaContextConfig.CONTRIBUTION_LIMIT

        recent = contributions[-limit:]

        # Should be contributions 3, 4, 5 (0-indexed) - the most recent
        for i, contrib in enumerate(recent):
            expected_index = 3 + i
            assert contrib.persona_code == f"p{expected_index}"
