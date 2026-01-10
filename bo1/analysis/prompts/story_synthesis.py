"""Prompt for synthesizing insights into a data story narrative.

Transforms individual insights into a cohesive narrative that
opens with the North Star, groups by objective, and provides
clear next steps.
"""

from typing import Any

STORY_SYNTHESIS_SYSTEM_PROMPT = """<role>
You are a business storyteller who transforms analytical findings into a compelling narrative for decision-makers.

You write for busy executives who want the bottom line first, then context. You group related findings, acknowledge limitations honestly, and always end with clear actions.
</role>

<storytelling_principles>
- Lead with impact: The most important finding comes first
- Group by objective: Organize insights by business goal, not by data pattern
- Be honest: Acknowledge what the data can't tell us
- End with action: Every story needs clear next steps
- Surprise value: Highlight anything unexpected - it often matters most
</storytelling_principles>

<output_format>
Return valid JSON with this structure:
{
    "opening_hook": "<1 sentence that captures attention, references the North Star goal>",
    "objective_sections": [
        {
            "objective_id": "<id>",
            "objective_name": "<name>",
            "summary": "<2-3 sentences synthesizing insights for this objective>",
            "insight_ids": ["<which insight ids belong here>"],
            "key_metric": "<the most important number for this objective>",
            "recommended_action": "<single most important action>"
        }
    ],
    "data_quality_summary": "<honest 1-2 sentence assessment of data limitations>",
    "unexpected_finding": {
        "headline": "<something interesting NOT directly in objectives>",
        "narrative": "<2-3 sentences on why this might matter>",
        "should_investigate": true|false
    } | null,
    "next_steps": [
        "<prioritized action 1 - most impactful>",
        "<prioritized action 2>",
        "<prioritized action 3>"
    ],
    "suggested_questions": [
        "<follow-up question derived from objectives + data>",
        "<another question>",
        "<another question>"
    ]
}
</output_format>"""


def format_context_for_synthesis(
    north_star: str | None = None,
    industry: str | None = None,
    business_model: str | None = None,
) -> str:
    """Format business context for story synthesis.

    Args:
        north_star: Primary business goal
        industry: Business industry
        business_model: Type of business model

    Returns:
        Formatted context string
    """
    lines = ["<context>"]
    if north_star:
        lines.append(f"  <north_star>{north_star}</north_star>")
    if industry:
        lines.append(f"  <industry>{industry}</industry>")
    if business_model:
        lines.append(f"  <model>{business_model}</model>")
    lines.append("</context>")
    return "\n".join(lines)


def format_relevance_for_synthesis(relevance: dict[str, Any]) -> str:
    """Format relevance assessment for story context.

    Args:
        relevance: Relevance assessment dict

    Returns:
        Formatted relevance string
    """
    lines = ["<relevance_assessment>"]

    score = relevance.get("relevance_score", 0)
    summary = relevance.get("assessment_summary", "")
    lines.append(f"  <score>{score}</score>")
    lines.append(f"  <summary>{summary}</summary>")

    objective_matches = relevance.get("objective_matches", [])
    if objective_matches:
        lines.append("  <objective_matches>")
        for match in objective_matches:
            obj_id = match.get("objective_id", "")
            obj_name = match.get("objective_name", "")
            relevance_level = match.get("relevance", "")
            lines.append(
                f'    <match id="{obj_id}" name="{obj_name}" relevance="{relevance_level}" />'
            )
        lines.append("  </objective_matches>")

    focus = relevance.get("recommended_focus", "")
    if focus:
        lines.append(f"  <focus>{focus}</focus>")

    lines.append("</relevance_assessment>")
    return "\n".join(lines)


def format_insights_for_synthesis(insights: list[dict[str, Any]]) -> str:
    """Format generated insights for story synthesis.

    Args:
        insights: List of insight dicts from insight generation

    Returns:
        Formatted insights string
    """
    if not insights:
        return "<insights>No insights generated</insights>"

    lines = ["<insights>"]
    for i, insight in enumerate(insights):
        insight_id = insight.get("id", f"insight_{i + 1}")
        objective_id = insight.get("objective_id", "")
        headline = insight.get("headline", "")
        narrative = insight.get("narrative", "")
        confidence = insight.get("confidence", "medium")
        recommendation = insight.get("recommendation", "")

        supporting = insight.get("supporting_data", {})
        metric = supporting.get("metric", "")
        comparison = supporting.get("comparison", "")

        lines.append(
            f'  <insight id="{insight_id}" objective="{objective_id}" confidence="{confidence}">'
        )
        lines.append(f"    <headline>{headline}</headline>")
        lines.append(f"    <narrative>{narrative}</narrative>")
        if metric:
            lines.append(f"    <key_metric>{metric}</key_metric>")
        if comparison:
            lines.append(f"    <comparison>{comparison}</comparison>")
        if recommendation:
            lines.append(f"    <recommendation>{recommendation}</recommendation>")
        lines.append("  </insight>")

    lines.append("</insights>")
    return "\n".join(lines)


def format_quality_issues_for_synthesis(issues: list[dict[str, Any]] | None = None) -> str:
    """Format data quality issues for synthesis context.

    Args:
        issues: List of data quality issue dicts

    Returns:
        Formatted quality issues string
    """
    if not issues:
        return "<data_quality>No significant issues</data_quality>"

    lines = ["<data_quality>"]
    for issue in issues[:3]:  # Top 3 for synthesis
        issue_type = issue.get("type", "")
        severity = issue.get("severity", "")
        description = issue.get("description", "")
        affected_pct = issue.get("affected_pct", 0)

        lines.append(
            f'  <issue type="{issue_type}" severity="{severity}" '
            f'impact="{affected_pct:.1f}%">{description}</issue>'
        )
    lines.append("</data_quality>")
    return "\n".join(lines)


def build_story_synthesis_prompt(
    insights: list[dict[str, Any]],
    relevance: dict[str, Any],
    quality_issues: list[dict[str, Any]] | None = None,
    north_star: str | None = None,
    industry: str | None = None,
    business_model: str | None = None,
) -> str:
    """Build the full prompt for data story synthesis.

    Args:
        insights: Generated insights from insight generation
        relevance: Relevance assessment dict
        quality_issues: Data quality issues
        north_star: Primary business goal
        industry: Business industry
        business_model: Type of business model

    Returns:
        Complete user prompt for the LLM
    """
    context = format_context_for_synthesis(
        north_star=north_star,
        industry=industry,
        business_model=business_model,
    )

    relevance_text = format_relevance_for_synthesis(relevance)
    insights_text = format_insights_for_synthesis(insights)
    quality_text = format_quality_issues_for_synthesis(quality_issues)

    return f"""{context}

{relevance_text}

{insights_text}

{quality_text}

<task>
Create a "Data Story" that:
1. Opens with the most important finding relative to the North Star goal
2. Groups insights by objective
3. Acknowledges data limitations honestly
4. Ends with clear, prioritized next steps

If there's something unexpected in the data that doesn't fit the stated objectives,
highlight it as an "unexpected finding" - these often reveal the most valuable insights.
</task>

Return your response as valid JSON matching the output format."""


def parse_story_response(response: str) -> dict[str, Any]:
    """Parse the LLM response into structured data story.

    Args:
        response: Raw LLM response text

    Returns:
        Parsed data story dictionary

    Raises:
        ValueError: If response cannot be parsed as valid JSON
    """
    import json

    response = response.strip()

    # Handle markdown code blocks
    if response.startswith("```"):
        lines = response.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            elif line.startswith("```") and in_block:
                break
            elif in_block:
                json_lines.append(line)
        response = "\n".join(json_lines)

    try:
        return dict(json.loads(response))
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse story response: {e}") from e
