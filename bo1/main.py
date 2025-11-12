"""Main entry point for Board of One application."""

import asyncio
import logging
import sys

from rich.console import Console

from bo1.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)
console = Console()


async def main_async() -> None:
    """Main async entry point."""
    # Configure logging from settings
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting Board of One v0.1.0")

    console.print("[bold cyan]Board of One v0.1.0[/bold cyan]")
    console.print("AI-powered decision-making through multi-agent debate\n")

    # TODO: Implement main application logic
    logger.debug("Main application logic not yet implemented")
    console.print("[yellow]Implementation in progress...[/yellow]")
    console.print("\nPlanned flow:")
    console.print("1. Problem intake and validation")
    console.print("2. Problem decomposition (1-5 sub-problems)")
    console.print("3. Expert persona selection (3-5 personas)")
    console.print("4. Multi-round deliberation (adaptive rounds)")
    console.print("5. Voting and synthesis")
    console.print("6. Final recommendation")


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(main_async())
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
