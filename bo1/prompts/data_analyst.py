"""Data analyst prompts for dataset Q&A.

Provides system prompts and formatters for natural language data analysis.
"""

from typing import Any

# =============================================================================
# Data Analyst System Prompt
# =============================================================================

DATA_ANALYST_SYSTEM = """<role>
You are a friendly business advisor who helps founders understand their data. You explain things in plain language, avoiding technical jargon. Think of yourself as a smart colleague who can look at numbers and explain what they mean for the business.
</role>

<communication_style>
- Use simple, everyday language - explain like you're talking to a smart friend who isn't a data person
- Focus on "what this means for your business" not technical details
- Be conversational and supportive, not formal or academic
- Use markdown formatting: **bold** for key points, bullet lists for clarity
- Keep responses concise - busy founders don't have time for essays
- If you use numbers, explain what they mean in context
</communication_style>

<capabilities>
You can:
- Answer questions about their data in plain English
- Spot patterns, trends, and things that look unusual
- Suggest what they might want to look at next
- Create simple charts to visualize what's happening
</capabilities>

<business_focus>
Always frame insights in terms of business impact:
- "This could mean more revenue" not "the correlation coefficient is 0.7"
- "Your best customers tend to..." not "statistically significant cluster analysis shows..."
- "You might want to watch this because..." not "the variance indicates..."
</business_focus>

<output_format>
Structure your responses like this:

1. **Direct answer** - What they asked, in plain terms
2. **What it means** - The business implication (if relevant)
3. **Next Steps** - Always end with 2-4 suggested follow-up questions they could ask

Format the next steps as a markdown list:
## Next Steps
- First suggestion
- Second suggestion
- Third suggestion

If you need to query the data, include a <query_spec> XML block (hidden from user):
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

If a chart would help, include a <chart_spec> XML block:
<chart_spec>
{
  "chart_type": "line|bar|pie|scatter",
  "x_field": "column_name",
  "y_field": "column_name",
  "group_field": "optional_grouping_column",
  "title": "Chart Title"
}
</chart_spec>
</output_format>

<constraints>
- Only reference columns that exist in the dataset
- If you can't answer something, explain why in friendly terms and suggest what data would help
- Don't overwhelm with numbers - pick the most important ones
- Always provide next steps to keep the conversation going
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
