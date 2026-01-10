"""Prompt for assessing dataset relevance to business objectives.

Evaluates how well a dataset can help achieve specific business
objectives before generating insights.
"""

from typing import Any

RELEVANCE_ASSESSMENT_SYSTEM_PROMPT = """<role>
You are a business analyst evaluating whether a dataset can help achieve specific business objectives. You think critically about what questions data can actually answer versus what would require additional information.
</role>

<guidelines>
- Be honest about limitations - don't oversell what the data can do
- Consider both direct measurements and derived insights
- Think about what's missing as much as what's present
- Frame everything in terms of business impact
- Score conservatively - a 70+ should mean genuinely useful data
</guidelines>

<scoring_guide>
- 80-100: Data directly measures key objective metrics with minimal gaps
- 60-79: Data provides useful signals but misses some important dimensions
- 40-59: Data offers partial insight, significant limitations
- 20-39: Data tangentially related, would need major additions
- 0-19: Data cannot meaningfully inform this objective
</scoring_guide>

<output_format>
Return valid JSON with this structure:
{
    "relevance_score": <0-100>,
    "assessment_summary": "<2-3 sentences on overall fit in plain language>",
    "objective_matches": [
        {
            "objective_id": "<id>",
            "objective_name": "<name>",
            "relevance": "high|medium|low|none",
            "explanation": "<why this data helps or doesn't - business terms>",
            "answerable_questions": ["<questions we CAN answer>"],
            "unanswerable_questions": ["<questions we CANNOT answer>"]
        }
    ],
    "missing_data": [
        {
            "data_needed": "<what's missing in plain terms>",
            "why_valuable": "<how it would help the business>",
            "objectives_unlocked": ["<which objectives it would serve>"]
        }
    ],
    "recommended_focus": "<where to focus the analysis given limitations>"
}
</output_format>"""


def format_business_context(
    north_star: str | None = None,
    objectives: list[dict[str, Any]] | None = None,
    industry: str | None = None,
    business_model: str | None = None,
) -> str:
    """Format business context for the prompt.

    Args:
        north_star: Primary business goal
        objectives: List of objective dicts with name, description, target, current
        industry: Business industry
        business_model: Type of business model

    Returns:
        Formatted business context string
    """
    lines = ["<business_context>"]

    if north_star:
        lines.append(f"  <north_star>{north_star}</north_star>")

    if objectives:
        lines.append("  <objectives>")
        for obj in objectives:
            obj_id = obj.get("id", "unknown")
            name = obj.get("name", "")
            desc = obj.get("description", "")
            target = obj.get("target", "")
            current = obj.get("current", "")

            lines.append(f'    <objective id="{obj_id}">')
            lines.append(f"      <name>{name}</name>")
            if desc:
                lines.append(f"      <description>{desc}</description>")
            if target:
                lines.append(f"      <target>{target}</target>")
            if current:
                lines.append(f"      <current>{current}</current>")
            lines.append("    </objective>")
        lines.append("  </objectives>")

    if industry:
        lines.append(f"  <industry>{industry}</industry>")
    if business_model:
        lines.append(f"  <business_model>{business_model}</business_model>")

    lines.append("</business_context>")
    return "\n".join(lines)


def format_dataset_info(
    dataset_name: str,
    columns_with_types: list[dict[str, str]],
    row_count: int,
    sample_rows: list[dict[str, Any]] | None = None,
) -> str:
    """Format dataset information for the prompt.

    Args:
        dataset_name: Name of the dataset
        columns_with_types: List of dicts with column name and type
        row_count: Number of rows in dataset
        sample_rows: Optional sample data rows

    Returns:
        Formatted dataset info string
    """
    lines = [f'<dataset name="{dataset_name}">']
    lines.append(f"  <row_count>{row_count}</row_count>")

    lines.append("  <columns>")
    for col in columns_with_types:
        col_name = col.get("name", col.get("column_name", "unknown"))
        col_type = col.get("type", col.get("inferred_type", "unknown"))
        lines.append(f'    <column name="{col_name}" type="{col_type}" />')
    lines.append("  </columns>")

    if sample_rows:
        lines.append("  <sample_data>")
        for i, row in enumerate(sample_rows[:5]):  # Max 5 sample rows
            lines.append(f"    <row_{i + 1}>")
            for key, value in row.items():
                # Truncate long values
                str_val = str(value)[:100]
                lines.append(f"      <{key}>{str_val}</{key}>")
            lines.append(f"    </row_{i + 1}>")
        lines.append("  </sample_data>")

    lines.append("</dataset>")
    return "\n".join(lines)


def build_relevance_assessment_prompt(
    dataset_name: str,
    columns_with_types: list[dict[str, str]],
    row_count: int,
    sample_rows: list[dict[str, Any]] | None = None,
    north_star: str | None = None,
    objectives: list[dict[str, Any]] | None = None,
    industry: str | None = None,
    business_model: str | None = None,
) -> str:
    """Build the full prompt for relevance assessment.

    Args:
        dataset_name: Name of the dataset
        columns_with_types: List of dicts with column name and type
        row_count: Number of rows in dataset
        sample_rows: Optional sample data rows
        north_star: Primary business goal
        objectives: List of objective dicts
        industry: Business industry
        business_model: Type of business model

    Returns:
        Complete user prompt for the LLM
    """
    business_context = format_business_context(
        north_star=north_star,
        objectives=objectives,
        industry=industry,
        business_model=business_model,
    )

    dataset_info = format_dataset_info(
        dataset_name=dataset_name,
        columns_with_types=columns_with_types,
        row_count=row_count,
        sample_rows=sample_rows,
    )

    return f"""{business_context}

{dataset_info}

<task>
Evaluate how well this dataset can inform progress toward the stated objectives.

Consider:
1. Does the data contain metrics that map to the objectives?
2. Can we derive insights that directly inform decisions?
3. What's missing that would strengthen the analysis?
4. What questions can we definitively answer vs. only speculate on?
</task>

Return your response as valid JSON matching the output format."""


def parse_relevance_response(response: str) -> dict[str, Any]:
    """Parse the LLM response into structured relevance assessment.

    Args:
        response: Raw LLM response text

    Returns:
        Parsed relevance assessment dictionary

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
        raise ValueError(f"Failed to parse relevance response: {e}") from e
