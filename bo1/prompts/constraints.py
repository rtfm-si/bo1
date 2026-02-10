"""Shared constraint formatting for prompt injection across all agents.

Provides a single formatter used by persona, facilitator, recommendation,
synthesis, and option extraction prompts.
"""

from bo1.models.problem import Constraint


def format_constraints_for_prompt(constraints: list[Constraint]) -> str:
    """Format constraints as XML block for LLM prompt injection.

    Returns empty string if no constraints, so callers can simply
    inject the result without conditional logic.

    Args:
        constraints: List of Constraint objects from Problem model

    Returns:
        XML-formatted constraint block or empty string
    """
    if not constraints:
        return ""

    lines = []
    for c in constraints:
        value_str = f" (value: {c.value})" if c.value is not None else ""
        lines.append(f"- [{c.type.value}] {c.description}{value_str}")

    return f"""<constraints>
ACTIVE CONSTRAINTS — you MUST consider these in your analysis.
Flag any recommendation that violates or creates tension with a constraint.

{chr(10).join(lines)}
</constraints>"""
