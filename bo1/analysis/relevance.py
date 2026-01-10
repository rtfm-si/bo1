"""Relevance assessment module for dataset-objective alignment.

Evaluates how well a dataset can inform progress toward business objectives
using LLM-based analysis.
"""

import logging
from typing import Any

from bo1.analysis.prompts.relevance_assessment import (
    RELEVANCE_ASSESSMENT_SYSTEM_PROMPT,
    build_relevance_assessment_prompt,
    parse_relevance_response,
)
from bo1.llm.client import ClaudeClient
from bo1.models.dataset_objective_analysis import (
    MissingData,
    ObjectiveMatch,
    RelevanceAssessment,
    RelevanceLevel,
)

logger = logging.getLogger(__name__)


async def assess_relevance(
    profile: dict[str, Any],
    objectives: list[dict[str, Any]] | None = None,
    north_star: str | None = None,
    industry: str | None = None,
    business_model: str | None = None,
    dataset_name: str | None = None,
) -> RelevanceAssessment:
    """Assess how relevant the dataset is to the user's objectives.

    Uses the relevance_assessment prompt to evaluate dataset-objective fit.
    Returns RelevanceAssessment model with relevance score, objective matches,
    and suggestions for missing data.

    Args:
        profile: Dataset profile with columns, sample rows, row_count, etc.
            Expected keys:
            - columns: list[dict] with 'name' and 'type' keys
            - sample_rows: list[dict] of sample data
            - row_count: int total rows
        objectives: List of objective dicts with id, name, description, target, current
        north_star: Primary business goal
        industry: Business industry for context
        business_model: Type of business model
        dataset_name: Name of the dataset being analyzed

    Returns:
        RelevanceAssessment with score, matches, missing data suggestions

    Raises:
        ValueError: If profile is missing required fields
    """
    # Handle missing objectives gracefully
    if not objectives:
        logger.info("No objectives provided, returning minimal relevance assessment")
        return RelevanceAssessment(
            relevance_score=0,
            assessment_summary="No business objectives defined. Analysis will use open exploration mode.",
            objective_matches=[],
            missing_data=[],
            recommended_focus="General data exploration and pattern discovery",
        )

    # Extract column info from profile
    columns = profile.get("columns", [])
    if not columns:
        logger.warning("Empty columns in profile, attempting to extract from column_profiles")
        column_profiles = profile.get("column_profiles", [])
        columns = [
            {
                "name": col.get("column_name", col.get("name", "unknown")),
                "type": col.get("data_type", col.get("type", "unknown")),
            }
            for col in column_profiles
        ]

    sample_rows = profile.get("sample_rows", profile.get("sample_data", []))
    row_count = profile.get("row_count", 0)
    name = dataset_name or profile.get("name", "Unnamed Dataset")

    # Build the prompt
    user_prompt = build_relevance_assessment_prompt(
        dataset_name=name,
        columns_with_types=columns,
        row_count=row_count,
        sample_rows=sample_rows,
        north_star=north_star,
        objectives=objectives,
        industry=industry,
        business_model=business_model,
    )

    # Call LLM
    client = ClaudeClient()
    try:
        response_text, usage = await client.call(
            model="sonnet",
            system=RELEVANCE_ASSESSMENT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            cache_system=True,
            temperature=0.3,  # Lower temp for more consistent assessment
            prefill="{",
        )

        # Parse response
        raw_result = parse_relevance_response(response_text)

        # Convert to typed models
        return _parse_relevance_result(raw_result)

    except Exception as e:
        logger.error(f"Error in relevance assessment: {e}")
        # Return a safe fallback
        return RelevanceAssessment(
            relevance_score=50,
            assessment_summary=f"Unable to complete relevance assessment: {e}",
            objective_matches=[],
            missing_data=[],
            recommended_focus="Open exploration of available data",
        )


def _parse_relevance_result(raw: dict[str, Any]) -> RelevanceAssessment:
    """Parse raw LLM response into typed RelevanceAssessment model.

    Args:
        raw: Parsed JSON from LLM response

    Returns:
        RelevanceAssessment model
    """
    # Parse objective matches
    objective_matches = []
    for match in raw.get("objective_matches", []):
        try:
            relevance_str = match.get("relevance", "medium").lower()
            relevance_level = RelevanceLevel(relevance_str)
        except ValueError:
            relevance_level = RelevanceLevel.MEDIUM

        objective_matches.append(
            ObjectiveMatch(
                objective_id=match.get("objective_id"),
                objective_name=match.get("objective_name", "Unknown"),
                relevance=relevance_level,
                explanation=match.get("explanation", ""),
                answerable_questions=match.get("answerable_questions", []),
                unanswerable_questions=match.get("unanswerable_questions", []),
            )
        )

    # Parse missing data suggestions
    missing_data = []
    for item in raw.get("missing_data", []):
        missing_data.append(
            MissingData(
                data_needed=item.get("data_needed", ""),
                why_valuable=item.get("why_valuable", ""),
                objectives_unlocked=item.get("objectives_unlocked", []),
            )
        )

    return RelevanceAssessment(
        relevance_score=raw.get("relevance_score", 50),
        assessment_summary=raw.get("assessment_summary", ""),
        objective_matches=objective_matches,
        missing_data=missing_data,
        recommended_focus=raw.get("recommended_focus", ""),
    )


def determine_analysis_mode(
    relevance_score: int,
    force_mode: str | None = None,
    has_objectives: bool = True,
) -> str:
    """Determine the analysis mode based on relevance score.

    Args:
        relevance_score: 0-100 relevance score from assessment
        force_mode: Optional forced mode ('objective_focused' or 'open_exploration')
        has_objectives: Whether the user has defined business objectives

    Returns:
        'objective_focused' or 'open_exploration'
    """
    from bo1.models.dataset_objective_analysis import AnalysisMode

    # Respect force_mode if provided
    if force_mode:
        if force_mode in [
            AnalysisMode.OBJECTIVE_FOCUSED.value,
            AnalysisMode.OPEN_EXPLORATION.value,
        ]:
            return force_mode
        logger.warning(f"Invalid force_mode '{force_mode}', ignoring")

    # No objectives means open exploration
    if not has_objectives:
        return AnalysisMode.OPEN_EXPLORATION.value

    # High relevance (70+) triggers objective-focused mode
    if relevance_score >= 70:
        return AnalysisMode.OBJECTIVE_FOCUSED.value

    # Low relevance triggers open exploration
    return AnalysisMode.OPEN_EXPLORATION.value
