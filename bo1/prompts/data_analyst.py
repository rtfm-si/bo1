"""Data analyst prompts for dataset Q&A.

Provides system prompts and formatters for natural language data analysis.
"""

from typing import Any

# =============================================================================
# Data Analyst System Prompt
# =============================================================================

DATA_ANALYST_SYSTEM = """<role>
You are a data analyst assistant. Help users explore and understand their data through natural language queries.
</role>

<capabilities>
You can:
- Answer questions about the data using the profile information provided
- Generate query specifications to fetch specific data
- Suggest charts to visualize patterns
- Explain statistical concepts in context
</capabilities>

<business_awareness>
When the user has provided business context (goals, industry, constraints), incorporate this into your analysis:
- Prioritize recommendations that align with stated business goals
- Consider industry-specific best practices and benchmarks
- Flag data insights that relate to known constraints or challenges
- Frame analysis in terms of business impact when relevant
</business_awareness>

<output_format>
For each response, provide:
1. A direct answer to the user's question based on available data
2. Optionally, a query_spec to fetch specific data (if needed)
3. Optionally, a chart_spec to visualize results (if helpful)

If you need to query the data, output a <query_spec> XML block:
<query_spec>
{
  "query_type": "aggregate|filter|trend|compare|correlate",
  "filters": [{"field": "col", "operator": "eq|ne|gt|lt|gte|lte|contains|in", "value": "x"}],
  "group_by": {"fields": ["col"], "aggregates": [{"field": "col", "function": "sum|avg|min|max|count"}]},
  "trend": {"date_field": "col", "value_field": "col", "interval": "day|week|month|year"},
  "compare": {"group_field": "col", "value_field": "col", "aggregate_function": "sum"},
  "correlate": {"field_a": "col", "field_b": "col", "method": "pearson|spearman"},
  "limit": 100
}
</query_spec>

If you want to suggest a chart, output a <chart_spec> XML block:
<chart_spec>
{
  "chart_type": "line|bar|pie|scatter",
  "x_field": "column_name",
  "y_field": "column_name",
  "group_field": "optional_grouping_column",
  "title": "Chart Title"
}
</chart_spec>

Always provide a text explanation, even when generating specs.
</output_format>

<constraints>
- Only reference columns that exist in the dataset profile
- Be specific about which columns you're analyzing
- If the question can't be answered with available data, explain why
- Keep explanations clear and actionable
</constraints>"""


def format_dataset_context(
    profile: dict[str, Any],
    dataset_name: str,
    summary: str | None = None,
) -> str:
    """Format dataset profile for inclusion in analyst prompt.

    Args:
        profile: Dataset profile dictionary with columns and stats
        dataset_name: Name of the dataset
        summary: Optional LLM-generated summary

    Returns:
        Formatted context string for prompt
    """
    lines = [
        f'<dataset name="{dataset_name}">',
        "<metadata>",
        f"  <rows>{profile.get('row_count', 'unknown')}</rows>",
        f"  <columns>{profile.get('column_count', 'unknown')}</columns>",
        "</metadata>",
    ]

    if summary:
        lines.extend(
            [
                "<summary>",
                summary,
                "</summary>",
            ]
        )

    lines.append("<schema>")
    for col in profile.get("columns", []):
        col_name = col.get("name", col.get("column_name", "unknown"))
        col_type = col.get("inferred_type", col.get("data_type", "unknown"))
        stats = col.get("stats", {})

        # Build stats string
        stat_parts = []
        if stats.get("null_count", 0) > 0:
            row_count = profile.get("row_count", 1)
            null_pct = (stats["null_count"] / row_count) * 100 if row_count else 0
            stat_parts.append(f"null: {null_pct:.1f}%")
        if stats.get("unique_count"):
            stat_parts.append(f"unique: {stats['unique_count']}")
        if stats.get("min_value") is not None:
            stat_parts.append(f"min: {stats['min_value']}")
        if stats.get("max_value") is not None:
            stat_parts.append(f"max: {stats['max_value']}")
        if stats.get("mean_value") is not None:
            stat_parts.append(f"mean: {stats['mean_value']:.2f}")

        stat_str = f" ({', '.join(stat_parts)})" if stat_parts else ""
        lines.append(f'  <column name="{col_name}" type="{col_type}"{stat_str} />')

    lines.append("</schema>")
    lines.append("</dataset>")

    return "\n".join(lines)


def format_conversation_history(messages: list[dict[str, Any]]) -> str:
    """Format conversation history for context.

    Args:
        messages: List of message dicts with role/content

    Returns:
        Formatted conversation string
    """
    if not messages:
        return ""

    lines = ["<conversation_history>"]
    for msg in messages[-10:]:  # Last 10 messages max
        role = msg.get("role", "user")
        content = msg.get("content", "")
        lines.append(f"<{role}>{content}</{role}>")
    lines.append("</conversation_history>")

    return "\n".join(lines)


def format_business_context(context: dict[str, Any] | None) -> str:
    """Format user business context for prompt injection.

    Args:
        context: User context dict with goals, industry, constraints, etc.

    Returns:
        Formatted business context string or empty string if no context
    """
    if not context:
        return ""

    lines = ["<business_context>"]

    if context.get("goals"):
        lines.append(f"  <goals>{context['goals']}</goals>")
    if context.get("industry"):
        lines.append(f"  <industry>{context['industry']}</industry>")
    if context.get("competitors"):
        lines.append(f"  <competitors>{context['competitors']}</competitors>")
    if context.get("constraints"):
        lines.append(f"  <constraints>{context['constraints']}</constraints>")
    if context.get("metrics"):
        lines.append(f"  <key_metrics>{context['metrics']}</key_metrics>")

    lines.append("</business_context>")

    # Only return if we have any content beyond the tags
    if len(lines) > 2:
        return "\n".join(lines)
    return ""


def format_clarifications_context(clarifications: list[dict[str, Any]]) -> str:
    """Format previous clarifications for context injection.

    Args:
        clarifications: List of {question, answer, timestamp} dicts

    Returns:
        Formatted clarifications string for prompt context
    """
    if not clarifications:
        return ""

    lines = [
        "<prior_clarifications>",
        "The user has previously provided these clarifications about their data:",
    ]
    for i, c in enumerate(clarifications[-10:], 1):  # Last 10 max
        q = c.get("question", "")
        a = c.get("answer", "")
        lines.append(f'  <clarification id="{i}">')
        lines.append(f"    <question>{q}</question>")
        lines.append(f"    <answer>{a}</answer>")
        lines.append("  </clarification>")
    lines.append("</prior_clarifications>")

    return "\n".join(lines)


def build_analyst_prompt(
    question: str,
    dataset_context: str,
    conversation_history: str = "",
    clarifications_context: str = "",
    business_context: str = "",
) -> str:
    """Build the full user prompt for the analyst.

    Args:
        question: User's question
        dataset_context: Formatted dataset context
        conversation_history: Optional conversation history
        clarifications_context: Optional prior clarifications context
        business_context: Optional user business context

    Returns:
        Complete user prompt
    """
    parts = [dataset_context]

    if business_context:
        parts.append(business_context)

    if clarifications_context:
        parts.append(clarifications_context)

    if conversation_history:
        parts.append(conversation_history)

    parts.append(f"<question>{question}</question>")
    parts.append(
        "Analyze the data and answer the question. "
        "Include query_spec or chart_spec if they would help."
    )

    return "\n\n".join(parts)
