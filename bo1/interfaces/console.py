"""Console adapter for LangGraph-based deliberations.

Provides a console-friendly interface for running deliberations with:
- Real-time progress display
- Pause/resume support
- Checkpoint recovery
- Rich UI integration
"""

import logging

from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from bo1.graph.config import create_deliberation_graph
from bo1.graph.state import DeliberationGraphState, create_initial_state
from bo1.models.problem import Problem
from bo1.ui.console import Console

logger = logging.getLogger(__name__)


async def run_console_deliberation(
    problem: Problem,
    session_id: str | None = None,
    max_rounds: int = 15,
    debug: bool = False,
) -> DeliberationGraphState:
    """Run a deliberation session with console UI.

    Args:
        problem: Problem to deliberate on
        session_id: Optional session ID to resume from checkpoint
        max_rounds: Maximum number of deliberation rounds
        debug: Enable debug output

    Returns:
        Final deliberation state

    Examples:
        >>> from bo1.models.problem import Problem
        >>> problem = Problem(
        ...     statement="Should we invest in AI?",
        ...     context={"budget": 100000}
        ... )
        >>> state = await run_console_deliberation(problem)
    """
    console = Console(debug=debug)

    # Create graph
    graph = create_deliberation_graph(checkpointer=True)

    # Resume from checkpoint or create new session
    if session_id:
        console.print(f"\n[info]Resuming session: {session_id}[/info]")
        config = {"configurable": {"thread_id": session_id}}

        # Load checkpoint to display progress
        state_snapshot = await graph.aget_state(config)
        if state_snapshot.values:
            console.print(
                f"[info]Resuming from phase: {state_snapshot.values.get('phase', 'UNKNOWN')}[/info]"
            )
            console.print(
                f"[info]Round: {state_snapshot.values.get('round_number', 0)}/{max_rounds}[/info]"
            )
            console.print(
                f"[info]Cost so far: ${state_snapshot.values.get('metrics', {}).get('total_cost', 0.0):.4f}[/info]\n"
            )

            # Ask user to continue
            response = console.input("[yellow]Continue deliberation? (y/n):[/yellow] ")
            if response.lower() != "y":
                console.print("[warning]Deliberation paused.[/warning]")
                return state_snapshot.values

        initial_state = None  # Resume from checkpoint
    else:
        console.print_header("Board of One - LangGraph Deliberation")
        console.print_problem(problem)

        # Create initial state
        initial_state = create_initial_state(problem, max_rounds=max_rounds)
        import uuid

        session_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": session_id}}

    # Execute graph with progress display
    console.print(f"\n[info]Session ID: {session_id}[/info]")
    console.print("[info]Starting deliberation...[/info]\n")

    # Use Rich progress display
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console.console,
    ) as progress:
        task = progress.add_task("[cyan]Running deliberation...", total=None)

        # Execute graph
        try:
            if initial_state:
                final_state = await graph.ainvoke(initial_state, config=config)
            else:
                # Resume from checkpoint
                final_state = await graph.ainvoke(None, config=config)

            progress.update(task, description="[green]✓ Deliberation complete")

        except Exception as e:
            progress.update(task, description=f"[red]✗ Error: {e}")
            raise

    # Display results
    console.print("\n")
    _display_results(console, final_state)

    return final_state


def _display_results(console: Console, state: DeliberationGraphState) -> None:
    """Display final deliberation results.

    Args:
        console: Console instance for output
        state: Final deliberation state
    """
    # Display phase costs
    console.print_header("Deliberation Complete")

    # Summary panel
    summary_lines = [
        f"**Phase**: {state['phase'].value}",
        f"**Rounds**: {state['round_number']}",
        f"**Total Cost**: ${state['metrics']['total_cost']:.4f}",
        f"**Stop Reason**: {state.get('stop_reason', 'N/A')}",
    ]

    console.print(
        Panel(
            "\n".join(summary_lines),
            title="[cyan]Summary[/cyan]",
            border_style="cyan",
        )
    )

    # Phase costs breakdown
    if state["metrics"]["phase_costs"]:
        console.print("\n[title]Cost Breakdown by Phase[/title]\n")

        from rich.table import Table

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Phase", style="cyan")
        table.add_column("Cost", justify="right")
        table.add_column("% of Total", justify="right")

        total = state["metrics"]["total_cost"]
        for phase, cost in state["metrics"]["phase_costs"].items():
            percentage = (cost / total * 100) if total > 0 else 0
            table.add_row(phase, f"${cost:.4f}", f"{percentage:.1f}%")

        console.print(table)

    # Display contributions summary
    console.print(f"\n[info]Total Contributions: {len(state['contributions'])}[/info]")

    # Offer to save results
    console.print(f"\n[success]Session saved with ID: {state['session_id']}[/success]")
    console.print("[info]Use --resume <session_id> to continue or inspect this session[/info]")


async def stream_deliberation_events(
    problem: Problem, session_id: str | None = None, max_rounds: int = 15
) -> DeliberationGraphState:
    """Stream deliberation events in real-time (for future SSE support).

    Args:
        problem: Problem to deliberate on
        session_id: Optional session ID to resume
        max_rounds: Maximum deliberation rounds

    Returns:
        Final deliberation state
    """
    # Create graph
    graph = create_deliberation_graph(checkpointer=True)

    # Create initial state or resume
    if session_id:
        config = {"configurable": {"thread_id": session_id}}
        initial_state = None
    else:
        initial_state = create_initial_state(problem, max_rounds=max_rounds)
        import uuid

        session_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": session_id}}

    # Stream events
    async for event in graph.astream_events(initial_state or {}, config=config, version="v2"):
        # Yield events for SSE streaming (Week 6)
        event_type = event.get("event")
        if event_type == "on_chain_start":
            logger.debug(f"Node started: {event.get('name')}")
        elif event_type == "on_chain_end":
            logger.debug(f"Node completed: {event.get('name')}")

    # Get final state
    final_state = await graph.aget_state(config)
    return final_state.values
