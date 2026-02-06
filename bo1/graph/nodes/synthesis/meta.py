"""Meta-synthesis node: Creates cross-sub-problem meta-synthesis."""

import json
import logging
import time
from typing import Any

from bo1.config import TokenBudgets, get_model_for_role
from bo1.graph.nodes.utils import emit_node_duration, log_with_session
from bo1.graph.state import (
    DeliberationGraphState,
    get_core_state,
    get_problem_state,
)
from bo1.graph.utils import ensure_metrics, track_phase_cost
from bo1.models.state import DeliberationPhase, SubProblemResult
from bo1.utils.checkpoint_helpers import get_problem_attr

logger = logging.getLogger(__name__)


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
    from bo1.prompts import META_SYNTHESIS_ACTION_PLAN_PROMPT

    _start_time = time.perf_counter()

    # Use nested state accessors for grouped field access
    core_state = get_core_state(state)
    problem_state = get_problem_state(state)

    session_id = core_state.get("session_id")
    log_with_session(
        logger,
        logging.INFO,
        session_id,
        "meta_synthesize_node: Starting meta-synthesis (structured JSON)",
    )

    # Get problem and sub-problem results from accessors
    problem = problem_state.get("problem")
    sub_problem_results_raw = problem_state.get("sub_problem_results", [])

    if not problem:
        raise ValueError("meta_synthesize_node called without problem")

    if not sub_problem_results_raw:
        raise ValueError("meta_synthesize_node called without sub_problem_results")

    # P0 FIX: Normalize sub_problem_results from dicts back to SubProblemResult objects
    # After checkpoint restoration, these may be dicts instead of Pydantic models
    sub_problem_results: list[SubProblemResult] = []
    for result in sub_problem_results_raw:
        if isinstance(result, dict):
            sub_problem_results.append(SubProblemResult.model_validate(result))
            logger.debug(
                f"meta_synthesize_node: Normalized dict result for {result.get('sub_problem_id', 'unknown')}"
            )
        else:
            sub_problem_results.append(result)

    # P0 DEBUG: Log synthesis lengths to diagnose 14-token issue
    for i, result in enumerate(sub_problem_results):
        synthesis_len = len(result.synthesis) if result.synthesis else 0
        logger.info(
            f"meta_synthesize_node: Sub-problem {i} ({result.sub_problem_id}) synthesis length: {synthesis_len} chars, "
            f"votes: {len(result.votes)}, contributions: {result.contribution_count}"
        )
        if synthesis_len == 0:
            logger.warning(
                f"meta_synthesize_node: EMPTY SYNTHESIS for sub-problem {result.sub_problem_id}!"
            )

    # Get sub_problems list (handles both dict and object)
    meta_sub_problems = get_problem_attr(problem, "sub_problems", [])

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
        original_problem=get_problem_attr(problem, "description", ""),
        problem_context=get_problem_attr(problem, "context") or "No additional context provided",
        sub_problem_count=len(sub_problem_results),
        all_sub_problem_syntheses="\n\n---\n\n".join(formatted_results),
    )

    # Create broker and request
    broker = PromptBroker()

    # Centralized model selection (respects experiment overrides and TASK_MODEL_DEFAULTS)
    meta_synthesis_model = get_model_for_role("meta_synthesis")
    log_with_session(
        logger,
        logging.INFO,
        session_id,
        f"meta_synthesize_node: Using model={meta_synthesis_model}",
    )

    request = PromptRequest(
        system=meta_prompt,
        user_message="Generate the JSON action plan now:",
        prefill="{",  # Force pure JSON output (no markdown, no XML wrapper)
        model=meta_synthesis_model,
        temperature=0.7,
        max_tokens=4000,
        phase="meta_synthesis",
        agent_type="meta_synthesizer",
        cache_system=True,  # Enable prompt caching (system prompt = static meta-synthesis template)
    )

    # Call LLM
    response = await broker.call(request)

    # TOKEN BUDGET WARNING: Check if output tokens approach/exceed budget
    if response.token_usage:
        output_tokens = response.token_usage.output_tokens
        warning_threshold = int(TokenBudgets.META_SYNTHESIS * 0.9)
        if output_tokens >= warning_threshold:
            log_with_session(
                logger,
                logging.WARNING,
                session_id,
                f"[TOKEN_BUDGET] Meta-synthesis output tokens ({output_tokens}) "
                f">= 90% of budget ({TokenBudgets.META_SYNTHESIS}). "
                f"Sub-problems: {len(sub_problem_results)}",
            )

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

    # Add deliberation summary footer (costs excluded - admin-only via phase_cost_breakdown event)
    footer = f"""

---

## Deliberation Summary

- **Original problem**: {get_problem_attr(problem, "description", "")}
- **Sub-problems deliberated**: {len(sub_problem_results)}
- **Total contributions**: {sum(r.contribution_count for r in sub_problem_results)}

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
    emit_node_duration("meta_synthesize_node", (time.perf_counter() - _start_time) * 1000)
    return {
        "synthesis": meta_synthesis_final,
        "phase": DeliberationPhase.COMPLETE,
        "metrics": metrics,
        "current_node": "meta_synthesis",
    }
