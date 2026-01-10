"""Prompt for conversational data analysis responses.

Handles user questions about their data with objective-aware
responses that connect findings to business goals.
"""

from typing import Any

CONVERSATION_SYSTEM_PROMPT = """<role>
You are a helpful data analyst having a conversation about a dataset. You answer questions clearly, in plain business language, and always connect back to business objectives when relevant.

Think of yourself as a smart colleague who can look at numbers and explain what they mean for the business.
</role>

<response_style>
- Plain language: No statistical jargon
- Direct answers: Lead with the answer, then explain
- Numbers in context: Always say what the number means
- Connected: Link findings to business objectives when relevant
- Actionable: End with what the user could do next
</response_style>

<markdown_formatting>
Use markdown in your narrative:
- **Bold** for key numbers and findings
- Bullet lists for multiple points
- Keep responses concise - busy founders don't have time for essays
</markdown_formatting>

<output_format>
Return valid JSON with this structure:
{
    "answer_narrative": "<your response in markdown - direct, clear, actionable>",
    "key_finding": "<1 sentence summary of the main answer>",
    "supporting_data": [
        {
            "label": "<what this measures>",
            "value": "<number or value>",
            "context": "<vs what, or why this matters>"
        }
    ],
    "visualization": {
        "type": "bar|line|scatter|pie|heatmap|table",
        "config": {
            "x_axis": "<column>",
            "y_axis": "<column>",
            "group_by": "<column or null>",
            "aggregation": "sum|avg|count|min|max",
            "filters": []
        },
        "title": "<chart title>",
        "insight_callout": "<what to notice in the chart>"
    } | null,
    "relevant_objectives": ["<objective_ids this relates to>"],
    "follow_up_questions": [
        "<natural next question 1>",
        "<natural next question 2>",
        "<natural next question 3>"
    ],
    "confidence": "high|medium|low",
    "caveats": ["<any limitations or warnings about this answer>"]
}

If the question cannot be answered with the available data:
- Set confidence to "low"
- Explain what's missing in the narrative
- Suggest what data would help
- Still provide follow_up_questions for what CAN be explored
</output_format>"""


def format_objectives_for_conversation(objectives: list[dict[str, Any]] | None = None) -> str:
    """Format business objectives for conversation context.

    Args:
        objectives: List of objective dicts

    Returns:
        Formatted objectives string
    """
    if not objectives:
        return ""

    lines = ["<business_objectives>"]
    for obj in objectives:
        obj_id = obj.get("id", "")
        name = obj.get("name", "")
        target = obj.get("target", "")
        current = obj.get("current", "")

        lines.append(f'  <objective id="{obj_id}">')
        lines.append(f"    <name>{name}</name>")
        if target:
            lines.append(f"    <target>{target}</target>")
        if current:
            lines.append(f"    <current>{current}</current>")
        lines.append("  </objective>")

    lines.append("</business_objectives>")
    return "\n".join(lines)


def format_dataset_profile_for_conversation(
    profile: dict[str, Any],
    dataset_name: str | None = None,
) -> str:
    """Format dataset profile for conversation context.

    Args:
        profile: Dataset profile dict with columns and stats
        dataset_name: Optional name of the dataset

    Returns:
        Formatted profile string
    """
    name = dataset_name or profile.get("name", "dataset")
    row_count = profile.get("row_count", "unknown")
    columns = profile.get("columns", [])

    lines = [f'<dataset name="{name}">']
    lines.append(f"  <rows>{row_count}</rows>")

    lines.append("  <columns>")
    for col in columns[:30]:  # Limit to 30 columns
        col_name = col.get("name", col.get("column_name", ""))
        col_type = col.get("type", col.get("inferred_type", ""))
        stats = col.get("stats", {})

        stat_parts = []
        if stats.get("unique_count"):
            stat_parts.append(f"unique={stats['unique_count']}")
        if stats.get("null_pct"):
            stat_parts.append(f"null={stats['null_pct']:.1f}%")
        if stats.get("min") is not None:
            stat_parts.append(f"min={stats['min']}")
        if stats.get("max") is not None:
            stat_parts.append(f"max={stats['max']}")

        stat_str = f" [{', '.join(stat_parts)}]" if stat_parts else ""
        lines.append(f'    <column name="{col_name}" type="{col_type}"{stat_str} />')

    lines.append("  </columns>")
    lines.append("</dataset>")
    return "\n".join(lines)


def format_conversation_history(messages: list[dict[str, Any]] | None = None) -> str:
    """Format previous conversation messages.

    Args:
        messages: List of message dicts with role and content

    Returns:
        Formatted conversation history string
    """
    if not messages:
        return ""

    lines = ["<conversation_history>"]
    for msg in messages[-8:]:  # Last 8 messages for context
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Truncate long messages
        if len(content) > 500:
            content = content[:500] + "..."
        lines.append(f"  <{role}>{content}</{role}>")
    lines.append("</conversation_history>")
    return "\n".join(lines)


def format_available_columns(columns: list[dict[str, Any]] | list[str]) -> str:
    """Format available columns for query context.

    Args:
        columns: List of column dicts or column names

    Returns:
        Formatted columns string
    """
    lines = ["<available_columns>"]

    for col in columns:
        if isinstance(col, str):
            lines.append(f"  <column>{col}</column>")
        else:
            name = col.get("name", col.get("column_name", ""))
            dtype = col.get("type", col.get("inferred_type", ""))
            lines.append(f'  <column name="{name}" type="{dtype}" />')

    lines.append("</available_columns>")
    return "\n".join(lines)


def build_conversation_prompt(
    question: str,
    profile: dict[str, Any],
    objectives: list[dict[str, Any]] | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    columns: list[dict[str, Any]] | list[str] | None = None,
    dataset_name: str | None = None,
) -> str:
    """Build the full prompt for conversational response.

    Args:
        question: User's question
        profile: Dataset profile dict
        objectives: Business objectives
        conversation_history: Previous messages
        columns: Available columns (if different from profile)
        dataset_name: Name of the dataset

    Returns:
        Complete user prompt for the LLM
    """
    parts = []

    # Add objectives if available
    objectives_text = format_objectives_for_conversation(objectives)
    if objectives_text:
        parts.append(objectives_text)

    # Add dataset profile
    profile_text = format_dataset_profile_for_conversation(profile, dataset_name)
    parts.append(profile_text)

    # Add available columns if provided separately
    if columns:
        columns_text = format_available_columns(columns)
        parts.append(columns_text)

    # Add conversation history
    history_text = format_conversation_history(conversation_history)
    if history_text:
        parts.append(history_text)

    # Add the question
    parts.append(f"<question>{question}</question>")

    # Add task instruction
    parts.append("""<task>
Answer the question:
1. In plain business language (no statistical jargon)
2. With supporting data and numbers
3. With a visualization if it would help understanding
4. Connected to relevant objectives
5. With suggested follow-up questions
</task>

Return your response as valid JSON matching the output format.""")

    return "\n\n".join(parts)


def parse_conversation_response(response: str) -> dict[str, Any]:
    """Parse the LLM response into structured conversation reply.

    Args:
        response: Raw LLM response text

    Returns:
        Parsed conversation response dictionary

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
        raise ValueError(f"Failed to parse conversation response: {e}") from e
