"""Context building utilities for sub-problem deliberation.

Provides functions for building context that flows between sub-problems,
enabling knowledge transfer and coherent synthesis.

This module is extracted from nodes.py for better testability.
Fixes Issue #22: Context passing between sub-problems.
"""

import logging
import re
from typing import Any

from bo1.models.problem import Problem, SubProblem
from bo1.models.state import SubProblemResult
from bo1.prompts.sanitizer import sanitize_user_input

logger = logging.getLogger(__name__)


def extract_recommendation_from_synthesis(synthesis: str) -> str:
    """Extract key recommendation from synthesis XML.

    Parses synthesis content to extract the core recommendation for context passing.
    Tries multiple XML tags in order of preference:
    1. <recommendation> tag (most specific)
    2. <executive_summary> tag (fallback)
    3. First 500 characters (last resort)

    Args:
        synthesis: Full synthesis text (may contain XML tags)

    Returns:
        Extracted recommendation text (truncated to 500 chars max)

    Example:
        >>> synthesis = "<recommendation>Invest in SEO...</recommendation>"
        >>> extract_recommendation_from_synthesis(synthesis)
        'Invest in SEO...'
    """
    # Try to extract <recommendation> tag content
    match = re.search(r"<recommendation[^>]*>(.*?)</recommendation>", synthesis, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try executive_summary as fallback
    match = re.search(r"<executive_summary[^>]*>(.*?)</executive_summary>", synthesis, re.DOTALL)
    if match:
        content = match.group(1).strip()
        return content[:500] + "..." if len(content) > 500 else content

    # Last resort: first 500 chars
    return synthesis[:500] + "..." if len(synthesis) > 500 else synthesis


def build_dependency_context(
    current_sp: SubProblem,
    sub_problem_results: list[SubProblemResult],
    problem: Problem | dict[str, Any],
) -> str | None:
    """Build context from dependent sub-problems.

    When a sub-problem has dependencies (earlier sub-problems that must complete first),
    this function extracts their conclusions and formats them for expert context.

    This fixes Issue #22A: Full synthesis not passed to dependent sub-problems.

    Args:
        current_sp: The current sub-problem being deliberated
        sub_problem_results: Results from completed sub-problems
        problem: The parent problem (contains all sub-problem metadata, may be dict after checkpoint)

    Returns:
        Formatted dependency context string, or None if no dependencies

    Example:
        >>> # Sub-problem 2 depends on sub-problem 1
        >>> context = build_dependency_context(sp2, [result1], problem)
        >>> print(context)
        <dependent_conclusions>
        This sub-problem depends on conclusions from earlier sub-problems:

        **Determine pricing tier structure** (Resolved)
        Key Conclusion: Use 3-tier model with $49, $99, $199 pricing...
        </dependent_conclusions>
    """
    if not current_sp.dependencies:
        return None

    # Handle both dict (from checkpoint) and Problem object
    if isinstance(problem, dict):
        sub_problems_raw = problem.get("sub_problems", []) or []
    else:
        sub_problems_raw = problem.sub_problems or []

    # Normalize sub_problems to SubProblem objects (may be dicts after checkpoint)
    sub_problems: list[SubProblem] = []
    for sp in sub_problems_raw:
        if isinstance(sp, dict):
            sub_problems.append(SubProblem.model_validate(sp))
        else:
            sub_problems.append(sp)

    context_parts = []
    context_parts.append("<dependent_conclusions>")
    context_parts.append("This sub-problem depends on conclusions from earlier sub-problems:\n")

    for dep_id in current_sp.dependencies:
        # Find the dependency sub-problem
        dep_sp = next((sp for sp in sub_problems if sp.id == dep_id), None)
        if not dep_sp:
            logger.warning(f"Dependency {dep_id} not found in problem.sub_problems")
            continue

        # Find the result for this dependency
        dep_result = next((r for r in sub_problem_results if r.sub_problem_id == dep_id), None)
        if not dep_result:
            logger.warning(f"No result found for dependency {dep_id}")
            continue

        # Use cached recommendation if available, otherwise extract from synthesis
        if dep_result.extracted_recommendation:
            recommendation = dep_result.extracted_recommendation
            logger.debug(f"build_dependency_context: Using cached recommendation for {dep_id}")
        else:
            recommendation = extract_recommendation_from_synthesis(dep_result.synthesis)
            logger.debug(
                f"build_dependency_context: Extracted recommendation for {dep_id} (cache miss)"
            )
        recommendation = sanitize_user_input(recommendation, context="synthesis_recommendation")

        context_parts.append(f"""
**{dep_sp.goal}** (Resolved)
Key Conclusion: {recommendation}
""")

    context_parts.append("</dependent_conclusions>")
    return "\n".join(context_parts)


def build_subproblem_context_for_all(sub_problem_results: list[SubProblemResult]) -> str | None:
    """Build context from all completed sub-problems for any expert.

    Provides ALL experts (even new ones) with context about previous sub-problem outcomes.
    This ensures experts who didn't participate in earlier sub-problems still know what
    was decided.

    This fixes Issue #22B: Non-participating experts get no context.

    Args:
        sub_problem_results: Results from all completed sub-problems

    Returns:
        Formatted context string, or None if no results

    Example:
        >>> context = build_subproblem_context_for_all([result1, result2])
        >>> print(context)
        <previous_subproblem_outcomes>

        Sub-problem: Determine pricing tier structure
        Conclusion: Use 3-tier model with $49, $99, $199 pricing...
        Expert Panel: maria, zara, chen

        Sub-problem: Select acquisition channels
        Conclusion: Focus on SEO and content marketing initially...
        Expert Panel: tariq, aria, elena
        </previous_subproblem_outcomes>
    """
    if not sub_problem_results:
        return None

    context_parts = []
    context_parts.append("<previous_subproblem_outcomes>")

    for result in sub_problem_results:
        recommendation = extract_recommendation_from_synthesis(result.synthesis)

        context_parts.append(f"""
Sub-problem: {result.sub_problem_goal}
Conclusion: {recommendation}
Expert Panel: {", ".join(result.expert_panel)}
""")

    context_parts.append("</previous_subproblem_outcomes>")
    return "\n".join(context_parts)
