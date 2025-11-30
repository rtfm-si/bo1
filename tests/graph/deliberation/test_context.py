"""Tests for context building utilities."""

import pytest

from bo1.graph.deliberation.context import (
    build_dependency_context,
    build_subproblem_context_for_all,
    extract_recommendation_from_synthesis,
)
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import SubProblemResult


class TestExtractRecommendationFromSynthesis:
    """Test recommendation extraction from synthesis text."""

    def test_extract_from_recommendation_tag(self):
        """Extract from <recommendation> tag."""
        synthesis = """
        Some analysis here.
        <recommendation>Use a 3-tier pricing model with clear value differentiation.</recommendation>
        More analysis.
        """
        result = extract_recommendation_from_synthesis(synthesis)
        assert result == "Use a 3-tier pricing model with clear value differentiation."

    def test_extract_from_executive_summary_tag(self):
        """Fallback to <executive_summary> tag."""
        synthesis = """
        <executive_summary>Focus on SEO and content marketing initially.</executive_summary>
        """
        result = extract_recommendation_from_synthesis(synthesis)
        assert result == "Focus on SEO and content marketing initially."

    def test_truncate_long_summary(self):
        """Long content is truncated to 500 chars."""
        long_content = "A" * 600
        synthesis = f"<executive_summary>{long_content}</executive_summary>"
        result = extract_recommendation_from_synthesis(synthesis)
        assert len(result) == 503  # 500 + "..."
        assert result.endswith("...")

    def test_fallback_to_first_500_chars(self):
        """Fallback to first 500 chars when no tags."""
        synthesis = "B" * 600
        result = extract_recommendation_from_synthesis(synthesis)
        assert len(result) == 503
        assert result.startswith("B" * 500)
        assert result.endswith("...")

    def test_short_text_no_truncation(self):
        """Short text without tags is returned as-is."""
        synthesis = "Short recommendation text"
        result = extract_recommendation_from_synthesis(synthesis)
        assert result == "Short recommendation text"

    def test_empty_string(self):
        """Empty string returns empty string."""
        result = extract_recommendation_from_synthesis("")
        assert result == ""

    def test_recommendation_tag_with_attributes(self):
        """Handle <recommendation> tag with attributes."""
        synthesis = '<recommendation confidence="high">Proceed with caution.</recommendation>'
        result = extract_recommendation_from_synthesis(synthesis)
        assert result == "Proceed with caution."


class TestBuildDependencyContext:
    """Test dependency context building."""

    @pytest.fixture
    def problem_with_deps(self):
        """Create problem with dependent sub-problems."""
        return Problem(
            title="Test Problem",
            description="Test description",
            context="Test context",
            constraints=[],
            sub_problems=[
                SubProblem(
                    id="sp1",
                    goal="Determine pricing",
                    context="",
                    complexity_score=5,
                    dependencies=[],
                ),
                SubProblem(
                    id="sp2",
                    goal="Select channels",
                    context="",
                    complexity_score=5,
                    dependencies=["sp1"],
                ),
            ],
        )

    @pytest.fixture
    def sp1_result(self):
        """Result for first sub-problem."""
        return SubProblemResult(
            sub_problem_id="sp1",
            sub_problem_goal="Determine pricing",
            synthesis="<recommendation>Use $49 pricing.</recommendation>",
            votes=[],
            contribution_count=5,
            cost=0.10,
            duration_seconds=30.0,
            expert_panel=["CFO", "CMO"],
            expert_summaries={},
        )

    def test_no_dependencies_returns_none(self, problem_with_deps, sp1_result):
        """Sub-problem without dependencies returns None."""
        sp1 = problem_with_deps.sub_problems[0]  # No dependencies
        result = build_dependency_context(sp1, [sp1_result], problem_with_deps)
        assert result is None

    def test_with_dependency(self, problem_with_deps, sp1_result):
        """Sub-problem with dependency includes context."""
        sp2 = problem_with_deps.sub_problems[1]  # Depends on sp1
        result = build_dependency_context(sp2, [sp1_result], problem_with_deps)

        assert result is not None
        assert "<dependent_conclusions>" in result
        assert "Determine pricing" in result
        assert "Use $49 pricing" in result
        assert "</dependent_conclusions>" in result

    def test_missing_dependency_result(self, problem_with_deps):
        """Missing dependency result is handled gracefully."""
        sp2 = problem_with_deps.sub_problems[1]
        result = build_dependency_context(sp2, [], problem_with_deps)  # No results

        # Should still have wrapper tags but no content
        assert result is not None
        assert "<dependent_conclusions>" in result
        assert "</dependent_conclusions>" in result

    def test_empty_results_list(self, problem_with_deps):
        """Empty results list handles sub-problem with dependencies."""
        sp2 = problem_with_deps.sub_problems[1]
        result = build_dependency_context(sp2, [], problem_with_deps)
        assert result is not None


class TestBuildSubproblemContextForAll:
    """Test building context for all experts."""

    @pytest.fixture
    def multiple_results(self):
        """Multiple sub-problem results."""
        return [
            SubProblemResult(
                sub_problem_id="sp1",
                sub_problem_goal="Determine pricing",
                synthesis="<recommendation>Use $49 pricing.</recommendation>",
                votes=[],
                contribution_count=5,
                cost=0.10,
                duration_seconds=30.0,
                expert_panel=["CFO", "CMO"],
                expert_summaries={},
            ),
            SubProblemResult(
                sub_problem_id="sp2",
                sub_problem_goal="Select channels",
                synthesis="<recommendation>Focus on SEO.</recommendation>",
                votes=[],
                contribution_count=4,
                cost=0.08,
                duration_seconds=25.0,
                expert_panel=["CMO", "VP_Sales"],
                expert_summaries={},
            ),
        ]

    def test_empty_results_returns_none(self):
        """Empty results list returns None."""
        result = build_subproblem_context_for_all([])
        assert result is None

    def test_single_result(self, multiple_results):
        """Single result produces valid context."""
        result = build_subproblem_context_for_all([multiple_results[0]])

        assert result is not None
        assert "<previous_subproblem_outcomes>" in result
        assert "Determine pricing" in result
        assert "Use $49 pricing" in result
        assert "CFO, CMO" in result
        assert "</previous_subproblem_outcomes>" in result

    def test_multiple_results(self, multiple_results):
        """Multiple results are all included."""
        result = build_subproblem_context_for_all(multiple_results)

        assert result is not None
        assert "Determine pricing" in result
        assert "Select channels" in result
        assert "Use $49 pricing" in result
        assert "Focus on SEO" in result

    def test_expert_panels_included(self, multiple_results):
        """Expert panels are included in context."""
        result = build_subproblem_context_for_all(multiple_results)

        assert "CFO, CMO" in result
        assert "CMO, VP_Sales" in result
