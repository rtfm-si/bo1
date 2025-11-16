"""Formatting utilities for deliberation state.

Provides functions for formatting discussion history and other state
components for prompt inclusion.
"""

import re

from bo1.models.state import ContributionMessage, DeliberationState


def format_discussion_history(
    state: DeliberationState,
    include_round_numbers: bool = True,
    include_thinking: bool = False,
    max_contributions: int | None = None,
    separator: str = "---",
) -> str:
    r"""Format discussion history for prompt inclusion.

    Args:
        state: The deliberation state containing contributions
        include_round_numbers: Include round number in header
        include_thinking: Include <thinking> tags in output
        max_contributions: Limit to last N contributions (None = all)
        separator: Separator line between contributions

    Returns:
        Formatted discussion history string

    Examples:
        >>> formatted = format_discussion_history(state)
        "--- Maria (Round 1) ---\nI think we should...\n\n--- ..."

        >>> formatted = format_discussion_history(state, max_contributions=5)
        # Only last 5 contributions
    """
    contributions = state.contributions
    if max_contributions:
        contributions = contributions[-max_contributions:]

    lines = []
    for msg in contributions:
        # Header
        if include_round_numbers:
            header = f"{separator} {msg.persona_name} (Round {msg.round_number}) {separator}"
        else:
            header = f"{separator} {msg.persona_name} {separator}"
        lines.append(header)

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

    return "\n".join(lines)


def format_contributions_list(
    contributions: list[ContributionMessage],
    include_round_numbers: bool = True,
    include_thinking: bool = False,
    separator: str = "---",
) -> str:
    """Format a list of contributions for prompt inclusion.

    Alternative to format_discussion_history that works directly with a
    contribution list instead of requiring a full state object.

    Args:
        contributions: List of contribution messages
        include_round_numbers: Include round number in header
        include_thinking: Include <thinking> tags in output
        separator: Separator line between contributions

    Returns:
        Formatted contributions string
    """
    lines = []
    for msg in contributions:
        # Header
        if include_round_numbers:
            header = f"{separator} {msg.persona_name} (Round {msg.round_number}) {separator}"
        else:
            header = f"{separator} {msg.persona_name} {separator}"
        lines.append(header)

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

    return "\n".join(lines)
