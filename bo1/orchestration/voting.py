"""Voting and synthesis orchestration for Board of One.

Handles the final voting phase and synthesis of deliberation results.
"""

import json
import logging
from typing import Any

from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.llm.response import LLMResponse
from bo1.models.state import DeliberationState
from bo1.models.votes import Vote, VoteAggregation, VoteDecision, aggregate_votes
from bo1.prompts.reusable_prompts import VOTING_PROMPT_TEMPLATE

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

        # Compose voting prompt
        voting_prompt = VOTING_PROMPT_TEMPLATE.format(
            persona_name=persona.name,
            discussion_history=discussion_history,
        )

        # Request vote from persona
        # Use Haiku for voting - it's a structured task (vote parsing)
        # Voting doesn't need deep reasoning, just structured response
        request = PromptRequest(
            system=voting_prompt,
            user_message="Please provide your final vote and recommendation.",
            prefill="<thinking>",  # Force XML structure
            model="haiku",  # Cost optimization: $0.25/1M vs $3/1M input
            temperature=0.7,  # Slightly lower for voting
            max_tokens=2000,
            phase="voting",
            agent_type=f"persona_{persona.code}",
        )

        try:
            response = await broker.call(request)

            # Parse vote from response (prepend prefill for complete content)
            full_content = "<thinking>" + response.content
            vote = _parse_vote_from_response(full_content, persona)

            logger.info(
                f"{persona.name} voted {vote.decision.value} (confidence: {vote.confidence:.2f})"
            )

            return vote, response

        except Exception as e:
            logger.error(f"Failed to collect vote from {persona.name}: {e}")
            return None, None

    # Collect all votes in parallel
    results = await asyncio.gather(
        *[_collect_single_vote(persona) for persona in state.selected_personas]
    )

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

    # Add all contributions
    lines.append("FULL DISCUSSION:")
    lines.append("")

    for msg in state.contributions:
        lines.append(f"--- {msg.persona_name} (Round {msg.round_number}) ---")
        lines.append(msg.content)
        lines.append("")

    return "\n".join(lines)


def _parse_vote_from_response(response_content: str, persona: Any) -> Vote:
    """Parse vote from LLM response.

    Args:
        response_content: Raw LLM response
        persona: Persona object

    Returns:
        Parsed Vote object
    """
    # Extract decision
    decision_str = _extract_xml_tag(response_content, "decision")
    if not decision_str:
        logger.error(
            f"⚠️ FALLBACK: Could not extract <decision> tag from {persona.name} vote response. "
            f"Defaulting to ABSTAIN. Response preview: {response_content[:200]}..."
        )
        decision = VoteDecision.ABSTAIN
    else:
        decision_str_lower = decision_str.lower().strip()
        if (
            "yes" in decision_str_lower
            or "approve" in decision_str_lower
            or "support" in decision_str_lower
        ):
            decision = VoteDecision.YES
        elif (
            "no" in decision_str_lower
            or "reject" in decision_str_lower
            or "oppose" in decision_str_lower
        ):
            decision = VoteDecision.NO
        elif "conditional" in decision_str_lower or "if" in decision_str_lower:
            decision = VoteDecision.CONDITIONAL
        else:
            decision = VoteDecision.ABSTAIN

    # Extract reasoning
    reasoning = _extract_xml_tag(response_content, "reasoning")
    if not reasoning:
        logger.warning(
            f"⚠️ FALLBACK: Could not extract <reasoning> tag from {persona.name} vote. "
            f"Using fallback text."
        )
        reasoning = "[Reasoning not provided in structured format]"

    # Extract confidence
    confidence_str = _extract_xml_tag(response_content, "confidence")
    if confidence_str:
        confidence_str_lower = confidence_str.lower().strip()
        if "high" in confidence_str_lower:
            confidence = 0.85
        elif "medium" in confidence_str_lower:
            confidence = 0.6
        elif "low" in confidence_str_lower:
            confidence = 0.3
        else:
            logger.warning(
                f"⚠️ FALLBACK: Could not parse confidence level '{confidence_str}' from {persona.name}. "
                f"Defaulting to 0.6 (medium)."
            )
            confidence = 0.6
    else:
        logger.warning(
            f"⚠️ FALLBACK: Could not extract <confidence> tag from {persona.name} vote. "
            f"Defaulting to 0.6 (medium)."
        )
        confidence = 0.6

    # Extract conditions
    conditions_str = _extract_xml_tag(response_content, "conditions")
    conditions = []
    if conditions_str:
        # Split by common delimiters
        for line in conditions_str.split("\n"):
            line = line.strip()
            if line and not line.startswith("<") and len(line) > 5:
                # Remove bullet points, dashes, numbers
                cleaned = line.lstrip("- •*0123456789.)")
                if cleaned:
                    conditions.append(cleaned.strip())

    return Vote(
        persona_code=persona.code,
        persona_name=persona.name,
        decision=decision,
        reasoning=reasoning,
        confidence=confidence,
        conditions=conditions,
        weight=1.0,  # Default weight
    )


def _extract_xml_tag(text: str, tag: str) -> str | None:
    """Extract content from XML-like tag.

    Args:
        text: Text containing XML tags
        tag: Tag name to extract

    Returns:
        Tag content or None if not found
    """
    import re

    pattern = rf"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


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
    system_prompt = """You are an expert vote synthesizer analyzing deliberation outcomes.

Your task: Intelligently aggregate votes, understanding conditional logic and preserving critical minority perspectives.

Output ONLY valid JSON in this exact format:
{
  "consensus_decision": "approve" | "reject" | "conditional" | "no_consensus",
  "confidence_level": "high" | "medium" | "low",
  "critical_conditions": ["condition 1", "condition 2", ...],
  "dissenting_views": ["persona: reasoning", ...],
  "rationale": "2-3 sentences explaining the synthesis"
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

Output JSON only."""

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

        # Parse JSON response (prepend prefill)
        json_content = "{" + response.content

        # Clean up any potential issues (sometimes LLMs add text after JSON)
        # Find the last closing brace
        last_brace = json_content.rfind("}")
        if last_brace != -1:
            json_content = json_content[: last_brace + 1]

        synthesis_data = json.loads(json_content)

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
        logger.error(
            f"⚠️ FALLBACK: AI vote aggregation FAILED. Falling back to traditional aggregate_votes(). "
            f"Error: {e}. This means vote synthesis will be mechanical (no conditional logic understanding)."
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
