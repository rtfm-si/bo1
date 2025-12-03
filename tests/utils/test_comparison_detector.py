"""Tests for the ComparisonDetector utility."""

from bo1.utils.comparison_detector import ComparisonDetector, ComparisonResult


class TestComparisonDetector:
    """Tests for ComparisonDetector.detect()."""

    def test_explicit_vs_pattern(self):
        """Test detection of 'X vs Y' pattern."""
        result = ComparisonDetector.detect("Should we use React vs Svelte for our frontend?")

        assert result.is_comparison
        assert "react" in [o.lower() for o in result.options]
        assert "svelte" in [o.lower() for o in result.options]
        assert result.comparison_type == "explicit"
        assert len(result.research_queries) > 0

    def test_or_choice_pattern(self):
        """Test detection of 'A or B' choice pattern."""
        result = ComparisonDetector.detect("Should we build or buy our analytics solution?")

        assert result.is_comparison
        assert "build" in [o.lower() for o in result.options]
        assert "buy" in [o.lower() for o in result.options]
        assert result.comparison_type == "build_vs_buy"

    def test_timing_pattern(self):
        """Test detection of timing comparison ('now vs later')."""
        result = ComparisonDetector.detect("Series A now vs wait 6 months?")

        assert result.is_comparison
        assert result.comparison_type == "timing"
        assert len(result.research_queries) > 0

    def test_market_expansion_pattern(self):
        """Test detection of market expansion comparison."""
        result = ComparisonDetector.detect("Should we expand to Europe or Asia first?")

        assert result.is_comparison
        assert "europe" in [o.lower() for o in result.options]
        assert "asia" in [o.lower() for o in result.options]

    def test_no_comparison_simple_question(self):
        """Test that simple questions are not detected as comparisons."""
        result = ComparisonDetector.detect("How should I improve my marketing?")

        assert not result.is_comparison
        assert result.options == []
        assert result.research_queries == []

    def test_no_comparison_statement(self):
        """Test that statements without comparison keywords are not detected."""
        result = ComparisonDetector.detect("We need to hire more engineers")

        assert not result.is_comparison

    def test_compare_to_pattern(self):
        """Test detection of 'compare X to Y' pattern."""
        result = ComparisonDetector.detect("Compare AWS to GCP for our infrastructure")

        assert result.is_comparison
        assert "aws" in [o.lower() for o in result.options]
        assert "gcp" in [o.lower() for o in result.options]

    def test_research_queries_generated(self):
        """Test that research queries are properly generated."""
        result = ComparisonDetector.detect("React vs Vue for new project")

        assert result.is_comparison
        assert len(result.research_queries) >= 2

        # Check query structure
        for query in result.research_queries:
            assert "question" in query
            assert "priority" in query
            assert "reason" in query
            assert query["priority"] in ["HIGH", "MEDIUM", "LOW"]

    def test_case_insensitivity(self):
        """Test that detection is case-insensitive."""
        result1 = ComparisonDetector.detect("REACT VS SVELTE")
        result2 = ComparisonDetector.detect("react vs svelte")

        assert result1.is_comparison == result2.is_comparison

    def test_with_context(self):
        """Test detection with additional context."""
        result = ComparisonDetector.detect(
            problem_statement="Which database?",
            context="We're choosing between PostgreSQL or MongoDB for our application",
        )

        assert result.is_comparison


class TestComparisonResultDataclass:
    """Tests for ComparisonResult dataclass."""

    def test_default_values(self):
        """Test default values for ComparisonResult."""
        result = ComparisonResult(is_comparison=False)

        assert result.is_comparison is False
        assert result.options == []
        assert result.comparison_type == ""
        assert result.research_queries == []

    def test_with_values(self):
        """Test ComparisonResult with all values set."""
        result = ComparisonResult(
            is_comparison=True,
            options=["A", "B"],
            comparison_type="explicit",
            research_queries=[{"question": "test", "priority": "HIGH", "reason": "test"}],
        )

        assert result.is_comparison is True
        assert result.options == ["A", "B"]
        assert result.comparison_type == "explicit"
        assert len(result.research_queries) == 1
