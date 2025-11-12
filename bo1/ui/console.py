"""Rich console UI for Board of One.

Provides formatted output for:
- Problem statements
- Persona contributions
- Voting results
- Progress indicators
- Error messages
"""

import logging
from typing import Any

from rich.console import Console as RichConsole
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.theme import Theme

from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.votes import Vote

logger = logging.getLogger(__name__)

# Custom theme for Board of One
BO1_THEME = Theme(
    {
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red bold",
        "persona": "blue bold",
        "facilitator": "magenta bold",
        "moderator": "yellow bold",
        "title": "cyan bold",
    }
)

# Persona color mapping (consistent colors for each persona)
PERSONA_COLORS = [
    "blue",
    "green",
    "magenta",
    "cyan",
    "yellow",
    "red",
    "bright_blue",
    "bright_green",
    "bright_magenta",
    "bright_cyan",
]


class Console:
    """Rich console wrapper for Board of One UI.

    Provides formatted, color-coded output for deliberations.

    Examples:
        >>> console = Console()
        >>> console.print_header("Board of One")
        >>> console.print_problem(problem)
    """

    def __init__(self, debug: bool = False) -> None:
        """Initialize console.

        Args:
            debug: Enable debug output
        """
        self.console = RichConsole(theme=BO1_THEME)
        self.debug_mode = debug
        self._persona_colors: dict[str, str] = {}

    def print(self, *args: Any, **kwargs: Any) -> None:
        """Print to console (wrapper for rich.console.print)."""
        self.console.print(*args, **kwargs)

    def print_header(self, title: str) -> None:
        """Print main header.

        Args:
            title: Header title
        """
        self.console.print(f"\n[title]═══ {title} ═══[/title]\n")

    def print_problem(self, problem: Problem) -> None:
        """Print problem statement.

        Args:
            problem: Problem to display
        """
        self.console.print(
            Panel.fit(
                f"[bold]{problem.title}[/bold]\n\n{problem.description}",
                title="Problem Statement",
                border_style="cyan",
            )
        )

        if problem.context:
            self.console.print(f"\n[dim]Context: {problem.context}[/dim]\n")

        if problem.constraints:
            table = Table(title="Constraints", show_header=True, header_style="bold cyan")
            table.add_column("Type", style="cyan")
            table.add_column("Description")
            table.add_column("Value", style="yellow")

            for constraint in problem.constraints:
                value_str = str(constraint.value) if constraint.value else "-"
                table.add_row(
                    constraint.type.value.upper(),
                    constraint.description,
                    value_str,
                )

            self.console.print(table)
            self.console.print()

    def print_sub_problem(self, sub_problem: SubProblem) -> None:
        """Print sub-problem details.

        Args:
            sub_problem: Sub-problem to display
        """
        complexity_bar = "█" * sub_problem.complexity_score + "░" * (
            10 - sub_problem.complexity_score
        )

        content = f"""[bold]Goal:[/bold] {sub_problem.goal}

[bold]Complexity:[/bold] {sub_problem.complexity_score}/10 [{complexity_bar}]

[bold]Context:[/bold] {sub_problem.context}"""

        if sub_problem.dependencies:
            content += f"\n\n[bold]Dependencies:[/bold] {', '.join(sub_problem.dependencies)}"

        self.console.print(
            Panel.fit(
                content,
                title=f"Sub-Problem: {sub_problem.id}",
                border_style="yellow",
            )
        )
        self.console.print()

    def print_personas(
        self, personas: list[PersonaProfile], title: str = "Selected Personas"
    ) -> None:
        """Print selected personas.

        Args:
            personas: List of personas
            title: Table title
        """
        table = Table(title=title, show_header=True, header_style="bold magenta")
        table.add_column("Code", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("Domain")
        table.add_column("Archetype", style="dim")

        for i, persona in enumerate(personas):
            # Assign consistent color
            color = PERSONA_COLORS[i % len(PERSONA_COLORS)]
            self._persona_colors[persona.code] = color

            table.add_row(
                persona.code,
                persona.name,
                persona.domain,
                persona.archetype,
            )

        self.console.print(table)
        self.console.print()

    def print_contribution(
        self,
        persona_name: str,
        persona_code: str,
        content: str,
        round_number: int,
        tokens_used: int = 0,
        cost: float = 0.0,
    ) -> None:
        """Print a persona contribution.

        Args:
            persona_name: Name of persona
            persona_code: Persona code
            content: Contribution content
            round_number: Round number
            tokens_used: Tokens used for this contribution
            cost: Cost in USD
        """
        # Get persona color
        color = self._persona_colors.get(persona_code, "blue")

        # Extract thinking and contribution sections
        thinking = None
        contribution = content

        if "<thinking>" in content:
            thinking_start = content.find("<thinking>") + len("<thinking>")
            thinking_end = content.find("</thinking>")
            if thinking_end > thinking_start:
                thinking = content[thinking_start:thinking_end].strip()

        if "<contribution>" in content:
            contrib_start = content.find("<contribution>") + len("<contribution>")
            contrib_end = content.find("</contribution>")
            if contrib_end > contrib_start:
                contribution = content[contrib_start:contrib_end].strip()

        # Format output
        title = f"Round {round_number}: {persona_name} ({persona_code})"

        panel_content = []

        if thinking and self.debug_mode:
            panel_content.append(f"[dim italic]Internal Reasoning:[/dim italic]\n{thinking}\n")

        panel_content.append(contribution)

        if tokens_used > 0:
            panel_content.append(f"\n[dim]Tokens: {tokens_used} | Cost: ${cost:.6f}[/dim]")

        self.console.print(
            Panel(
                "\n".join(panel_content),
                title=title,
                border_style=color,
                padding=(1, 2),
            )
        )
        self.console.print()

    def print_vote(self, vote: Vote) -> None:
        """Print a single vote.

        Args:
            vote: Vote to display
        """
        color = self._persona_colors.get(vote.persona_code, "blue")
        confidence_pct = int(vote.confidence * 100)
        confidence_bar = "█" * (confidence_pct // 10) + "░" * (10 - confidence_pct // 10)

        content = f"""[bold]Decision:[/bold] {vote.decision}
[bold]Confidence:[/bold] {confidence_pct}% [{confidence_bar}]

[bold]Reasoning:[/bold]
{vote.reasoning}"""

        if vote.conditions:
            content += "\n\n[bold]Conditions:[/bold]"
            for condition in vote.conditions:
                content += f"\n  • {condition}"

        self.console.print(
            Panel(
                content,
                title=f"{vote.persona_name} ({vote.persona_code})",
                border_style=color,
                padding=(1, 2),
            )
        )

    def print_votes_summary(self, votes: list[Vote]) -> None:
        """Print voting summary.

        Args:
            votes: List of votes
        """
        if not votes:
            return

        table = Table(title="Voting Summary", show_header=True, header_style="bold green")
        table.add_column("Persona", style="cyan")
        table.add_column("Decision", style="bold")
        table.add_column("Confidence", justify="right")

        for vote in votes:
            confidence_pct = f"{int(vote.confidence * 100)}%"
            table.add_row(vote.persona_name, vote.decision, confidence_pct)

        self.console.print(table)
        self.console.print()

    def print_synthesis(self, synthesis: str) -> None:
        """Print final synthesis.

        Args:
            synthesis: Synthesis text
        """
        self.console.print(
            Panel(
                Markdown(synthesis),
                title="Final Synthesis",
                border_style="green bold",
                padding=(1, 2),
            )
        )
        self.console.print()

    def print_progress(self, message: str) -> None:
        """Print progress message.

        Args:
            message: Progress message
        """
        self.console.print(f"[info]▶[/info] {message}")

    def print_success(self, message: str) -> None:
        """Print success message.

        Args:
            message: Success message
        """
        self.console.print(f"[success]✓[/success] {message}")

    def print_warning(self, message: str) -> None:
        """Print warning message.

        Args:
            message: Warning message
        """
        self.console.print(f"[warning]⚠[/warning] {message}")

    def print_error(self, message: str) -> None:
        """Print error message.

        Args:
            message: Error message
        """
        self.console.print(f"[error]✗ Error:[/error] {message}")

    def print_metrics(self, metrics: dict[str, Any]) -> None:
        """Print session metrics.

        Args:
            metrics: Dictionary of metrics to display
        """
        table = Table(title="Session Metrics", show_header=False)
        table.add_column("Metric", style="cyan bold")
        table.add_column("Value", style="yellow")

        for key, value in metrics.items():
            # Format metric name
            metric_name = key.replace("_", " ").title()
            # Format value
            if isinstance(value, float):
                value_str = f"{value:.6f}" if "cost" in key.lower() else f"{value:.2f}"
            elif isinstance(value, int):
                value_str = f"{value:,}"
            else:
                value_str = str(value)

            table.add_row(metric_name, value_str)

        self.console.print(table)
        self.console.print()

    def spinner(self, text: str) -> Progress:
        """Create a spinner progress indicator.

        Args:
            text: Text to display with spinner

        Returns:
            Progress context manager

        Examples:
            >>> console = Console()
            >>> with console.spinner("Processing..."):
            ...     # Do work
            ...     pass
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        )

    def clear(self) -> None:
        """Clear the console."""
        self.console.clear()

    def rule(self, title: str = "") -> None:
        """Print a horizontal rule.

        Args:
            title: Optional title for the rule
        """
        self.console.rule(title, style="dim")
