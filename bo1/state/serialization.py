"""State serialization utilities for export and reporting.

Provides functions to convert deliberation state into various formats:
- JSON (machine-readable)
- Markdown (human-readable transcripts)
- Summary reports
"""

from typing import Any

from bo1.models.state import DeliberationState


def to_json(state: DeliberationState, indent: int = 2) -> str:
    """Export deliberation state as JSON.

    Args:
        state: Deliberation state to export
        indent: JSON indentation (default: 2 spaces)

    Returns:
        JSON string representation

    Examples:
        >>> state = DeliberationState(...)
        >>> json_str = to_json(state)
        >>> with open("session.json", "w") as f:
        ...     f.write(json_str)
    """
    return state.model_dump_json(indent=indent)


def from_json(json_str: str) -> DeliberationState:
    """Import deliberation state from JSON.

    Args:
        json_str: JSON string

    Returns:
        Deliberation state object

    Examples:
        >>> with open("session.json") as f:
        ...     json_str = f.read()
        >>> state = from_json(json_str)
    """
    return DeliberationState.model_validate_json(json_str)


def to_markdown(state: DeliberationState, include_metadata: bool = True) -> str:
    """Export deliberation as human-readable Markdown transcript.

    Args:
        state: Deliberation state to export
        include_metadata: Include session metadata (timestamps, costs, etc.)

    Returns:
        Markdown-formatted transcript

    Examples:
        >>> state = DeliberationState(...)
        >>> markdown = to_markdown(state)
        >>> with open("transcript.md", "w") as f:
        ...     f.write(markdown)
    """
    lines = []

    # Header
    lines.append("# Board of One Deliberation Transcript\n")

    if include_metadata:
        lines.append("## Session Metadata\n")
        lines.append(f"- **Session ID**: `{state.session_id}`")
        lines.append(f"- **Created**: {state.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if state.completed_at:
            duration = (state.completed_at - state.created_at).total_seconds()
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            lines.append(f"- **Completed**: {state.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"- **Duration**: {minutes}m {seconds}s")
        lines.append(f"- **Phase**: {state.phase.value}")
        lines.append(f"- **Current Round**: {state.current_round}\n")

    # Problem
    lines.append("## Problem Statement\n")
    lines.append(f"**{state.problem.title}**\n")
    lines.append(f"{state.problem.description}\n")

    if state.problem.context:
        lines.append("### Context\n")
        lines.append(f"{state.problem.context}\n")

    if state.problem.constraints:
        lines.append("### Constraints\n")
        for constraint in state.problem.constraints:
            value_str = f" ({constraint.value})" if constraint.value else ""
            lines.append(f"- **{constraint.type.value}**: {constraint.description}{value_str}")
        lines.append("")

    # Sub-problems
    if state.sub_problem:
        lines.append("## Sub-Problem Under Deliberation\n")
        lines.append(f"**ID**: `{state.sub_problem.id}`")
        lines.append(f"**Goal**: {state.sub_problem.goal}")
        lines.append(f"**Complexity**: {state.sub_problem.complexity_score}/10\n")

        if state.sub_problem.context:
            lines.append(f"**Context**: {state.sub_problem.context}\n")

    # Participants
    if state.selected_personas:
        lines.append("## Participants\n")
        for persona in state.selected_personas:
            lines.append(f"- **{persona.name}** (`{persona.code}`) - {persona.domain}")
        lines.append("")

    # Contributions
    if state.contributions:
        lines.append("## Deliberation Transcript\n")

        for contrib in state.contributions:
            lines.append(f"### Round {contrib.round_number}: {contrib.persona_name}\n")

            # Parse contribution content (assuming XML format)
            content = contrib.content

            # Extract thinking section if present
            if "<thinking>" in content:
                thinking_start = content.find("<thinking>") + len("<thinking>")
                thinking_end = content.find("</thinking>")
                if thinking_end > thinking_start:
                    thinking = content[thinking_start:thinking_end].strip()
                    lines.append("**Internal Reasoning:**\n")
                    lines.append(f"_{thinking}_\n")

            # Extract contribution section if present
            if "<contribution>" in content:
                contrib_start = content.find("<contribution>") + len("<contribution>")
                contrib_end = content.find("</contribution>")
                if contrib_end > contrib_start:
                    contribution_text = content[contrib_start:contrib_end].strip()
                    lines.append("**Contribution:**\n")
                    lines.append(f"{contribution_text}\n")
            elif "<thinking>" not in content:
                # If no XML tags, just include raw content
                lines.append(f"{content}\n")

            # Metadata
            lines.append(f"_Tokens: {contrib.tokens_used} | Cost: ${contrib.cost:.6f}_\n")
            lines.append("---\n")

    # Votes
    if state.votes:
        lines.append("## Voting Results\n")

        for vote in state.votes:
            lines.append(f"### {vote.persona_name} (`{vote.persona_code}`)\n")
            lines.append(f"**Decision**: {vote.decision}")
            lines.append(f"**Confidence**: {vote.confidence * 100:.0f}%\n")

            if vote.reasoning:
                lines.append(f"**Reasoning**: {vote.reasoning}\n")

            if vote.conditions:
                lines.append("**Conditions:**")
                for condition in vote.conditions:
                    lines.append(f"- {condition}")
                lines.append("")

            lines.append("---\n")

    # Synthesis
    if state.synthesis:
        lines.append("## Final Synthesis\n")
        lines.append(f"{state.synthesis}\n")

    # Cost summary
    if include_metadata:
        lines.append("## Cost Summary\n")
        lines.append(f"- **Total Tokens**: {state.total_tokens:,}")
        lines.append(f"- **Total Cost**: ${state.total_cost:.6f}")

        if state.total_cost > 0:
            cost_per_round = state.total_cost / max(state.current_round, 1)
            lines.append(f"- **Cost per Round**: ${cost_per_round:.6f}")

    return "\n".join(lines)


def to_summary_dict(state: DeliberationState) -> dict[str, Any]:
    """Export deliberation summary as a dictionary.

    Useful for analytics, dashboards, or API responses.

    Args:
        state: Deliberation state

    Returns:
        Dictionary with summary metrics

    Examples:
        >>> state = DeliberationState(...)
        >>> summary = to_summary_dict(state)
        >>> print(f"Completed in {summary['duration_seconds']}s")
    """
    duration_seconds = None
    if state.completed_at:
        duration_seconds = (state.completed_at - state.created_at).total_seconds()

    return {
        "session_id": state.session_id,
        "problem_title": state.problem.title,
        "sub_problem_id": state.sub_problem.id if state.sub_problem else None,
        "sub_problem_goal": state.sub_problem.goal if state.sub_problem else None,
        "phase": state.phase.value,
        "current_round": state.current_round,
        "total_contributions": len(state.contributions),
        "total_votes": len(state.votes),
        "participants": [p.code for p in state.selected_personas]
        if state.selected_personas
        else [],
        "created_at": state.created_at.isoformat(),
        "completed_at": state.completed_at.isoformat() if state.completed_at else None,
        "duration_seconds": duration_seconds,
        "total_tokens": state.total_tokens,
        "total_cost": state.total_cost,
        "has_synthesis": state.synthesis is not None,
    }


def export_to_file(state: DeliberationState, filepath: str, format: str = "markdown") -> None:
    """Export deliberation to a file.

    Args:
        state: Deliberation state
        filepath: Path to output file
        format: Export format ('json' or 'markdown')

    Raises:
        ValueError: If format is not supported

    Examples:
        >>> state = DeliberationState(...)
        >>> export_to_file(state, "transcript.md", format="markdown")
        >>> export_to_file(state, "session.json", format="json")
    """
    if format == "markdown":
        content = to_markdown(state)
    elif format == "json":
        content = to_json(state)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'markdown'.")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
