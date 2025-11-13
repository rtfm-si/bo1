"""Voting and synthesis orchestration for Board of One.

Handles the final voting phase and synthesis of deliberation results.
"""

import logging
from typing import Any

from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.llm.response import LLMResponse
from bo1.llm.response_parser import ResponseParser
from bo1.models.state import DeliberationState
from bo1.models.votes import Vote, VoteAggregation, aggregate_votes
from bo1.prompts.reusable_prompts import VOTING_SYSTEM_PROMPT, VOTING_USER_MESSAGE
from bo1.utils.json_parsing import parse_json_with_fallback
from bo1.utils.logging_helpers import LogHelper

logger = logging.getLogger(__name__)


async def collect_votes(
    state: DeliberationState,
    broker: PromptBroker,
) -> tuple[list[Vote], list[LLMResponse]]:
    """Collect votes from all personas in parallel.

    Args:
        state: Current deliberation state
        broker: PromptBroker for LLM calls

    Returns:
        Tuple of (votes, llm_responses)
    """
    import asyncio

    logger.info(f"Collecting votes from {len(state.selected_personas)} personas (parallel)")

    # Build discussion history once
    discussion_history = _format_discussion_history(state)

    # Create voting tasks for all personas
    async def _collect_single_vote(persona: Any) -> tuple[Vote | None, LLMResponse | None]:
        """Collect vote from a single persona."""
        logger.info(f"Requesting vote from {persona.name} ({persona.code})")

        # CACHE-OPTIMIZED: System prompt shared across all personas (cached!)
        # Persona identity in user message (not cached, but tiny)
        voting_system = VOTING_SYSTEM_PROMPT.format(
            discussion_history=discussion_history,
        )

        # User message includes persona identity (variable per persona)
        voting_user = VOTING_USER_MESSAGE.format(
            persona_name=persona.name,
        )

        # Request vote from persona
        # CACHE OPTIMIZATION: System prompt is IDENTICAL for all personas
        # - First persona: Creates cache (~1,200 tokens)
        # - Remaining personas: Hit cache (90% cost savings)
        # - Cross-persona cache sharing: 80% cache hit rate
        # - Sonnet cached ($0.30/1M) < Haiku ($1.00/1M) + better reasoning quality
        request = PromptRequest(
            system=voting_system,  # CACHED - shared by all personas
            user_message=voting_user,  # NOT cached - unique per persona
            prefill="<thinking>",  # Force XML structure
            model="sonnet",  # Sonnet + caching = 30% of Haiku cost + better quality
            cache_system=True,  # Enable prompt caching (discussion history cached)
            temperature=0.7,  # Slightly lower for voting
            max_tokens=2000,
            phase="voting",
            agent_type=f"persona_{persona.code}",
        )

        try:
            response = await broker.call(request)

            # Parse vote from response (prepend prefill for complete content)
            full_content = "<thinking>" + response.content
            vote = ResponseParser.parse_vote_from_response(full_content, persona)

            LogHelper.log_vote_collected(
                logger, persona.name, vote.decision.value, vote.confidence, vote.conditions
            )

            return vote, response

        except Exception as e:
            logger.error(f"Failed to collect vote from {persona.name}: {e}")
            return None, None

    # Collect votes using sequential-then-parallel pattern for cache optimization
    # First vote creates cache, remaining votes hit cache (90% cost savings)
    personas_list = state.selected_personas

    if not personas_list:
        logger.warning("No personas to collect votes from")
        return [], []

    # Collect first vote to create prompt cache
    logger.info(f"Collecting first vote from {personas_list[0].name} (creates cache)")
    first_result = await _collect_single_vote(personas_list[0])

    # Collect remaining votes in parallel (all hit cache)
    if len(personas_list) > 1:
        logger.info(f"Collecting remaining {len(personas_list) - 1} votes in parallel (cache hits)")
        remaining_results = await asyncio.gather(
            *[_collect_single_vote(persona) for persona in personas_list[1:]]
        )
        results = [first_result] + remaining_results
    else:
        results = [first_result]

    # Separate votes and responses
    votes = [vote for vote, _ in results if vote is not None]
    llm_responses = [resp for _, resp in results if resp is not None]

    logger.info(f"Collected {len(votes)}/{len(state.selected_personas)} votes")

    return votes, llm_responses


def _format_discussion_history(state: DeliberationState) -> str:
    """Format full discussion history for voting context.

    Args:
        state: Current deliberation state

    Returns:
        Formatted discussion history string
    """
    lines = []

    # Add problem statement
    lines.append("PROBLEM STATEMENT:")
    lines.append(state.problem.description)
    lines.append("")

    # Add all contributions using state method
    lines.append("FULL DISCUSSION:")
    lines.append("")
    lines.append(state.format_discussion_history())

    return "\n".join(lines)


async def aggregate_votes_ai(
    votes: list[Vote],
    discussion_context: str,
    broker: PromptBroker,
) -> tuple[VoteAggregation, LLMResponse]:
    """Aggregate votes using AI-driven synthesis (Haiku).

    This is an AI-first approach that understands conditional votes,
    preserves minority perspectives, and captures nuance that pattern
    matching would miss.

    Args:
        votes: List of Vote objects
        discussion_context: Full discussion context for reference
        broker: PromptBroker for Haiku call

    Returns:
        Tuple of (VoteAggregation, LLMResponse from Haiku)
    """
    logger.info(f"Synthesizing {len(votes)} votes using AI (Haiku)")

    # Format votes for analysis
    votes_formatted = _format_votes_for_ai(votes)

    # Compose Haiku prompt for vote synthesis
    # Following PROMPT_ENGINEERING_FRAMEWORK.md best practices:
    # - Use assistant prefill ("{") to force JSON output
    # - Explicit format specification
    # - Example provided
    system_prompt = """You are an expert vote synthesizer analyzing deliberation outcomes.

Your task: Intelligently aggregate votes, understanding conditional logic and preserving critical minority perspectives.

CRITICAL OUTPUT REQUIREMENTS:
- Output ONLY valid JSON
- No markdown, no code blocks, no explanatory text
- The opening brace { is prefilled for you - continue with the fields
- Use EXACTLY the field names specified below
- Use double quotes for all strings
- Follow the example format precisely

Required JSON fields:
  "consensus_decision": "approve" | "reject" | "conditional" | "no_consensus"
  "confidence_level": "high" | "medium" | "low"
  "critical_conditions": ["condition 1", "condition 2", ...]
  "dissenting_views": ["PersonaName: reasoning", ...]
  "rationale": "2-3 sentences explaining the synthesis"

Example output (continue after the opening brace):
  "consensus_decision": "approve",
  "confidence_level": "medium",
  "critical_conditions": ["Validate market demand first", "Keep initial budget under $25K"],
  "dissenting_views": ["Maria Santos: Concerned about cash flow impact"],
  "rationale": "Majority supports the approach with careful budget management. Financial risks require monitoring."
}"""

    user_message = f"""Analyze these votes and synthesize a decision:

<votes>
{votes_formatted}
</votes>

<discussion_context>
{discussion_context[:1000]}...
</discussion_context>

Consider:
1. What is the overall consensus? (approve/reject/conditional/no_consensus)
2. What conditions are CRITICAL (mentioned by multiple personas or high-confidence votes)?
3. Which dissenting views MUST be preserved (substantive concerns from domain experts)?
4. What is the overall confidence level?

Output ONLY the JSON object (starting with the fields after the opening brace)."""

    request = PromptRequest(
        system=system_prompt,
        user_message=user_message,
        prefill="{",  # JSON prefill
        model="haiku",  # Use Haiku for vote synthesis
        temperature=0.3,  # Lower for analysis
        max_tokens=1500,
        phase="vote_aggregation",
        agent_type="vote_synthesizer",
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
            context="vote aggregation",
            logger=logger,
        )

        if synthesis_data is None:
            raise ValueError(f"Could not parse JSON from response. Errors: {parsing_errors}")

        # Build VoteAggregation from AI synthesis + traditional metrics
        traditional_agg = aggregate_votes(votes)

        # Override with AI insights where appropriate
        ai_aggregation = VoteAggregation(
            total_votes=traditional_agg.total_votes,
            yes_votes=traditional_agg.yes_votes,
            no_votes=traditional_agg.no_votes,
            abstain_votes=traditional_agg.abstain_votes,
            conditional_votes=traditional_agg.conditional_votes,
            simple_majority=traditional_agg.simple_majority,
            supermajority=traditional_agg.supermajority,
            consensus_level=traditional_agg.consensus_level,
            confidence_weighted_score=traditional_agg.confidence_weighted_score,
            average_confidence=traditional_agg.average_confidence,
            # AI-enhanced fields
            dissenting_opinions=synthesis_data.get(
                "dissenting_views", traditional_agg.dissenting_opinions
            ),
            conditions_summary=synthesis_data.get(
                "critical_conditions", traditional_agg.conditions_summary
            ),
        )

        logger.info(
            f"AI vote synthesis: {synthesis_data.get('consensus_decision', 'unknown')} "
            f"(confidence: {synthesis_data.get('confidence_level', 'unknown')})"
        )

        return ai_aggregation, response

    except Exception as e:
        LogHelper.log_fallback_used(
            logger,
            operation="AI vote aggregation",
            reason="Failed to parse or call LLM",
            fallback_action="traditional aggregate_votes() (mechanical synthesis)",
            error=e,
        )
        # Fallback to traditional aggregation
        traditional_agg = aggregate_votes(votes)

        # Create a dummy response to indicate fallback was used
        import uuid
        from datetime import datetime

        from bo1.llm.client import TokenUsage
        from bo1.llm.response import LLMResponse

        fallback_response = LLMResponse(
            content="[FALLBACK: Traditional vote aggregation used due to AI synthesis failure]",
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

        return traditional_agg, fallback_response


def _format_votes_for_ai(votes: list[Vote]) -> str:
    """Format votes for AI analysis.

    Args:
        votes: List of Vote objects

    Returns:
        Formatted string for AI consumption
    """
    lines = []
    for vote in votes:
        lines.append(f"--- {vote.persona_name} ({vote.persona_code}) ---")
        lines.append(f"Decision: {vote.decision.value}")
        lines.append(f"Confidence: {vote.confidence:.2f}")
        lines.append(f"Reasoning: {vote.reasoning}")
        if vote.conditions:
            lines.append(f"Conditions: {', '.join(vote.conditions)}")
        lines.append("")

    return "\n".join(lines)
