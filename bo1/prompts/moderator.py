"""Moderator agent prompts for strategic interventions in deliberations.

Moderators intervene to challenge assumptions, push for rigorous thinking,
and improve overall deliberation quality.
"""

from bo1.config import TokenBudgets
from bo1.prompts.protocols import (
    CITATION_REQUIREMENTS,
    CORE_PROTOCOL,
    SECURITY_PROTOCOL,
)
from bo1.prompts.sanitizer import sanitize_user_input

# Token budget constants for facilitator/moderator LLM calls (centralized in TokenBudgets)
FACILITATOR_MAX_TOKENS = TokenBudgets.FACILITATOR
FACILITATOR_TOKEN_WARNING_THRESHOLD = 0.9  # Warn at 90% usage

# =============================================================================
# Moderator System Prompt Template
# =============================================================================

MODERATOR_SYSTEM_TEMPLATE = """<system_role>
You are {persona_name}, a {persona_archetype} who intervenes strategically to improve deliberation quality.

Your role:
- Challenge prevailing assumptions when needed
- {moderator_specific_role}
- Push the group toward more rigorous thinking
- Intervene briefly and return focus to standard personas
</system_role>

<intervention_context>
Problem: {problem_statement}

Discussion so far: {discussion_excerpt}

Why you're being invoked: {trigger_reason}
</intervention_context>

{core_protocol}

<communication_protocol>
Format your intervention:

<thinking>
- What pattern in the discussion triggered my involvement?
- What assumption or blind spot needs challenging?
- What question or perspective is being overlooked?
- How can I add value without derailing the discussion?
</thinking>

<intervention>
Your strategic challenge (1-2 paragraphs):
- Challenge a specific assumption or gap in reasoning
- Raise questions the group may be avoiding
- Offer an alternative perspective to consider
- Include at least 1 source citation if making factual claims
- Keep it focused and hand discussion back to standard personas
</intervention>
</communication_protocol>

{citation_requirements}

{security_protocol}

<your_task>
Intervene to improve debate quality by {moderator_task_specific}, then return focus to the standard expert personas.
</your_task>"""


def compose_moderator_prompt(
    persona_name: str,
    persona_archetype: str,
    moderator_specific_role: str,
    moderator_task_specific: str,
    problem_statement: str,
    discussion_excerpt: str,
    trigger_reason: str,
) -> str:
    """Compose moderator intervention prompt."""
    safe_problem_statement = sanitize_user_input(problem_statement, context="problem_statement")
    return MODERATOR_SYSTEM_TEMPLATE.format(
        persona_name=persona_name,
        persona_archetype=persona_archetype,
        moderator_specific_role=moderator_specific_role,
        moderator_task_specific=moderator_task_specific,
        problem_statement=safe_problem_statement,
        discussion_excerpt=discussion_excerpt,
        trigger_reason=trigger_reason,
        core_protocol=CORE_PROTOCOL,
        citation_requirements=CITATION_REQUIREMENTS,
        security_protocol=SECURITY_PROTOCOL,
    )
