"""Tests for ResponseParser facilitator action parsing and contribution validation."""

from unittest.mock import MagicMock

import pytest

from bo1.constants import TokenLimits
from bo1.llm.response_parser import ResponseParser


class TestParseFacilitatorDecision:
    """Test facilitator decision parsing with XML and keyword extraction."""

    @pytest.fixture
    def mock_state(self):
        """Create mock state with session_id and personas."""
        persona1 = MagicMock()
        persona1.code = "ceo"
        persona1.name = "CEO"
        persona2 = MagicMock()
        persona2.code = "cto"
        persona2.name = "CTO"
        return {
            "session_id": "bo1_test123",
            "personas": [persona1, persona2],
        }

    def test_parse_action_from_xml_tag(self, mock_state):
        """Verify action extracted from <action> XML tag."""
        content = """<thinking>Analysis here</thinking>
        <action>continue</action>
        <next_speaker>ceo</next_speaker>"""

        result = ResponseParser.parse_facilitator_decision(content, mock_state)

        assert result["action"] == "continue"

    def test_parse_action_from_decision_tag(self, mock_state):
        """Verify action extracted from <decision> XML tag."""
        content = """<thinking>Time to vote</thinking>
        <decision>vote</decision>
        <summary>Discussion complete</summary>"""

        result = ResponseParser.parse_facilitator_decision(content, mock_state)

        assert result["action"] == "vote"

    def test_parse_action_xml_case_insensitive(self, mock_state):
        """Verify XML action parsing is case insensitive."""
        content = """<action>RESEARCH</action>
        <query>Market analysis needed</query>"""

        result = ResponseParser.parse_facilitator_decision(content, mock_state)

        assert result["action"] == "research"

    def test_parse_action_from_option_a_keyword(self, mock_state):
        """Verify 'Option A' keyword maps to continue."""
        content = """Based on the analysis, I choose Option A.
        The discussion should continue with the CTO."""

        result = ResponseParser.parse_facilitator_decision(content, mock_state)

        assert result["action"] == "continue"

    def test_parse_action_from_option_b_keyword(self, mock_state):
        """Verify 'Option B' keyword maps to vote."""
        content = """After careful consideration, Option B is best.
        We should transition to voting."""

        result = ResponseParser.parse_facilitator_decision(content, mock_state)

        assert result["action"] == "vote"

    def test_parse_action_from_research_keyword(self, mock_state):
        """Verify 'research' keyword is detected."""
        content = """We need more research on the market trends
        before making a decision."""

        result = ResponseParser.parse_facilitator_decision(content, mock_state)

        assert result["action"] == "research"

    def test_parse_action_from_moderator_keyword(self, mock_state):
        """Verify 'moderator' keyword is detected."""
        content = """A moderator intervention is needed to
        challenge the current consensus."""

        result = ResponseParser.parse_facilitator_decision(content, mock_state)

        assert result["action"] == "moderator"

    def test_parse_action_from_clarify_keyword(self, mock_state):
        """Verify 'clarify' or 'clarification' keyword is detected."""
        content = """We need clarification from the user
        about their budget constraints."""

        result = ResponseParser.parse_facilitator_decision(content, mock_state)

        assert result["action"] == "clarify"

    def test_parse_invalid_defaults_to_continue(self, mock_state):
        """Verify invalid/unclear input defaults to 'continue'."""
        content = """Some random gibberish that doesn't match
        any known action pattern or XML tag."""

        result = ResponseParser.parse_facilitator_decision(content, mock_state)

        assert result["action"] == "continue"

    def test_parse_all_valid_actions(self, mock_state):
        """Verify all 5 valid actions parse correctly from XML."""
        for action in ["continue", "vote", "research", "moderator", "clarify"]:
            content = f"<action>{action}</action>"
            result = ResponseParser.parse_facilitator_decision(content, mock_state)
            assert result["action"] == action, f"Failed for action: {action}"

    def test_parse_extracts_reasoning(self, mock_state):
        """Verify reasoning is extracted from <thinking> tag."""
        content = """<thinking>The discussion needs more depth</thinking>
        <action>continue</action>"""

        result = ResponseParser.parse_facilitator_decision(content, mock_state)

        assert "discussion needs more depth" in result["reasoning"]

    def test_parse_reasoning_fallback_to_content(self, mock_state):
        """Verify reasoning falls back to content preview if no <thinking> tag."""
        content = """Option A - continue discussion with CEO"""

        result = ResponseParser.parse_facilitator_decision(content, mock_state)

        assert "Option A" in result["reasoning"]

    def test_xml_takes_priority_over_keyword(self, mock_state):
        """Verify XML tag takes priority when both present."""
        # Content has "vote" keyword but XML says "continue"
        content = """We could vote but <action>continue</action> is better."""

        result = ResponseParser.parse_facilitator_decision(content, mock_state)

        assert result["action"] == "continue"

    def test_invalid_xml_value_falls_back_to_keyword(self, mock_state):
        """Verify invalid XML value triggers keyword fallback."""
        content = """<action>invalid_action</action>
        Let's vote on this proposal."""

        result = ResponseParser.parse_facilitator_decision(content, mock_state)

        assert result["action"] == "vote"


class TestValidateContributionContent:
    """Test contribution content validation for length limits."""

    def test_validate_contribution_overlength(self):
        """Verify overlength contributions are rejected."""
        # 400 words exceeds 300 limit
        long_content = "word " * 400
        is_valid, reason = ResponseParser.validate_contribution_content(long_content, "TestPersona")

        assert is_valid is False
        assert "Overlength" in reason
        assert "400" in reason
        assert str(TokenLimits.MAX_CONTRIBUTION_WORDS) in reason

    def test_validate_contribution_exact_limit(self):
        """Verify contributions at exact limit pass."""
        # Exactly 300 words should pass
        exact_content = "word " * TokenLimits.MAX_CONTRIBUTION_WORDS
        is_valid, reason = ResponseParser.validate_contribution_content(
            exact_content, "TestPersona"
        )

        assert is_valid is True
        assert reason == ""

    def test_validate_contribution_under_limit(self):
        """Verify contributions under limit pass."""
        # 100 words is well under limit
        short_content = "word " * 100
        is_valid, reason = ResponseParser.validate_contribution_content(
            short_content, "TestPersona"
        )

        assert is_valid is True
        assert reason == ""

    def test_validate_contribution_too_short(self):
        """Verify too-short contributions are rejected."""
        # 10 words is below 20 minimum
        short_content = "word " * 10
        is_valid, reason = ResponseParser.validate_contribution_content(
            short_content, "TestPersona"
        )

        assert is_valid is False
        assert "Insufficient substance" in reason


class TestTruncateContribution:
    """Test contribution truncation at sentence boundaries."""

    def test_truncate_at_sentence_boundary(self):
        """Verify truncation prefers sentence boundaries."""
        # Create content with clear sentences
        content = "This is sentence one. This is sentence two. " + "More words. " * 100
        result = ResponseParser.truncate_contribution(content, max_words=50)

        assert "[truncated]" in result
        # Should end at a sentence boundary
        assert result.removesuffix(" [truncated]").endswith(".")

    def test_truncate_preserves_minimum(self):
        """Verify truncation preserves at least 50% of content."""
        # Create content where sentence boundary would leave < 50%
        content = "Short first sentence. " + "word " * 100
        result = ResponseParser.truncate_contribution(content, max_words=50)

        # Should have at least 25 words (50% of 50)
        word_count = len(result.replace("[truncated]", "").split())
        assert word_count >= 25

    def test_truncate_no_action_under_limit(self):
        """Verify no truncation when under limit."""
        content = "This is a short contribution with just a few words."
        result = ResponseParser.truncate_contribution(content, max_words=300)

        assert result == content
        assert "[truncated]" not in result

    def test_truncate_word_boundary_fallback(self):
        """Verify word boundary fallback when no sentence boundary."""
        # Content without sentence endings
        content = "word " * 400
        result = ResponseParser.truncate_contribution(content, max_words=50)

        assert "[truncated]" in result
        # Should have approximately 50 words + marker
        word_count = len(result.split())
        assert word_count <= 52  # 50 + [truncated]
