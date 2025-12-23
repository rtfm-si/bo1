"""Tests for ResponseParser facilitator action parsing and contribution validation."""

from unittest.mock import MagicMock

import pytest

from bo1.constants import TokenLimits
from bo1.llm.response_parser import (
    CHALLENGE_INDICATOR_PATTERNS,
    GENERIC_AGREEMENT_PATTERNS,
    CitationValidationResult,
    ResponseParser,
    XMLValidationError,
    XMLValidator,
    get_facilitator_parse_stats,
    reset_facilitator_parse_stats,
    validate_citations,
)


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

    def test_parse_missing_action_tag_raises_error(self, mock_state):
        """Verify missing <action> tag raises XMLValidationError."""
        content = """Based on the analysis, I choose Option A.
        The discussion should continue with the CTO."""

        with pytest.raises(XMLValidationError) as exc_info:
            ResponseParser.parse_facilitator_decision(content, mock_state)

        assert exc_info.value.tag == "action"
        assert "Missing required" in str(exc_info.value)

    def test_parse_invalid_action_value_raises_error(self, mock_state):
        """Verify invalid action value raises XMLValidationError."""
        content = """<thinking>Analysis</thinking>
        <action>dance_party</action>"""

        with pytest.raises(XMLValidationError) as exc_info:
            ResponseParser.parse_facilitator_decision(content, mock_state)

        assert exc_info.value.tag == "action"
        assert "dance_party" in str(exc_info.value)

    def test_parse_no_fallback_to_keyword(self, mock_state):
        """Verify keyword-only content raises XMLValidationError (no fallback)."""
        content = """We need more research on the market trends
        before making a decision."""

        with pytest.raises(XMLValidationError) as exc_info:
            ResponseParser.parse_facilitator_decision(content, mock_state)

        assert exc_info.value.tag == "action"

    def test_parse_no_fallback_to_moderator_keyword(self, mock_state):
        """Verify moderator keyword without XML raises XMLValidationError."""
        content = """A moderator intervention is needed to
        challenge the current consensus."""

        with pytest.raises(XMLValidationError):
            ResponseParser.parse_facilitator_decision(content, mock_state)

    def test_parse_no_fallback_to_clarify_keyword(self, mock_state):
        """Verify clarify keyword without XML raises XMLValidationError."""
        content = """We need clarification from the user
        about their budget constraints."""

        with pytest.raises(XMLValidationError):
            ResponseParser.parse_facilitator_decision(content, mock_state)

    def test_parse_gibberish_raises_error(self, mock_state):
        """Verify gibberish without action tag raises XMLValidationError."""
        content = """Some random gibberish that doesn't match
        any known action pattern or XML tag."""

        with pytest.raises(XMLValidationError) as exc_info:
            ResponseParser.parse_facilitator_decision(content, mock_state)

        assert exc_info.value.tag == "action"

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
        content = """<action>continue</action>
        Option A - continue discussion with CEO"""

        result = ResponseParser.parse_facilitator_decision(content, mock_state)

        assert "Option A" in result["reasoning"]

    def test_xml_takes_priority_over_keyword(self, mock_state):
        """Verify XML tag takes priority when both present."""
        # Content has "vote" keyword but XML says "continue"
        content = """We could vote but <action>continue</action> is better."""

        result = ResponseParser.parse_facilitator_decision(content, mock_state)

        assert result["action"] == "continue"

    def test_invalid_xml_value_raises_error(self, mock_state):
        """Verify invalid XML value raises XMLValidationError (no keyword fallback)."""
        content = """<action>invalid_action</action>
        Let's vote on this proposal."""

        with pytest.raises(XMLValidationError) as exc_info:
            ResponseParser.parse_facilitator_decision(content, mock_state)

        assert exc_info.value.tag == "action"
        assert "invalid_action" in str(exc_info.value)


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


class TestXMLValidator:
    """Test XML validation for LLM responses."""

    def test_find_unclosed_tags_single(self):
        """Verify single unclosed tag is detected."""
        text = "<thinking>Analysis without closing tag"
        unclosed = XMLValidator.find_unclosed_tags(text)
        assert "thinking" in unclosed

    def test_find_unclosed_tags_multiple(self):
        """Verify multiple unclosed tags are detected."""
        text = "<thinking>Analysis<contribution>Content"
        unclosed = XMLValidator.find_unclosed_tags(text)
        assert "thinking" in unclosed
        assert "contribution" in unclosed

    def test_find_unclosed_tags_properly_closed(self):
        """Verify properly closed tags return empty list."""
        text = "<thinking>Analysis</thinking><contribution>Content</contribution>"
        unclosed = XMLValidator.find_unclosed_tags(text)
        assert len(unclosed) == 0

    def test_find_unclosed_tags_ignores_unknown(self):
        """Verify unknown tags are ignored."""
        text = "<custom_tag>Content without closing"
        unclosed = XMLValidator.find_unclosed_tags(text)
        assert len(unclosed) == 0

    def test_find_invalid_nesting_correct(self):
        """Verify correct nesting returns empty list."""
        text = "<thinking><contribution>Nested</contribution></thinking>"
        invalid = XMLValidator.find_invalid_nesting(text)
        assert len(invalid) == 0

    def test_find_invalid_nesting_interleaved(self):
        """Verify interleaved tags are detected."""
        text = "<thinking>Start<contribution>Middle</thinking>End</contribution>"
        invalid = XMLValidator.find_invalid_nesting(text)
        # contribution opened inside thinking but thinking closed first
        assert len(invalid) > 0

    def test_validate_valid_content(self):
        """Verify valid XML passes validation."""
        text = "<thinking>Analysis</thinking><action>continue</action>"
        is_valid, errors = XMLValidator.validate(text)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_unclosed_tag(self):
        """Verify unclosed tag fails validation."""
        text = "<thinking>Analysis without closing"
        is_valid, errors = XMLValidator.validate(text)
        assert is_valid is False
        assert any("Unclosed" in e for e in errors)

    def test_validate_missing_required(self):
        """Verify missing required tag fails validation."""
        text = "<thinking>Analysis</thinking>"
        is_valid, errors = XMLValidator.validate(text, required_tags=["action"])
        assert is_valid is False
        assert any("Missing required" in e for e in errors)

    def test_validate_required_present(self):
        """Verify required tag present passes validation."""
        text = "<thinking>Analysis</thinking><action>continue</action>"
        is_valid, errors = XMLValidator.validate(text, required_tags=["action"])
        assert is_valid is True

    def test_get_validation_feedback(self):
        """Verify feedback message is generated correctly."""
        errors = ["Unclosed tags: thinking", "Missing required tag: <action>"]
        feedback = XMLValidator.get_validation_feedback(errors)
        assert "XML formatting issues" in feedback
        assert "Unclosed tags" in feedback
        assert "action" in feedback


class TestFacilitatorParseStats:
    """Test facilitator action parsing statistics tracking."""

    @pytest.fixture(autouse=True)
    def reset_stats(self):
        """Reset stats before each test."""
        reset_facilitator_parse_stats()

    @pytest.fixture
    def mock_state(self):
        """Create mock state with session_id and personas."""
        persona1 = MagicMock()
        persona1.code = "ceo"
        persona1.name = "CEO"
        return {
            "session_id": "bo1_stats_test",
            "personas": [persona1],
        }

    def test_stats_success_on_xml_parse(self, mock_state):
        """Verify success counter increments on XML tag extraction."""
        content = "<action>continue</action>"
        ResponseParser.parse_facilitator_decision(content, mock_state)
        stats = get_facilitator_parse_stats()
        assert stats["success"] == 1
        assert stats["fallback"] == 0
        assert stats["invalid_action"] == 0

    def test_stats_invalid_on_missing_tag(self, mock_state):
        """Verify invalid_action counter increments on missing action tag."""
        content = "We should continue discussion with the CEO."
        with pytest.raises(XMLValidationError):
            ResponseParser.parse_facilitator_decision(content, mock_state)
        stats = get_facilitator_parse_stats()
        assert stats["invalid_action"] == 1
        assert stats["success"] == 0

    def test_stats_invalid_action_on_unknown(self, mock_state):
        """Verify invalid_action counter increments on unknown action."""
        content = "Random gibberish with no recognizable action"
        with pytest.raises(XMLValidationError):
            ResponseParser.parse_facilitator_decision(content, mock_state)
        stats = get_facilitator_parse_stats()
        assert stats["invalid_action"] == 1

    def test_stats_invalid_action_on_invalid_xml_value(self, mock_state):
        """Verify invalid_action counter increments on invalid XML value."""
        content = "<action>dance_party</action>"  # Not a valid action
        with pytest.raises(XMLValidationError):
            ResponseParser.parse_facilitator_decision(content, mock_state)
        stats = get_facilitator_parse_stats()
        assert stats["invalid_action"] == 1

    def test_analyze_data_action_valid(self, mock_state):
        """Verify analyze_data is recognized as valid action."""
        content = "<action>analyze_data</action>"
        result = ResponseParser.parse_facilitator_decision(content, mock_state)
        assert result["action"] == "analyze_data"
        stats = get_facilitator_parse_stats()
        assert stats["success"] == 1


class TestValidateCitations:
    """Test citation validation for masked persona responses."""

    def test_validate_citations_zero_sources(self):
        """Verify 0 citations returns invalid with warning."""
        content = "This response has no sources or citations."
        result = validate_citations(content, min_citations=3)

        assert result.citation_count == 0
        assert result.is_valid is False
        assert result.warning is not None
        assert "0 citation(s)" in result.warning

    def test_validate_citations_three_sources_pass(self):
        """Verify 3+ structured sources passes validation."""
        content = """<sources>
        <source><url>https://example.com/1</url><name>Source 1</name></source>
        <source><url>https://example.com/2</url><name>Source 2</name></source>
        <source><url>https://example.com/3</url><name>Source 3</name></source>
        </sources>"""
        result = validate_citations(content, min_citations=3)

        assert result.citation_count == 3
        assert result.is_valid is True
        assert result.warning is None

    def test_validate_citations_one_two_warns(self):
        """Verify 1-2 citations returns warning for researcher."""
        content = """<sources>
        <source><url>https://example.com/1</url><name>Source 1</name></source>
        <source><url>https://example.com/2</url><name>Source 2</name></source>
        </sources>"""
        result = validate_citations(content, min_citations=3, persona_type="researcher")

        assert result.citation_count == 2
        assert result.is_valid is False
        assert "researcher" in result.warning
        assert "2 citation(s)" in result.warning
        assert "minimum 3" in result.warning

    def test_validate_citations_xml_sources_block(self):
        """Verify extraction from structured XML sources block."""
        content = """<sources>
        <source>
            <url>https://docs.python.org/3/library/re.html</url>
            <name>Python - re module</name>
            <type>documentation</type>
            <relevance>Regex patterns for validation</relevance>
        </source>
        <source>
            <url>https://example.com/article</url>
            <name>Example Article</name>
            <type>article</type>
            <relevance>Reference implementation</relevance>
        </source>
        </sources>"""
        result = validate_citations(content, min_citations=2)

        assert result.citation_count == 2
        assert result.is_valid is True

    def test_validate_citations_url_fallback(self):
        """Verify URL fallback when no structured sources."""
        content = """Found these resources:
        - https://example.com/article1
        - https://docs.example.org/guide
        - https://api.example.com/docs
        """
        result = validate_citations(content, min_citations=3)

        assert result.citation_count == 3
        assert result.is_valid is True

    def test_validate_citations_moderator_lower_threshold(self):
        """Verify moderator has lower threshold (1 source)."""
        content = """<sources>
        <source><url>https://example.com/study</url><name>Study</name></source>
        </sources>"""
        result = validate_citations(content, min_citations=1, persona_type="moderator")

        assert result.citation_count == 1
        assert result.is_valid is True

    def test_validate_citations_deduplicates_urls(self):
        """Verify duplicate URLs are counted once."""
        content = """See https://example.com/doc for details.
        More info at https://example.com/doc and https://example.com/other."""
        result = validate_citations(content, min_citations=2)

        # Should count 2 unique URLs, not 3
        assert result.citation_count == 2
        assert result.is_valid is True

    def test_citation_validation_result_attributes(self):
        """Verify CitationValidationResult has expected attributes."""
        result = CitationValidationResult(
            citation_count=5,
            min_required=3,
            is_valid=True,
            warning=None,
        )
        assert result.citation_count == 5
        assert result.min_required == 3
        assert result.is_valid is True
        assert result.warning is None


class TestChallengePhaseValidation:
    """Test challenge phase contribution validation for rounds 3-4."""

    def test_generic_agreement_detection_positive(self):
        """Verify generic agreement patterns are detected."""
        agreeable_content = (
            "I agree with Henrik's excellent analysis. He makes a great point about the market. "
            "Building on his insight, we should focus on user acquisition."
        )
        is_valid, reason = ResponseParser.validate_challenge_phase_contribution(
            agreeable_content, round_number=3
        )
        assert is_valid is False
        assert "Challenge phase requires substantive critique" in reason

    def test_generic_agreement_detection_negative(self):
        """Verify challenge content passes validation."""
        challenge_content = (
            "However, Henrik overlooks a critical risk in this approach. "
            "The market analysis fails to account for regulatory changes, "
            "which could undermine the entire strategy."
        )
        is_valid, reason = ResponseParser.validate_challenge_phase_contribution(
            challenge_content, round_number=3
        )
        assert is_valid is True
        assert reason == ""

    def test_challenge_indicators_detected_disagree(self):
        """Verify 'I disagree' is detected as challenge indicator."""
        content = "I disagree with the proposed timeline. It's too aggressive."
        is_valid, reason = ResponseParser.validate_challenge_phase_contribution(
            content, round_number=3
        )
        assert is_valid is True

    def test_challenge_indicators_detected_flaw(self):
        """Verify 'the flaw in' is detected as challenge indicator."""
        content = "The flaw in this reasoning is the assumption about customer behavior."
        is_valid, reason = ResponseParser.validate_challenge_phase_contribution(
            content, round_number=4
        )
        assert is_valid is True

    def test_challenge_indicators_detected_what_about(self):
        """Verify 'what about the risk' is detected as challenge indicator."""
        content = "What about the risk of regulatory intervention?"
        is_valid, reason = ResponseParser.validate_challenge_phase_contribution(
            content, round_number=3
        )
        assert is_valid is True

    def test_valid_challenge_contribution(self):
        """Verify contribution with explicit disagreement passes."""
        content = (
            "I strongly disagree with the current proposal. The assumptions underlying "
            "the financial projections are flawed, and we're ignoring significant "
            "competitive threats that could derail the entire initiative."
        )
        is_valid, reason = ResponseParser.validate_challenge_phase_contribution(
            content, round_number=3, persona_name="TestExpert"
        )
        assert is_valid is True
        assert reason == ""

    def test_invalid_agreeable_contribution(self):
        """Verify pure agreement without challenge fails in round 3."""
        content = (
            "I fully agree with Sarah's view on this. She makes an excellent point "
            "about customer segmentation. Well said, Sarah! Henrik is exactly right "
            "about the timeline as well."
        )
        is_valid, reason = ResponseParser.validate_challenge_phase_contribution(
            content, round_number=3, persona_name="TestExpert"
        )
        assert is_valid is False
        assert "Challenge phase requires substantive critique" in reason

    def test_mixed_content_passes(self):
        """Verify content with both agreement and challenge passes."""
        content = (
            "I agree with Henrik's point about market size. However, I disagree "
            "with the go-to-market strategy. The flaw in this approach is that "
            "it ignores enterprise customers entirely."
        )
        is_valid, reason = ResponseParser.validate_challenge_phase_contribution(
            content, round_number=3
        )
        assert is_valid is True

    def test_non_challenge_round_passes_agreement(self):
        """Verify agreement is allowed in non-challenge rounds."""
        agreeable_content = (
            "I agree with Henrik's analysis. Building on his excellent point, "
            "we should consider additional market segments."
        )
        # Round 2 is not a challenge phase round
        is_valid, reason = ResponseParser.validate_challenge_phase_contribution(
            agreeable_content, round_number=2
        )
        assert is_valid is True
        assert reason == ""

    def test_round_5_not_challenge_phase(self):
        """Verify round 5 is not treated as challenge phase."""
        agreeable_content = "I agree with the consensus. Great work everyone."
        is_valid, reason = ResponseParser.validate_challenge_phase_contribution(
            agreeable_content, round_number=5
        )
        assert is_valid is True

    def test_neutral_technical_content_passes(self):
        """Verify neutral technical contribution without agreement passes."""
        content = (
            "Based on our financial analysis, the projected ROI is 15% over 3 years. "
            "The break-even point occurs at month 18 assuming current burn rate."
        )
        is_valid, reason = ResponseParser.validate_challenge_phase_contribution(
            content, round_number=3
        )
        # No agreement patterns, no challenge indicators - should pass
        assert is_valid is True


class TestGenericAgreementPatterns:
    """Test pattern coverage for generic agreement detection."""

    def test_pattern_i_agree_with(self):
        """Verify 'I agree with X' pattern matches."""
        import re

        text = "I agree with Henrik on this matter."
        pattern = GENERIC_AGREEMENT_PATTERNS[0]  # "\bi\s+(?:fully\s+)?agree\s+with\s+\w+"
        assert re.search(pattern, text.lower()) is not None

    def test_pattern_building_on(self):
        """Verify 'building on X's point' pattern matches."""
        import re

        text = "Building on Sarah's point about pricing..."
        pattern = GENERIC_AGREEMENT_PATTERNS[1]
        assert re.search(pattern, text.lower()) is not None

    def test_pattern_great_point(self):
        """Verify 'great point X' pattern matches."""
        import re

        text = "Great point by Henrik about the timeline."
        pattern = GENERIC_AGREEMENT_PATTERNS[3]
        assert re.search(pattern, text.lower()) is not None

    def test_pattern_exactly_right(self):
        """Verify 'X is exactly right' pattern matches."""
        import re

        text = "Sarah is exactly right about this issue."
        pattern = GENERIC_AGREEMENT_PATTERNS[4]
        assert re.search(pattern, text.lower()) is not None


class TestChallengeIndicatorPatterns:
    """Test pattern coverage for challenge indicator detection."""

    def test_pattern_i_disagree(self):
        """Verify 'I disagree' pattern matches."""
        import re

        text = "I disagree with the proposed approach."
        pattern = CHALLENGE_INDICATOR_PATTERNS[0]
        assert re.search(pattern, text.lower()) is not None

    def test_pattern_however_argue(self):
        """Verify 'however I would argue' pattern matches."""
        import re

        text = "However, I would argue that this overlooks key risks."
        pattern = CHALLENGE_INDICATOR_PATTERNS[1]
        assert re.search(pattern, text.lower()) is not None

    def test_pattern_flaw_in(self):
        """Verify 'the flaw in' pattern matches."""
        import re

        text = "The flaw in this reasoning is the market assumption."
        pattern = CHALLENGE_INDICATOR_PATTERNS[2]
        assert re.search(pattern, text.lower()) is not None

    def test_pattern_critical_risk(self):
        """Verify 'a critical risk' pattern matches."""
        import re

        text = "There is a critical risk we haven't addressed."
        pattern = CHALLENGE_INDICATOR_PATTERNS[9]
        assert re.search(pattern, text.lower()) is not None

    def test_pattern_not_convinced(self):
        """Verify 'I'm not convinced' pattern matches."""
        import re

        text = "I'm not convinced by this analysis."
        pattern = CHALLENGE_INDICATOR_PATTERNS[11]
        assert re.search(pattern, text.lower()) is not None
