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
from rich.progress import Progress, SpinnerColumn, TextColumn

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
    max_rounds: int = 15,
    debug: bool = False,
) -> Any:  # Returns DeliberationGraphState but typing is complex
    """Run a deliberation session with console UI.

    Args:
        problem: Problem to deliberate on
        session_id: Optional session ID to resume from checkpoint
        max_rounds: Maximum number of deliberation rounds
        debug: Enable debug output

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

    # Create graph with checkpointer if resuming session
    # Otherwise disable checkpointing (for now - Week 5 will enable by default)
    checkpointer_enabled = session_id is not None
    if checkpointer_enabled:
        # Use Redis checkpointer for resume functionality
        graph = create_deliberation_graph(checkpointer=None)  # Auto-creates RedisSaver
    else:
        # Disable checkpointing for new sessions (for now)
        graph = create_deliberation_graph(checkpointer=False)

    # Resume from checkpoint or create new session
    if session_id:
        console.print(f"\n[info]Resuming session: {session_id}[/info]")
        config = {"configurable": {"thread_id": session_id}}

        try:
            # Load checkpoint to display progress
            state_snapshot = await graph.aget_state(config)

            # Check if checkpoint exists and is valid
            if not state_snapshot or not state_snapshot.values:
                error_msg = f"No checkpoint found for session: {session_id}"
                console.print(f"[error]{error_msg}[/error]")
                raise ValueError(error_msg)

            # Validate checkpoint has required fields
            required_fields = ["phase", "round_number", "metrics"]
            missing_fields = [f for f in required_fields if f not in state_snapshot.values]
            if missing_fields:
                error_msg = f"Corrupted checkpoint for session {session_id}. Missing fields: {missing_fields}"
                console.print(f"[error]{error_msg}[/error]")
                raise ValueError(error_msg)

            console.print(
                f"[info]Resuming from phase: {state_snapshot.values.get('phase', 'UNKNOWN')}[/info]"
            )
            console.print(
                f"[info]Round: {state_snapshot.values.get('round_number', 0)}/{max_rounds}[/info]"
            )
            console.print(
                f"[info]Cost so far: ${state_snapshot.values.get('metrics', {}).get('total_cost', 0.0):.4f}[/info]\n"
            )

            # Ask user to continue with input validation
            while True:
                response = console.input("[yellow]Continue deliberation? (y/n):[/yellow] ")
                if validate_user_input(response, ["y", "n"]):
                    break
                console.print("[warning]Invalid input. Please enter 'y' or 'n'.[/warning]")

            if response.lower() != "y":
                console.print("[warning]Deliberation paused.[/warning]")
                return state_snapshot.values

        except ValueError as e:
            # Check for LangGraph "No checkpointer set" error first
            if "No checkpointer set" in str(e):
                error_msg = f"No checkpoint found for session: {session_id}"
                console.print(f"[error]{error_msg}[/error]")
                raise ValueError(error_msg) from e
            # Re-raise explicit errors (no checkpoint found, corrupted)
            if "No checkpoint found" in str(e) or "Corrupted checkpoint" in str(e):
                raise
            # Re-raise other ValueErrors with context
            error_msg = f"Error loading checkpoint for session {session_id}: {e}"
            console.print(f"[error]{error_msg}[/error]")
            raise ValueError(error_msg) from e
        except Exception as e:
            # Handle non-ValueError exceptions
            error_msg = f"Error loading checkpoint for session {session_id}: {e}"
            console.print(f"[error]{error_msg}[/error]")
            raise ValueError(error_msg) from e

        initial_state = None  # Resume from checkpoint
    else:
        console.print_header("Board of One - LangGraph Deliberation")
        console.print_problem(problem)

        # Create initial state
        session_id = str(uuid.uuid4())
        initial_state = create_initial_state(
            session_id=session_id, problem=problem, max_rounds=max_rounds
        )
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


def _display_results(console: Console, state: Any) -> None:  # state is DeliberationGraphState
    """Display final deliberation results.

    Args:
        console: Console instance for output
        state: Final deliberation state
    """
    # Display phase costs
    console.print_header("Deliberation Complete")

    # Get metrics object (DeliberationMetrics is already an object, not a dict)
    metrics = state["metrics"]

    # Summary panel
    summary_lines = [
        f"**Phase**: {state['phase'].value}",
        f"**Rounds**: {state['round_number']}",
        f"**Total Cost**: ${metrics.total_cost:.4f}",
        f"**Stop Reason**: {state.get('stop_reason', 'N/A')}",
    ]

    console.print(
        Panel(
            "\n".join(summary_lines),
            title="[cyan]Summary[/cyan]",
            border_style="cyan",
        )
    )

    # Phase costs breakdown (Week 5 feature - not yet implemented)
    # For now, just show total cost
    console.print(f"\n[info]Total tokens: {metrics.total_tokens:,}[/info]")

    # Display contributions summary
    console.print(f"\n[info]Total Contributions: {len(state['contributions'])}[/info]")

    # Offer to save results
    console.print(f"\n[success]Session saved with ID: {state['session_id']}[/success]")
    console.print("[info]Use --resume <session_id> to continue or inspect this session[/info]")


async def stream_deliberation_events(
    problem: Problem, session_id: str | None = None, max_rounds: int = 15
) -> Any:  # Returns DeliberationGraphState
    """Stream deliberation events in real-time (for future SSE support).

    Args:
        problem: Problem to deliberate on
        session_id: Optional session ID to resume
        max_rounds: Maximum deliberation rounds

    Returns:
        Final deliberation state
    """
    # Create graph (disable checkpointing for streaming)
    graph = create_deliberation_graph(checkpointer=False)

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
