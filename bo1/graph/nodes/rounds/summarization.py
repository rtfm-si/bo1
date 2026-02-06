"""Round summarization and research detection.

Contains functions for summarizing round contributions
and detecting research needs.
"""

import logging
from typing import Any

from bo1.constants import SimilarityCacheThresholds
from bo1.graph.utils import track_accumulated_cost
from bo1.prompts.sanitizer import sanitize_user_input

logger = logging.getLogger(__name__)


async def _summarize_round(
    contributions: list[Any],
    round_number: int,
    current_phase: str,
    problem_statement: str | None,
    metrics: Any,
) -> str | None:
    """Summarize contributions from a round.

    Creates a summary of the round's contributions for hierarchical context.

    Args:
        contributions: List of ContributionMessage objects
        round_number: Current round number
        current_phase: Current deliberation phase
        problem_statement: Problem description for context
        metrics: Metrics object for cost tracking

    Returns:
        Summary string or fallback summary on error
    """
    from bo1.agents.summarizer import SummarizerAgent

    if round_number <= 0 or not contributions:
        return None

    summarizer = SummarizerAgent()
    round_contributions = [{"persona": c.persona_name, "content": c.content} for c in contributions]

    try:
        summary_response = await summarizer.summarize_round(
            round_number=round_number,
            contributions=round_contributions,
            problem_statement=problem_statement,
        )

        track_accumulated_cost(metrics, "summarization", summary_response)

        logger.info(
            f"Round {round_number} summarized: {summary_response.token_usage.output_tokens} tokens, "
            f"${summary_response.cost_total:.6f}"
        )
        # Sanitize summary before re-injection into subsequent prompts
        return sanitize_user_input(summary_response.content, context="round_summary")

    except Exception as e:
        logger.warning(f"Failed to summarize round {round_number}: {e}")
        expert_names = ", ".join([c.persona_name for c in contributions])
        fallback_summary = (
            f"Round {round_number} ({current_phase} phase): "
            f"{len(contributions)} contributions from {expert_names}. "
            f"(Detailed summary unavailable due to error: {str(e)[:50]})"
        )
        logger.info(f"Added fallback summary for round {round_number}")
        return fallback_summary


async def _detect_research_needs(
    contributions: list[Any],
    problem_context: str,
    metrics: Any,
) -> list[Any]:
    """Detect research needs in contributions.

    Analyzes contributions for research opportunities and returns
    queries for proactive research.

    Args:
        contributions: List of ContributionMessage objects
        problem_context: Problem description for context
        metrics: Metrics object for cost tracking

    Returns:
        List of detected research queries
    """
    from bo1.agents.research_detector import detect_and_trigger_research

    if not contributions:
        return []

    try:
        detected_queries = await detect_and_trigger_research(
            contributions=contributions,
            problem_context=problem_context,
            min_confidence=SimilarityCacheThresholds.PROACTIVE_CONFIDENCE,
        )

        if detected_queries:
            logger.info(
                f"Proactive research detected: {len(detected_queries)} queries from "
                f"{len(contributions)} contributions"
            )
            # Track detection cost (approximate)
            detection_cost = len(contributions) * 0.001  # ~$0.001 per contribution
            metrics.total_cost += detection_cost
            logger.debug(f"Research detection cost: ${detection_cost:.4f}")
        else:
            logger.debug("No proactive research triggers detected in this round")

        return detected_queries

    except Exception as e:
        logger.warning(f"Proactive research detection failed: {e}. Continuing without detection.")
        return []
