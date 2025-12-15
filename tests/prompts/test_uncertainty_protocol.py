"""Tests for UNCERTAINTY_FALLBACK protocol and persona prompt injection."""

from bo1.prompts.persona import compose_persona_contribution_prompt
from bo1.prompts.protocols import UNCERTAINTY_FALLBACK


class TestUncertaintyFallbackConstant:
    """Tests for UNCERTAINTY_FALLBACK constant existence and content."""

    def test_uncertainty_fallback_exists(self) -> None:
        """UNCERTAINTY_FALLBACK constant should exist and be non-empty."""
        assert UNCERTAINTY_FALLBACK is not None
        assert len(UNCERTAINTY_FALLBACK) > 0

    def test_uncertainty_fallback_contains_key_guidance(self) -> None:
        """UNCERTAINTY_FALLBACK should contain key uncertainty handling guidance."""
        # Check for critical phrases from the protocol
        assert "I don't have data" in UNCERTAINTY_FALLBACK
        assert "never fabricate" in UNCERTAINTY_FALLBACK.lower()
        assert "conditional analysis" in UNCERTAINTY_FALLBACK.lower()
        assert "assumptions explicitly" in UNCERTAINTY_FALLBACK.lower()

    def test_uncertainty_fallback_has_xml_structure(self) -> None:
        """UNCERTAINTY_FALLBACK should use XML tags for structure."""
        assert "<uncertainty_protocol>" in UNCERTAINTY_FALLBACK
        assert "</uncertainty_protocol>" in UNCERTAINTY_FALLBACK


class TestPersonaPromptUncertaintyInjection:
    """Tests for uncertainty guidance injection into persona prompts."""

    def test_compose_persona_contribution_prompt_includes_uncertainty(self) -> None:
        """compose_persona_contribution_prompt should include uncertainty guidance."""
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

        # Check uncertainty protocol is injected
        assert "<uncertainty_protocol>" in system_prompt
        assert "I don't have data" in system_prompt

    def test_uncertainty_guidance_present_in_all_phases(self) -> None:
        """Uncertainty guidance should be present regardless of round/phase."""
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

            assert "<uncertainty_protocol>" in system_prompt, (
                f"Uncertainty protocol missing in round {round_number}"
            )

    def test_uncertainty_appears_after_forbidden_patterns(self) -> None:
        """Uncertainty protocol should appear after forbidden_patterns block."""
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

        forbidden_pos = system_prompt.find("</forbidden_patterns>")
        uncertainty_pos = system_prompt.find("<uncertainty_protocol>")

        assert forbidden_pos < uncertainty_pos, (
            "Uncertainty protocol should come after forbidden_patterns"
        )
