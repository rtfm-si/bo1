"""Console adapter for LangGraph-based deliberations.

Provides a console-friendly interface for running deliberations with:
- Real-time progress display
- Pause/resume support
- Checkpoint recovery
- Rich UI integration
"""

import logging
import re
import uuid
from typing import Any

from rich.panel import Panel

from bo1.constants import GraphConfig
from bo1.graph.config import create_deliberation_graph
from bo1.graph.state import create_initial_state
from bo1.models.problem import Problem
from bo1.ui.console import Console

logger = logging.getLogger(__name__)


def validate_session_id(session_id: str) -> bool:
    """Validate session ID format (must be a valid UUID).

    Args:
        session_id: Session ID to validate

    Returns:
        True if valid UUID format, False otherwise
    """
    try:
        uuid.UUID(session_id)
        return True
    except (ValueError, AttributeError):
        return False


def sanitize_problem_statement(statement: str) -> str:
    """Sanitize problem statement to prevent injection attacks.

    Removes potentially dangerous characters while preserving meaningful content.

    Args:
        statement: Raw problem statement from user input

    Returns:
        Sanitized problem statement
    """
    # Strip leading/trailing whitespace
    sanitized = statement.strip()

    # Limit length to prevent DoS
    max_length = 10000
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    # Remove any null bytes
    sanitized = sanitized.replace("\x00", "")

    # Remove control characters except newlines, tabs, and carriage returns
    sanitized = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", sanitized)

    return sanitized


def validate_user_input(user_input: str, valid_options: list[str]) -> bool:
    """Validate user input against allowed options.

    Args:
        user_input: User's input string
        valid_options: List of valid options (case-insensitive)

    Returns:
        True if input is valid, False otherwise
    """
    return user_input.lower().strip() in [opt.lower() for opt in valid_options]


async def run_console_deliberation(
    problem: Problem,
    session_id: str | None = None,
    max_rounds: int = GraphConfig.MAX_ROUNDS_DEFAULT,
    debug: bool = False,
    export: bool = False,
    include_logs: bool = False,
) -> Any:  # Returns DeliberationGraphState but typing is complex
    """Run a deliberation session with console UI.

    Args:
        problem: Problem to deliberate on
        session_id: Optional session ID to resume from checkpoint
        max_rounds: Maximum number of deliberation rounds
        debug: Enable debug output
        export: Export transcript to exports/ directory (markdown + JSON)
        include_logs: Include detailed logs in export (tokens, costs, thinking)

    Returns:
        Final deliberation state

    Raises:
        ValueError: If session_id is invalid or problem statement is malformed

    Examples:
        >>> from bo1.models.problem import Problem
        >>> problem = Problem(
        ...     statement="Should we invest in AI?",
        ...     context={"budget": 100000}
        ... )
        >>> state = await run_console_deliberation(problem)
    """
    console = Console(debug=debug)

    # Validate session_id if provided
    if session_id and not validate_session_id(session_id):
        error_msg = f"Invalid session ID format: {session_id}. Must be a valid UUID."
        console.print(f"[error]{error_msg}[/error]")
        raise ValueError(error_msg)

    # Sanitize problem statement
    if problem.description:
        problem.description = sanitize_problem_statement(problem.description)
    if problem.title:
        problem.title = sanitize_problem_statement(problem.title)
    if problem.context:
        problem.context = sanitize_problem_statement(problem.context)

    # Validate problem is not empty
    if not problem.description or not problem.description.strip():
        error_msg = "Problem description cannot be empty"
        console.print(f"[error]{error_msg}[/error]")
        raise ValueError(error_msg)

    # Create graph with Redis checkpointer
    graph = create_deliberation_graph()  # Uses RedisSaver by default

    # Resume from checkpoint or create new session
    if session_id:
        # Attempt to resume from checkpoint
        console.print_header("Board of One - Resume Session")
        console.print(f"\n[info]Attempting to resume session: {session_id}[/info]\n")

        config = {"configurable": {"thread_id": session_id}}

        try:
            # Get checkpoint state
            checkpoint_state = await graph.aget_state(config)

            if not checkpoint_state or not checkpoint_state.values:
                error_msg = f"No checkpoint found for session: {session_id}"
                console.print(f"[error]{error_msg}[/error]")
                raise ValueError(error_msg)

            # Display resume info
            state_values = checkpoint_state.values
            round_number = state_values.get("round_number", 0)
            phase = state_values.get("phase", "unknown")
            personas = state_values.get("personas", [])
            metrics = state_values.get("metrics", {})

            # Handle metrics as either dict or DeliberationMetrics object
            if hasattr(metrics, "total_cost"):
                total_cost = metrics.total_cost
            else:
                total_cost = metrics.get("total_cost", 0.0)

            console.print("[cyan]Checkpoint found![/cyan]")
            console.print(f"  Round: {round_number}")
            console.print(f"  Phase: {phase}")
            console.print(f"  Experts: {len(personas)}")
            console.print(f"  Cost so far: ${total_cost:.4f}")
            console.print()

            # Ask user to continue
            response = input("Continue deliberation? (y/n): ").strip().lower()
            if response != "y":
                console.print("\n[yellow]Resume cancelled by user.[/yellow]")
                return state_values

            console.print("\n[info]Resuming deliberation...[/info]\n")
            initial_state = None  # Resume from checkpoint

        except Exception as e:
            error_msg = f"Failed to resume session: {e}"
            console.print(f"[error]{error_msg}[/error]")
            raise ValueError(error_msg) from e
    else:
        # Create new session
        console.print_header("Board of One - LangGraph Deliberation")
        console.print_problem(problem)

        # Create initial state
        session_id = str(uuid.uuid4())
        initial_state = create_initial_state(
            session_id=session_id, problem=problem, max_rounds=max_rounds
        )

    # Import recursion limit from loop prevention
    from bo1.graph.safety.loop_prevention import DELIBERATION_RECURSION_LIMIT

    run_config: dict[str, Any] = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": DELIBERATION_RECURSION_LIMIT,
    }

    # Execute graph with progress display
    console.print(f"\n[info]Session ID: {session_id}[/info]")
    console.print("[info]Starting deliberation...[/info]\n")

    # Execute graph with streaming to display intermediate results
    final_state = None
    try:
        # Use astream_events to intercept node completions and display progress
        # If resuming (initial_state is None), pass None to continue from checkpoint
        async for event in (
            graph.astream_events(initial_state, config=run_config, version="v2")
            if initial_state
            else graph.astream_events(None, config=run_config, version="v2")
        ):
            event_type = event.get("event")
            event_name = event.get("name", "")

            # Display output when nodes complete
            if event_type == "on_chain_end" and "data" in event:
                output = event.get("data", {}).get("output", {})

                # Display based on node type
                if event_name == "decompose" and isinstance(output, dict):
                    _display_sub_problems(console, output)
                elif event_name == "select_personas" and isinstance(output, dict):
                    _display_personas(console, output)
                    # Check if this is a multi-sub-problem scenario
                    problem = output.get("problem")  # type: ignore[assignment]
                    sub_problem_index = output.get("sub_problem_index", 0)
                    if (
                        problem
                        and hasattr(problem, "sub_problems")
                        and len(problem.sub_problems) > 1
                    ):
                        current_sp = output.get("current_sub_problem")
                        if current_sp:
                            console.print(
                                f"\n[bold cyan]═══ Focus Area {sub_problem_index + 1} of {len(problem.sub_problems)} ═══[/bold cyan]"
                            )
                            console.print(f"[dim]{current_sp.goal}[/dim]\n")
                elif event_name == "initial_round" and isinstance(output, dict):
                    contributions = output.get("contributions", [])
                    if contributions:
                        console.print("\n")
                        console.print_header("Initial Round - All Experts Contribute")
                        for contrib in contributions:
                            _display_contribution(console, contrib, round_num=0)
                elif event_name == "facilitator_decide" and isinstance(output, dict):
                    decision = output.get("facilitator_decision")
                    round_num = output.get("round_number", 1)
                    if decision:
                        _display_facilitator_decision(console, decision, round_num)
                elif event_name == "parallel_round" and isinstance(output, dict):
                    contributions = output.get("contributions", [])
                    round_num = output.get("round_number", 1)
                    # Get contributions from this round (round_num-1 since it's incremented)
                    completed_round = round_num - 1
                    round_contributions = [
                        c for c in contributions if c.round_number == completed_round
                    ]
                    if round_contributions:
                        console.print(
                            f"\n[cyan]═══ Round {completed_round} ({len(round_contributions)} experts) ═══[/cyan]"
                        )
                        for contrib in round_contributions:
                            _display_contribution(console, contrib, completed_round)
                elif event_name == "check_convergence" and isinstance(output, dict):
                    _display_convergence_check(console, output)
                elif event_name == "moderator_intervene" and isinstance(output, dict):
                    contributions = output.get("contributions", [])
                    round_num = output.get("round_number", 1)
                    if contributions:
                        console.print(
                            f"\n[magenta]═══ Moderator Intervention (Round {round_num}) ═══[/magenta]"
                        )
                        _display_contribution(console, contributions[-1], round_num)
                elif event_name == "vote" and isinstance(output, dict):
                    _display_votes(console, output)
                elif event_name == "synthesize" and isinstance(output, dict):
                    _display_synthesis(console, output)
                elif event_name == "next_subproblem" and isinstance(output, dict):
                    # Display sub-problem completion message
                    _display_subproblem_completion(console, output)
                elif event_name == "meta_synthesize" and isinstance(output, dict):
                    # Display meta-synthesis header and result
                    _display_meta_synthesis(console, output)

                # Capture the final state from the last event
                if isinstance(output, dict):
                    final_state = output

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise

    # Display results
    if final_state:
        _display_results(console, final_state)

        # Export if requested
        if export:
            await _export_deliberation(console, final_state, include_logs)
    else:
        console.print("\n[yellow]Warning: No final state captured[/yellow]")

    return final_state


def _display_sub_problems(console: Console, state: Any) -> None:
    """Display decomposed sub-problems.

    Args:
        console: Console instance for output
        state: Graph state with sub_problems
    """
    sub_problems = state.get("sub_problems", [])
    if not sub_problems:
        return

    console.print("\n")
    console.print_header("Decision Breakdown")
    console.print(f"\n[cyan]Broken down into {len(sub_problems)} focus areas:[/cyan]\n")

    for i, sp in enumerate(sub_problems, 1):
        console.print(f"[bold cyan]{i}. {sp.goal}[/bold cyan]")
        if sp.rationale:
            console.print(f"   [dim]→ {sp.rationale}[/dim]")
        console.print()


def _display_personas(console: Console, state: Any) -> None:
    """Display selected personas with selection rationale.

    Args:
        console: Console instance for output
        state: Graph state with personas and recommendations
    """
    personas = state.get("personas", [])
    recommendations = state.get("persona_recommendations", [])

    if not personas:
        return

    console.print("\n")
    console.print_header("Expert Panel Selected")
    console.print(f"\n[cyan]{len(personas)} experts will deliberate:[/cyan]\n")

    # Create a map of code -> rationale from recommendations
    rationale_map = (
        {rec["code"]: rec.get("rationale", "") for rec in recommendations}
        if recommendations
        else {}
    )

    for persona in personas:
        # Get rationale
        rationale = rationale_map.get(persona.code, "")

        # Build the left side (name + expertise)
        left_lines = [f"  • [bold]{persona.name}[/bold]"]
        if persona.domain_expertise:
            expertise_str = ", ".join(persona.domain_expertise)
            left_lines.append(f"    [dim]{expertise_str}[/dim]")

        # If we have rationale, display it in a card to the right
        if rationale:
            from rich.columns import Columns
            from rich.panel import Panel

            # Create left column (name + expertise)
            left_text = "\n".join(left_lines)

            # Create right column (rationale in a subtle panel)
            rationale_panel = Panel(
                rationale,
                border_style="dim cyan",
                padding=(0, 1),
                expand=False,
            )

            # Display side by side
            columns = Columns([left_text, rationale_panel], padding=2, expand=False)
            console.print(columns)
        else:
            # No rationale, just display name and expertise normally
            for line in left_lines:
                console.print(line)

        console.print()  # Add spacing between personas

    console.print()


def _display_contribution(console: Console, contribution: Any, round_num: int) -> None:
    """Display a single expert contribution.

    Args:
        console: Console instance for output
        contribution: ContributionMessage object
        round_num: Current round number
    """
    console.print(
        f"\n[bold cyan]═══ {contribution.persona_name} (Round {round_num}) ═══[/bold cyan]"
    )
    console.print(contribution.content)
    console.print()


def _display_facilitator_decision(console: Console, decision: Any, round_num: int) -> None:
    """Display facilitator's decision.

    Args:
        console: Console instance for output
        decision: FacilitatorDecision object
        round_num: Current round number
    """
    console.print(f"\n[yellow]━━━ Facilitator Decision (Round {round_num}) ━━━[/yellow]")
    console.print(f"Action: [bold]{decision['action']}[/bold]")

    if decision.get("reasoning"):
        console.print(f"Reasoning: {decision['reasoning'][:200]}...")

    if decision["action"] == "continue" and decision.get("next_speaker"):
        console.print(f"Next speaker: [cyan]{decision['next_speaker']}[/cyan]")
    elif decision["action"] == "moderator" and decision.get("moderator_type"):
        console.print(f"Moderator type: [magenta]{decision['moderator_type']}[/magenta]")
    elif decision["action"] == "research" and decision.get("research_query"):
        console.print(f"Research query: {decision['research_query'][:100]}...")

    console.print()


def _display_convergence_check(console: Console, state: Any) -> None:
    """Display convergence check results.

    Args:
        console: Console instance for output
        state: Graph state with convergence metrics
    """
    should_stop = state.get("should_stop", False)
    stop_reason = state.get("stop_reason")
    round_number = state.get("round_number", 0)
    max_rounds = state.get("max_rounds", GraphConfig.MAX_ROUNDS_DEFAULT)

    status = "[green]CONTINUING[/green]" if not should_stop else "[red]STOPPING[/red]"
    console.print(f"\n[dim]Convergence Check: {status} (Round {round_number}/{max_rounds})[/dim]")

    if stop_reason:
        console.print(f"[dim]Reason: {stop_reason}[/dim]")
    console.print()


def _display_votes(console: Console, state: Any) -> None:
    """Display voting results.

    Args:
        console: Console instance for output
        state: Graph state with recommendations
    """
    votes = state.get("recommendations", [])
    if not votes:
        return

    console.print("\n")
    console.print_header("Recommendations")
    console.print(f"\n[cyan]{len(votes)} expert recommendations:[/cyan]\n")

    for vote in votes:
        # Extract recommendation data
        persona_name = vote.get("persona_name", "Unknown")
        recommendation = vote.get("recommendation", "No recommendation provided")
        confidence = vote.get("confidence", 0.0)
        reasoning = vote.get("reasoning", "")
        conditions = vote.get("conditions", [])

        # Display recommendation
        console.print(
            f"[bold]{persona_name}[/bold]: {recommendation} (confidence: {confidence:.0%})"
        )
        if reasoning:
            # Truncate long reasoning
            short_reasoning = reasoning[:150] + "..." if len(reasoning) > 150 else reasoning
            console.print(f"  [dim]{short_reasoning}[/dim]")
        if conditions:
            console.print(f"  [yellow]Conditions: {', '.join(conditions)}[/yellow]")
        console.print()


def _display_synthesis(console: Console, state: Any) -> None:
    """Display synthesis report.

    Args:
        console: Console instance for output
        state: Graph state with synthesis
    """
    synthesis = state.get("synthesis")
    if not synthesis:
        return

    console.print("\n")
    console.print_header("Final Synthesis")
    console.print()
    console.print(synthesis)
    console.print()


def _display_subproblem_completion(console: Console, state: Any) -> None:
    """Display sub-problem completion message.

    Args:
        console: Console instance for output
        state: Graph state with sub_problem_results
    """
    sub_problem_results = state.get("sub_problem_results", [])
    if not sub_problem_results:
        return

    # Get the most recently completed sub-problem
    result = sub_problem_results[-1]
    sub_problem_index = len(sub_problem_results) - 1

    console.print(f"\n[green]✓ Focus area {sub_problem_index + 1} complete[/green]")
    console.print(f"[dim]Cost: ${result.cost:.4f} | Duration: {result.duration_seconds:.1f}s[/dim]")
    console.print(f"[dim]Expert panel: {', '.join(result.expert_panel)}[/dim]\n")


def _display_meta_synthesis(console: Console, state: Any) -> None:
    """Display meta-synthesis header and report.

    Args:
        console: Console instance for output
        state: Graph state with meta-synthesis
    """
    sub_problem_results = state.get("sub_problem_results", [])
    synthesis = state.get("synthesis")

    # Display header before synthesis
    if sub_problem_results:
        console.print("\n[bold magenta]═══ Cross-Focus Area Meta-Synthesis ═══[/bold magenta]")
        console.print(
            f"[dim]Integrating insights from {len(sub_problem_results)} deliberations...[/dim]\n"
        )

    # Display the meta-synthesis report with Rich formatting
    if synthesis:
        console.print("\n")
        console.print(
            Panel(
                synthesis,
                title="[magenta]Meta-Synthesis Report[/magenta]",
                border_style="magenta",
            )
        )
        console.print()


def _display_phase_costs(console: Console, state: Any) -> None:
    """Display phase cost breakdown table.

    Args:
        console: Console instance for output
        state: Graph state with phase costs
    """
    from rich.table import Table

    from bo1.graph.analytics import calculate_cost_breakdown

    breakdown = calculate_cost_breakdown(state)
    if not breakdown:
        return

    # Create Rich table
    table = Table(title="Cost Breakdown by Phase", show_header=True, header_style="bold cyan")
    table.add_column("Phase", style="cyan", no_wrap=False)
    table.add_column("Cost (USD)", justify="right", style="green")
    table.add_column("% of Total", justify="right", style="yellow")

    # Add rows for each phase
    for item in breakdown:
        phase_name = item["phase"].replace("_", " ").title()
        cost = f"${item['cost']:.4f}"
        percentage = f"{item['percentage']:.1f}%"
        table.add_row(phase_name, cost, percentage)

    console.print("\n")
    console.print(table)


def _display_results(console: Console, state: Any) -> None:  # state is DeliberationGraphState
    """Display final deliberation results.

    Args:
        console: Console instance for output
        state: Final deliberation state
    """
    # Display phase costs
    console.print("\n")
    console.print_header("Deliberation Complete")

    # Get metrics object (DeliberationMetrics is already an object, not a dict)
    metrics = state["metrics"]

    # Summary panel
    summary_lines = [
        f"**Phase**: {state['phase'].value}",
        f"**Rounds**: {state['round_number']}",
        f"**Total Cost**: ${metrics.total_cost:.4f}",
        f"**Stop Reason**: {state.get('stop_reason', 'None')}",
    ]

    console.print(
        Panel(
            "\n".join(summary_lines),
            title="[cyan]Summary[/cyan]",
            border_style="cyan",
        )
    )

    # Display phase cost breakdown
    _display_phase_costs(console, state)

    console.print(f"\n[info]Total tokens: {metrics.total_tokens:,}[/info]")

    # Display contributions summary
    contributions = state.get("contributions", [])
    console.print(f"\n[info]Total Contributions: {len(contributions)}[/info]")

    # Show each contribution briefly
    if contributions:
        console.print("\n[cyan]Contribution Summary:[/cyan]")
        for i, contrib in enumerate(contributions, 1):
            snippet = (
                contrib.content[:100] + "..." if len(contrib.content) > 100 else contrib.content
            )
            console.print(f"  {i}. [bold]{contrib.persona_name}:[/bold] {snippet}")

    # Display session info
    console.print(f"\n[success]Session ID: {state['session_id']}[/success]")
    console.print(
        "[info]To resume this session later, use: --resume {session_id}[/info]".format(
            session_id=state["session_id"]
        )
    )


async def _export_deliberation(console: Console, state: Any, include_logs: bool = False) -> None:
    """Export deliberation to files.

    Args:
        console: Console instance for output
        state: Final deliberation state (DeliberationGraphState)
        include_logs: Include detailed logs (tokens, costs, thinking sections)
    """
    import os
    from datetime import datetime

    from bo1.state.serialization import to_json, to_markdown

    console.print("\n")
    console.print_header("Exporting Deliberation")

    # Create exports directory if it doesn't exist
    exports_dir = "exports"
    os.makedirs(exports_dir, exist_ok=True)

    # Generate filename with timestamp
    session_id = state.get("session_id", "unknown")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"{session_id}_{timestamp}"

    # Export markdown transcript (directly with v2 state)
    try:
        md_path = os.path.join(exports_dir, f"{base_filename}.md")
        markdown_content = to_markdown(state, include_metadata=include_logs)
        with open(md_path, "w") as f:
            f.write(markdown_content)
        console.print(f"[green]✓[/green] Markdown transcript: {md_path}")
    except Exception as e:
        console.print(f"[red]✗ Markdown export failed: {e}[/red]")

    # Export JSON (full state)
    try:
        json_path = os.path.join(exports_dir, f"{base_filename}.json")
        json_content = to_json(state, indent=2)
        with open(json_path, "w") as f:
            f.write(json_content)
        console.print(f"[green]✓[/green] JSON state: {json_path}")
    except Exception as e:
        console.print(f"[red]✗ JSON export failed: {e}[/red]")

    console.print(f"\n[cyan]Exports saved to ./{exports_dir}/[/cyan]")
    console.print()


async def stream_deliberation_events(
    problem: Problem,
    session_id: str | None = None,
    max_rounds: int = GraphConfig.MAX_ROUNDS_DEFAULT,
) -> Any:  # Returns DeliberationGraphState
    """Stream deliberation events in real-time (for future SSE support).

    Args:
        problem: Problem to deliberate on
        session_id: Optional session ID to resume
        max_rounds: Maximum deliberation rounds

    Returns:
        Final deliberation state
    """
    # Create graph with checkpointing enabled
    graph = create_deliberation_graph()

    # Create initial state or resume
    if session_id:
        config = {"configurable": {"thread_id": session_id}}
        initial_state = None
    else:
        import uuid

        session_id = str(uuid.uuid4())
        initial_state = create_initial_state(
            session_id=session_id, problem=problem, max_rounds=max_rounds
        )
        config = {"configurable": {"thread_id": session_id}}

    # Stream events
    final_state = None
    async for event in graph.astream_events(initial_state or None, config=config, version="v2"):
        # Yield events for SSE streaming (Week 6)
        event_type = event.get("event")
        if event_type == "on_chain_start":
            logger.debug(f"Node started: {event.get('name')}")
        elif event_type == "on_chain_end":
            logger.debug(f"Node completed: {event.get('name')}")
            # Capture final state from last event
            output = event.get("data", {}).get("output", {})
            if isinstance(output, dict):
                final_state = output

    # Retrieve final state from checkpoint if not captured
    if not final_state:
        checkpoint_state = await graph.aget_state(config)
        if checkpoint_state:
            final_state = checkpoint_state.values

    return final_state
