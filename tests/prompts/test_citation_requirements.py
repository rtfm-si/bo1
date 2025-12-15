"""Tests for citation requirements in masked persona prompts."""

from bo1.prompts.moderator import compose_moderator_prompt
from bo1.prompts.protocols import CITATION_REQUIREMENTS
from bo1.prompts.researcher import compose_researcher_prompt


class TestCitationRequirementsConstant:
    """Test CITATION_REQUIREMENTS constant format and content."""

    def test_citation_requirements_has_minimum_sources(self):
        """Verify CITATION_REQUIREMENTS specifies minimum source counts."""
        assert "3-5 sources" in CITATION_REQUIREMENTS
        assert "Researcher" in CITATION_REQUIREMENTS
        assert "Moderator" in CITATION_REQUIREMENTS

    def test_citation_requirements_has_source_format(self):
        """Verify CITATION_REQUIREMENTS includes structured source format."""
        assert "<source>" in CITATION_REQUIREMENTS
        assert "<url>" in CITATION_REQUIREMENTS
        assert "<name>" in CITATION_REQUIREMENTS
        assert "<type>" in CITATION_REQUIREMENTS
        assert "<relevance>" in CITATION_REQUIREMENTS

    def test_citation_requirements_has_validation_rules(self):
        """Verify CITATION_REQUIREMENTS includes validation guidance."""
        assert "MUST have a valid URL" in CITATION_REQUIREMENTS
        assert "https://" in CITATION_REQUIREMENTS

    def test_citation_requirements_has_failure_guidance(self):
        """Verify CITATION_REQUIREMENTS includes fallback guidance."""
        assert "Do NOT fabricate" in CITATION_REQUIREMENTS
        assert "fewer than" in CITATION_REQUIREMENTS.lower()


class TestResearcherPromptCitations:
    """Test researcher prompt includes citation requirements."""

    def test_researcher_prompt_includes_citation_requirements(self):
        """Verify compose_researcher_prompt includes CITATION_REQUIREMENTS."""
        prompt = compose_researcher_prompt(
            problem_statement="Test problem",
            discussion_excerpt="Discussion excerpt",
            what_personas_need="Market data",
            specific_query="What is the market size?",
        )

        assert "citation_requirements" in prompt or "<citation_requirements>" in prompt
        assert "3-5 sources" in prompt
        assert "HARD REQUIREMENT" in prompt

    def test_researcher_prompt_requires_minimum_citations(self):
        """Verify researcher prompt emphasizes minimum 3 citations."""
        prompt = compose_researcher_prompt(
            problem_statement="Test",
            discussion_excerpt="Discussion",
            what_personas_need="Info",
            specific_query="Query",
        )

        assert "minimum 3" in prompt.lower() or "3-5 sources" in prompt.lower()

    def test_researcher_output_format_structured(self):
        """Verify researcher prompt has structured output format for sources."""
        prompt = compose_researcher_prompt(
            problem_statement="Test",
            discussion_excerpt="Discussion",
            what_personas_need="Info",
            specific_query="Query",
        )

        # Should have structured source format instructions
        assert "<source>" in prompt
        assert "<url>" in prompt
        assert "<type>" in prompt


class TestModeratorPromptCitations:
    """Test moderator prompt includes citation requirements."""

    def test_moderator_prompt_includes_citation_requirements(self):
        """Verify compose_moderator_prompt includes CITATION_REQUIREMENTS."""
        prompt = compose_moderator_prompt(
            persona_name="Test Moderator",
            persona_archetype="contrarian",
            moderator_specific_role="Challenge assumptions",
            moderator_task_specific="questioning consensus",
            problem_statement="Test problem",
            discussion_excerpt="Discussion excerpt",
            trigger_reason="Groupthink detected",
        )

        assert "<citation_requirements>" in prompt
        # Moderator has soft requirement (1 source)
        assert "SOFT REQUIREMENT" in prompt

    def test_moderator_prompt_lower_citation_threshold(self):
        """Verify moderator prompt has lower citation requirement than researcher."""
        prompt = compose_moderator_prompt(
            persona_name="Test",
            persona_archetype="contrarian",
            moderator_specific_role="Challenge",
            moderator_task_specific="challenging",
            problem_statement="Test",
            discussion_excerpt="Discussion",
            trigger_reason="Reason",
        )

        # Moderator should require 1+ sources, not 3-5
        assert "1+" in prompt or "at least 1" in prompt.lower()

    def test_moderator_intervention_mentions_citations(self):
        """Verify intervention format mentions citations."""
        prompt = compose_moderator_prompt(
            persona_name="Test",
            persona_archetype="contrarian",
            moderator_specific_role="Challenge",
            moderator_task_specific="challenging",
            problem_statement="Test",
            discussion_excerpt="Discussion",
            trigger_reason="Reason",
        )

        assert "source citation" in prompt.lower() or "factual claims" in prompt.lower()
