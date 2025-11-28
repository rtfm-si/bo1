"""Business context collection agent.

Collects business information from the user to enhance deliberation quality.
This context helps personas make more informed, relevant recommendations.

Note: This is currently only used in demo mode (bo1/demo.py).
Not integrated into production API workflow.
If you're looking for context handling in production, see:
- backend/api/streaming.py - SSE event streaming
- bo1/graph/execution.py - Main execution flow
"""

import logging
from typing import Any

from bo1.ui.console import Console
from bo1.utils.formatting import XMLContextFormatter

logger = logging.getLogger(__name__)


class BusinessContextCollector:
    """Collects business context from users to improve deliberation quality.

    Features:
    - Optional business information gathering
    - Web scraping fallback (future enhancement)
    - Structured business context storage
    - User-friendly console forms

    Examples:
        >>> collector = BusinessContextCollector()
        >>> context = collector.collect_context()
        >>> if context:
        ...     print(f"Business: {context['business_model']}")
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the context collector.

        Args:
            console: Console instance for user interaction (creates new if None)
        """
        self.console = console or Console()

    def collect_context(self, skip_prompt: bool = False) -> dict[str, Any] | None:
        """Collect business context from the user.

        Args:
            skip_prompt: If True, skip the prompt and don't collect context

        Returns:
            Dictionary of business context, or None if user declined

        Examples:
            >>> collector = BusinessContextCollector()
            >>> context = collector.collect_context()
            >>> if context:
            ...     print(context["business_model"])
        """
        if skip_prompt:
            logger.info("Skipping business context collection (skip_prompt=True)")
            return None

        # Prompt user for consent
        self.console.print("\n[bold cyan]📊 Business Context Collection[/bold cyan]")
        self.console.print(
            "Providing business context helps the deliberation personas make more informed recommendations."
        )
        self.console.print("This step is [bold]optional[/bold] but recommended.\n")

        # Ask if user wants to provide context
        response = self.console.input("Would you like to provide business context? (y/n): ")
        if response.lower() != "y":
            logger.info("User declined business context collection")
            return None

        # Collect business information
        self.console.print("\n[bold]Please provide the following information:[/bold]")
        self.console.print("[dim](Leave blank to skip any field)[/dim]\n")

        context: dict[str, Any] = {}

        # Business model
        business_model = self.console.input(
            "Business model (e.g., B2B SaaS, B2C marketplace, D2C e-commerce): "
        ).strip()
        if business_model:
            context["business_model"] = business_model

        # Target market
        target_market = self.console.input(
            "Target market (e.g., small businesses, enterprise, consumers): "
        ).strip()
        if target_market:
            context["target_market"] = target_market

        # Product/service description
        product_description = self.console.input(
            "Product/service description (brief 1-2 sentence summary): "
        ).strip()
        if product_description:
            context["product_description"] = product_description

        # Current metrics (optional)
        self.console.print("\n[bold]Current metrics (optional):[/bold]")
        revenue = self.console.input("Monthly/Annual revenue (or 'N/A'): ").strip()
        if revenue and revenue.lower() != "n/a":
            context["revenue"] = revenue

        customers = self.console.input("Number of customers/users (or 'N/A'): ").strip()
        if customers and customers.lower() != "n/a":
            context["customers"] = customers

        growth_rate = self.console.input("Growth rate % (or 'N/A'): ").strip()
        if growth_rate and growth_rate.lower() != "n/a":
            context["growth_rate"] = growth_rate

        # Competitors
        competitors = self.console.input("\nKey competitors (comma-separated, or 'N/A'): ").strip()
        if competitors and competitors.lower() != "n/a":
            context["competitors"] = competitors

        # Website (for future web scraping)
        website = self.console.input("\nWebsite URL (for reference, optional): ").strip()
        if website:
            context["website"] = website

        if not context:
            logger.info("No business context provided by user")
            return None

        # Display collected context for confirmation
        self.console.print("\n[bold green]✓ Business context collected:[/bold green]")
        for key, value in context.items():
            self.console.print(f"  • {key.replace('_', ' ').title()}: {value}")

        logger.info(f"Collected business context with {len(context)} fields")
        return context

    def format_context_for_prompt(self, context: dict[str, Any] | None) -> str:
        """Format business context for inclusion in deliberation prompts.

        Args:
            context: Business context dictionary (or None)

        Returns:
            Formatted string for prompt inclusion

        Examples:
            >>> collector = BusinessContextCollector()
            >>> context = {"business_model": "B2B SaaS", "target_market": "SMBs"}
            >>> formatted = collector.format_context_for_prompt(context)
            >>> print(formatted)
        """
        if not context:
            return ""

        # Use XMLContextFormatter utility instead of manual formatting
        return XMLContextFormatter.format_dict_as_xml(context, "business_context")

    def collect_internal_answers(self, internal_gaps: list[dict[str, Any]]) -> dict[str, str]:
        """Collect answers to internal information gap questions.

        Args:
            internal_gaps: List of internal gaps from identify_information_gaps()
                Format: [{"question": "...", "priority": "CRITICAL|NICE_TO_HAVE", "reason": "..."}]

        Returns:
            Dictionary mapping questions to answers (only for answered questions)

        Examples:
            >>> collector = BusinessContextCollector()
            >>> gaps = [
            ...     {"question": "What is your current churn rate?", "priority": "CRITICAL", "reason": "..."},
            ...     {"question": "How many employees do you have?", "priority": "NICE_TO_HAVE", "reason": "..."}
            ... ]
            >>> answers = collector.collect_internal_answers(gaps)
        """
        if not internal_gaps:
            logger.info("No internal gaps to collect")
            return {}

        # Separate critical and nice-to-have gaps
        critical_gaps = [g for g in internal_gaps if g.get("priority") == "CRITICAL"]
        nice_to_have_gaps = [g for g in internal_gaps if g.get("priority") == "NICE_TO_HAVE"]

        self.console.print("\n[bold cyan]📋 Information Needed for Deliberation[/bold cyan]")
        self.console.print(
            "The following information would help the deliberation personas provide better recommendations.\n"
        )

        answers: dict[str, str] = {}

        # Collect critical answers
        if critical_gaps:
            self.console.print("[bold red]Critical Information:[/bold red]")
            self.console.print("[dim]These are essential for high-quality recommendations.[/dim]\n")

            for i, gap in enumerate(critical_gaps, 1):
                question = gap.get("question", "")
                reason = gap.get("reason", "")

                self.console.print(f"[bold]{i}. {question}[/bold]")
                self.console.print(f"   [dim]Why: {reason}[/dim]")

                answer = self.console.input("   Answer (or 'skip'): ").strip()

                if answer and answer.lower() != "skip":
                    answers[question] = answer
                    self.console.print("   [green]✓ Recorded[/green]\n")
                else:
                    self.console.print(
                        "   [yellow]⚠ Skipped - deliberation quality may be reduced[/yellow]\n"
                    )

        # Collect nice-to-have answers
        if nice_to_have_gaps:
            self.console.print("\n[bold cyan]Additional Information (Optional):[/bold cyan]")
            self.console.print("[dim]These would be helpful but are not essential.[/dim]\n")

            # Ask if user wants to provide optional info
            provide_optional = self.console.input(
                "Would you like to provide optional information? (y/n): "
            ).strip()

            if provide_optional.lower() == "y":
                for i, gap in enumerate(nice_to_have_gaps, 1):
                    question = gap.get("question", "")
                    reason = gap.get("reason", "")

                    self.console.print(f"\n[bold]{i}. {question}[/bold]")
                    self.console.print(f"   [dim]Why: {reason}[/dim]")

                    answer = self.console.input("   Answer (or 'skip'): ").strip()

                    if answer and answer.lower() != "skip":
                        answers[question] = answer
                        self.console.print("   [green]✓ Recorded[/green]")

        # Summary
        if answers:
            self.console.print(f"\n[bold green]✓ Collected {len(answers)} answers[/bold green]")
        else:
            self.console.print("\n[yellow]No internal information provided[/yellow]")

        logger.info(
            f"Collected {len(answers)} internal answers out of {len(internal_gaps)} questions"
        )

        return answers

    def format_internal_context(self, answers: dict[str, str]) -> str:
        """Format internal answers for inclusion in deliberation prompts.

        Args:
            answers: Dictionary mapping questions to answers

        Returns:
            Formatted string for prompt inclusion

        Examples:
            >>> collector = BusinessContextCollector()
            >>> answers = {"What is your churn rate?": "5% monthly"}
            >>> formatted = collector.format_internal_context(answers)
        """
        if not answers:
            return ""

        lines = ["<internal_context>"]
        for question, answer in answers.items():
            lines.append("  <item>")
            lines.append(f"    <question>{question}</question>")
            lines.append(f"    <answer>{answer}</answer>")
            lines.append("  </item>")
        lines.append("</internal_context>")

        return "\n".join(lines)
