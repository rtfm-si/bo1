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

from bo1.llm.client import TokenUsage
from bo1.llm.response import DeliberationMetrics, LLMResponse
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.recommendations import Recommendation

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

    def input(self, prompt: str = "") -> str:
        """Get user input (wrapper for rich.console.input).

        Args:
            prompt: Prompt to display to the user

        Returns:
            User input as string
        """
        return str(self.console.input(prompt))

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
                title=f"Focus Area: {sub_problem.id}",
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

    def print_vote(self, vote: Recommendation) -> None:
        """Print a single vote.

        Args:
            vote: Recommendation to display
        """
        color = self._persona_colors.get(vote.persona_code, "blue")
        confidence_pct = int(vote.confidence * 100)
        confidence_bar = "█" * (confidence_pct // 10) + "░" * (10 - confidence_pct // 10)

        content = f"""[bold]Recommendation:[/bold] {vote.recommendation}
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

    def print_votes_summary(self, votes: list[Recommendation]) -> None:
        """Print voting summary.

        Args:
            votes: List of votes
        """
        if not votes:
            return

        table = Table(title="Recommendations Summary", show_header=True, header_style="bold green")
        table.add_column("Persona", style="cyan")
        table.add_column("Recommendation", style="bold")
        table.add_column("Confidence", justify="right")

        for vote in votes:
            confidence_pct = f"{int(vote.confidence * 100)}%"
            # Truncate long recommendations for table display
            rec_display = (
                vote.recommendation[:60] + "..."
                if len(vote.recommendation) > 60
                else vote.recommendation
            )
            table.add_row(vote.persona_name, rec_display, confidence_pct)

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

    def print_llm_cost(
        self,
        phase: str,
        token_usage: TokenUsage,
        cost: float,
        model_name: str = "",
    ) -> None:
        """Print LLM usage statistics for a phase.

        Args:
            phase: Phase name (e.g., "Decomposition", "Persona Selection")
            token_usage: TokenUsage object with detailed token counts
            cost: Total cost in USD
            model_name: Optional model name to display
        """
        # Build cost summary
        parts = []

        # Tokens
        total_tokens = token_usage.total_tokens
        parts.append(f"Total: {total_tokens:,} tokens")

        # Cache breakdown if applicable
        if token_usage.cache_read_tokens > 0:
            cache_pct = int(token_usage.cache_hit_rate * 100)
            parts.append(f"(cached: {token_usage.cache_read_tokens:,}, {cache_pct}%)")

        # Cost
        parts.append(f"Cost: ${cost:.6f}")

        # Model
        if model_name:
            parts.append(f"Model: {model_name}")

        summary = " | ".join(parts)

        self.console.print(f"[dim]  └─ {phase}: {summary}[/dim]")

    def spinner(self, text: str) -> Progress:
        """Create a spinner progress indicator.

        Args:
            text: Text to display with spinner

        Returns:
            Progress context manager with task already added

        Examples:
            >>> console = Console()
            >>> with console.spinner("Processing...") as progress:
            ...     # Do work
            ...     pass
        """
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        )
        # Add task with the provided text when entering context
        progress.add_task(text, total=None)
        return progress

    def clear(self) -> None:
        """Clear the console."""
        self.console.clear()

    def rule(self, title: str = "") -> None:
        """Print a horizontal rule.

        Args:
            title: Optional title for the rule
        """
        self.console.rule(title, style="dim")

    def print_decomposition(self, decomposition: dict[str, Any]) -> None:
        """Print decomposition result.

        Args:
            decomposition: Decomposition dictionary with analysis and sub-problems
        """
        # Print analysis
        analysis = decomposition.get("analysis", "No analysis provided")
        self.console.print(
            Panel.fit(
                analysis,
                title="Problem Analysis",
                border_style="cyan",
            )
        )
        self.console.print()

        # Print atomic status
        is_atomic = decomposition.get("is_atomic", False)
        if is_atomic:
            self.console.print(
                "[info]ℹ This problem is atomic and will be deliberated as a single question[/info]\n"
            )
        else:
            sub_count = len(decomposition.get("sub_problems", []))
            self.console.print(
                f"[success]✓ Successfully broken down into {sub_count} focus areas[/success]\n"
            )

        # Print sub-problems table
        sub_problems = decomposition.get("sub_problems", [])
        if sub_problems:
            table = Table(title="Focus Areas", show_header=True, header_style="bold yellow")
            table.add_column("#", style="cyan", width=4)
            table.add_column("ID", style="dim")
            table.add_column("Goal", style="bold")
            table.add_column("Complexity", justify="center", width=12)
            table.add_column("Dependencies", style="dim")

            for i, sp in enumerate(sub_problems, 1):
                complexity = sp.get("complexity_score", 0)
                complexity_bar = "█" * complexity + "░" * (10 - complexity)
                deps = ", ".join(sp.get("dependencies", [])) or "-"

                table.add_row(
                    str(i),
                    sp.get("id", ""),
                    sp.get("goal", ""),
                    f"{complexity}/10\n{complexity_bar}",
                    deps,
                )

            self.console.print(table)
            self.console.print()

    def review_decomposition(self, decomposition: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        """Interactive review of decomposition with user.

        Allows user to:
        - Approve decomposition
        - Modify sub-problems
        - Add new sub-problems
        - Merge sub-problems

        Args:
            decomposition: Decomposition to review

        Returns:
            Tuple of (approved, modified_decomposition)
        """
        self.console.print("[title]═══ Decomposition Review ═══[/title]\n")
        self.print_decomposition(decomposition)

        # Ask for approval
        self.console.print(
            "[bold]Do you approve this decomposition?[/bold]\n"
            "  [cyan]a[/cyan] - Approve and continue\n"
            "  [cyan]m[/cyan] - Modify sub-problems\n"
            "  [cyan]r[/cyan] - Reject and provide new problem description\n"
        )

        choice = self.console.input("Your choice [a/m/r]: ").strip().lower()

        if choice == "a":
            self.print_success("Decomposition approved!")
            return True, decomposition

        elif choice == "m":
            # Modification flow
            self.console.print("\n[info]Modification options:[/info]")
            self.console.print(
                "  [cyan]1[/cyan] - Edit a sub-problem goal\n"
                "  [cyan]2[/cyan] - Change complexity score\n"
                "  [cyan]3[/cyan] - Add dependencies\n"
                "  [cyan]4[/cyan] - Add new sub-problem\n"
                "  [cyan]5[/cyan] - Remove sub-problem\n"
                "  [cyan]d[/cyan] - Done with modifications\n"
            )

            modified = dict(decomposition)  # Create a copy

            while True:
                mod_choice = self.console.input("\nModification choice [1-5/d]: ").strip()

                if mod_choice == "d":
                    self.print_success("Modifications complete!")
                    return True, modified

                elif mod_choice == "1":
                    # Edit goal
                    sp_num = int(self.console.input("Sub-problem number to edit: ").strip())
                    if 1 <= sp_num <= len(modified["sub_problems"]):
                        new_goal = self.console.input("New goal: ").strip()
                        modified["sub_problems"][sp_num - 1]["goal"] = new_goal
                        self.print_success(f"Updated sub-problem {sp_num} goal")
                    else:
                        self.print_error("Invalid sub-problem number")

                elif mod_choice == "2":
                    # Change complexity
                    sp_num = int(self.console.input("Sub-problem number to edit: ").strip())
                    if 1 <= sp_num <= len(modified["sub_problems"]):
                        new_complexity = int(self.console.input("New complexity (1-10): ").strip())
                        if 1 <= new_complexity <= 10:
                            modified["sub_problems"][sp_num - 1]["complexity_score"] = (
                                new_complexity
                            )
                            self.print_success(f"Updated sub-problem {sp_num} complexity")
                        else:
                            self.print_error("Complexity must be 1-10")
                    else:
                        self.print_error("Invalid sub-problem number")

                elif mod_choice == "4":
                    # Add new sub-problem
                    new_id = f"sp_{len(modified['sub_problems']) + 1:03d}"
                    new_goal = self.console.input("Goal: ").strip()
                    new_context = self.console.input("Context: ").strip()
                    new_complexity = int(self.console.input("Complexity (1-10): ").strip())

                    modified["sub_problems"].append(
                        {
                            "id": new_id,
                            "goal": new_goal,
                            "context": new_context,
                            "complexity_score": new_complexity,
                            "dependencies": [],
                            "rationale": "User-added sub-problem",
                        }
                    )
                    modified["is_atomic"] = False
                    self.print_success(f"Added sub-problem {new_id}")

                elif mod_choice == "5":
                    # Remove sub-problem
                    sp_num = int(self.console.input("Sub-problem number to remove: ").strip())
                    if 1 <= sp_num <= len(modified["sub_problems"]):
                        removed = modified["sub_problems"].pop(sp_num - 1)
                        self.print_success(f"Removed sub-problem {removed['id']}")
                    else:
                        self.print_error("Invalid sub-problem number")

                else:
                    self.print_warning("Invalid choice, try again")

        else:  # choice == "r"
            self.console.print("\n[warning]Decomposition rejected[/warning]")
            return False, decomposition

    def print_llm_response(
        self,
        response: LLMResponse,
        show_content: bool = False,
    ) -> None:
        """Print LLM response metrics in rich format.

        Args:
            response: LLMResponse object with comprehensive metrics
            show_content: Whether to display response content (default: False)
        """
        # Build summary parts
        parts = []

        # Phase/Agent info
        if response.phase and response.agent_type:
            parts.append(f"[cyan]{response.phase}[/cyan] ({response.agent_type})")
        elif response.phase:
            parts.append(f"[cyan]{response.phase}[/cyan]")

        # Model
        parts.append(f"Model: {response.model}")

        # Tokens with cache breakdown
        token_str = f"Tokens: {response.total_tokens:,}"
        if response.cache_hit_rate > 0:
            cache_pct = int(response.cache_hit_rate * 100)
            token_str += f" ({cache_pct}% cached)"
        parts.append(token_str)

        # Cost with savings
        cost_str = f"Cost: ${response.cost_total:.6f}"
        if response.cache_savings > 0:
            cost_str += f" (saved ${response.cache_savings:.6f})"
        parts.append(cost_str)

        # Performance
        duration_s = response.duration_ms / 1000
        perf_str = f"Duration: {duration_s:.1f}s"
        if response.retry_count > 0:
            perf_str += f" ({response.retry_count} retries)"
        parts.append(perf_str)

        # Print summary
        summary = " | ".join(parts)
        self.console.print(f"[dim]  └─ {summary}[/dim]")

        # Optionally show content
        if show_content:
            self.console.print(
                Panel(response.content, title="Response Content", border_style="dim")
            )

    def print_deliberation_metrics(
        self,
        metrics: DeliberationMetrics,
        show_phase_breakdown: bool = True,
    ) -> None:
        """Print comprehensive deliberation metrics.

        Args:
            metrics: DeliberationMetrics with aggregated session data
            show_phase_breakdown: Whether to show per-phase breakdown
        """
        self.console.print("\n[cyan bold]Deliberation Metrics[/cyan bold]\n")

        # Summary table
        summary_table = Table(title="Summary", show_header=True, header_style="bold magenta")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", justify="right")

        summary_table.add_row("Total Cost", f"${metrics.total_cost:.4f}")
        summary_table.add_row("Total Tokens", f"{metrics.total_tokens:,}")
        summary_table.add_row("LLM Calls", f"{metrics.call_count}")
        summary_table.add_row("Total Retries", f"{metrics.total_retries}")
        summary_table.add_row("Total Duration", f"{metrics.total_duration_ms / 1000:.1f}s")
        summary_table.add_row("Cache Savings", f"${metrics.total_cache_savings:.4f}")
        summary_table.add_row("Avg Cache Hit Rate", f"{int(metrics.avg_cache_hit_rate * 100)}%")

        self.console.print(summary_table)
        self.console.print()

        # Token breakdown table
        token_table = Table(title="Token Breakdown", show_header=True, header_style="bold magenta")
        token_table.add_column("Type", style="cyan")
        token_table.add_column("Count", justify="right")
        token_table.add_column("Percentage", justify="right")

        total = metrics.total_tokens
        token_table.add_row(
            "Input",
            f"{metrics.total_input_tokens:,}",
            f"{int(metrics.total_input_tokens / total * 100) if total > 0 else 0}%",
        )
        token_table.add_row(
            "Output",
            f"{metrics.total_output_tokens:,}",
            f"{int(metrics.total_output_tokens / total * 100) if total > 0 else 0}%",
        )
        token_table.add_row(
            "Cache Read",
            f"{metrics.total_cache_read_tokens:,}",
            f"{int(metrics.total_cache_read_tokens / total * 100) if total > 0 else 0}%",
        )
        token_table.add_row("Total", f"{metrics.total_tokens:,}", "100%", style="bold")

        self.console.print(token_table)
        self.console.print()

        # Phase breakdown
        if show_phase_breakdown and metrics.get_all_phases():
            phase_table = Table(
                title="Per-Phase Breakdown", show_header=True, header_style="bold magenta"
            )
            phase_table.add_column("Phase", style="cyan")
            phase_table.add_column("Calls", justify="right")
            phase_table.add_column("Tokens", justify="right")
            phase_table.add_column("Cost", justify="right")
            phase_table.add_column("Duration", justify="right")
            phase_table.add_column("Retries", justify="right")

            for phase in metrics.get_all_phases():
                phase_metrics = metrics.get_phase_metrics(phase)
                phase_table.add_row(
                    phase,
                    str(phase_metrics["calls"]),
                    f"{phase_metrics['tokens']:,}",
                    f"${phase_metrics['cost']:.4f}",
                    f"{phase_metrics['duration_ms'] / 1000:.1f}s",
                    str(phase_metrics["retries"]),
                )

            self.console.print(phase_table)
            self.console.print()
