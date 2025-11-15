"""Tests for vote parsing utilities.

DEPRECATED: parse_vote_decision is no longer used in the recommendation system.
Only testing parse_confidence_level and parse_conditions which are still used.
"""

from bo1.utils.vote_parsing import parse_conditions, parse_confidence_level, parse_vote_decision


class TestParseVoteDecision:
    """Test parse_vote_decision function.

    DEPRECATED: This function is no longer used but kept for backward compatibility.
    """

    def test_yes_variations(self):
        """Test various forms of YES votes."""
        assert parse_vote_decision("Yes") == "yes"
        assert parse_vote_decision("YES") == "yes"
        assert parse_vote_decision("yes") == "yes"
        assert parse_vote_decision("I approve this proposal") == "yes"
        assert parse_vote_decision("I support this idea") == "yes"
        assert parse_vote_decision("Accept") == "yes"

    def test_no_variations(self):
        """Test various forms of NO votes."""
        assert parse_vote_decision("No") == "no"
        assert parse_vote_decision("NO") == "no"
        assert parse_vote_decision("no") == "no"
        assert parse_vote_decision("I reject this proposal") == "no"
        assert parse_vote_decision("I oppose this plan") == "no"
        assert parse_vote_decision("Decline") == "no"

    def test_conditional_variations(self):
        """Test various forms of CONDITIONAL votes."""
        assert parse_vote_decision("Conditional") == "conditional"
        assert parse_vote_decision("CONDITIONAL") == "conditional"
        assert parse_vote_decision("conditional") == "conditional"
        assert parse_vote_decision("Yes, if budget is approved") == "conditional"
        assert parse_vote_decision("Only if timeline is realistic") == "conditional"
        assert parse_vote_decision("Provided that we have resources") == "conditional"

    def test_abstain_variations(self):
        """Test various forms of ABSTAIN votes."""
        assert parse_vote_decision("Abstain") == "abstain"
        assert parse_vote_decision("ABSTAIN") == "abstain"
        assert parse_vote_decision("abstain") == "abstain"
        assert parse_vote_decision("Unclear response") == "abstain"
        assert parse_vote_decision("") == "abstain"
        assert parse_vote_decision(None) == "abstain"

    def test_ambiguous_responses(self):
        """Test handling of ambiguous responses."""
        # Should default to abstain for truly ambiguous cases
        assert parse_vote_decision("Maybe") == "abstain"
        assert parse_vote_decision("I'm not sure") == "abstain"

    def test_priority_handling(self):
        """Test that YES/NO take priority over conditional keywords."""
        # "Yes if" should be conditional, not yes
        assert parse_vote_decision("Yes if budget approved") == "conditional"
        # "No" should be no even with extra text (but "if" makes it conditional)
        assert parse_vote_decision("No, I reject this") == "no"


class TestParseConfidenceLevel:
    """Test parse_confidence_level function."""

    def test_named_levels(self):
        """Test parsing of named confidence levels."""
        assert parse_confidence_level("High") == 0.85
        assert parse_confidence_level("HIGH") == 0.85
        assert parse_confidence_level("high") == 0.85
        assert parse_confidence_level("Strong") == 0.85

        assert parse_confidence_level("Medium") == 0.6
        assert parse_confidence_level("MEDIUM") == 0.6
        assert parse_confidence_level("medium") == 0.6
        assert parse_confidence_level("Moderate") == 0.6

        assert parse_confidence_level("Low") == 0.3
        assert parse_confidence_level("LOW") == 0.3
        assert parse_confidence_level("low") == 0.3
        assert parse_confidence_level("Weak") == 0.3

    def test_numeric_values_0_to_1(self):
        """Test parsing of numeric values in 0-1 range."""
        assert parse_confidence_level("0.5") == 0.5
        assert parse_confidence_level("0.75") == 0.75
        assert parse_confidence_level("0.9") == 0.9
        assert parse_confidence_level("1.0") == 1.0
        assert parse_confidence_level("0.0") == 0.0

    def test_percentage_values(self):
        """Test parsing of percentage values."""
        assert parse_confidence_level("50%") == 0.5
        assert parse_confidence_level("75%") == 0.75
        assert parse_confidence_level("90%") == 0.9
        assert parse_confidence_level("100%") == 1.0
        assert parse_confidence_level("0%") == 0.0

    def test_percentage_without_symbol(self):
        """Test parsing of numbers > 1 as percentages."""
        assert parse_confidence_level("50") == 0.5
        assert parse_confidence_level("75") == 0.75
        assert parse_confidence_level("90") == 0.9
        assert parse_confidence_level("100") == 1.0

    def test_clamping(self):
        """Test that values are clamped to 0-1 range."""
        assert parse_confidence_level("150%") == 1.0  # Percentage over 100
        assert parse_confidence_level("200") == 1.0  # Number over 100 (treated as percentage)
        assert parse_confidence_level("-10%") == 0.0  # Negative percentage
        assert parse_confidence_level("-0.5") == 0.0  # Negative decimal

    def test_invalid_input(self):
        """Test handling of invalid input."""
        assert parse_confidence_level("invalid") == 0.6
        assert parse_confidence_level("") == 0.6
        assert parse_confidence_level(None) == 0.6
        assert parse_confidence_level("abc123") == 0.6


class TestParseConditions:
    """Test parse_conditions function."""

    def test_bulleted_list(self):
        """Test parsing of bulleted conditions."""
        conditions = parse_conditions("- Budget must be approved\n- Timeline is 6 months")
        assert len(conditions) == 2
        assert "Budget must be approved" in conditions
        assert "Timeline is 6 months" in conditions

    def test_numbered_list(self):
        """Test parsing of numbered conditions."""
        conditions = parse_conditions("1. First condition\n2. Second condition\n3. Third condition")
        assert len(conditions) == 3
        assert "First condition" in conditions
        assert "Second condition" in conditions
        assert "Third condition" in conditions

    def test_mixed_formats(self):
        """Test parsing of mixed format conditions."""
        conditions = parse_conditions(
            "- Budget approved\n• Timeline realistic\n* Resources available\n1) Team committed"
        )
        assert len(conditions) == 4
        assert "Budget approved" in conditions
        assert "Timeline realistic" in conditions
        assert "Resources available" in conditions
        assert "Team committed" in conditions

    def test_empty_lines_ignored(self):
        """Test that empty lines are ignored."""
        conditions = parse_conditions("- First condition\n\n- Second condition\n\n")
        assert len(conditions) == 2
        assert "First condition" in conditions
        assert "Second condition" in conditions

    def test_xml_tags_ignored(self):
        """Test that XML tags are ignored."""
        conditions = parse_conditions("<conditions>\n- Real condition\n</conditions>")
        assert len(conditions) == 1
        assert "Real condition" in conditions

    def test_short_lines_ignored(self):
        """Test that very short lines are ignored."""
        conditions = parse_conditions(
            "- Real condition\n- OK\n- No\n- Yes\n- Another real condition"
        )
        # "OK", "No", "Yes" should be ignored as too short (<=5 chars after cleanup)
        assert len(conditions) == 2
        assert "Real condition" in conditions
        assert "Another real condition" in conditions

    def test_empty_input(self):
        """Test handling of empty input."""
        assert parse_conditions("") == []
        assert parse_conditions(None) == []
        assert parse_conditions("   \n  \n  ") == []

    def test_complex_conditions(self):
        """Test parsing of complex, real-world conditions."""
        text = """
        <conditions>
        1. Budget must not exceed $500K
        2. Timeline should be within 6 months
        3. Team must have relevant experience
        - Risk mitigation plan is required
        • Stakeholder buy-in is confirmed
        </conditions>
        """
        conditions = parse_conditions(text)
        assert len(conditions) == 5
        assert any("$500K" in c for c in conditions)
        assert any("6 months" in c for c in conditions)
        assert any("experience" in c for c in conditions)
        assert any("Risk mitigation" in c for c in conditions)
        assert any("Stakeholder" in c for c in conditions)
