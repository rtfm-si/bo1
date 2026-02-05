"""Main entry point for Board of One application."""

import argparse
import asyncio
import logging
import sys

from rich.console import Console

from bo1.config import get_settings
from bo1.constants import GraphConfig
from bo1.interfaces.console import run_console_deliberation
from bo1.models.problem import Problem

# Configure logging
logger = logging.getLogger(__name__)
console = Console()


async def main_async(args: argparse.Namespace) -> None:
    """Main async entry point.

    Args:
        args: Parsed command-line arguments
    """
    # Configure logging from settings
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting Board of One v0.2.0 (LangGraph)")

    # Resume existing session
    if args.resume:
        logger.info(f"Resuming session: {args.resume}")
        console.print(f"[cyan]Resuming session: {args.resume}[/cyan]\n")

        # For resume, we don't need a problem (loaded from checkpoint)
        # But we still need to create a dummy problem to satisfy the function signature
        # The actual problem will be loaded from the checkpoint
        dummy_problem = Problem(
            title="Resuming Session",
            description="Resuming from checkpoint",
            context="Session will be loaded from saved checkpoint",
        )

        await run_console_deliberation(
            problem=dummy_problem,
            session_id=args.resume,
            max_rounds=args.max_rounds,
            debug=args.debug,
        )
        return

    # New session - get problem from user
    if args.problem:
        problem_description = args.problem
        problem_title = (
            problem_description[:50] + "..."
            if len(problem_description) > 50
            else problem_description
        )
    else:
        console.print("[bold cyan]Board of One v0.2.0 (LangGraph)[/bold cyan]")
        console.print("AI-powered decision-making through multi-agent debate\n")
        console.print(
            "[yellow]Enter your problem statement (press Enter twice when done):[/yellow]"
        )

        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)

        problem_description = "\n".join(lines)

        if not problem_description.strip():
            console.print("[red]Error: Problem statement cannot be empty[/red]")
            sys.exit(1)

        problem_title = (
            problem_description[:50] + "..."
            if len(problem_description) > 50
            else problem_description
        )

    # Create problem
    problem = Problem(
        title=problem_title,
        description=problem_description,
        context="User-provided problem for deliberation",
    )

    # Run deliberation
    await run_console_deliberation(
        problem=problem,
        session_id=None,
        max_rounds=args.max_rounds,
        debug=args.debug,
        export=args.export,
        include_logs=args.include_logs,
    )


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Board of One - AI-powered decision-making through multi-agent debate"
    )
    parser.add_argument(
        "--problem",
        "-p",
        type=str,
        help="Problem statement (if not provided, will prompt interactively)",
    )
    parser.add_argument(
        "--resume",
        "-r",
        type=str,
        help="Resume existing session by ID",
    )
    parser.add_argument(
        "--max-rounds",
        "-m",
        type=int,
        default=GraphConfig.MAX_ROUNDS_DEFAULT,
        help=f"Maximum deliberation rounds (default: {GraphConfig.MAX_ROUNDS_DEFAULT})",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug output",
    )
    parser.add_argument(
        "--export",
        "-e",
        action="store_true",
        help="Export deliberation transcript to exports/ directory (markdown + JSON)",
    )
    parser.add_argument(
        "--include-logs",
        action="store_true",
        help="Include detailed logs in export (tokens, costs, thinking sections)",
    )

    args = parser.parse_args()

    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        logger.info("Session interrupted by user")
        console.print("\n[yellow]Session interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        logger.exception("Fatal error in main()")
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
