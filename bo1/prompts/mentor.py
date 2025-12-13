"""Mentor chat prompts for business advisory conversations.

Provides system prompts and formatters for the mentor chat feature.
Personas: general, action_coach, data_analyst
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.services.mention_resolver import ResolvedMentions

# =============================================================================
# Mentor System Prompts (by persona)
# =============================================================================

MENTOR_SYSTEM_GENERAL = """<role>
You are a seasoned business mentor with expertise across strategy, operations, and growth.
Help the user think through business challenges with practical, actionable guidance.
</role>

<style>
- Be direct and concise
- Ask clarifying questions when needed
- Provide structured recommendations when appropriate
- Reference the user's business context when relevant
- Suggest concrete next steps
</style>

<constraints>
- Focus on actionable advice, not theory
- Consider the user's specific business context
- If you don't have enough context, ask
- Keep responses focused and practical
</constraints>"""

MENTOR_SYSTEM_ACTION_COACH = """<role>
You are an action-oriented business coach specializing in execution, prioritization, and getting things done.
Help the user manage their actions, overcome blockers, and stay focused on high-impact work.
</role>

<style>
- Be direct and results-focused
- Help prioritize ruthlessly
- Break down complex tasks into actionable steps
- Identify and address blockers
- Suggest timeboxing and deadlines
</style>

<constraints>
- Focus on execution, not strategy
- Reference the user's active actions when relevant
- Help with prioritization decisions
- Suggest concrete next actions
</constraints>"""

MENTOR_SYSTEM_DATA_ANALYST = """<role>
You are a data-savvy business analyst who helps interpret metrics and make data-driven decisions.
Help the user understand their data, identify patterns, and translate insights into action.
</role>

<style>
- Ground advice in data when available
- Explain metrics in business terms
- Suggest what data to track
- Help interpret trends and anomalies
</style>

<constraints>
- Reference the user's datasets when available
- Suggest specific analyses when helpful
- Keep explanations accessible to non-technical users
- Focus on actionable insights, not just numbers
</constraints>"""

# Mapping of persona to system prompt
MENTOR_PERSONAS = {
    "general": MENTOR_SYSTEM_GENERAL,
    "action_coach": MENTOR_SYSTEM_ACTION_COACH,
    "data_analyst": MENTOR_SYSTEM_DATA_ANALYST,
}


def get_mentor_system_prompt(persona: str = "general") -> str:
    """Get the system prompt for a mentor persona.

    Args:
        persona: Persona name (general, action_coach, data_analyst)

    Returns:
        System prompt string
    """
    return MENTOR_PERSONAS.get(persona, MENTOR_SYSTEM_GENERAL)


# =============================================================================
# Context Formatters
# =============================================================================


def format_business_context(context: dict[str, Any] | None) -> str:
    """Format user's business context for inclusion in mentor prompt.

    Args:
        context: Business context dictionary from user_context table

    Returns:
        Formatted context string or empty string if no context
    """
    if not context:
        return ""

    lines = ["<business_context>"]

    # Core business info
    if context.get("company_name"):
        lines.append(f"  <company>{context['company_name']}</company>")
    if context.get("business_model"):
        lines.append(f"  <model>{context['business_model']}</model>")
    if context.get("target_market"):
        lines.append(f"  <market>{context['target_market']}</market>")
    if context.get("product_description"):
        lines.append(f"  <product>{context['product_description']}</product>")
    if context.get("industry"):
        lines.append(f"  <industry>{context['industry']}</industry>")
    if context.get("business_stage"):
        lines.append(f"  <stage>{context['business_stage']}</stage>")

    # Key metrics
    metrics = []
    if context.get("revenue"):
        metrics.append(f"revenue: {context['revenue']}")
    if context.get("customers"):
        metrics.append(f"customers: {context['customers']}")
    if context.get("growth_rate"):
        metrics.append(f"growth: {context['growth_rate']}")
    if context.get("team_size"):
        metrics.append(f"team: {context['team_size']}")
    if metrics:
        lines.append(f"  <metrics>{', '.join(metrics)}</metrics>")

    # Constraints
    constraints = []
    if context.get("budget_constraints"):
        constraints.append(f"budget: {context['budget_constraints']}")
    if context.get("time_constraints"):
        constraints.append(f"time: {context['time_constraints']}")
    if context.get("regulatory_constraints"):
        constraints.append(f"regulatory: {context['regulatory_constraints']}")
    if constraints:
        lines.append(f"  <constraints>{', '.join(constraints)}</constraints>")

    # Objectives
    if context.get("primary_objective"):
        lines.append(f"  <objective>{context['primary_objective']}</objective>")
    if context.get("main_value_proposition"):
        lines.append(f"  <value_prop>{context['main_value_proposition']}</value_prop>")

    lines.append("</business_context>")

    # Only return if we have actual content
    if len(lines) > 2:
        return "\n".join(lines)
    return ""


def format_recent_meetings(meetings: list[dict[str, Any]]) -> str:
    """Format recent meetings/sessions for context.

    Args:
        meetings: List of recent session dicts with problem_statement, created_at, synthesis

    Returns:
        Formatted meetings context string
    """
    if not meetings:
        return ""

    lines = [
        "<recent_meetings>",
        "The user has recently discussed these topics:",
    ]

    for meeting in meetings[:5]:  # Last 5 max
        problem = meeting.get("problem_statement", "")[:200]
        created = meeting.get("created_at", "")[:10]  # Just date
        lines.append(f'  <meeting date="{created}">')
        lines.append(f"    <topic>{problem}</topic>")
        if meeting.get("synthesis"):
            # Include brief synthesis summary if available
            synth = meeting.get("synthesis", "")
            if isinstance(synth, dict):
                synth = synth.get("executive_summary", "")[:300]
            elif isinstance(synth, str):
                synth = synth[:300]
            if synth:
                lines.append(f"    <outcome>{synth}</outcome>")
        lines.append("  </meeting>")

    lines.append("</recent_meetings>")
    return "\n".join(lines)


def format_active_actions(actions: list[dict[str, Any]]) -> str:
    """Format active actions for context (especially for action_coach persona).

    Args:
        actions: List of action dicts with title, status, priority, due dates

    Returns:
        Formatted actions context string
    """
    if not actions:
        return ""

    lines = [
        "<active_actions>",
        "The user's current action items:",
    ]

    # Group by status
    in_progress = [a for a in actions if a.get("status") == "in_progress"]
    todo = [a for a in actions if a.get("status") == "todo"]
    blocked = [a for a in actions if a.get("status") == "blocked"]

    def format_action(action: dict[str, Any]) -> str:
        title = action.get("title", "Untitled")
        priority = action.get("priority", "medium")
        due = action.get("target_end_date") or action.get("estimated_end_date")
        due_str = f' due="{due}"' if due else ""
        return f'    <action priority="{priority}"{due_str}>{title}</action>'

    if in_progress:
        lines.append("  <in_progress>")
        lines.extend([format_action(a) for a in in_progress[:5]])
        lines.append("  </in_progress>")

    if todo:
        lines.append("  <todo>")
        lines.extend([format_action(a) for a in todo[:5]])
        lines.append("  </todo>")

    if blocked:
        lines.append("  <blocked>")
        for a in blocked[:3]:
            title = a.get("title", "Untitled")
            reason = a.get("blocking_reason", "Unknown")
            lines.append(f'    <action reason="{reason}">{title}</action>')
        lines.append("  </blocked>")

    lines.append("</active_actions>")
    return "\n".join(lines)


def format_dataset_summaries(datasets: list[dict[str, Any]]) -> str:
    """Format dataset summaries for context (especially for data_analyst persona).

    Args:
        datasets: List of dataset dicts with name, summary, row_count, column_count

    Returns:
        Formatted datasets context string
    """
    if not datasets:
        return ""

    lines = [
        "<available_datasets>",
        "The user has these datasets:",
    ]

    for ds in datasets[:5]:  # Max 5 datasets
        name = ds.get("name", "Unnamed")
        rows = ds.get("row_count", 0)
        cols = ds.get("column_count", 0)
        lines.append(f'  <dataset name="{name}" rows="{rows}" columns="{cols}">')
        if ds.get("summary"):
            lines.append(f"    <summary>{ds['summary'][:200]}</summary>")
        lines.append("  </dataset>")

    lines.append("</available_datasets>")
    return "\n".join(lines)


def format_conversation_history(messages: list[dict[str, Any]]) -> str:
    """Format mentor conversation history for context.

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


def build_mentor_prompt(
    question: str,
    business_context: str = "",
    meetings_context: str = "",
    actions_context: str = "",
    datasets_context: str = "",
    conversation_history: str = "",
    mentioned_context: str = "",
) -> str:
    """Build the full user prompt for the mentor.

    Args:
        question: User's question
        business_context: Formatted business context
        meetings_context: Formatted recent meetings
        actions_context: Formatted active actions
        datasets_context: Formatted dataset summaries
        conversation_history: Formatted conversation history
        mentioned_context: Formatted @mention context (meetings, actions, datasets)

    Returns:
        Complete user prompt
    """
    parts = []

    if business_context:
        parts.append(business_context)
    if meetings_context:
        parts.append(meetings_context)
    if actions_context:
        parts.append(actions_context)
    if datasets_context:
        parts.append(datasets_context)
    # Add mentioned context just before conversation history and question
    if mentioned_context:
        parts.append(mentioned_context)
    if conversation_history:
        parts.append(conversation_history)

    parts.append(f"<question>{question}</question>")

    return "\n\n".join(parts)


# =============================================================================
# Mentioned Context Formatter
# =============================================================================


def format_mentioned_context(resolved: "ResolvedMentions") -> str:
    """Format resolved mentions for injection into mentor prompt.

    Args:
        resolved: ResolvedMentions from mention_resolver

    Returns:
        Formatted XML string for prompt injection, or empty string if no context
    """
    if not resolved.has_context():
        return ""

    lines = [
        "<mentioned_context>",
        "The user has specifically referenced these items:",
    ]

    # Format meetings
    if resolved.meetings:
        lines.append("  <referenced_meetings>")
        for m in resolved.meetings:
            lines.append(
                f'    <meeting id="{m.id}" status="{m.status}" date="{m.created_at or "unknown"}">'
            )
            lines.append(f"      <topic>{m.problem_statement}</topic>")
            if m.synthesis_summary:
                lines.append(f"      <outcome>{m.synthesis_summary}</outcome>")
            lines.append("    </meeting>")
        lines.append("  </referenced_meetings>")

    # Format actions
    if resolved.actions:
        lines.append("  <referenced_actions>")
        for a in resolved.actions:
            due_attr = f' due="{a.due_date}"' if a.due_date else ""
            priority_attr = f' priority="{a.priority}"' if a.priority else ""
            lines.append(f'    <action id="{a.id}" status="{a.status}"{priority_attr}{due_attr}>')
            lines.append(f"      <title>{a.title}</title>")
            if a.description:
                lines.append(f"      <description>{a.description}</description>")
            lines.append("    </action>")
        lines.append("  </referenced_actions>")

    # Format datasets
    if resolved.datasets:
        lines.append("  <referenced_datasets>")
        for d in resolved.datasets:
            rows = d.row_count or 0
            cols = d.column_count or 0
            lines.append(f'    <dataset id="{d.id}" rows="{rows}" columns="{cols}">')
            lines.append(f"      <name>{d.name}</name>")
            if d.description:
                lines.append(f"      <description>{d.description}</description>")
            if d.summary:
                lines.append(f"      <summary>{d.summary}</summary>")
            lines.append("    </dataset>")
        lines.append("  </referenced_datasets>")

    # Note if some mentions couldn't be resolved
    if resolved.not_found:
        lines.append(f"  <not_found>{', '.join(resolved.not_found)}</not_found>")

    lines.append("</mentioned_context>")
    return "\n".join(lines)
