"""Recommendation collection and synthesis orchestration for Board of One.

Handles the final recommendation phase and synthesis of deliberation results.
"""

import logging
from typing import Any

from bo1.graph.state import DeliberationGraphState
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.llm.response import LLMResponse
from bo1.llm.response_parser import ResponseParser
from bo1.models.recommendations import ConsensusLevel, Recommendation, RecommendationAggregation
from bo1.prompts.reusable_prompts import RECOMMENDATION_SYSTEM_PROMPT, RECOMMENDATION_USER_MESSAGE
from bo1.utils.error_logger import ErrorLogger
from bo1.utils.json_parsing import parse_json_with_fallback

logger = logging.getLogger(__name__)


async def collect_recommendations(
    state: DeliberationGraphState,
    broker: PromptBroker,
) -> tuple[list[Recommendation], list[LLMResponse]]:
    """Collect recommendations from all personas in parallel.

    Args:
        state: Current deliberation state (v2 graph state)
        broker: PromptBroker for LLM calls

    Returns:
        Tuple of (recommendations, llm_responses)
    """
    import asyncio

    personas = state.get("personas", [])
    logger.info(f"Collecting recommendations from {len(personas)} personas (parallel)")

    # Build discussion history once
    discussion_history = _format_discussion_history(state)

    # Create recommendation tasks for all personas
    async def _collect_single_recommendation(
        persona: Any,
    ) -> tuple[Recommendation | None, LLMResponse | None]:
        """Collect recommendation from a single persona."""
        logger.info(f"Requesting recommendation from {persona.name} ({persona.code})")

        # CACHE-OPTIMIZED: System prompt shared across all personas (cached!)
        # Persona identity in user message (not cached, but tiny)
        recommendation_system = RECOMMENDATION_SYSTEM_PROMPT.format(
            discussion_history=discussion_history,
        )

        # User message includes persona identity (variable per persona)
        recommendation_user = RECOMMENDATION_USER_MESSAGE.format(
            persona_name=persona.name,
        )

        # Request recommendation from persona
        # CACHE OPTIMIZATION: System prompt is IDENTICAL for all personas
        # - First persona: Creates cache (~1,200 tokens)
        # - Remaining personas: Hit cache (90% cost savings)
        # - Cross-persona cache sharing: 80% cache hit rate
        # - Sonnet cached ($0.30/1M) < Haiku ($1.00/1M) + better reasoning quality
        request = PromptRequest(
            system=recommendation_system,  # CACHED - shared by all personas
            user_message=recommendation_user,  # NOT cached - unique per persona
            prefill="<thinking>",  # Force XML structure
            model="sonnet",  # Sonnet + caching = 30% of Haiku cost + better quality
            cache_system=True,  # Enable prompt caching (discussion history cached)
            temperature=0.7,  # Slightly lower for recommendations
            max_tokens=2000,
            phase="recommendation",
            agent_type=f"persona_{persona.code}",
        )

        try:
            response = await broker.call(request)

            # Parse recommendation from response (prepend prefill for complete content)
            full_content = "<thinking>" + response.content
            recommendation = ResponseParser.parse_recommendation_from_response(
                full_content, persona
            )

            logger.info(
                f"✅ Collected recommendation from {persona.name}: "
                f"{recommendation.recommendation[:80]}... (confidence: {recommendation.confidence:.2f})"
            )

            return recommendation, response

        except Exception as e:
            logger.error(f"Failed to collect recommendation from {persona.name}: {e}")
            return None, None

    # Collect recommendations using sequential-then-parallel pattern for cache optimization
    # First recommendation creates cache, remaining recommendations hit cache (90% cost savings)
    if not personas:
        logger.warning("No personas to collect recommendations from")
        return [], []

    # Collect first recommendation to create prompt cache
    logger.info(f"Collecting first recommendation from {personas[0].name} (creates cache)")
    first_result = await _collect_single_recommendation(personas[0])

    # Collect remaining recommendations in parallel (all hit cache)
    if len(personas) > 1:
        logger.info(
            f"Collecting remaining {len(personas) - 1} recommendations in parallel (cache hits)"
        )
        remaining_results = await asyncio.gather(
            *[_collect_single_recommendation(persona) for persona in personas[1:]]
        )
        results = [first_result] + remaining_results
    else:
        results = [first_result]

    # Separate recommendations and responses
    recommendations = [rec for rec, _ in results if rec is not None]
    llm_responses = [resp for _, resp in results if resp is not None]

    logger.info(f"Collected {len(recommendations)}/{len(personas)} recommendations")

    return recommendations, llm_responses


def _format_discussion_history(state: DeliberationGraphState) -> str:
    """Format full discussion history for voting context.

    Args:
        state: Current deliberation state (v2 graph state)

    Returns:
        Formatted discussion history string
    """
    lines = []

    # Add problem statement
    problem = state.get("problem")
    lines.append("PROBLEM STATEMENT:")
    lines.append(problem.description if problem else "No problem defined")
    lines.append("")

    # Add all contributions
    lines.append("FULL DISCUSSION:")
    lines.append("")
    contributions = state.get("contributions", [])
    for msg in contributions:
        lines.append(f"--- {msg.persona_name} (Round {msg.round_number}) ---")
        lines.append(msg.content)
        lines.append("")

    return "\n".join(lines)


async def aggregate_recommendations_ai(
    recommendations: list[Recommendation],
    discussion_context: str,
    broker: PromptBroker,
) -> tuple[RecommendationAggregation, LLMResponse]:
    """Aggregate recommendations using AI-driven synthesis (Haiku).

    This AI approach understands flexible recommendations, preserves
    minority perspectives, and captures nuance that mechanical aggregation
    would miss.

    Args:
        recommendations: List of Recommendation objects
        discussion_context: Full discussion context for reference
        broker: PromptBroker for Haiku call

    Returns:
        Tuple of (RecommendationAggregation, LLMResponse from Haiku)
    """
    logger.info(f"Synthesizing {len(recommendations)} recommendations using AI (Haiku)")

    # Format recommendations for analysis
    recommendations_formatted = _format_recommendations_for_ai(recommendations)

    # Compose Haiku prompt for recommendation synthesis
    # Following PROMPT_ENGINEERING_FRAMEWORK.md best practices:
    # - Use assistant prefill ("{") to force JSON output
    # - Explicit format specification
    # - Example provided
    system_prompt = """You are an expert recommendation synthesizer analyzing deliberation outcomes.

Your task: Intelligently aggregate expert recommendations, understanding both binary and strategic recommendations, and preserving critical minority perspectives.

CRITICAL OUTPUT REQUIREMENTS:
- Output ONLY valid JSON
- No markdown, no code blocks, no explanatory text
- The opening brace { is prefilled for you - continue with the fields
- Use EXACTLY the field names specified below
- Use double quotes for all strings
- Follow the example format precisely

Required JSON fields:
  "consensus_recommendation": "The synthesized recommendation (specific and actionable)"
  "confidence_level": "high" | "medium" | "low"
  "alternative_approaches": ["Alternative 1", "Alternative 2", ...]
  "critical_conditions": ["condition 1", "condition 2", ...]
  "dissenting_views": ["PersonaName: reasoning", ...]
  "rationale": "2-3 sentences explaining the synthesis"

Example output (continue after the opening brace):
  "consensus_recommendation": "Hybrid compensation structure: 60% salary, 40% dividends",
  "confidence_level": "high",
  "alternative_approaches": ["Pure salary until profitability", "70/30 split with quarterly rebalancing"],
  "critical_conditions": ["Quarterly review and rebalancing", "Legal compliance verification"],
  "dissenting_views": ["Ahmad Ibrahim: Prefers pure salary until company reaches profitability"],
  "rationale": "Majority of experts support a hybrid approach that balances stability with tax efficiency. Quarterly reviews will help adjust as company situation evolves."
}"""

    user_message = f"""Analyze these expert recommendations and synthesize a consensus:

<recommendations>
{recommendations_formatted}
</recommendations>

<discussion_context>
{discussion_context[:1000]}...
</discussion_context>

Consider:
1. What is the consensus recommendation? (synthesize from all expert views)
2. What alternative approaches were proposed? (capture distinct minority recommendations)
3. What conditions are CRITICAL (mentioned by multiple experts or high-confidence recommendations)?
4. Which dissenting views MUST be preserved (substantive alternative perspectives from domain experts)?
5. What is the overall confidence level based on expert agreement and confidence scores?

Output ONLY the JSON object (starting with the fields after the opening brace)."""

    request = PromptRequest(
        system=system_prompt,
        user_message=user_message,
        prefill="{",  # JSON prefill
        model="haiku",  # Use Haiku for recommendation synthesis
        temperature=0.3,  # Lower for analysis
        max_tokens=1500,
        phase="recommendation_aggregation",
        agent_type="recommendation_synthesizer",
    )

    try:
        response = await broker.call(request)

        # Parse JSON response (prefill adds "{", response.content has the rest)
        json_content = "{" + response.content.strip()

        # Clean up: find the last valid closing brace
        last_brace = json_content.rfind("}")
        if last_brace != -1:
            json_content = json_content[: last_brace + 1]

        # Use utility function for JSON parsing with fallback strategies
        synthesis_data, parsing_errors = parse_json_with_fallback(
            content=json_content,
            prefill="",  # Already prepended above
            context="recommendation aggregation",
            logger=logger,
        )

        if synthesis_data is None:
            raise ValueError(f"Could not parse JSON from response. Errors: {parsing_errors}")

        # Build RecommendationAggregation from AI synthesis
        # Calculate basic metrics
        total_recs = len(recommendations)
        average_confidence = (
            sum(r.confidence for r in recommendations) / total_recs if total_recs > 0 else 0.0
        )

        # Determine consensus level from AI confidence
        confidence_level_str = synthesis_data.get("confidence_level", "medium")
        if confidence_level_str == "high":
            consensus_level = ConsensusLevel.STRONG
        elif confidence_level_str == "low":
            consensus_level = ConsensusLevel.WEAK
        else:
            consensus_level = ConsensusLevel.MODERATE

        ai_aggregation = RecommendationAggregation(
            total_recommendations=total_recs,
            consensus_recommendation=synthesis_data.get(
                "consensus_recommendation", "No consensus reached"
            ),
            confidence_level=confidence_level_str,
            alternative_approaches=synthesis_data.get("alternative_approaches", []),
            critical_conditions=synthesis_data.get("critical_conditions", []),
            dissenting_views=synthesis_data.get("dissenting_views", []),
            confidence_weighted_score=average_confidence,
            average_confidence=average_confidence,
            consensus_level=consensus_level,
        )

        logger.info(
            f"AI recommendation synthesis: {synthesis_data.get('consensus_recommendation', 'unknown')[:60]}... "
            f"(confidence: {confidence_level_str})"
        )

        return ai_aggregation, response

    except Exception as e:
        ErrorLogger.log_fallback(
            logger,
            operation="AI recommendation aggregation",
            reason="Failed to parse or call LLM",
            fallback_action="basic aggregate_votes() fallback",
            error=e,
        )
        # Fallback to simple aggregation
        total_recs = len(recommendations)
        average_confidence = (
            sum(r.confidence for r in recommendations) / total_recs if total_recs > 0 else 0.0
        )

        fallback_agg = RecommendationAggregation(
            total_recommendations=total_recs,
            consensus_recommendation=recommendations[0].recommendation
            if recommendations
            else "No consensus",
            confidence_level="medium",
            confidence_weighted_score=average_confidence,
            average_confidence=average_confidence,
            consensus_level=ConsensusLevel.MODERATE,
        )

        # Create a dummy response to indicate fallback was used
        import uuid
        from datetime import datetime

        from bo1.llm.client import TokenUsage
        from bo1.llm.response import LLMResponse

        fallback_response = LLMResponse(
            content="[FALLBACK: Simple aggregation used due to AI synthesis failure]",
            model="fallback",
            token_usage=TokenUsage(
                input_tokens=0,
                output_tokens=0,
                cache_creation_tokens=0,
                cache_read_tokens=0,
            ),
            duration_ms=0,
            retry_count=0,
            timestamp=datetime.now(),
            request_id=str(uuid.uuid4()),
        )

        return fallback_agg, fallback_response


def _format_recommendations_for_ai(recommendations: list[Recommendation]) -> str:
    """Format recommendations for AI analysis.

    Args:
        recommendations: List of Recommendation objects

    Returns:
        Formatted string for AI consumption
    """
    lines = []
    for rec in recommendations:
        lines.append(f"--- {rec.persona_name} ({rec.persona_code}) ---")
        lines.append(f"Recommendation: {rec.recommendation}")
        lines.append(f"Confidence: {rec.confidence:.2f}")
        lines.append(f"Reasoning: {rec.reasoning}")
        if rec.conditions:
            lines.append(f"Conditions: {', '.join(rec.conditions)}")
        lines.append("")

    return "\n".join(lines)
