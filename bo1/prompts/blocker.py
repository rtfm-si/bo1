"""Blocker analyzer prompts for suggesting unblock paths.

Provides prompt templates for analyzing blocked actions and generating
actionable suggestions to help users get unblocked.
"""

# System prompt for blocker analysis
BLOCKER_SYSTEM_PROMPT = """You are an expert business coach helping to unblock stalled actions.
Given a blocked action and its context, suggest 3-5 concrete approaches to move forward.

Each suggestion must be:
- Actionable: Can be started immediately
- Specific: Not vague advice like "try harder"
- Realistic: Achievable within reasonable effort

Effort levels:
- low: <2 hours, minimal dependencies
- medium: 2-8 hours or 1-2 dependencies
- high: >8 hours or multiple dependencies

Output JSON array:
[
  {"approach": "...", "rationale": "...", "effort_level": "low|medium|high"},
  ...
]

No markdown, no explanation - just the JSON array."""

# User prompt template
BLOCKER_USER_TEMPLATE = """Blocked action:
- Title: {title}
- Description: {description}
- Blocking reason: {blocking_reason}

{project_context}

Suggest 3-5 approaches to unblock this action."""


def build_blocker_prompt(
    title: str,
    description: str | None,
    blocking_reason: str | None,
    project_name: str | None = None,
) -> str:
    """Build the user prompt for blocker analysis.

    Args:
        title: Action title
        description: Action description (optional)
        blocking_reason: Why the action is blocked (optional)
        project_name: Parent project name if any

    Returns:
        Formatted user prompt string
    """
    project_context = ""
    if project_name:
        project_context = f"Project: {project_name}"

    return BLOCKER_USER_TEMPLATE.format(
        title=title,
        description=description or "(no description)",
        blocking_reason=blocking_reason or "(no blocking reason provided)",
        project_context=project_context,
    )
