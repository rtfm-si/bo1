"""Data story synthesis module for narrative generation.

Transforms individual insights into a cohesive narrative that
opens with the North Star, groups by objective, and provides
clear next steps.
"""

import logging
from typing import Any

from bo1.analysis.prompts.story_synthesis import (
    STORY_SYNTHESIS_SYSTEM_PROMPT,
    build_story_synthesis_prompt,
    parse_story_response,
)
from bo1.llm.client import ClaudeClient
from bo1.models.dataset_objective_analysis import (
    DataStory,
    Insight,
    ObjectiveSection,
    RelevanceAssessment,
    UnexpectedFinding,
)

logger = logging.getLogger(__name__)


async def compile_data_story(
    insights: list[Insight],
    relevance: RelevanceAssessment | None = None,
    data_quality: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> DataStory:
    """Synthesize insights into a coherent data story narrative.

    Uses the story_synthesis prompt to create a compelling narrative
    for decision-makers that groups insights by objective.

    Args:
        insights: List of Insight models from generate_insights()
        relevance: RelevanceAssessment with objective matches
        data_quality: Dict of data quality issues with keys:
            - issues: list[dict] with type, severity, description, affected_rows, affected_pct
        context: Business context dict with:
            - north_star_goal: Primary business goal
            - industry: Business industry
            - business_model: Type of business model

    Returns:
        DataStory with opening hook, objective sections, and next steps
    """
    # Handle empty insights
    if not insights:
        return DataStory(
            opening_hook="No significant patterns found in this dataset.",
            objective_sections=[],
            data_quality_summary=_format_quality_summary(data_quality),
            unexpected_finding=None,
            next_steps=["Upload additional data for deeper analysis"],
            suggested_questions=["What patterns were you hoping to find?"],
        )

    # Convert insights to dict format for prompt
    insights_dicts = [
        {
            "id": insight.id,
            "objective_id": insight.objective_id,
            "headline": insight.headline,
            "narrative": insight.narrative,
            "confidence": insight.confidence.value,
            "recommendation": insight.recommendation,
            "supporting_data": insight.supporting_data,
        }
        for insight in insights
    ]

    # Convert relevance to dict format
    relevance_dict: dict[str, Any] = {}
    if relevance:
        relevance_dict = {
            "relevance_score": relevance.relevance_score,
            "assessment_summary": relevance.assessment_summary,
            "objective_matches": [
                {
                    "objective_id": match.objective_id,
                    "objective_name": match.objective_name,
                    "relevance": match.relevance.value,
                }
                for match in relevance.objective_matches
            ],
            "recommended_focus": relevance.recommended_focus,
        }

    # Extract quality issues
    quality_issues = []
    if data_quality:
        quality_issues = data_quality.get("issues", [])

    # Extract context values
    north_star = context.get("north_star_goal", context.get("north_star")) if context else None
    industry = context.get("industry") if context else None
    business_model = context.get("business_model") if context else None

    # Build the prompt
    user_prompt = build_story_synthesis_prompt(
        insights=insights_dicts,
        relevance=relevance_dict,
        quality_issues=quality_issues,
        north_star=north_star,
        industry=industry,
        business_model=business_model,
    )

    # Call LLM
    client = ClaudeClient()
    try:
        response_text, usage = await client.call(
            model="sonnet",
            system=STORY_SYNTHESIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            cache_system=True,
            temperature=0.4,  # Slightly creative for storytelling
            prefill="{",
        )

        # Parse response
        raw_story = parse_story_response(response_text)

        # Convert to typed model
        return _parse_story(raw_story)

    except Exception as e:
        logger.error(f"Error compiling data story: {e}")
        # Return a fallback story using insights directly
        return _create_fallback_story(insights, relevance, data_quality)


def _parse_story(raw: dict[str, Any]) -> DataStory:
    """Parse raw LLM response into typed DataStory model.

    Args:
        raw: Parsed JSON from LLM response

    Returns:
        DataStory model
    """
    # Parse objective sections
    objective_sections = []
    for section in raw.get("objective_sections", []):
        objective_sections.append(
            ObjectiveSection(
                objective_id=section.get("objective_id"),
                objective_name=section.get("objective_name", "Analysis"),
                summary=section.get("summary", ""),
                insight_ids=section.get("insight_ids", []),
                key_metric=section.get("key_metric", ""),
                recommended_action=section.get("recommended_action", ""),
            )
        )

    # Parse unexpected finding
    unexpected_finding = None
    raw_unexpected = raw.get("unexpected_finding")
    if raw_unexpected and isinstance(raw_unexpected, dict):
        unexpected_finding = UnexpectedFinding(
            headline=raw_unexpected.get("headline", ""),
            narrative=raw_unexpected.get("narrative", ""),
            should_investigate=raw_unexpected.get("should_investigate", False),
        )

    return DataStory(
        opening_hook=raw.get("opening_hook", "Here's what your data reveals:"),
        objective_sections=objective_sections,
        data_quality_summary=raw.get("data_quality_summary", "No significant data quality issues."),
        unexpected_finding=unexpected_finding,
        next_steps=raw.get("next_steps", []),
        suggested_questions=raw.get("suggested_questions", []),
    )


def _create_fallback_story(
    insights: list[Insight],
    relevance: RelevanceAssessment | None,
    data_quality: dict[str, Any] | None,
) -> DataStory:
    """Create a fallback data story when LLM call fails.

    Args:
        insights: Available insights
        relevance: Relevance assessment if available
        data_quality: Data quality issues if available

    Returns:
        Basic DataStory assembled from available data
    """
    # Group insights by objective
    objective_map: dict[str, list[Insight]] = {}
    for insight in insights:
        obj_id = insight.objective_id or "general"
        if obj_id not in objective_map:
            objective_map[obj_id] = []
        objective_map[obj_id].append(insight)

    # Create sections
    sections = []
    for obj_id, obj_insights in objective_map.items():
        obj_name = obj_insights[0].objective_name or "General Analysis"
        sections.append(
            ObjectiveSection(
                objective_id=obj_id if obj_id != "general" else None,
                objective_name=obj_name,
                summary="; ".join(i.headline for i in obj_insights[:3]),
                insight_ids=[i.id for i in obj_insights],
                key_metric=obj_insights[0].supporting_data.get("metric", "")
                if obj_insights[0].supporting_data
                else "",
                recommended_action=obj_insights[0].recommendation or "",
            )
        )

    # Build opening hook
    if relevance and relevance.relevance_score >= 70:
        hook = f"Your data is {relevance.relevance_score}% aligned with your objectives. Here's what it reveals:"
    elif insights:
        hook = f"I found {len(insights)} key patterns in your data:"
    else:
        hook = "Here's what your data reveals:"

    return DataStory(
        opening_hook=hook,
        objective_sections=sections,
        data_quality_summary=_format_quality_summary(data_quality),
        unexpected_finding=None,
        next_steps=[i.recommendation for i in insights[:3] if i.recommendation],
        suggested_questions=[q for i in insights for q in i.follow_up_questions[:1]],
    )


def _format_quality_summary(data_quality: dict[str, Any] | None) -> str:
    """Format data quality issues into a summary string.

    Args:
        data_quality: Dict with 'issues' list

    Returns:
        Human-readable summary of data quality
    """
    if not data_quality:
        return "No significant data quality issues detected."

    issues = data_quality.get("issues", [])
    if not issues:
        return "No significant data quality issues detected."

    # Count by severity
    severe = sum(1 for i in issues if i.get("severity") == "high")
    moderate = sum(1 for i in issues if i.get("severity") == "medium")

    if severe > 0:
        return f"{severe} severe and {moderate} moderate data quality issues found. Review recommended before analysis."
    elif moderate > 0:
        return f"{moderate} moderate data quality issues detected. Results may be affected."
    else:
        return f"{len(issues)} minor data quality observations noted."
