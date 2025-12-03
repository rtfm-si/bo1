"""Formatting utilities for deliberation state.

Provides functions for formatting discussion history and other state
components for prompt inclusion.

Consolidates formatting logic previously duplicated across:
- bo1/orchestration/voting.py
- bo1/agents/facilitator.py
"""

import re
from typing import TYPE_CHECKING, Literal

from bo1.models.state import ContributionMessage

if TYPE_CHECKING:
    from bo1.graph.state import DeliberationGraphState


FormatStyle = Literal["default", "compact", "voting"]


def format_discussion_history(
    state: "DeliberationGraphState",
    style: FormatStyle = "default",
    include_round_numbers: bool = True,
    include_thinking: bool = False,
    max_contributions: int | None = None,
) -> str:
    r"""Format discussion history for prompt inclusion.

    Args:
        state: The deliberation state containing contributions (v2 graph state)
        style: Format style to use:
            - "default": "--- persona_name (Round N) ---" format
            - "compact": "[Round N] persona_code:" format (for facilitator)
            - "voting": Includes problem statement header (for voting context)
        include_round_numbers: Include round number in header
        include_thinking: Include <thinking> tags in output
        max_contributions: Limit to last N contributions (None = all)

    Returns:
        Formatted discussion history string

    Examples:
        >>> format_discussion_history(state)
        "--- Maria (Round 1) ---\nI think we should...\n\n--- ..."

        >>> format_discussion_history(state, style="compact")
        "[Round 1] strategist:\nI think we should...\n"

        >>> format_discussion_history(state, style="voting")
        "PROBLEM STATEMENT:\n...\n\nFULL DISCUSSION:\n--- Maria (Round 1) ---\n..."
    """
    contributions = state.get("contributions", [])

    # Handle empty contributions for compact style
    if style == "compact" and not contributions:
        return "No contributions yet (initial round)."

    if max_contributions:
        contributions = contributions[-max_contributions:]

    # Build contribution lines
    contrib_lines = _format_contributions(
        contributions,
        style=style,
        include_round_numbers=include_round_numbers,
        include_thinking=include_thinking,
    )

    # Add headers for voting style
    if style == "voting":
        lines = []
        problem = state.get("problem")
        lines.append("PROBLEM STATEMENT:")
        lines.append(problem.description if problem else "No problem defined")
        lines.append("")
        lines.append("FULL DISCUSSION:")
        lines.append("")
        lines.extend(contrib_lines)
        return "\n".join(lines)

    return "\n".join(contrib_lines)


def format_contributions_list(
    contributions: list[ContributionMessage],
    style: FormatStyle = "default",
    include_round_numbers: bool = True,
    include_thinking: bool = False,
) -> str:
    """Format a list of contributions for prompt inclusion.

    Alternative to format_discussion_history that works directly with a
    contribution list instead of requiring a full state object.

    Args:
        contributions: List of contribution messages
        style: Format style ("default", "compact")
        include_round_numbers: Include round number in header
        include_thinking: Include <thinking> tags in output

    Returns:
        Formatted contributions string
    """
    lines = _format_contributions(
        contributions,
        style=style,
        include_round_numbers=include_round_numbers,
        include_thinking=include_thinking,
    )
    return "\n".join(lines)


def _format_contributions(
    contributions: list[ContributionMessage],
    style: FormatStyle,
    include_round_numbers: bool,
    include_thinking: bool,
) -> list[str]:
    """Internal helper to format contribution list."""
    lines = []

    for msg in contributions:
        # Header varies by style
        if style == "compact":
            # Facilitator style: [Round N] persona_code:
            lines.append(f"[Round {msg.round_number}] {msg.persona_code}:")
        elif include_round_numbers:
            # Default/voting style: --- persona_name (Round N) ---
            lines.append(f"--- {msg.persona_name} (Round {msg.round_number}) ---")
        else:
            lines.append(f"--- {msg.persona_name} ---")

        # Content
        content = msg.content
        if not include_thinking and msg.thinking:
            # Strip <thinking> tags if requested
            content = re.sub(
                r"<thinking>.*?</thinking>", "", content, flags=re.DOTALL | re.IGNORECASE
            )
            content = content.strip()

        lines.append(content)
        lines.append("")  # Blank line between contributions

    return lines
