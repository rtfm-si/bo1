"""Summarizer agent for compressing deliberation rounds into concise summaries.

The Summarizer runs asynchronously after each round to create hierarchical context,
preventing quadratic token growth while maintaining information fidelity.
"""

import json
import logging
from typing import Any

from bo1.agents.base import BaseAgent
from bo1.config import get_model_for_role
from bo1.constants import TokenLimits
from bo1.llm.response import LLMResponse
from bo1.prompts.summarizer_prompts import (
    SUMMARIZER_SYSTEM_PROMPT,
    VALIDATION_SYSTEM_PROMPT,
    compose_summarization_request,
    compose_validation_request,
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
                prefill="<thinking>",  # Consistent reasoning pattern
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
        """Validate that summary preserves critical information using AI evaluation.

        Uses Haiku 4.5 to compare the summary against original contributions and
        assess information fidelity across multiple dimensions.

        Args:
            summary: The generated summary
            original_contributions: Original contributions that were summarized

        Returns:
            Dict with quality metrics:
                - preserves_dissent: bool (are disagreements captured?)
                - preserves_evidence: bool (are data points included?)
                - captures_key_points: bool (are main arguments present?)
                - quality_score: float (0.0-1.0)
                - missing_elements: list[str] (critical info that was lost)
                - within_token_budget: bool (is it under target?)
                - token_estimate: int (rough word count)

        Raises:
            Exception: If validation LLM call fails
        """
        logger.info("Validating summary quality with AI evaluation")

        # Compose validation request
        user_message = compose_validation_request(
            summary=summary,
            original_contributions=original_contributions,
        )

        try:
            # Use Haiku for fast, cost-effective validation (~$0.001 per call)
            response = await self._create_and_call_prompt(
                system=VALIDATION_SYSTEM_PROMPT,
                user_message=user_message,
                phase="validation",
                temperature=0.3,  # Low temperature for consistent evaluation
                max_tokens=500,  # Small response needed
                prefill="{",  # Encourage JSON output
            )

            # Parse JSON response
            validation_result = json.loads(response.content)

            # Add token budget check
            token_estimate = len(summary.split())  # Rough estimate
            within_budget = token_estimate <= TokenLimits.SUMMARY_TARGET * 1.2

            # Merge AI validation with token budget check
            result = {
                "preserves_dissent": validation_result.get("preserves_dissent", False),
                "preserves_evidence": validation_result.get("preserves_evidence", False),
                "captures_key_points": validation_result.get("captures_key_points", False),
                "quality_score": validation_result.get("quality_score", 0.0),
                "missing_elements": validation_result.get("missing_elements", []),
                "within_token_budget": within_budget,
                "token_estimate": token_estimate,
            }

            logger.info(
                f"Validation complete: quality_score={result['quality_score']:.2f}, "
                f"dissent={result['preserves_dissent']}, "
                f"evidence={result['preserves_evidence']}, "
                f"key_points={result['captures_key_points']}"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse validation JSON: {e}")
            # Fallback to basic heuristics if AI validation fails
            token_estimate = len(summary.split())
            return {
                "preserves_dissent": False,
                "preserves_evidence": False,
                "captures_key_points": False,
                "quality_score": 0.5,  # Uncertain quality
                "missing_elements": ["Validation failed - could not assess"],
                "within_token_budget": token_estimate <= TokenLimits.SUMMARY_TARGET * 1.2,
                "token_estimate": token_estimate,
            }
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            raise

    async def summarize_with_validation(
        self,
        round_number: int,
        contributions: list[dict[str, str]],
        problem_statement: str | None = None,
        target_tokens: int | None = None,
        quality_threshold: float = 0.6,
        max_retries: int = 1,
    ) -> tuple[LLMResponse, dict[str, Any]]:
        """Summarize a round with automatic quality validation and regeneration.

        This is the recommended high-level method for summarization. It will:
        1. Generate an initial summary
        2. Validate the summary quality
        3. If quality is below threshold, regenerate with specific instructions
        4. Return the summary and validation metrics

        Args:
            round_number: Round number (1-based)
            contributions: List of dicts with 'persona' and 'content' keys
            problem_statement: Optional problem context (helpful for Round 1)
            target_tokens: Target summary length (default: TokenLimits.SUMMARY_TARGET)
            quality_threshold: Minimum acceptable quality score (default: 0.6)
            max_retries: Maximum regeneration attempts (default: 1)

        Returns:
            Tuple of (LLMResponse with summary, validation metrics dict)

        Raises:
            Exception: If summarization or validation fails

        Examples:
            >>> response, quality = await summarizer.summarize_with_validation(
            ...     round_number=1,
            ...     contributions=contributions,
            ...     problem_statement="Should we invest in SEO?"
            ... )
            >>> if quality['quality_score'] >= 0.6:
            ...     print(f"High quality summary: {response.content}")
        """
        # Generate initial summary
        response = await self.summarize_round(
            round_number=round_number,
            contributions=contributions,
            problem_statement=problem_statement,
            target_tokens=target_tokens,
        )

        # Validate quality
        quality = await self.validate_summary_quality(
            summary=response.content,
            original_contributions=contributions,
        )

        # If quality is below threshold, try to regenerate with specific instructions
        retries = 0
        while quality["quality_score"] < quality_threshold and retries < max_retries:
            logger.warning(
                f"Summary quality {quality['quality_score']:.2f} below threshold "
                f"{quality_threshold}. Regenerating with focused instructions. "
                f"(Attempt {retries + 1}/{max_retries})"
            )

            # Build focused instructions based on what's missing
            focus_instructions = []
            if not quality["preserves_dissent"]:
                focus_instructions.append(
                    "CRITICAL: Include all disagreements and opposing viewpoints"
                )
            if not quality["preserves_evidence"]:
                focus_instructions.append(
                    "CRITICAL: Preserve all specific numbers, data points, and timeframes"
                )
            if not quality["captures_key_points"]:
                focus_instructions.append(
                    "CRITICAL: Ensure each persona's main position is represented"
                )
            if quality["missing_elements"]:
                missing_str = ", ".join(quality["missing_elements"][:3])  # Top 3
                focus_instructions.append(f"MUST INCLUDE: {missing_str}")

            # Regenerate with enhanced prompt
            user_message = compose_summarization_request(
                round_number=round_number,
                contributions=contributions,
                problem_statement=problem_statement,
            )

            # Add focused instructions
            enhanced_message = (
                f"{user_message}\n\n"
                f"<quality_requirements>\n"
                f"{chr(10).join(f'- {instr}' for instr in focus_instructions)}\n"
                f"</quality_requirements>"
            )

            target = target_tokens or TokenLimits.SUMMARY_TARGET
            response = await self._create_and_call_prompt(
                system=SUMMARIZER_SYSTEM_PROMPT,
                user_message=enhanced_message,
                phase="summarization_retry",
                prefill="<thinking>",  # Consistent reasoning pattern
                temperature=0.3,
                max_tokens=target + 50,
            )

            # Revalidate
            quality = await self.validate_summary_quality(
                summary=response.content,
                original_contributions=contributions,
            )

            retries += 1

        if quality["quality_score"] >= quality_threshold:
            logger.info(f"Summary accepted with quality score {quality['quality_score']:.2f}")
        else:
            logger.warning(
                f"Summary quality {quality['quality_score']:.2f} still below threshold "
                f"after {retries} retries. Using best available summary."
            )

        return response, quality


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
            print(f"  Captures key points: {quality['captures_key_points']}")
            print(f"  Within token budget: {quality['within_token_budget']}")
            print(f"  Quality score:       {quality['quality_score']:.2f}")
            if quality["missing_elements"]:
                print(f"  Missing elements:    {', '.join(quality['missing_elements'])}")

        except Exception as e:
            print(f"ERROR: {e}")

    # Run test
    asyncio.run(test_summarizer())
