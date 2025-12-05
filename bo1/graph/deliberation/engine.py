"""Deliberation engine for single sub-problem execution.

This module contains the core deliberation orchestration logic for a single
sub-problem, extracted from nodes.py to improve modularity and testability.
"""

import json
import logging
import time
from typing import TYPE_CHECKING, Any

from bo1.agents.selector import PersonaSelectorAgent
from bo1.agents.summarizer import SummarizerAgent
from bo1.data import get_persona_by_code
from bo1.graph.safety.loop_prevention import check_convergence_node, get_adaptive_max_rounds
from bo1.graph.state import DeliberationGraphState
from bo1.graph.utils import track_aggregated_cost, track_phase_cost
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import DeliberationMetrics, DeliberationPhase, SubProblemResult
from bo1.orchestration.voting import collect_recommendations
from bo1.prompts.reusable_prompts import SYNTHESIS_PROMPT_TEMPLATE

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


async def _select_personas_for_subproblem(
    sub_problem: SubProblem,
    problem: Problem,
    metrics: DeliberationMetrics,
    event_bridge: Any | None,
) -> tuple[list[PersonaProfile], list[dict[str, Any]]]:
    """Select personas for a sub-problem.

    Returns:
        Tuple of (personas list, recommended_personas dicts for rationale lookup)
    """
    selector = PersonaSelectorAgent()
    response = await selector.recommend_personas(
        sub_problem=sub_problem,
        problem_context=problem.context,
    )

    recommendations = json.loads(response.content)
    recommended_personas = recommendations.get("recommended_personas", [])
    persona_codes = [p["code"] for p in recommended_personas]

    personas = []
    for code in persona_codes:
        persona_dict = get_persona_by_code(code)
        if persona_dict:
            personas.append(PersonaProfile.model_validate(persona_dict))

    track_phase_cost(metrics, "persona_selection", response)

    # Emit events
    if event_bridge:
        for i, persona in enumerate(personas):
            rationale = next(
                (
                    r.get("rationale", "")
                    for r in recommended_personas
                    if r.get("code") == persona.code
                ),
                "",
            )
            event_bridge.emit(
                "persona_selected",
                {
                    "persona": {
                        "code": persona.code,
                        "name": persona.name,
                        "archetype": persona.archetype,
                        "display_name": persona.display_name,
                        "domain_expertise": persona.domain_expertise,
                    },
                    "rationale": rationale,
                    "order": i + 1,
                },
            )

        event_bridge.emit(
            "persona_selection_complete",
            {
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
            },
        )

    logger.info(f"Selected {len(personas)} personas: {persona_codes}")
    return personas, recommended_personas


def _build_expert_memory_from_results(previous_results: list[SubProblemResult]) -> dict[str, str]:
    """Build expert memory from previous sub-problem results."""
    if not previous_results:
        return {}

    memory_parts: dict[str, list[str]] = {}
    for result in previous_results:
        for expert_code, summary in result.expert_summaries.items():
            if expert_code not in memory_parts:
                memory_parts[expert_code] = []
            memory_parts[expert_code].append(
                f"Sub-problem: {result.sub_problem_goal}\nYour position: {summary}"
            )

    return {code: "\n\n".join(parts) for code, parts in memory_parts.items() if parts}


async def _generate_synthesis(
    sub_problem: SubProblem,
    contributions: list[Any],
    votes: list[dict[str, Any]],
    metrics: DeliberationMetrics,
    event_bridge: Any | None,
) -> str:
    """Generate synthesis for a sub-problem."""
    if event_bridge:
        event_bridge.emit("synthesis_started", {})

    # Format context
    context_parts = ["=== DISCUSSION ===\n"]
    for contrib in contributions:
        context_parts.append(
            f"Round {contrib.round_number} - {contrib.persona_name}:\n{contrib.content}\n"
        )

    context_parts.append("\n=== RECOMMENDATIONS ===\n")
    for vote in votes:
        context_parts.append(
            f"{vote['persona_name']}: {vote['recommendation']} (confidence: {vote['confidence']:.2f})\nReasoning: {vote['reasoning']}\n"
        )
        if vote.get("conditions"):
            context_parts.append(f"Conditions: {', '.join(str(c) for c in vote['conditions'])}\n")
        context_parts.append("\n")

    synthesis_prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
        problem_statement=sub_problem.goal,
        all_contributions_and_votes="".join(context_parts),
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

    if event_bridge:
        event_bridge.emit(
            "synthesis_complete", {"synthesis": synthesis, "word_count": len(synthesis.split())}
        )

    logger.info(f"Synthesis generated (cost: ${response.cost_total:.4f})")
    return synthesis


async def _generate_expert_summaries(
    personas: list[PersonaProfile],
    contributions: list[Any],
    sub_problem: SubProblem,
    round_number: int,
    metrics: DeliberationMetrics,
) -> dict[str, str]:
    """Generate expert summaries for memory."""
    expert_summaries: dict[str, str] = {}
    summarizer = SummarizerAgent()

    for persona in personas:
        expert_contributions = [c for c in contributions if c.persona_code == persona.code]
        if not expert_contributions:
            continue

        try:
            contribution_dicts = [
                {"persona": c.persona_name, "content": c.content} for c in expert_contributions
            ]
            summary_response = await summarizer.summarize_round(
                round_number=round_number,
                contributions=contribution_dicts,
                problem_statement=sub_problem.goal,
                target_tokens=75,
            )
            expert_summaries[persona.code] = summary_response.content
            track_phase_cost(metrics, "expert_memory", summary_response)
        except Exception as e:
            logger.warning(f"Failed to generate summary for {persona.display_name}: {e}")

    return expert_summaries


async def deliberate_subproblem(
    sub_problem: SubProblem,
    problem: Problem,
    all_personas: list[PersonaProfile],
    previous_results: list[SubProblemResult],
    sub_problem_index: int,
    user_id: str | None = None,
    event_bridge: Any | None = None,
) -> SubProblemResult:
    """Run complete deliberation for a single sub-problem.

    Args:
        sub_problem: The sub-problem to deliberate
        problem: The parent problem (for context)
        all_personas: Available personas (persona selection will choose subset)
        previous_results: Results from previously completed sub-problems
        sub_problem_index: Index of this sub-problem (0-based)
        user_id: Optional user ID for context persistence
        event_bridge: Optional EventBridge for real-time events

    Returns:
        SubProblemResult with synthesis, votes, costs, and expert summaries
    """
    from bo1.graph import nodes as graph_nodes

    logger.info(f"deliberate_subproblem: Starting '{sub_problem.id}': {sub_problem.goal[:80]}")

    metrics = DeliberationMetrics()
    start_time = time.time()

    # Step 1: Select personas
    personas, _ = await _select_personas_for_subproblem(sub_problem, problem, metrics, event_bridge)

    # Step 2: Build expert memory from previous results
    expert_memory = _build_expert_memory_from_results(previous_results)
    if expert_memory:
        logger.info(
            f"Built expert memory for {len(expert_memory)} experts from {len(previous_results)} previous sub-problems"
        )

    # Step 3: Run deliberation rounds
    contributions = []
    round_summaries = []
    # Issue #11: Use adaptive round limits based on sub-problem complexity
    max_rounds = get_adaptive_max_rounds(sub_problem.complexity_score)

    # Create a minimal graph state for deliberation
    # This allows us to reuse existing parallel_round_node logic
    mini_state = DeliberationGraphState(
        session_id=f"subproblem_{sub_problem.id}",
        problem=problem,
        current_sub_problem=sub_problem,
        personas=personas,
        contributions=[],
        round_summaries=[],
        phase=DeliberationPhase.DISCUSSION,
        round_number=1,
        max_rounds=max_rounds,
        metrics=metrics,
        facilitator_decision=None,
        should_stop=False,
        stop_reason=None,
        user_input=None,
        user_id=user_id,
        current_node="parallel_subproblem_deliberation",
        votes=[],
        synthesis=None,
        sub_problem_results=previous_results,
        sub_problem_index=sub_problem_index,
        collect_context=False,
        business_context=None,
        pending_clarification=None,
        phase_costs={},
        current_phase="exploration",
        experts_per_round=[],
        semantic_novelty_scores={},
        exploration_score=0.0,
        focus_score=1.0,
        completed_research_queries=[],
    )

    # Run rounds until convergence or max rounds (parallel multi-expert architecture)
    for round_num in range(1, max_rounds + 1):
        mini_state["round_number"] = round_num

        # Emit round start event
        if event_bridge:
            event_bridge.emit(
                "round_started",
                {
                    "round_number": round_num,
                },
            )

        # Run parallel round
        updates = await graph_nodes.parallel_round_node(mini_state)

        # Update mini_state with results
        mini_state["contributions"] = updates["contributions"]
        mini_state["round_number"] = updates["round_number"]
        mini_state["round_summaries"] = updates["round_summaries"]
        mini_state["metrics"] = updates["metrics"]
        mini_state["current_phase"] = updates.get("current_phase", "exploration")
        mini_state["experts_per_round"] = updates.get("experts_per_round", [])

        # Emit individual contribution events (matching sequential execution)
        if event_bridge:
            # Get contributions from this round
            round_contributions = [
                c for c in mini_state["contributions"] if c.round_number == round_num
            ]

            # Emit one event per contribution
            for contrib in round_contributions:
                # Get persona profile for archetype and domain_expertise
                contrib_persona: PersonaProfile | None = None
                for p in personas:
                    if p.code == contrib.persona_code:
                        contrib_persona = p
                        break

                # Note: contribution_summaries are not generated in parallel execution
                # The summary field is optional in frontend TypeScript types
                event_bridge.emit(
                    "contribution",
                    {
                        "persona_code": contrib.persona_code,
                        "persona_name": contrib.persona_name,
                        "archetype": contrib_persona.archetype if contrib_persona else "",
                        "domain_expertise": contrib_persona.domain_expertise
                        if contrib_persona
                        else [],
                        "content": contrib.content,
                        "round": round_num,
                        "contribution_type": "initial" if round_num == 1 else "followup",
                    },
                )

        # Check convergence
        convergence_updates = await check_convergence_node(mini_state)
        mini_state["should_stop"] = convergence_updates.get("should_stop", False)
        mini_state["stop_reason"] = convergence_updates.get("stop_reason")

        if mini_state["should_stop"]:
            logger.info(
                f"deliberate_subproblem: Convergence reached at round {round_num} for {sub_problem.id}"
            )
            break

    # Extract final contributions and summaries
    contributions = mini_state["contributions"]
    round_summaries = mini_state["round_summaries"]
    metrics = mini_state["metrics"]

    logger.info(
        f"deliberate_subproblem: Deliberation complete for {sub_problem.id} - {len(contributions)} contributions, {len(round_summaries)} rounds"
    )

    # Step 4: Collect recommendations
    logger.info(f"deliberate_subproblem: Collecting recommendations for {sub_problem.id}")

    # Emit voting started event
    if event_bridge:
        event_bridge.emit(
            "voting_started",
            {
                "experts": [p.code for p in personas],
                "count": len(personas),
            },
        )

    broker = PromptBroker()
    recommendations, llm_responses = await collect_recommendations(state=mini_state, broker=broker)
    track_aggregated_cost(metrics, "voting", llm_responses)

    # Convert recommendations to dicts
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

    logger.info(
        f"deliberate_subproblem: Collected {len(votes)} recommendations for {sub_problem.id}"
    )

    # Emit voting complete event
    if event_bridge:
        # Calculate consensus level based on agreement (simple heuristic)
        # Could be improved with actual consensus analysis
        consensus_level = "moderate"
        if len(votes) >= len(personas) * 0.8:
            consensus_level = "strong"
        elif len(votes) < len(personas) * 0.5:
            consensus_level = "weak"

        event_bridge.emit(
            "voting_complete",
            {
                "votes_count": len(votes),
                "consensus_level": consensus_level,
            },
        )

    # Step 5: Generate synthesis
    logger.info(f"deliberate_subproblem: Generating synthesis for {sub_problem.id}")
    synthesis = await _generate_synthesis(sub_problem, contributions, votes, metrics, event_bridge)

    # Step 6: Generate expert summaries for memory
    expert_summaries = await _generate_expert_summaries(
        personas, contributions, sub_problem, mini_state["round_number"], metrics
    )

    # Calculate duration
    duration_seconds = time.time() - start_time

    # Create result
    result = SubProblemResult(
        sub_problem_id=sub_problem.id,
        sub_problem_goal=sub_problem.goal,
        synthesis=synthesis,
        votes=votes,
        contribution_count=len(contributions),
        cost=metrics.total_cost,
        duration_seconds=duration_seconds,
        expert_panel=[p.code for p in personas],
        expert_summaries=expert_summaries,
    )

    logger.info(
        f"deliberate_subproblem: Complete for {sub_problem.id} - "
        f"{len(contributions)} contributions, ${metrics.total_cost:.4f}, {duration_seconds:.1f}s"
    )

    return result
