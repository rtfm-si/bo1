"""Synthesis and voting nodes.

This module contains nodes for the final stages of deliberation:
- vote_node: Collects recommendations from all personas
- synthesize_node: Creates synthesis from deliberation
- next_subproblem_node: Handles transition between sub-problems
- meta_synthesize_node: Creates cross-sub-problem meta-synthesis
"""

import json
import logging
from typing import Any

from bo1.graph.state import DeliberationGraphState
from bo1.graph.utils import ensure_metrics, track_aggregated_cost, track_phase_cost
from bo1.models.state import DeliberationPhase, SubProblemResult

logger = logging.getLogger(__name__)


def _get_problem_attr(problem: Any, attr: str, default: Any = None) -> Any:
    """Safely get attribute from problem (handles both dict and object).

    After checkpoint restoration, Problem objects may be deserialized as dicts.
    This helper handles both cases.
    """
    if problem is None:
        return default
    if isinstance(problem, dict):
        return problem.get(attr, default)
    return getattr(problem, attr, default)


def _get_subproblem_attr(sp: Any, attr: str, default: Any = None) -> Any:
    """Safely get attribute from sub-problem (handles both dict and object).

    After checkpoint restoration, SubProblem objects may be deserialized as dicts.
    This helper handles both cases.
    """
    if sp is None:
        return default
    if isinstance(sp, dict):
        return sp.get(attr, default)
    return getattr(sp, attr, default)


async def vote_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Collect recommendations from all personas.

    This node wraps the collect_recommendations() function from voting.py
    and updates the graph state with the collected recommendations.

    IMPORTANT: Recommendation System (NOT Voting)
    - Uses free-form text recommendations, NOT binary votes
    - Legacy "votes" key retained for backward compatibility
    - Recommendation model: persona_code, persona_name, recommendation (string),
      reasoning, confidence (0-1), conditions (list), weight
    - See bo1/models/recommendations.py for Recommendation model
    - See bo1/orchestration/voting.py:collect_recommendations() for implementation

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates (votes, recommendations, metrics)
    """
    from bo1.llm.broker import PromptBroker
    from bo1.orchestration.voting import collect_recommendations

    logger.info("vote_node: Starting recommendation collection phase")

    # Create broker for LLM calls
    broker = PromptBroker()

    # Collect recommendations from all personas with v2 state
    recommendations, llm_responses = await collect_recommendations(state=state, broker=broker)

    # Track cost in metrics
    metrics = ensure_metrics(state)
    track_aggregated_cost(metrics, "voting", llm_responses)

    rec_cost = sum(r.cost_total for r in llm_responses)

    logger.info(
        f"vote_node: Complete - {len(recommendations)} recommendations collected (cost: ${rec_cost:.4f})"
    )

    # Convert Recommendation objects to dicts for state storage
    recommendations_dicts = [
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

    # Return state updates
    # Keep "votes" key for backward compatibility during migration
    return {
        "votes": recommendations_dicts,
        "recommendations": recommendations_dicts,
        "phase": DeliberationPhase.VOTING,
        "metrics": metrics,
        "current_node": "vote",
        "sub_problem_index": state.get("sub_problem_index", 0),  # Preserve sub_problem_index
    }


async def synthesize_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Synthesize final recommendation from deliberation using lean McKinsey-style template.

    Uses hierarchical summarization + lean output format for complete, premium results:
    - Round summaries provide deliberation evolution (already condensed)
    - Final round contributions provide detail
    - Output follows Pyramid Principle: answer first, then support
    - Structured sections: Bottom Line, Why It Matters, Next Steps, Risks, Confidence
    - Expected output: ~800-1000 tokens (fits within 1500 limit with headroom)

    Args:
        state: Current graph state (must have votes and contributions)

    Returns:
        Dictionary with state updates (synthesis report, phase=COMPLETE)
    """
    from bo1.llm.broker import PromptBroker, PromptRequest
    from bo1.prompts.reusable_prompts import SYNTHESIS_LEAN_TEMPLATE, get_limited_context_sections

    logger.info("synthesize_node: Starting synthesis with lean McKinsey-style template")

    # Get problem and contributions
    problem = state.get("problem")
    contributions = state.get("contributions", [])
    votes = state.get("votes", [])
    round_summaries = state.get("round_summaries", [])
    current_round = state.get("round_number", 1)

    if not problem:
        raise ValueError("synthesize_node called without problem in state")

    # AUDIT FIX (Priority 3, Task 3.1): Hierarchical context composition
    # Build round summaries section (rounds 1 to N-1)
    round_summaries_text = []
    if round_summaries:
        for i, summary in enumerate(round_summaries, start=1):
            round_summaries_text.append(f"Round {i}: {summary}")
    else:
        round_summaries_text.append("(No round summaries available)")

    # Build final round contributions (only contributions from final round)
    final_round_contributions = []
    final_round_num = current_round  # Current round is the final one

    # Get contributions from final round only
    final_round_contribs = [c for c in contributions if c.round_number == final_round_num]

    if final_round_contribs:
        for contrib in final_round_contribs:
            final_round_contributions.append(f"{contrib.persona_name}:\n{contrib.content}\n")
    else:
        # Fallback: if no final round contributions, use last 5 contributions
        logger.warning("synthesize_node: No final round contributions found, using last 5")
        for contrib in contributions[-5:]:
            final_round_contributions.append(
                f"Round {contrib.round_number} - {contrib.persona_name}:\n{contrib.content}\n"
            )

    # Format votes/recommendations
    votes_text = []
    for vote in votes:
        votes_text.append(
            f"{vote['persona_name']}: {vote['recommendation']} "
            f"(confidence: {vote['confidence']:.2f})\n"
            f"Reasoning: {vote['reasoning']}\n"
        )
        conditions = vote.get("conditions")
        if conditions and isinstance(conditions, list):
            votes_text.append(f"Conditions: {', '.join(str(c) for c in conditions)}\n")
        votes_text.append("\n")

    # Check for limited context mode (Option D+E Hybrid - Phase 8)
    limited_context_mode = state.get("limited_context_mode", False)
    prompt_section, output_section = get_limited_context_sections(limited_context_mode)

    if limited_context_mode:
        logger.info("synthesize_node: Limited context mode active - including assumptions section")

    # Compose synthesis prompt using lean McKinsey-style template
    synthesis_prompt = SYNTHESIS_LEAN_TEMPLATE.format(
        problem_statement=_get_problem_attr(problem, "description", ""),
        round_summaries="\n".join(round_summaries_text),
        final_round_contributions="\n".join(final_round_contributions),
        votes="\n".join(votes_text),
        limited_context_section=prompt_section,
        limited_context_output_section=output_section,
    )

    logger.info(
        f"synthesize_node: Context built - {len(round_summaries)} round summaries, "
        f"{len(final_round_contribs)} final round contributions, {len(votes)} votes"
    )

    # Create broker and request
    broker = PromptBroker()
    request = PromptRequest(
        system=synthesis_prompt,
        user_message="Generate the executive brief now. Follow the output format exactly.",
        prefill="## The Bottom Line",  # Force immediate answer-first structure (no trailing whitespace)
        model="sonnet",  # Use Sonnet for high-quality synthesis
        temperature=0.7,
        max_tokens=1500,  # Lean template produces ~800-1000 tokens, leaving headroom
        phase="synthesis",
        agent_type="synthesizer",
        cache_system=True,  # Enable prompt caching (system prompt = static template)
    )

    # Call LLM
    response = await broker.call(request)

    # Clean up response - ensure proper markdown structure
    raw_content = response.content.strip()
    # Prepend the prefill since it's not included in response
    synthesis_report = "## The Bottom Line\n\n" + raw_content

    # ISSUE #2 FIX: Validate synthesis is not empty/suspiciously short
    synthesis_length = len(synthesis_report)
    if synthesis_length < 100:
        logger.warning(
            f"synthesize_node: SYNTHESIS WARNING - Suspiciously short synthesis "
            f"({synthesis_length} chars). This may indicate extraction issues. "
            f"Content preview: {synthesis_report[:200]}"
        )

    # Add AI-generated content disclaimer
    disclaimer = (
        "\n\n---\n\n"
        "Warning: This content is AI-generated for learning and knowledge purposes only, "
        "not professional advisory.\n\n"
        "Always verify recommendations using licensed legal/financial professionals "
        "for your location."
    )
    synthesis_report_with_disclaimer = synthesis_report + disclaimer

    # Track cost in metrics
    metrics = ensure_metrics(state)
    track_phase_cost(metrics, "synthesis", response)

    logger.info(
        f"synthesize_node: Complete - synthesis generated "
        f"({synthesis_length} chars, cost: ${response.cost_total:.4f})"
    )

    # Return state updates
    return {
        "synthesis": synthesis_report_with_disclaimer,
        "phase": DeliberationPhase.SYNTHESIS,  # Don't set COMPLETE yet - may have more sub-problems
        "metrics": metrics,
        "current_node": "synthesize",
        "sub_problem_index": state.get("sub_problem_index", 0),  # Preserve sub_problem_index
    }


async def next_subproblem_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Move to next sub-problem after synthesis.

    This node:
    1. Saves the current sub-problem result (synthesis, votes, costs)
    2. Generates per-expert summaries for memory
    3. Increments sub_problem_index
    4. If more sub-problems: resets deliberation state and sets next sub-problem
    5. If all complete: triggers meta-synthesis by setting current_sub_problem=None

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates
    """
    from bo1.agents.summarizer import SummarizerAgent

    # Extract current sub-problem data
    current_sp = state.get("current_sub_problem")
    problem = state.get("problem")
    contributions = state.get("contributions", [])
    votes = state.get("votes", [])
    personas = state.get("personas", [])
    synthesis = state.get("synthesis", "")
    metrics = state.get("metrics")
    sub_problem_index = state.get("sub_problem_index", 0)

    # Enhanced logging for sub-problem progression (Bug #3 fix)
    sub_problems = _get_problem_attr(problem, "sub_problems", [])
    total_sub_problems = len(sub_problems) if sub_problems else 0
    logger.info(
        f"next_subproblem_node: Saving result for sub-problem {sub_problem_index + 1}/{total_sub_problems}: "
        f"{_get_subproblem_attr(current_sp, 'goal', 'unknown')}"
    )

    if not current_sp:
        raise ValueError("next_subproblem_node called without current_sub_problem")

    if not problem:
        raise ValueError("next_subproblem_node called without problem")

    # Calculate cost for this sub-problem (all phase costs accumulated)
    # For simplicity, use total_cost - sum of previous sub-problem costs
    total_cost_so_far = metrics.total_cost if metrics else 0.0
    previous_results = state.get("sub_problem_results", [])
    previous_cost = sum(r.cost for r in previous_results)
    sub_problem_cost = total_cost_so_far - previous_cost

    # Track duration (placeholder - could enhance with actual timing)
    duration_seconds = 0.0

    # Generate per-expert summaries for memory (if there are contributions)
    expert_summaries: dict[str, str] = {}

    if contributions:
        summarizer = SummarizerAgent()

        for persona in personas:
            # Get contributions from this expert
            expert_contributions = [c for c in contributions if c.persona_code == persona.code]

            if expert_contributions:
                try:
                    # Convert contributions to dict format for summarizer
                    contribution_dicts = [
                        {"persona": c.persona_name, "content": c.content}
                        for c in expert_contributions
                    ]

                    # Summarize expert's contributions
                    response = await summarizer.summarize_round(
                        round_number=state.get("round_number", 1),
                        contributions=contribution_dicts,
                        problem_statement=_get_subproblem_attr(current_sp, "goal", ""),
                        target_tokens=75,  # Concise summary for memory
                    )

                    expert_summaries[persona.code] = response.content

                    # Track cost
                    if metrics:
                        phase_costs = metrics.phase_costs
                        phase_costs["expert_memory"] = (
                            phase_costs.get("expert_memory", 0.0) + response.cost_total
                        )

                    logger.info(
                        f"Generated memory summary for {persona.display_name}: "
                        f"{response.token_usage.output_tokens} tokens, ${response.cost_total:.6f}"
                    )

                except Exception as e:
                    logger.warning(
                        f"Failed to generate summary for {persona.display_name}: {e}. "
                        f"Expert will not have memory for next sub-problem."
                    )

    # Create SubProblemResult
    result = SubProblemResult(
        sub_problem_id=_get_subproblem_attr(current_sp, "id", ""),
        sub_problem_goal=_get_subproblem_attr(current_sp, "goal", ""),
        synthesis=synthesis or "",  # Ensure not None
        votes=votes,
        contribution_count=len(contributions),
        cost=sub_problem_cost,
        duration_seconds=duration_seconds,
        expert_panel=[p.code for p in personas],
        expert_summaries=expert_summaries,
    )

    # Add to results
    sub_problem_results = list(previous_results)
    sub_problem_results.append(result)

    # Increment index
    next_index = sub_problem_index + 1

    # Check if more sub-problems
    if next_index < len(sub_problems):
        next_sp = sub_problems[next_index]

        logger.info(
            f"Moving to sub-problem {next_index + 1}/{len(sub_problems)}: {_get_subproblem_attr(next_sp, 'goal', 'unknown')}"
        )

        return {
            "current_sub_problem": next_sp,
            "sub_problem_index": next_index,
            "sub_problem_results": sub_problem_results,
            "round_number": 0,  # Will be set to 1 by initial_round_node
            "contributions": [],
            "votes": [],
            "synthesis": None,
            "facilitator_decision": None,
            "should_stop": False,
            "stop_reason": None,
            "round_summaries": [],  # Reset for new sub-problem
            "personas": [],  # Will be re-selected by select_personas_node
            "phase": DeliberationPhase.DECOMPOSITION,  # Ready for new sub-problem
            "metrics": metrics,  # Keep metrics (accumulates across sub-problems)
            "current_node": "next_subproblem",
            "completed_research_queries": [],  # Reset research tracking for new sub-problem
        }
    else:
        # All complete -> meta-synthesis
        logger.info("All sub-problems complete, proceeding to meta-synthesis")
        return {
            "current_sub_problem": None,
            "sub_problem_results": sub_problem_results,
            "phase": DeliberationPhase.SYNTHESIS,  # Meta-synthesis phase
            "current_node": "next_subproblem",
        }


async def meta_synthesize_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Create cross-sub-problem meta-synthesis with structured action plan.

    This node integrates insights from ALL sub-problem deliberations into
    a unified, actionable recommendation in JSON format.

    Args:
        state: Current graph state (must have sub_problem_results)

    Returns:
        Dictionary with state updates (meta-synthesis JSON action plan, phase=COMPLETE)
    """
    from bo1.llm.broker import PromptBroker, PromptRequest
    from bo1.prompts.reusable_prompts import META_SYNTHESIS_ACTION_PLAN_PROMPT

    logger.info("meta_synthesize_node: Starting meta-synthesis (structured JSON)")

    # Get problem and sub-problem results
    problem = state.get("problem")
    sub_problem_results = state.get("sub_problem_results", [])

    if not problem:
        raise ValueError("meta_synthesize_node called without problem")

    if not sub_problem_results:
        raise ValueError("meta_synthesize_node called without sub_problem_results")

    # Get sub_problems list (handles both dict and object)
    meta_sub_problems = _get_problem_attr(problem, "sub_problems", [])

    # Format all sub-problem syntheses
    formatted_results = []
    total_cost = 0.0
    total_duration = 0.0

    for i, result in enumerate(sub_problem_results, 1):
        # Find the sub-problem by ID (handle both dict and object sub-problems)
        sp = None
        for sub_p in meta_sub_problems:
            sp_id = sub_p.get("id") if isinstance(sub_p, dict) else sub_p.id
            if sp_id == result.sub_problem_id:
                sp = sub_p
                break
        sp_goal = (
            (sp.get("goal") if isinstance(sp, dict) else sp.goal) if sp else result.sub_problem_goal
        )

        # Format votes
        votes_summary = []
        for vote in result.votes:
            votes_summary.append(
                f"- {vote.get('persona_name', 'Unknown')}: {vote.get('recommendation', 'N/A')} "
                f"(confidence: {vote.get('confidence', 0.0):.2f})"
            )

        formatted_results.append(
            f"""## Sub-Problem {i} ({result.sub_problem_id}): {sp_goal}

**Synthesis:**
{result.synthesis}

**Expert Recommendations:**
{chr(10).join(votes_summary) if votes_summary else "No votes recorded"}

**Deliberation Metrics:**
- Contributions: {result.contribution_count}
- Cost: ${result.cost:.4f}
- Experts: {", ".join(result.expert_panel)}
"""
        )
        total_cost += result.cost
        total_duration += result.duration_seconds

    # Create meta-synthesis prompt (structured JSON)
    meta_prompt = META_SYNTHESIS_ACTION_PLAN_PROMPT.format(
        original_problem=_get_problem_attr(problem, "description", ""),
        problem_context=_get_problem_attr(problem, "context") or "No additional context provided",
        sub_problem_count=len(sub_problem_results),
        all_sub_problem_syntheses="\n\n---\n\n".join(formatted_results),
    )

    # Create broker and request
    broker = PromptBroker()
    request = PromptRequest(
        system=meta_prompt,
        user_message="Generate the JSON action plan now:",
        prefill="{",  # Force pure JSON output (no markdown, no XML wrapper)
        model="sonnet",  # Use Sonnet for high-quality meta-synthesis
        temperature=0.7,
        max_tokens=4000,
        phase="meta_synthesis",
        agent_type="meta_synthesizer",
        cache_system=True,  # TASK 1 FIX: Enable prompt caching (system prompt = static meta-synthesis template)
    )

    # Call LLM
    response = await broker.call(request)

    # Prepend prefill to get complete JSON (including opening brace)
    json_content = "{" + response.content

    # Parse and validate JSON
    try:
        action_plan = json.loads(json_content)
        logger.info("meta_synthesize_node: Successfully parsed JSON action plan")
    except json.JSONDecodeError as e:
        logger.warning(f"meta_synthesize_node: Failed to parse JSON, using fallback: {e}")
        # Fallback to plain text if JSON parsing fails
        action_plan = None
        json_content = response.content

    # Store both JSON and formatted output
    if action_plan:
        # Create readable markdown from JSON for backwards compatibility
        meta_synthesis = f"""# Action Plan

{action_plan.get("synthesis_summary", "")}

## Recommended Actions

"""
        for i, action in enumerate(action_plan.get("recommended_actions", []), 1):
            meta_synthesis += f"""### {i}. {action.get("action", "N/A")} [{action.get("priority", "medium").upper()}]

**Timeline:** {action.get("timeline", "TBD")}

**Rationale:** {action.get("rationale", "N/A")}

**Success Metrics:**
{chr(10).join(f"- {m}" for m in action.get("success_metrics", []))}

**Risks:**
{chr(10).join(f"- {r}" for r in action.get("risks", []))}

---

"""
    else:
        # Fallback to plain content
        meta_synthesis = json_content

    # Add deliberation summary footer
    footer = f"""

---

## Deliberation Summary

- **Original problem**: {_get_problem_attr(problem, "description", "")}
- **Sub-problems deliberated**: {len(sub_problem_results)}
- **Total contributions**: {sum(r.contribution_count for r in sub_problem_results)}
- **Total cost**: ${total_cost:.4f}
- **Meta-synthesis cost**: ${response.cost_total:.4f}
- **Grand total cost**: ${total_cost + response.cost_total:.4f}

Warning: This content is AI-generated for learning and knowledge purposes only, not professional advisory.
Always verify recommendations using licensed legal/financial professionals for your location.
"""

    # Store JSON in synthesis field for frontend parsing
    if action_plan:
        # Frontend will parse this JSON
        meta_synthesis_final = json_content + footer
    else:
        meta_synthesis_final = meta_synthesis + footer

    # Track cost in metrics
    metrics = ensure_metrics(state)
    track_phase_cost(metrics, "meta_synthesis", response)

    logger.info(
        f"meta_synthesize_node: Complete - meta-synthesis generated "
        f"(cost: ${response.cost_total:.4f}, total: ${metrics.total_cost:.4f})"
    )

    # Return state updates
    return {
        "synthesis": meta_synthesis_final,
        "phase": DeliberationPhase.COMPLETE,
        "metrics": metrics,
        "current_node": "meta_synthesis",
    }
