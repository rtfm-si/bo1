"""Unit tests for DeliberationAnalyzer utilities."""

from bo1.models.problem import Problem
from bo1.models.state import ContributionMessage, DeliberationState
from bo1.utils.deliberation_analysis import DeliberationAnalyzer


def create_test_problem():
    """Create a test problem for deliberation states."""
    return Problem(
        title="Test Problem",
        description="Test problem description",
        statement="Test problem",
        context="Test context",
        constraints=[],
        sub_problems=[],
    )


class TestDetectPrematureConsensus:
    """Tests for premature consensus detection."""

    def test_no_consensus_with_few_contributions(self):
        """Should return False with fewer than 4 contributions."""
        contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="I agree with the proposal",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="ZARA",
                persona_name="Zara",
                content="Yes, this seems correct",
                round_number=1,
            ),
        ]
        assert not DeliberationAnalyzer.detect_premature_consensus(contributions)

    def test_no_consensus_with_diverse_opinions(self):
        """Should return False when opinions are diverse."""
        contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="I think we should consider alternative approaches here",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="ZARA",
                persona_name="Zara",
                content="There are several different perspectives to explore",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="TARIQ",
                persona_name="Tariq",
                content="Let me offer a contrasting viewpoint on this matter",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="PRIYA",
                persona_name="Priya",
                content="I see things differently and have concerns about this",
                round_number=1,
            ),
        ]
        assert not DeliberationAnalyzer.detect_premature_consensus(contributions)

    def test_detects_premature_consensus(self):
        """Should detect when too many agreement keywords are present."""
        contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="I agree completely yes this is exactly correct",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="ZARA",
                persona_name="Zara",
                content="Yes indeed I agree this is exactly right aligned thinking",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="TARIQ",
                persona_name="Tariq",
                content="Correct yes I agree completely same conclusion here",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="PRIYA",
                persona_name="Priya",
                content="Indeed yes exactly aligned with everyone else",
                round_number=1,
            ),
        ]
        assert DeliberationAnalyzer.detect_premature_consensus(contributions)

    def test_handles_empty_contributions(self):
        """Should handle empty contribution list."""
        assert not DeliberationAnalyzer.detect_premature_consensus([])


class TestDetectUnverifiedClaims:
    """Tests for unverified claims detection."""

    def test_no_claims(self):
        """Should return False when no strong claims are made."""
        contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="This might be a good approach to consider",
                round_number=1,
            ),
        ]
        assert not DeliberationAnalyzer.detect_unverified_claims(contributions)

    def test_claims_with_evidence(self):
        """Should return False when claims have supporting evidence."""
        contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content=(
                    "We should definitely invest because data shows that "
                    "this will yield returns and research indicates strong performance"
                ),
                round_number=1,
            ),
        ]
        assert not DeliberationAnalyzer.detect_unverified_claims(contributions)

    def test_detects_unverified_claims(self):
        """Should detect multiple claims without evidence."""
        contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content=(
                    "We must do this immediately. This will definitely work. "
                    "It should be our top priority and will certainly succeed"
                ),
                round_number=1,
            ),
        ]
        assert DeliberationAnalyzer.detect_unverified_claims(contributions)

    def test_handles_empty_list(self):
        """Should handle empty contribution list."""
        assert not DeliberationAnalyzer.detect_unverified_claims([])


class TestDetectNegativitySpiral:
    """Tests for negativity spiral detection."""

    def test_balanced_discussion(self):
        """Should return False when discussion is balanced."""
        contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="There are problems but also opportunities and possible solutions",
                round_number=1,
            ),
        ]
        assert not DeliberationAnalyzer.detect_negativity_spiral(contributions)

    def test_positive_discussion(self):
        """Should return False for predominantly positive discussion."""
        contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="This could work and might provide opportunities with potential solutions",
                round_number=1,
            ),
        ]
        assert not DeliberationAnalyzer.detect_negativity_spiral(contributions)

    def test_detects_negativity_spiral(self):
        """Should detect when negative keywords dominate."""
        contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content=(
                    "This won't work it's impossible and can't succeed. "
                    "Too risky with many problems and will fail"
                ),
                round_number=1,
            ),
            ContributionMessage(
                persona_code="ZARA",
                persona_name="Zara",
                content=(
                    "Multiple issues here that can't be resolved. "
                    "This will fail and the problems are impossible to fix"
                ),
                round_number=1,
            ),
        ]
        assert DeliberationAnalyzer.detect_negativity_spiral(contributions)

    def test_detects_spiral_with_no_positive_words(self):
        """Should detect spiral when negative words exist but no positive ones."""
        contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="There are problems issues and more problems with this approach",
                round_number=1,
            ),
        ]
        assert DeliberationAnalyzer.detect_negativity_spiral(contributions)

    def test_handles_empty_list(self):
        """Should handle empty contribution list."""
        assert not DeliberationAnalyzer.detect_negativity_spiral([])


class TestDetectCircularArguments:
    """Tests for circular argument detection."""

    def test_no_circular_with_few_contributions(self):
        """Should return False with fewer than 4 contributions."""
        contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="This is my argument",
                round_number=1,
            ),
        ]
        assert not DeliberationAnalyzer.detect_circular_arguments(contributions)

    def test_diverse_arguments(self):
        """Should return False when arguments are diverse."""
        contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="First unique perspective with different ideas",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="ZARA",
                persona_name="Zara",
                content="Second alternative viewpoint brings fresh insights",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="TARIQ",
                persona_name="Tariq",
                content="Third distinct approach offers novel solutions",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="PRIYA",
                persona_name="Priya",
                content="Fourth separate angle provides additional value",
                round_number=1,
            ),
        ]
        assert not DeliberationAnalyzer.detect_circular_arguments(contributions)

    def test_detects_circular_arguments(self):
        """Should detect when same phrases repeat across contributions."""
        contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="market analysis shows market trends indicate market opportunity",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="ZARA",
                persona_name="Zara",
                content="market analysis reveals market patterns suggest market growth",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="TARIQ",
                persona_name="Tariq",
                content="market trends show market analysis indicates market potential",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="PRIYA",
                persona_name="Priya",
                content="market opportunity shows market analysis suggests market trends",
                round_number=1,
            ),
        ]
        assert DeliberationAnalyzer.detect_circular_arguments(contributions)

    def test_handles_empty_contributions(self):
        """Should handle empty contribution content."""
        contributions = [
            ContributionMessage(
                persona_code="MARIA", persona_name="Maria", content="", round_number=1
            ),
            ContributionMessage(
                persona_code="ZARA", persona_name="Zara", content="", round_number=1
            ),
            ContributionMessage(
                persona_code="TARIQ", persona_name="Tariq", content="", round_number=1
            ),
            ContributionMessage(
                persona_code="PRIYA", persona_name="Priya", content="", round_number=1
            ),
        ]
        assert not DeliberationAnalyzer.detect_circular_arguments(contributions)


class TestCheckResearchNeeded:
    """Tests for research need detection."""

    def test_no_research_needed_with_few_contributions(self):
        """Should return None with fewer than 2 contributions."""
        state = DeliberationState(
            session_id="test",
            problem=create_test_problem(),
            contributions=[
                ContributionMessage(
                    persona_code="MARIA",
                    persona_name="Maria",
                    content="Initial thought",
                    round_number=1,
                )
            ],
        )
        assert DeliberationAnalyzer.check_research_needed(state) is None

    def test_no_research_needed_with_clear_discussion(self):
        """Should return None when no information gaps exist."""
        state = DeliberationState(
            session_id="test",
            problem=create_test_problem(),
            contributions=[
                ContributionMessage(
                    persona_code="MARIA",
                    persona_name="Maria",
                    content="Based on the available evidence, we can proceed",
                    round_number=1,
                ),
                ContributionMessage(
                    persona_code="ZARA",
                    persona_name="Zara",
                    content="The data supports this conclusion clearly",
                    round_number=1,
                ),
            ],
        )
        assert DeliberationAnalyzer.check_research_needed(state) is None

    def test_detects_direct_questions(self):
        """Should detect when direct questions are asked."""
        state = DeliberationState(
            session_id="test",
            problem=create_test_problem(),
            contributions=[
                ContributionMessage(
                    persona_code="MARIA",
                    persona_name="Maria",
                    content="What is the current market size for this product?",
                    round_number=1,
                ),
                ContributionMessage(
                    persona_code="ZARA",
                    persona_name="Zara",
                    content="General discussion point",
                    round_number=1,
                ),
            ],
        )
        result = DeliberationAnalyzer.check_research_needed(state)
        assert result is not None
        assert "query" in result
        assert "reason" in result
        assert "market" in result["query"].lower()

    def test_detects_uncertainty_markers(self):
        """Should detect uncertainty and information gaps."""
        state = DeliberationState(
            session_id="test",
            problem=create_test_problem(),
            contributions=[
                ContributionMessage(
                    persona_code="MARIA",
                    persona_name="Maria",
                    content="It's unclear whether this approach will work at scale",
                    round_number=1,
                ),
                ContributionMessage(
                    persona_code="ZARA",
                    persona_name="Zara",
                    content="General point",
                    round_number=1,
                ),
            ],
        )
        result = DeliberationAnalyzer.check_research_needed(state)
        assert result is not None
        assert "unclear" in result["query"].lower()

    def test_detects_data_requests(self):
        """Should detect explicit requests for data or information."""
        state = DeliberationState(
            session_id="test",
            problem=create_test_problem(),
            contributions=[
                ContributionMessage(
                    persona_code="MARIA",
                    persona_name="Maria",
                    content="We need data on customer acquisition costs before deciding",
                    round_number=1,
                ),
                ContributionMessage(
                    persona_code="ZARA",
                    persona_name="Zara",
                    content="General discussion",
                    round_number=1,
                ),
            ],
        )
        result = DeliberationAnalyzer.check_research_needed(state)
        assert result is not None
        assert "need data" in result["query"].lower()

    def test_only_checks_recent_contributions(self):
        """Should only check the last 3 contributions."""
        state = DeliberationState(
            session_id="test",
            problem=create_test_problem(),
            contributions=[
                # Old contribution with question (should be ignored)
                ContributionMessage(
                    persona_code="MARIA",
                    persona_name="Maria",
                    content="What is the market size?",
                    round_number=1,
                ),
                # Recent contributions without questions
                ContributionMessage(
                    persona_code="ZARA",
                    persona_name="Zara",
                    content="This is clear and well understood",
                    round_number=2,
                ),
                ContributionMessage(
                    persona_code="TARIQ",
                    persona_name="Tariq",
                    content="The evidence supports this conclusion",
                    round_number=2,
                ),
                ContributionMessage(
                    persona_code="PRIYA",
                    persona_name="Priya",
                    content="We have all the information needed",
                    round_number=2,
                ),
            ],
        )
        assert DeliberationAnalyzer.check_research_needed(state) is None

    def test_query_length_limit(self):
        """Should limit query length to 200 characters."""
        long_question = "What is " + "x" * 300 + "?"
        state = DeliberationState(
            session_id="test",
            problem=create_test_problem(),
            contributions=[
                ContributionMessage(
                    persona_code="MARIA",
                    persona_name="Maria",
                    content=long_question,
                    round_number=1,
                ),
                ContributionMessage(
                    persona_code="ZARA",
                    persona_name="Zara",
                    content="General point",
                    round_number=1,
                ),
            ],
        )
        result = DeliberationAnalyzer.check_research_needed(state)
        assert result is not None
        assert len(result["query"]) <= 200
