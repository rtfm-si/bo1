"""Tests for uncertainty handling in protocols and persona prompts.

Note: UNCERTAINTY_FALLBACK was consolidated into BEHAVIORAL_GUIDELINES,
then BEHAVIORAL_GUIDELINES + EVIDENCE_PROTOCOL were further consolidated
into CORE_PROTOCOL for ~180 token savings per contribution.

These tests verify the core behavioral requirements are still enforced.
"""

from bo1.prompts.persona import compose_persona_contribution_prompt
from bo1.prompts.protocols import (
    BEHAVIORAL_GUIDELINES,
    CORE_PROTOCOL,
    UNCERTAINTY_FALLBACK,
)


class TestLegacyProtocols:
    """Tests for legacy protocols (kept for backward compatibility)."""

    def test_uncertainty_fallback_deprecated(self) -> None:
        """UNCERTAINTY_FALLBACK should be empty (deprecated)."""
        assert UNCERTAINTY_FALLBACK == ""

    def test_behavioral_guidelines_still_exists(self) -> None:
        """BEHAVIORAL_GUIDELINES should still exist for backward compatibility."""
        assert "<behavioral_guidelines>" in BEHAVIORAL_GUIDELINES
        assert "</behavioral_guidelines>" in BEHAVIORAL_GUIDELINES
        assert "WHEN UNCERTAIN" in BEHAVIORAL_GUIDELINES


class TestCoreProtocol:
    """Tests for the consolidated CORE_PROTOCOL."""

    def test_core_protocol_has_xml_structure(self) -> None:
        """CORE_PROTOCOL should use XML tags for structure."""
        assert "<core_protocol>" in CORE_PROTOCOL
        assert "</core_protocol>" in CORE_PROTOCOL

    def test_core_protocol_contains_uncertainty_handling(self) -> None:
        """CORE_PROTOCOL should contain uncertainty handling guidance."""
        # Critical uncertainty handling phrases (compressed format)
        assert "UNCERTAIN" in CORE_PROTOCOL
        assert "uncertain" in CORE_PROTOCOL.lower()
        assert "defer" in CORE_PROTOCOL.lower()

    def test_core_protocol_contains_citation_guidance(self) -> None:
        """CORE_PROTOCOL should contain citation guidance."""
        assert "<citation>" in CORE_PROTOCOL
        assert "Problem statement" in CORE_PROTOCOL
        assert "Research" in CORE_PROTOCOL

    def test_core_protocol_contains_behavioral_rules(self) -> None:
        """CORE_PROTOCOL should contain ALWAYS/NEVER behavioral rules."""
        assert "ALWAYS:" in CORE_PROTOCOL
        assert "NEVER:" in CORE_PROTOCOL

    def test_core_protocol_contains_examples(self) -> None:
        """CORE_PROTOCOL should contain examples."""
        assert "<examples>" in CORE_PROTOCOL
        assert "✅" in CORE_PROTOCOL
        assert "❌" in CORE_PROTOCOL

    def test_core_protocol_is_shorter_than_legacy(self) -> None:
        """CORE_PROTOCOL should be significantly shorter than legacy combined."""
        from bo1.prompts.protocols import EVIDENCE_PROTOCOL

        legacy_combined_len = len(BEHAVIORAL_GUIDELINES) + len(EVIDENCE_PROTOCOL)
        consolidated_len = len(CORE_PROTOCOL)

        # Should be at least 30% shorter (target is ~50% reduction)
        assert consolidated_len < legacy_combined_len * 0.7, (
            f"CORE_PROTOCOL ({consolidated_len} chars) should be <70% of "
            f"legacy combined ({legacy_combined_len} chars)"
        )


class TestPersonaPromptProtocolInjection:
    """Tests for protocol injection into persona prompts."""

    def test_compose_persona_contribution_prompt_includes_core_protocol(
        self,
    ) -> None:
        """compose_persona_contribution_prompt should include CORE_PROTOCOL."""
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

        # Check CORE_PROTOCOL (which includes uncertainty handling) is injected
        assert "<core_protocol>" in system_prompt
        assert "UNCERTAIN" in system_prompt

    def test_core_protocol_present_in_all_phases(self) -> None:
        """Core protocol should be present regardless of round/phase."""
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

            assert "<core_protocol>" in system_prompt, (
                f"Core protocol missing in round {round_number}"
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
