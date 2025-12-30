"""Tests for uncertainty handling in protocols and persona prompts.

Note: UNCERTAINTY_FALLBACK was consolidated into BEHAVIORAL_GUIDELINES
for token efficiency. These tests verify the core uncertainty handling
requirements are still enforced.
"""

from bo1.prompts.persona import compose_persona_contribution_prompt
from bo1.prompts.protocols import BEHAVIORAL_GUIDELINES, UNCERTAINTY_FALLBACK


class TestUncertaintyInBehavioralGuidelines:
    """Tests for uncertainty handling now in BEHAVIORAL_GUIDELINES."""

    def test_uncertainty_fallback_deprecated(self) -> None:
        """UNCERTAINTY_FALLBACK should be empty (deprecated)."""
        assert UNCERTAINTY_FALLBACK == ""

    def test_behavioral_guidelines_contains_uncertainty_handling(self) -> None:
        """BEHAVIORAL_GUIDELINES should contain uncertainty handling guidance."""
        # Critical uncertainty handling phrases
        assert "WHEN UNCERTAIN" in BEHAVIORAL_GUIDELINES
        assert "uncertain" in BEHAVIORAL_GUIDELINES.lower()
        assert "defer" in BEHAVIORAL_GUIDELINES.lower()

    def test_behavioral_guidelines_has_xml_structure(self) -> None:
        """BEHAVIORAL_GUIDELINES should use XML tags for structure."""
        assert "<behavioral_guidelines>" in BEHAVIORAL_GUIDELINES
        assert "</behavioral_guidelines>" in BEHAVIORAL_GUIDELINES


class TestPersonaPromptBehavioralInjection:
    """Tests for behavioral guidelines injection into persona prompts."""

    def test_compose_persona_contribution_prompt_includes_behavioral_guidelines(
        self,
    ) -> None:
        """compose_persona_contribution_prompt should include behavioral guidelines."""
        system_prompt, user_message = compose_persona_contribution_prompt(
            persona_name="Test Expert",
            persona_description="A test expert for testing",
            persona_expertise="Testing and quality assurance",
            persona_communication_style="Direct and analytical",
            problem_statement="Should we adopt test-driven development?",
            previous_contributions=[],
            speaker_prompt="Provide your analysis",
            round_number=1,
        )

        # Check behavioral guidelines (which includes uncertainty handling) are injected
        assert "<behavioral_guidelines>" in system_prompt
        assert "WHEN UNCERTAIN" in system_prompt

    def test_behavioral_guidelines_present_in_all_phases(self) -> None:
        """Behavioral guidelines should be present regardless of round/phase."""
        for round_number in [1, 2, 3, 4, 5, 6]:
            system_prompt, _ = compose_persona_contribution_prompt(
                persona_name="Test Expert",
                persona_description="A test expert",
                persona_expertise="Testing",
                persona_communication_style="Direct",
                problem_statement="Test problem",
                previous_contributions=[],
                speaker_prompt="Analyze",
                round_number=round_number,
            )

            assert "<behavioral_guidelines>" in system_prompt, (
                f"Behavioral guidelines missing in round {round_number}"
            )

    def test_response_format_in_persona_prompt(self) -> None:
        """Response format block should appear in persona prompts."""
        system_prompt, _ = compose_persona_contribution_prompt(
            persona_name="Test Expert",
            persona_description="A test expert",
            persona_expertise="Testing",
            persona_communication_style="Direct",
            problem_statement="Test problem",
            previous_contributions=[],
            speaker_prompt="Analyze",
            round_number=1,
        )

        # Check new compact response_format block exists
        assert "<response_format>" in system_prompt
        assert "actionable recommendation" in system_prompt
