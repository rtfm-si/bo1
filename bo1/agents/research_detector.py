"""Proactive research detection for expert contributions.

This module analyzes expert contributions in real-time to detect when research
would be beneficial, triggering automatic research without requiring explicit
facilitator requests.

Detection Triggers:
1. Uncertainty signals: "I think", "possibly", "might be", "not sure"
2. Verifiable claims: statistics, market data, regulatory info, dates
3. Information gaps: topics requiring current/external data

Cost: ~$0.001 per contribution analyzed (Haiku)
"""

import json
import logging
from typing import Any

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from bo1.config import get_settings, resolve_model_alias
from bo1.llm.context import get_cost_context
from bo1.llm.cost_tracker import CostTracker
from bo1.models.state import ContributionMessage
from bo1.prompts.research_detector_prompts import (
    RESEARCH_DETECTOR_PREFILL,
    RESEARCH_DETECTOR_SYSTEM_PROMPT,
    RESEARCH_DETECTOR_USER_TEMPLATE,
)

logger = logging.getLogger(__name__)


class ResearchNeeds(BaseModel):
    """Research needs detected in a contribution."""

    needs_research: bool = Field(description="Whether research would benefit this contribution")
    confidence: float = Field(description="Confidence in this assessment (0.0-1.0)", ge=0.0, le=1.0)
    queries: list[str] = Field(
        description="Specific search queries to run", default_factory=list, max_length=3
    )
    reason: str = Field(description="Why research would help", default="")
    signals: list[str] = Field(
        description="Specific uncertainty/claim signals found", default_factory=list
    )


class ResearchDetector:
    """Detector for proactive research opportunities in contributions."""

    def __init__(self) -> None:
        """Initialize the research detector."""
        self.settings = get_settings()
        self.anthropic_client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        logger.info("ResearchDetector initialized")

    async def detect_research_needs(
        self,
        contribution: ContributionMessage,
        problem_context: str,
    ) -> ResearchNeeds:
        """Analyze a contribution for research opportunities.

        Uses Haiku for fast, cheap detection (~$0.001 per contribution).

        Args:
            contribution: Expert contribution to analyze
            problem_context: Problem description for context

        Returns:
            ResearchNeeds with detection results

        Example:
            >>> detector = ResearchDetector()
            >>> needs = await detector.detect_research_needs(contribution, problem)
            >>> if needs.needs_research:
            ...     print(f"Research needed: {needs.queries}")
        """
        try:
            # Build user message from template
            user_message = RESEARCH_DETECTOR_USER_TEMPLATE.format(
                contribution=contribution.content,
                problem_context=problem_context,
            )

            # Call Haiku for fast detection with cost tracking
            ctx = get_cost_context()
            model = resolve_model_alias("haiku")

            with CostTracker.track_call(
                provider="anthropic",
                operation_type="completion",
                model_name=model,
                session_id=ctx.get("session_id"),
                user_id=ctx.get("user_id"),
                node_name="research_detector",
                phase=ctx.get("phase"),
                persona_name=contribution.persona_name,
                round_number=ctx.get("round_number"),
                sub_problem_index=ctx.get("sub_problem_index"),
            ) as cost_record:
                response = await self.anthropic_client.messages.create(
                    model=model,
                    max_tokens=500,
                    temperature=0.0,  # Deterministic for consistency
                    system=RESEARCH_DETECTOR_SYSTEM_PROMPT,
                    messages=[
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": RESEARCH_DETECTOR_PREFILL},
                    ],
                )

                # Track token usage
                cost_record.input_tokens = response.usage.input_tokens
                cost_record.output_tokens = response.usage.output_tokens

            # Extract JSON response (prepend the prefill we used)
            first_block = response.content[0] if response.content else None
            raw_content = first_block.text if first_block and hasattr(first_block, "text") else "}"
            content = RESEARCH_DETECTOR_PREFILL + raw_content  # Prepend the prefill character

            # Parse JSON (use robust extraction as fallback)
            from bo1.llm.response_parser import extract_json_from_response

            try:
                result_data = extract_json_from_response(content)
                result = ResearchNeeds(**result_data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse research detection JSON: {e}\nContent: {content}")
                # Fallback: no research needed
                result = ResearchNeeds(
                    needs_research=False,
                    confidence=0.0,
                    queries=[],
                    reason="Failed to parse detection result",
                    signals=[],
                )

            # Log detection
            if result.needs_research:
                logger.info(
                    f"Research detected for {contribution.persona_name}: "
                    f"{len(result.queries)} queries (confidence: {result.confidence:.2f})"
                )
            else:
                logger.debug(f"No research needed for {contribution.persona_name}")

            return result

        except Exception as e:
            logger.error(f"Research detection failed: {e}")
            # Fallback: no research needed
            return ResearchNeeds(
                needs_research=False,
                confidence=0.0,
                queries=[],
                reason=f"Detection error: {str(e)[:100]}",
                signals=[],
            )

    async def detect_batch_research_needs(
        self,
        contributions: list[ContributionMessage],
        problem_context: str,
        min_confidence: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Detect research needs for a batch of contributions.

        This is the main entry point for parallel_round_node integration.

        Args:
            contributions: List of contributions to analyze
            problem_context: Problem description for context
            min_confidence: Minimum confidence threshold for triggering research (default: 0.7)

        Returns:
            List of research queries with metadata:
            [
                {
                    "question": "search query",
                    "priority": "HIGH|MEDIUM|LOW",
                    "persona": "persona_name",
                    "reason": "why research is needed",
                    "confidence": 0.85
                }
            ]

        Example:
            >>> detector = ResearchDetector()
            >>> queries = await detector.detect_batch_research_needs(
            ...     contributions, problem_context, min_confidence=0.7
            ... )
            >>> # Pass queries to ResearcherAgent.research_questions()
        """
        if not contributions:
            return []

        logger.info(
            f"Detecting research needs for {len(contributions)} contributions "
            f"(min_confidence: {min_confidence})"
        )

        # Analyze all contributions in parallel
        import asyncio

        tasks = [
            self.detect_research_needs(contribution, problem_context)
            for contribution in contributions
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect queries from high-confidence detections
        research_queries = []
        for i, result in enumerate(results):
            # Handle exceptions
            if isinstance(result, Exception):
                logger.warning(f"Detection failed for contribution {i}: {result}")
                continue

            # Type guard: ensure result is ResearchNeeds
            if not isinstance(result, ResearchNeeds):
                logger.warning(f"Unexpected result type at index {i}: {type(result)}")
                continue

            # Check if research is needed and confidence is high enough
            if result.needs_research and result.confidence >= min_confidence:
                contribution = contributions[i]

                # Determine priority based on confidence
                if result.confidence >= 0.85:
                    priority = "HIGH"
                elif result.confidence >= 0.75:
                    priority = "MEDIUM"
                else:
                    priority = "LOW"

                # Add each query with metadata
                for query in result.queries:
                    research_queries.append(
                        {
                            "question": query,
                            "priority": priority,
                            "persona": contribution.persona_name,
                            "reason": result.reason,
                            "confidence": result.confidence,
                            "signals": result.signals,
                        }
                    )

        logger.info(
            f"Detected {len(research_queries)} research queries from {len(contributions)} contributions"
        )

        return research_queries


async def detect_and_trigger_research(
    contributions: list[ContributionMessage],
    problem_context: str,
    min_confidence: float = 0.7,
) -> list[dict[str, Any]]:
    """Convenience function for detecting research needs.

    This is a simpler API for one-off detection without creating a detector instance.

    Args:
        contributions: List of contributions to analyze
        problem_context: Problem description for context
        min_confidence: Minimum confidence threshold (default: 0.7)

    Returns:
        List of research queries ready for ResearcherAgent

    Example:
        >>> queries = await detect_and_trigger_research(contributions, problem_context)
        >>> if queries:
        ...     researcher = ResearcherAgent()
        ...     results = await researcher.research_questions(queries)
    """
    detector = ResearchDetector()
    return await detector.detect_batch_research_needs(
        contributions, problem_context, min_confidence
    )
