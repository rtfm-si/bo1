"""State serialization utilities for export and reporting.

Provides functions to convert deliberation state into various formats:
- JSON (machine-readable)
- Markdown (human-readable transcripts)
- Summary reports
"""

import json
from typing import Any

from bo1.graph.state import DeliberationGraphState


def to_json(state: DeliberationGraphState, indent: int = 2) -> str:
    """Export deliberation state as JSON.

    Args:
        state: Deliberation state to export (v2 graph state)
        indent: JSON indentation (default: 2 spaces)

    Returns:
        JSON string representation

    Examples:
        >>> json_str = to_json(state)
        >>> with open("session.json", "w") as f:
        ...     f.write(json_str)
    """
    # Convert state to serializable dict
    serializable = _state_to_serializable(state)
    return json.dumps(serializable, indent=indent, default=str)


def from_json(json_str: str) -> DeliberationGraphState:
    """Import deliberation state from JSON.

    Args:
        json_str: JSON string

    Returns:
        Deliberation state object (v2 graph state)

    Examples:
        >>> with open("session.json") as f:
        ...     json_str = f.read()
        >>> state = from_json(json_str)
    """
    data = json.loads(json_str)
    # Convert back to DeliberationGraphState (TypedDict)
    return _dict_to_state(data)


def _state_to_serializable(state: DeliberationGraphState) -> dict[str, Any]:
    """Convert state to a JSON-serializable dictionary."""
    result: dict[str, Any] = {}

    # Copy simple fields
    result["session_id"] = state.get("session_id", "")
    result["phase"] = str(state.get("phase", "")) if state.get("phase") else None
    result["round_number"] = state.get("round_number", 0)
    result["max_rounds"] = state.get("max_rounds", 10)
    result["synthesis"] = state.get("synthesis")
    result["should_stop"] = state.get("should_stop", False)
    result["stop_reason"] = state.get("stop_reason")

    # Serialize problem
    problem = state.get("problem")
    if problem:
        result["problem"] = (
            problem.model_dump() if hasattr(problem, "model_dump") else dict(problem)
        )

    # Serialize current_sub_problem
    current_sp = state.get("current_sub_problem")
    if current_sp:
        result["current_sub_problem"] = (
            current_sp.model_dump() if hasattr(current_sp, "model_dump") else dict(current_sp)
        )

    # Serialize personas
    personas = state.get("personas", [])
    result["personas"] = [p.model_dump() if hasattr(p, "model_dump") else dict(p) for p in personas]

    # Serialize contributions
    contributions = state.get("contributions", [])
    result["contributions"] = [
        c.model_dump() if hasattr(c, "model_dump") else dict(c) for c in contributions
    ]

    # Serialize votes/recommendations
    result["votes"] = state.get("votes", [])

    # Serialize metrics
    metrics = state.get("metrics")
    if metrics:
        result["metrics"] = (
            metrics.model_dump() if hasattr(metrics, "model_dump") else dict(metrics)
        )

    # Serialize round_summaries
    result["round_summaries"] = state.get("round_summaries", [])

    return result


def _dict_to_state(data: dict[str, Any]) -> DeliberationGraphState:
    """Convert a dictionary back to DeliberationGraphState."""
    from bo1.graph.state import create_initial_state
    from bo1.models.persona import PersonaProfile
    from bo1.models.problem import Problem, SubProblem
    from bo1.models.state import ContributionMessage, DeliberationMetrics, DeliberationPhase

    # Recreate problem
    problem = (
        Problem(**data["problem"])
        if data.get("problem")
        else Problem(title="Unknown", description="Unknown", context="")
    )

    # Create initial state
    state = create_initial_state(
        session_id=data.get("session_id", ""),
        problem=problem,
        max_rounds=data.get("max_rounds", 10),
    )

    # Set phase
    phase_str = data.get("phase")
    if phase_str:
        try:
            state["phase"] = DeliberationPhase(phase_str)
        except (ValueError, KeyError):
            pass

    # Set round_number
    state["round_number"] = data.get("round_number", 0)

    # Restore current_sub_problem
    if data.get("current_sub_problem"):
        state["current_sub_problem"] = SubProblem(**data["current_sub_problem"])

    # Restore personas
    if data.get("personas"):
        state["personas"] = [PersonaProfile(**p) for p in data["personas"]]

    # Restore contributions
    if data.get("contributions"):
        state["contributions"] = [ContributionMessage(**c) for c in data["contributions"]]

    # Restore votes
    state["votes"] = data.get("votes", [])

    # Restore synthesis
    state["synthesis"] = data.get("synthesis")

    # Restore metrics
    if data.get("metrics"):
        state["metrics"] = DeliberationMetrics(**data["metrics"])

    # Restore round_summaries
    state["round_summaries"] = data.get("round_summaries", [])

    return state


def to_markdown(state: DeliberationGraphState, include_metadata: bool = True) -> str:
    """Export deliberation as human-readable Markdown transcript.

    Args:
        state: Deliberation state to export (v2 graph state)
        include_metadata: Include session metadata (timestamps, costs, etc.)

    Returns:
        Markdown-formatted transcript

    Examples:
        >>> markdown = to_markdown(state)
        >>> with open("transcript.md", "w") as f:
        ...     f.write(markdown)
    """
    lines = []

    # Header
    lines.append("# Board of One Deliberation Transcript\n")

    session_id = state.get("session_id", "unknown")
    phase = state.get("phase")
    round_number = state.get("round_number", 0)
    problem = state.get("problem")
    current_sp = state.get("current_sub_problem")
    personas = state.get("personas", [])
    contributions = state.get("contributions", [])
    votes = state.get("votes", [])
    synthesis = state.get("synthesis")
    metrics = state.get("metrics")

    if include_metadata:
        lines.append("## Session Metadata\n")
        lines.append(f"- **Session ID**: `{session_id}`")
        lines.append(f"- **Phase**: {phase.value if phase else 'unknown'}")
        lines.append(f"- **Current Round**: {round_number}\n")

    # Problem
    if problem:
        lines.append("## Problem Statement\n")
        lines.append(f"**{problem.title}**\n")
        lines.append(f"{problem.description}\n")

        if problem.context:
            lines.append("### Context\n")
            lines.append(f"{problem.context}\n")

        if problem.constraints:
            lines.append("### Constraints\n")
            for constraint in problem.constraints:
                value_str = f" ({constraint.value})" if constraint.value else ""
                lines.append(f"- **{constraint.type.value}**: {constraint.description}{value_str}")
            lines.append("")

    # Sub-problems
    if current_sp:
        lines.append("## Sub-Problem Under Deliberation\n")
        lines.append(f"**ID**: `{current_sp.id}`")
        lines.append(f"**Goal**: {current_sp.goal}")
        lines.append(f"**Complexity**: {current_sp.complexity_score}/10\n")

        if current_sp.context:
            lines.append(f"**Context**: {current_sp.context}\n")

    # Participants
    if personas:
        lines.append("## Participants\n")
        for persona in personas:
            lines.append(f"- **{persona.name}** (`{persona.code}`) - {persona.domain}")
        lines.append("")

    # Contributions
    if contributions:
        lines.append("## Deliberation Transcript\n")

        for contrib in contributions:
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
            tokens_used = (
                contrib.tokens_used
                if hasattr(contrib, "tokens_used")
                else (contrib.token_count or 0)
            )
            cost = contrib.cost or 0.0
            lines.append(f"_Tokens: {tokens_used} | Cost: ${cost:.6f}_\n")
            lines.append("---\n")

    # Votes/Recommendations
    if votes:
        lines.append("## Voting Results\n")

        for vote in votes:
            # Handle both dict and object formats
            if isinstance(vote, dict):
                persona_name = vote.get("persona_name", "Unknown")
                persona_code = vote.get("persona_code", "unknown")
                recommendation = vote.get("recommendation", "")
                confidence = vote.get("confidence", 0)
                reasoning = vote.get("reasoning", "")
                conditions = vote.get("conditions", [])
            else:
                persona_name = vote.persona_name
                persona_code = vote.persona_code
                recommendation = vote.recommendation
                confidence = vote.confidence
                reasoning = vote.reasoning
                conditions = vote.conditions

            lines.append(f"### {persona_name} (`{persona_code}`)\n")
            lines.append(f"**Recommendation**: {recommendation}")
            lines.append(f"**Confidence**: {confidence * 100:.0f}%\n")

            if reasoning:
                lines.append(f"**Reasoning**: {reasoning}\n")

            if conditions:
                lines.append("**Conditions:**")
                for condition in conditions:
                    lines.append(f"- {condition}")
                lines.append("")

            lines.append("---\n")

    # Synthesis
    if synthesis:
        lines.append("## Final Synthesis\n")
        lines.append(f"{synthesis}\n")

    # Cost summary
    if include_metadata and metrics:
        lines.append("## Cost Summary\n")
        total_tokens = metrics.total_tokens
        total_cost = metrics.total_cost
        lines.append(f"- **Total Tokens**: {total_tokens:,}")
        lines.append(f"- **Total Cost**: ${total_cost:.6f}")

        if total_cost > 0:
            cost_per_round = total_cost / max(round_number, 1)
            lines.append(f"- **Cost per Round**: ${cost_per_round:.6f}")

    return "\n".join(lines)


def to_summary_dict(state: DeliberationGraphState) -> dict[str, Any]:
    """Export deliberation summary as a dictionary.

    Useful for analytics, dashboards, or API responses.

    Args:
        state: Deliberation state (v2 graph state)

    Returns:
        Dictionary with summary metrics

    Examples:
        >>> summary = to_summary_dict(state)
        >>> print(f"Completed in {summary['duration_seconds']}s")
    """
    problem = state.get("problem")
    current_sp = state.get("current_sub_problem")
    phase = state.get("phase")
    round_number = state.get("round_number", 0)
    contributions = state.get("contributions", [])
    votes = state.get("votes", [])
    personas = state.get("personas", [])
    synthesis = state.get("synthesis")
    metrics = state.get("metrics")

    total_tokens = 0
    total_cost = 0.0
    if metrics:
        total_tokens = metrics.total_tokens
        total_cost = metrics.total_cost

    return {
        "session_id": state.get("session_id", ""),
        "problem_title": problem.title if problem else None,
        "sub_problem_id": current_sp.id if current_sp else None,
        "sub_problem_goal": current_sp.goal if current_sp else None,
        "phase": phase.value if phase else None,
        "current_round": round_number,
        "total_contributions": len(contributions),
        "total_votes": len(votes),
        "participants": [p.code for p in personas],
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "has_synthesis": synthesis is not None,
    }


def export_to_file(state: DeliberationGraphState, filepath: str, format: str = "markdown") -> None:
    """Export deliberation to a file.

    Args:
        state: Deliberation state (v2 graph state)
        filepath: Path to output file
        format: Export format ('json' or 'markdown')

    Raises:
        ValueError: If format is not supported

    Examples:
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
