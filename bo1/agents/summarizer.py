"""Summarizer agent for compressing deliberation rounds into concise summaries.

The Summarizer runs asynchronously after each round to create hierarchical context,
preventing quadratic token growth while maintaining information fidelity.
"""

import logging
from typing import Any

from bo1.agents.base import BaseAgent
from bo1.config import get_model_for_role
from bo1.constants import TokenLimits
from bo1.llm.response import LLMResponse
from bo1.prompts.summarizer_prompts import (
    SUMMARIZER_SYSTEM_PROMPT,
    compose_summarization_request,
)

logger = logging.getLogger(__name__)


class SummarizerAgent(BaseAgent):
    """Agent that compresses deliberation rounds into summaries for hierarchical context.

    Uses Haiku 4.5 for fast, cost-effective summarization. Runs asynchronously after
    each round completes, with zero latency impact on deliberation.

    Design:
    - Round N summary is created while Round N+1 proceeds
    - Summary ready when Round N+2 needs it (1-round lag)
    - Target: 100-150 tokens per summary (configurable via TokenLimits.SUMMARY_TARGET)
    - Cost: ~$0.001 per summary with Haiku

    Usage:
        summarizer = SummarizerAgent()
        summary = await summarizer.summarize_round(
            round_number=1,
            contributions=round_1_contributions,
            problem_statement="Should we invest in SEO?"
        )
    """

    def get_default_model(self) -> str:
        """Return the default model for summarization.

        Uses Haiku 4.5 for fast, cost-effective compression.
        """
        return get_model_for_role("SUMMARIZER")

    async def summarize_round(
        self,
        round_number: int,
        contributions: list[dict[str, str]],
        problem_statement: str | None = None,
        target_tokens: int | None = None,
    ) -> LLMResponse:
        """Summarize a completed deliberation round.

        Args:
            round_number: Round number (1-based)
            contributions: List of dicts with 'persona' and 'content' keys
            problem_statement: Optional problem context (helpful for Round 1)
            target_tokens: Target summary length (default: TokenLimits.SUMMARY_TARGET)

        Returns:
            LLMResponse containing the summary and metrics

        Raises:
            Exception: If LLM call fails (no fallback - caller should handle)

        Examples:
            >>> contributions = [
            ...     {"persona": "Maria (Finance)", "content": "I'm concerned about..."},
            ...     {"persona": "Zara (Growth)", "content": "We should focus on..."}
            ... ]
            >>> response = await summarizer.summarize_round(
            ...     round_number=1,
            ...     contributions=contributions,
            ...     problem_statement="Should we invest $50K in SEO?"
            ... )
            >>> summary = response.content
            >>> print(f"Summary ({response.usage.output_tokens} tokens): {summary}")
        """
        if not contributions:
            logger.warning("No contributions provided for summarization. Skipping.")
            raise ValueError("Cannot summarize empty contributions list")

        # Use configured target or default
        target = target_tokens or TokenLimits.SUMMARY_TARGET

        logger.info(
            f"Summarizing Round {round_number} ({len(contributions)} contributions, "
            f"target: {target} tokens)"
        )

        # Compose summarization request
        user_message = compose_summarization_request(
            round_number=round_number,
            contributions=contributions,
            problem_statement=problem_statement,
        )

        # Use new helper method instead of manual PromptRequest creation
        try:
            response = await self._create_and_call_prompt(
                system=SUMMARIZER_SYSTEM_PROMPT,
                user_message=user_message,
                phase="summarization",
                temperature=0.3,
                max_tokens=target + 50,
            )

            logger.info(
                f"Round {round_number} summary generated: {response.token_usage.output_tokens} tokens, "
                f"${response.cost_total:.6f}"
            )

            return response

        except Exception as e:
            logger.error(f"Failed to summarize Round {round_number}: {e}")
            raise

    async def validate_summary_quality(
        self,
        summary: str,
        original_contributions: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Validate that summary preserves critical information (optional quality check).

        This is an optional enhancement for Day 26 AI-first quality validation.
        For now, it's a placeholder that returns basic metrics.

        Args:
            summary: The generated summary
            original_contributions: Original contributions that were summarized

        Returns:
            Dict with quality metrics:
                - preserves_dissent: bool (are disagreements captured?)
                - preserves_evidence: bool (are data points included?)
                - within_token_budget: bool (is it under target?)
                - quality_score: float (0.0-1.0)

        Future Enhancement (Day 26):
            Use Haiku to validate summary quality:
            - "Does this summary capture all critical disagreements?"
            - "Are specific numbers/data preserved?"
            - "Is the summary actionable for next round?"
        """
        # Placeholder implementation
        # TODO (Day 26): Replace with AI-driven quality validation using Haiku

        # Basic heuristics for now
        token_estimate = len(summary.split())  # Rough estimate
        within_budget = token_estimate <= TokenLimits.SUMMARY_TARGET * 1.2

        # Check for common quality signals
        has_numbers = any(char.isdigit() for char in summary)
        has_disagreement_keywords = any(
            word in summary.lower()
            for word in ["however", "but", "concern", "disagree", "risk", "tension"]
        )

        return {
            "preserves_dissent": has_disagreement_keywords,
            "preserves_evidence": has_numbers,
            "within_token_budget": within_budget,
            "quality_score": 0.8,  # Placeholder score
            "token_estimate": token_estimate,
        }


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def test_summarizer() -> None:
        """Test the summarizer with example contributions."""
        summarizer = SummarizerAgent()

        # Example contributions from PromptBroker discussion
        contributions = [
            {
                "persona": "Zara Morales (Growth)",
                "content": (
                    "I see significant opportunity in the SEO channel. Our CAC via paid "
                    "ads is $80, while industry benchmarks show SEO can achieve $15-20 once "
                    "ramped. The 6-month lag is real, but this is a long-term play. I'd "
                    "propose a 70/30 split: $35K SEO, $15K paid to maintain pipeline."
                ),
            },
            {
                "persona": "Maria Santos (Finance)",
                "content": (
                    "The numbers concern me. $50K is 40% of our quarterly marketing budget. "
                    "SEO ROI won't materialize for 6+ months, creating cash flow risk. I need "
                    "to see: (1) sensitivity analysis on timeline, (2) contingency if results "
                    "lag, (3) impact on runway. What's our break-even assumption?"
                ),
            },
            {
                "persona": "Sarah Kim (Marketing)",
                "content": (
                    "Both channels are necessary but serve different goals. Paid ads = "
                    "predictable pipeline for Q4 targets. SEO = strategic moat for 2025. "
                    "I agree with Zara's split approach but suggest starting 60/40 to derisk. "
                    "We can shift allocation in Q1 based on early SEO signals."
                ),
            },
        ]

        print("=" * 70)
        print("TESTING SUMMARIZER AGENT")
        print("=" * 70)
        print(f"\nSummarizing {len(contributions)} contributions...")
        print(f"Target: {TokenLimits.SUMMARY_TARGET} tokens\n")

        try:
            response = await summarizer.summarize_round(
                round_number=1,
                contributions=contributions,
                problem_statement="Should we invest $50K in SEO or paid ads?",
            )

            print("SUMMARY:")
            print("-" * 70)
            print(response.content)
            print("-" * 70)

            print("\nMETRICS:")
            print(f"  Tokens (output): {response.token_usage.output_tokens}")
            print(f"  Tokens (input):  {response.token_usage.input_tokens}")
            print(f"  Cost:            ${response.cost_total:.6f}")
            print(f"  Duration:        {response.duration_ms:.0f}ms")
            print(f"  Model:           {response.model}")

            # Validate quality
            quality = await summarizer.validate_summary_quality(
                summary=response.content,
                original_contributions=contributions,
            )

            print("\nQUALITY VALIDATION:")
            print(f"  Preserves dissent:   {quality['preserves_dissent']}")
            print(f"  Preserves evidence:  {quality['preserves_evidence']}")
            print(f"  Within token budget: {quality['within_token_budget']}")
            print(f"  Quality score:       {quality['quality_score']:.2f}")

        except Exception as e:
            print(f"ERROR: {e}")

    # Run test
    asyncio.run(test_summarizer())
