"""Prompt for generating data requirements for a specific objective.

Helps users understand what data they need to collect to analyze
progress toward a business objective.
"""

from typing import Any

DATA_REQUIREMENTS_SYSTEM_PROMPT = """<role>
You are a data analyst helping a business user understand what data they need to collect to analyze progress toward a specific objective.

You explain data needs in plain business language, focusing on what's practical and actionable. You understand common business systems and what data they typically provide.
</role>

<guidelines>
- Be specific to the objective, not generic
- Use industry-appropriate terminology
- Suggest realistic, commonly available data sources
- Prioritize actionability over comprehensiveness
- Explain WHY each data type is needed in business terms
- Keep example column names realistic and recognizable
</guidelines>

<output_format>
Return valid JSON with this structure:
{
    "objective_summary": "<1 sentence restating what we're trying to analyze>",
    "essential_data": [
        {
            "name": "<data type name>",
            "description": "<what this data represents in plain terms>",
            "example_columns": ["<column_name_1>", "<column_name_2>"],
            "why_essential": "<why analysis fails without this - business impact>",
            "questions_answered": ["<what business questions this enables>"]
        }
    ],
    "valuable_additions": [
        {
            "name": "<data type name>",
            "description": "<what this data represents>",
            "insight_unlocked": "<what additional business insight this provides>",
            "priority": "high|medium|low"
        }
    ],
    "data_sources": [
        {
            "source_type": "<CRM|Analytics|Billing|Support|Marketing|Operations>",
            "example_tools": ["<Tool1>", "<Tool2>"],
            "typical_export_name": "<common export/report name>",
            "columns_typically_included": ["<col1>", "<col2>"]
        }
    ],
    "analysis_preview": "<2-3 sentences describing what kind of insights would be possible with this data>"
}
</output_format>"""


def format_objective_context(
    objective_name: str,
    objective_description: str | None = None,
    target_value: str | None = None,
    current_value: str | None = None,
    industry: str | None = None,
    business_model: str | None = None,
) -> str:
    """Format objective details for the prompt.

    Args:
        objective_name: Name of the objective
        objective_description: Optional detailed description
        target_value: Target to achieve
        current_value: Current state
        industry: Business industry
        business_model: Type of business model

    Returns:
        Formatted objective context string
    """
    lines = ["<objective>"]
    lines.append(f"  <name>{objective_name}</name>")

    if objective_description:
        lines.append(f"  <description>{objective_description}</description>")
    if target_value:
        lines.append(f"  <target>{target_value}</target>")
    if current_value:
        lines.append(f"  <current>{current_value}</current>")

    lines.append("</objective>")

    if industry or business_model:
        lines.append("<business>")
        if industry:
            lines.append(f"  <industry>{industry}</industry>")
        if business_model:
            lines.append(f"  <model>{business_model}</model>")
        lines.append("</business>")

    return "\n".join(lines)


def build_data_requirements_prompt(
    objective_name: str,
    objective_description: str | None = None,
    target_value: str | None = None,
    current_value: str | None = None,
    industry: str | None = None,
    business_model: str | None = None,
) -> str:
    """Build the full prompt for data requirements generation.

    Args:
        objective_name: Name of the objective
        objective_description: Optional detailed description
        target_value: Target to achieve
        current_value: Current state
        industry: Business industry
        business_model: Type of business model

    Returns:
        Complete user prompt for the LLM
    """
    objective_context = format_objective_context(
        objective_name=objective_name,
        objective_description=objective_description,
        target_value=target_value,
        current_value=current_value,
        industry=industry,
        business_model=business_model,
    )

    return f"""{objective_context}

<task>
Generate a comprehensive guide for what data would be needed to meaningfully analyze this objective.

Think about:
1. What metrics directly measure progress toward this objective?
2. What dimensions would allow segmentation and deeper analysis?
3. What temporal data is needed to track trends?
4. What contextual data would explain the "why" behind the numbers?
</task>

Return your response as valid JSON matching the output format."""


def parse_data_requirements_response(response: str) -> dict[str, Any]:
    """Parse the LLM response into structured data requirements.

    Args:
        response: Raw LLM response text

    Returns:
        Parsed data requirements dictionary

    Raises:
        ValueError: If response cannot be parsed as valid JSON
    """
    import json

    # Try to extract JSON from response
    response = response.strip()

    # Handle markdown code blocks
    if response.startswith("```"):
        lines = response.split("\n")
        # Remove first and last lines (code block markers)
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
        raise ValueError(f"Failed to parse data requirements response: {e}") from e
