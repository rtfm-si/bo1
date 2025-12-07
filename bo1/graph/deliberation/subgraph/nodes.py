"""Subgraph node implementations for sub-problem deliberation.

These nodes use get_stream_writer() for real-time event streaming,
enabling per-expert progress events instead of waiting for node completion.

Key improvements over legacy engine.py approach:
- contribution_started fires BEFORE LLM call (instant feedback)
- contribution fires AFTER LLM call (with content)
- All events include sub_problem_index for frontend filtering
"""

import asyncio
import json
import logging
from typing import Any

from langgraph.config import get_stream_writer

from bo1.agents.selector import PersonaSelectorAgent
from bo1.agents.summarizer import SummarizerAgent
from bo1.data import get_persona_by_code
from bo1.graph.deliberation.subgraph.state import SubProblemGraphState
from bo1.graph.safety.loop_prevention import check_convergence_node as _check_convergence
from bo1.graph.utils import track_aggregated_cost, track_phase_cost
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.models.persona import PersonaProfile
from bo1.models.state import ContributionMessage, ContributionType, DeliberationMetrics
from bo1.orchestration.voting import collect_recommendations
from bo1.prompts.reusable_prompts import (
    SYNTHESIS_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)


def _determine_phase(round_number: int, max_rounds: int) -> str:
    """Determine deliberation phase based on round progression.

    Phases:
    - exploration (rounds 1-2): Divergent thinking, surface all perspectives
    - challenge (rounds 3-4): Deep analysis with evidence, challenge weak arguments
    - convergence (rounds 5+): Synthesis, explicit recommendations
    """
    if round_number <= 2:
        return "exploration"
    elif round_number <= max_rounds - 2:
        return "challenge"
    else:
        return "convergence"


async def select_personas_sp_node(state: SubProblemGraphState) -> dict[str, Any]:
    """Select personas for this sub-problem with real-time streaming.

    Emits events:
    - persona_selected (per persona): Instant feedback as each is selected
    - persona_selection_complete: When all personas are selected
    """
    writer = get_stream_writer()
    sub_problem_index = state["sub_problem_index"]
    sub_problem = state["sub_problem"]
    parent_problem = state["parent_problem"]

    logger.info(f"select_personas_sp_node: Selecting personas for sub-problem {sub_problem_index}")

    # Initialize metrics if not present
    metrics = state.get("metrics") or DeliberationMetrics()

    # Select personas using PersonaSelectorAgent
    selector = PersonaSelectorAgent()
    response = await selector.recommend_personas(
        sub_problem=sub_problem,
        problem_context=parent_problem.context,
    )

    # Parse recommendations
    recommendations = json.loads(response.content)
    recommended_personas = recommendations.get("recommended_personas", [])
    persona_codes = [p["code"] for p in recommended_personas]

    # Load persona profiles and emit events
    personas: list[PersonaProfile] = []
    for i, code in enumerate(persona_codes):
        persona_dict = get_persona_by_code(code)
        if persona_dict:
            persona = PersonaProfile.model_validate(persona_dict)
            personas.append(persona)

            # Find rationale from recommendations
            rationale = ""
            for rec in recommended_personas:
                if rec.get("code") == code:
                    rationale = rec.get("rationale", "")
                    break

            # Emit persona_selected event immediately
            writer(
                {
                    "event_type": "persona_selected",
                    "sub_problem_index": sub_problem_index,
                    "persona": {
                        "code": persona.code,
                        "name": persona.name,
                        "archetype": persona.archetype,
                        "display_name": persona.display_name,
                        "domain_expertise": persona.domain_expertise,
                    },
                    "rationale": rationale,
                    "order": i + 1,
                }
            )

    # Emit persona_selection_complete
    writer(
        {
            "event_type": "persona_selection_complete",
            "sub_problem_index": sub_problem_index,
            "personas": [
                {
                    "code": p.code,
                    "name": p.name,
                    "archetype": p.archetype,
                    "display_name": p.display_name,
                    "domain_expertise": p.domain_expertise,
                }
                for p in personas
            ],
            "count": len(personas),
        }
    )

    # Track cost
    track_phase_cost(metrics, "persona_selection", response)

    logger.info(
        f"select_personas_sp_node: Selected {len(personas)} personas for sub-problem {sub_problem_index}"
    )

    return {
        "personas": personas,
        "round_number": 1,
        "metrics": metrics,
    }


async def parallel_round_sp_node(state: SubProblemGraphState) -> dict[str, Any]:
    """Execute a deliberation round with parallel expert contributions.

    Uses get_stream_writer() to emit per-expert events:
    - round_started: When round begins
    - contribution_started: Before each expert's LLM call (instant feedback)
    - contribution: After each expert's LLM call completes (with content)

    This eliminates the 20-40 second silence from asyncio.gather() blocking.
    """
    writer = get_stream_writer()
    sub_problem_index = state["sub_problem_index"]
    round_number = state["round_number"]
    max_rounds = state["max_rounds"]
    personas = state["personas"]
    contributions = list(state.get("contributions", []))
    round_summaries = list(state.get("round_summaries", []))
    metrics = state.get("metrics") or DeliberationMetrics()
    sub_problem = state["sub_problem"]
    expert_memory = state.get("expert_memory", {})

    # Determine phase
    current_phase = _determine_phase(round_number, max_rounds)

    # Select experts for this round based on phase
    if current_phase == "exploration":
        experts_count = min(len(personas), 4)  # 3-4 experts in exploration
    elif current_phase == "challenge":
        experts_count = min(len(personas), 3)  # 2-3 in challenge
    else:
        experts_count = min(len(personas), 3)  # 2-3 in convergence

    selected_experts = personas[:experts_count]

    logger.info(
        f"parallel_round_sp_node: Round {round_number} ({current_phase}) for sub-problem {sub_problem_index} with {len(selected_experts)} experts"
    )

    # Emit round_started event immediately
    writer(
        {
            "event_type": "round_started",
            "sub_problem_index": sub_problem_index,
            "round_number": round_number,
            "phase": current_phase,
            "experts": [e.code for e in selected_experts],
        }
    )

    # P2 FIX: Get focus prompts from state for targeted expert guidance
    focus_prompts = state.get("next_round_focus_prompts", [])
    missing_aspects = state.get("missing_critical_aspects", [])

    # Generate contributions with per-expert streaming
    async def generate_with_streaming(expert: PersonaProfile) -> ContributionMessage | None:
        """Generate contribution with streaming events."""
        # Emit contribution_started IMMEDIATELY (before LLM call)
        writer(
            {
                "event_type": "contribution_started",
                "sub_problem_index": sub_problem_index,
                "round_number": round_number,
                "persona_code": expert.code,
                "persona_name": expert.display_name,
            }
        )

        try:
            # Build context for this expert
            context_parts = [
                f"# Sub-Problem\n{sub_problem.goal}",
                f"\n# Context\n{sub_problem.context}",
            ]

            # Add expert memory if available
            if expert.code in expert_memory:
                context_parts.append(f"\n# Your Previous Positions\n{expert_memory[expert.code]}")

            # Add recent contributions
            recent = contributions[-6:] if contributions else []
            if recent:
                context_parts.append("\n# Recent Discussion")
                for c in recent:
                    context_parts.append(f"\n{c.persona_name}: {c.content[:500]}...")

            # Add round summaries
            if round_summaries:
                context_parts.append("\n# Round Summaries")
                for i, summary in enumerate(round_summaries[-3:], 1):
                    context_parts.append(f"\nRound {i}: {summary}")

            full_context = "\n".join(context_parts)

            # Phase-specific instructions
            phase_instructions = {
                "exploration": "Explore the problem space broadly. Surface new perspectives and considerations.",
                "challenge": "Critically analyze previous contributions. Challenge weak arguments with evidence.",
                "convergence": "Focus on synthesis and actionable recommendations. Build consensus.",
            }

            # P2 FIX: Build targeted guidance from judge feedback
            # This is the critical fix - experts now receive specific direction on missing aspects
            targeted_guidance = ""
            if focus_prompts and round_number > 1:
                targeted_guidance = "\n\n**IMPORTANT - Areas Needing Deeper Exploration:**\n"
                for prompt in focus_prompts[:3]:  # Top 3 focus prompts
                    targeted_guidance += f"• {prompt}\n"
                if missing_aspects:
                    targeted_guidance += f"\nMissing aspects: {', '.join(missing_aspects)}\n"
                targeted_guidance += (
                    "\nPlease address these gaps specifically in your contribution."
                )

            system_prompt = f"""You are {expert.display_name}, a {expert.archetype}.

Your expertise: {", ".join(expert.domain_expertise)}

{phase_instructions.get(current_phase, "")}{targeted_guidance}

Respond with your analysis and recommendations. Be specific and actionable.
Use <thinking> tags for internal reasoning, then provide your contribution."""

            broker = PromptBroker()
            request = PromptRequest(
                system=system_prompt,
                user_message=full_context,
                prefill="<thinking>",
                model="sonnet",
                temperature=0.7,
                max_tokens=1500,
                phase="deliberation",
                agent_type="expert",
            )

            response = await broker.call(request)
            content = "<thinking>" + response.content

            # Create contribution
            contribution = ContributionMessage(
                persona_code=expert.code,
                persona_name=expert.display_name,
                content=content,
                thinking=None,
                contribution_type=ContributionType.INITIAL
                if round_number == 1
                else ContributionType.RESPONSE,
                round_number=round_number,
                token_count=response.token_usage.total_tokens,
                cost=response.cost_total,
            )

            # Emit contribution event with content
            writer(
                {
                    "event_type": "contribution",
                    "sub_problem_index": sub_problem_index,
                    "round_number": round_number,
                    "persona_code": expert.code,
                    "persona_name": expert.display_name,
                    "archetype": expert.archetype,
                    "domain_expertise": expert.domain_expertise,
                    "content": content,
                    "contribution_type": "initial" if round_number == 1 else "followup",
                }
            )

            # Track cost
            track_phase_cost(metrics, "deliberation", response)

            return contribution

        except Exception as e:
            logger.error(f"Failed to generate contribution for {expert.display_name}: {e}")
            return None

    # Execute contributions in parallel - events stream as each completes
    tasks = [generate_with_streaming(expert) for expert in selected_experts]
    results = await asyncio.gather(*tasks)

    # Filter successful contributions
    new_contributions = [c for c in results if c is not None]
    all_contributions = contributions + new_contributions

    # Generate round summary
    summarizer = SummarizerAgent()
    try:
        summary_response = await summarizer.summarize_round(
            round_number=round_number,
            contributions=[
                {"persona": c.persona_name, "content": c.content} for c in new_contributions
            ],
            problem_statement=sub_problem.goal,
            target_tokens=100,
        )
        round_summaries.append(summary_response.content)
        track_phase_cost(metrics, "summarization", summary_response)
    except Exception as e:
        logger.warning(f"Failed to generate round summary: {e}")
        round_summaries.append(f"Round {round_number}: {len(new_contributions)} contributions")

    # Track experts for this round
    experts_per_round = list(state.get("experts_per_round", []))
    experts_per_round.append([e.code for e in selected_experts])

    return {
        "contributions": all_contributions,
        "round_number": round_number + 1,
        "round_summaries": round_summaries,
        "metrics": metrics,
        "current_phase": current_phase,
        "experts_per_round": experts_per_round,
    }


async def check_convergence_sp_node(state: SubProblemGraphState) -> dict[str, Any]:
    """Check if deliberation has converged for this sub-problem.

    Emits:
    - convergence_checked: With convergence status and metrics
    """
    writer = get_stream_writer()
    sub_problem_index = state["sub_problem_index"]

    # Build minimal state for convergence check
    from bo1.graph.state import DeliberationGraphState
    from bo1.models.state import DeliberationPhase

    mini_state = DeliberationGraphState(
        session_id=state["session_id"],
        problem=state["parent_problem"],
        current_sub_problem=state["sub_problem"],
        personas=state["personas"],
        contributions=state["contributions"],
        round_summaries=state["round_summaries"],
        phase=DeliberationPhase.DISCUSSION,
        round_number=state["round_number"],
        max_rounds=state["max_rounds"],
        metrics=state["metrics"],
        should_stop=False,
        stop_reason=None,
    )

    # Run convergence check
    result = await _check_convergence(mini_state)

    should_stop = result.get("should_stop", False)
    stop_reason = result.get("stop_reason")

    # P2 FIX: Extract focus prompts from updated metrics for next round
    updated_metrics = result.get("metrics")
    focus_prompts: list[str] = []
    missing_aspects: list[str] = []
    if updated_metrics:
        focus_prompts = getattr(updated_metrics, "next_round_focus_prompts", []) or []
        missing_aspects = getattr(updated_metrics, "missing_critical_aspects", []) or []
        logger.info(
            f"check_convergence_sp_node: Sub-problem {sub_problem_index} - "
            f"focus_prompts: {len(focus_prompts)}, missing: {missing_aspects}"
        )

    # Emit convergence event
    writer(
        {
            "event_type": "convergence_checked",
            "sub_problem_index": sub_problem_index,
            "round_number": state["round_number"],
            "should_stop": should_stop,
            "stop_reason": stop_reason,
            "missing_aspects": missing_aspects,  # P2 FIX: Include for UI
        }
    )

    logger.info(
        f"check_convergence_sp_node: Sub-problem {sub_problem_index} round {state['round_number']} - should_stop={should_stop}"
    )

    return {
        "should_stop": should_stop,
        "stop_reason": stop_reason,
        # P2 FIX: Pass focus prompts to next round for expert guidance
        "next_round_focus_prompts": focus_prompts,
        "missing_critical_aspects": missing_aspects,
        "metrics": updated_metrics,  # Pass updated metrics back to state
    }


async def vote_sp_node(state: SubProblemGraphState) -> dict[str, Any]:
    """Collect recommendations from all experts.

    Emits:
    - voting_started: When voting begins
    - voting_complete: With aggregated results
    """
    writer = get_stream_writer()
    sub_problem_index = state["sub_problem_index"]
    personas = state["personas"]
    metrics = state.get("metrics") or DeliberationMetrics()

    logger.info(f"vote_sp_node: Collecting recommendations for sub-problem {sub_problem_index}")

    # Emit voting_started
    writer(
        {
            "event_type": "voting_started",
            "sub_problem_index": sub_problem_index,
            "experts": [p.code for p in personas],
            "count": len(personas),
        }
    )

    # Build mini state for voting
    from bo1.graph.state import DeliberationGraphState
    from bo1.models.state import DeliberationPhase

    mini_state = DeliberationGraphState(
        session_id=state["session_id"],
        problem=state["parent_problem"],
        current_sub_problem=state["sub_problem"],
        personas=state["personas"],
        contributions=state["contributions"],
        round_summaries=state["round_summaries"],
        phase=DeliberationPhase.VOTING,
        round_number=state["round_number"],
        max_rounds=state["max_rounds"],
        metrics=metrics,
        should_stop=True,
        stop_reason=state.get("stop_reason"),
    )

    # Collect recommendations
    broker = PromptBroker()
    recommendations, llm_responses = await collect_recommendations(state=mini_state, broker=broker)
    track_aggregated_cost(metrics, "voting", llm_responses)

    # Convert to dicts
    votes = [
        {
            "persona_code": r.persona_code,
            "persona_name": r.persona_name,
            "recommendation": r.recommendation,
            "reasoning": r.reasoning,
            "confidence": r.confidence,
            "conditions": r.conditions,
            "weight": r.weight,
        }
        for r in recommendations
    ]

    # Calculate consensus level
    consensus_level = "moderate"
    if len(votes) >= len(personas) * 0.8:
        consensus_level = "strong"
    elif len(votes) < len(personas) * 0.5:
        consensus_level = "weak"

    # Emit voting_complete
    writer(
        {
            "event_type": "voting_complete",
            "sub_problem_index": sub_problem_index,
            "votes_count": len(votes),
            "consensus_level": consensus_level,
        }
    )

    logger.info(
        f"vote_sp_node: Collected {len(votes)} recommendations for sub-problem {sub_problem_index}"
    )

    return {
        "votes": votes,
        "metrics": metrics,
    }


async def synthesize_sp_node(state: SubProblemGraphState) -> dict[str, Any]:
    """Generate final synthesis for this sub-problem.

    Emits:
    - synthesis_started: When synthesis begins
    - synthesis_complete: With full synthesis content
    """
    writer = get_stream_writer()
    sub_problem_index = state["sub_problem_index"]
    sub_problem = state["sub_problem"]
    contributions = state["contributions"]
    votes = state["votes"]
    personas = state["personas"]
    metrics = state.get("metrics") or DeliberationMetrics()

    logger.info(f"synthesize_sp_node: Generating synthesis for sub-problem {sub_problem_index}")

    # Emit synthesis_started
    writer(
        {
            "event_type": "synthesis_started",
            "sub_problem_index": sub_problem_index,
        }
    )

    # Format contributions and votes
    all_contributions_and_votes = []
    all_contributions_and_votes.append("=== DISCUSSION ===\n")
    for contrib in contributions:
        all_contributions_and_votes.append(
            f"Round {contrib.round_number} - {contrib.persona_name}:\n{contrib.content}\n"
        )

    all_contributions_and_votes.append("\n=== RECOMMENDATIONS ===\n")
    for vote in votes:
        all_contributions_and_votes.append(
            f"{vote['persona_name']}: {vote['recommendation']} "
            f"(confidence: {vote['confidence']:.2f})\n"
            f"Reasoning: {vote['reasoning']}\n"
        )
        conditions = vote.get("conditions")
        if conditions and isinstance(conditions, list):
            all_contributions_and_votes.append(
                f"Conditions: {', '.join(str(c) for c in conditions)}\n"
            )
        all_contributions_and_votes.append("\n")

    full_context = "".join(all_contributions_and_votes)

    synthesis_prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
        problem_statement=sub_problem.goal,
        all_contributions_and_votes=full_context,
    )

    broker = PromptBroker()
    request = PromptRequest(
        system=synthesis_prompt,
        user_message="Generate the synthesis report now.",
        prefill="<thinking>",
        model="sonnet",
        temperature=0.7,
        max_tokens=3000,
        phase="synthesis",
        agent_type="synthesizer",
    )

    response = await broker.call(request)
    synthesis = "<thinking>" + response.content
    track_phase_cost(metrics, "synthesis", response)

    # Emit synthesis_complete
    writer(
        {
            "event_type": "synthesis_complete",
            "sub_problem_index": sub_problem_index,
            "synthesis": synthesis,
            "word_count": len(synthesis.split()),
        }
    )

    # Generate expert summaries for memory
    expert_summaries: dict[str, str] = {}
    summarizer = SummarizerAgent()

    for persona in personas:
        expert_contributions = [c for c in contributions if c.persona_code == persona.code]

        if expert_contributions:
            try:
                contribution_dicts = [
                    {"persona": c.persona_name, "content": c.content} for c in expert_contributions
                ]

                summary_response = await summarizer.summarize_round(
                    round_number=state["round_number"],
                    contributions=contribution_dicts,
                    problem_statement=sub_problem.goal,
                    target_tokens=75,
                )

                expert_summaries[persona.code] = summary_response.content
                track_phase_cost(metrics, "expert_memory", summary_response)

            except Exception as e:
                logger.warning(
                    f"Failed to generate summary for {persona.display_name} in sub-problem {sub_problem_index}: {e}"
                )

    logger.info(
        f"synthesize_sp_node: Synthesis complete for sub-problem {sub_problem_index} (cost: ${metrics.total_cost:.4f})"
    )

    return {
        "synthesis": synthesis,
        "expert_summaries": expert_summaries,
        "metrics": metrics,
    }
