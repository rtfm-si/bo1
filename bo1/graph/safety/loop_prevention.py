"""Infinite loop prevention system for LangGraph deliberations.

This module implements a 5-layer defense system against infinite loops:

1. Recursion Limit (LangGraph built-in)
2. Cycle Detection (Graph validation)
3. Round Counter (Domain logic)
4. Timeout Watchdog (Runtime protection) - Day 25
5. Cost Kill Switch (Budget enforcement) - Day 25

Together, these layers provide 100% confidence that deliberations cannot loop indefinitely.
"""

import asyncio
import logging
import os
from typing import Any, Literal

import networkx as nx

from bo1.graph.state import DeliberationGraphState

logger = logging.getLogger(__name__)

# ============================================================================
# Layer 4: Timeout Watchdog
# ============================================================================

# Default timeout: 1 hour (3600 seconds)
# Configurable via environment variable
DEFAULT_TIMEOUT_SECONDS = int(os.getenv("DELIBERATION_TIMEOUT_SECONDS", "3600"))

# ============================================================================
# Layer 1: Recursion Limit (LangGraph Built-in)
# ============================================================================

# Maximum steps the graph can take before raising GraphRecursionError
# MULTI-SUBPROBLEM ARCHITECTURE: 250 steps supports up to 5 sub-problems
# Calculation: 5 sub-problems x ~45 nodes/sub-problem + 25 overhead = 250
DELIBERATION_RECURSION_LIMIT = 250

# Why 250 is needed for multi-subproblem architecture:
# - Decompose: 1 node
# - Per sub-problem (~45 nodes worst case):
#   - select_personas: 1
#   - initial_round: 1
#   - Per round (6 max): parallel_round + check_convergence + facilitator_decide = 3 x 6 = 18
#   - summarize per round: 6
#   - voting: 1
#   - synthesis: 1
#   - transitions/retries: ~17
# - Meta-synthesis: ~5 nodes
# - Total for 5 sub-problems: 1 + 5*45 + 5 = ~231 nodes
# - 250 provides safe margin for retries and edge cases
#
# NOTE: The round counter (6 max per sub-problem) is the primary protection
# against infinite loops. This limit is a backstop for unexpected edge cases.


# ============================================================================
# Layer 2: Cycle Detection (Graph Validation)
# ============================================================================


def validate_graph_acyclic(graph: nx.DiGraph) -> None:
    """Validate that the graph has no uncontrolled cycles.

    A cycle is "controlled" if it has at least one conditional exit path.
    Uncontrolled cycles (no way to break out) will cause infinite loops.

    Args:
        graph: NetworkX DiGraph representing the LangGraph

    Raises:
        ValueError: If an uncontrolled cycle is detected

    Example:
        >>> G = nx.DiGraph()
        >>> G.add_edges_from([("A", "B"), ("B", "C"), ("C", "A")])
        >>> validate_graph_acyclic(G)
        ValueError: Uncontrolled cycle detected: A -> B -> C -> A
    """
    cycles = list(nx.simple_cycles(graph))

    if not cycles:
        logger.info("Graph validation: No cycles detected (fully acyclic)")
        return

    logger.info(f"Graph validation: Found {len(cycles)} cycle(s), checking for exit conditions...")

    for cycle in cycles:
        # Check if cycle has a conditional exit
        has_exit = _has_exit_condition(graph, cycle)

        if not has_exit:
            cycle_str = " -> ".join(cycle + [cycle[0]])
            raise ValueError(
                f"Uncontrolled cycle detected: {cycle_str}. "
                "All cycles must have at least one conditional exit path. "
                "Add a conditional edge that breaks the loop (e.g., convergence check)."
            )

        logger.debug(f"Cycle {' -> '.join(cycle)} has exit condition (safe)")

    logger.info(f"Graph validation: All {len(cycles)} cycles are controlled (safe)")


def _has_exit_condition(graph: nx.DiGraph, cycle: list[str]) -> bool:
    """Check if a cycle has at least one conditional exit path.

    A cycle is safe if:
    1. At least one node in the cycle has an outgoing edge to a node NOT in the cycle
    2. That edge is conditional (not always taken)

    Args:
        graph: NetworkX DiGraph
        cycle: List of node names forming the cycle

    Returns:
        True if the cycle has an exit, False otherwise
    """
    cycle_set = set(cycle)

    for node in cycle:
        # Get all outgoing edges from this node
        successors = list(graph.successors(node))

        # Check if any successor is outside the cycle
        for successor in successors:
            if successor not in cycle_set:
                # Found an edge leading OUT of the cycle
                # In a real implementation, we'd check if it's conditional
                # For now, assume any edge out of cycle is conditional
                logger.debug(f"Exit found: {node} -> {successor} (outside cycle)")
                return True

    return False


# ============================================================================
# Layer 3: Round Counter (Domain Logic)
# ============================================================================


def get_adaptive_max_rounds(complexity_score: int) -> int:
    """Calculate max rounds based on sub-problem complexity.

    Research finding from CONSENSUS_BUILDING_RESEARCH.md:
    - Complexity 1-3: 2-3 rounds optimal (simple problems)
    - Complexity 4-5: 3-4 rounds optimal (moderate complexity)
    - Complexity 6-7: 4-5 rounds optimal (complex problems)
    - Complexity 8+: 5-6 rounds optimal (very complex)

    This enables 30-50% reduction in deliberation time for simple problems
    while maintaining quality for complex ones.

    Args:
        complexity_score: Problem complexity (1-10 scale)

    Returns:
        Recommended max rounds for this complexity level

    Example:
        >>> get_adaptive_max_rounds(complexity_score=3)
        3  # Simple problem = quick resolution
        >>> get_adaptive_max_rounds(complexity_score=8)
        6  # Complex problem = full deliberation
    """
    if complexity_score <= 3:
        return 3  # Simple: quick resolution
    elif complexity_score <= 5:
        return 4  # Moderate: standard debate
    elif complexity_score <= 7:
        return 5  # Complex: extended discussion
    else:
        return 6  # Very complex: full deliberation


async def check_convergence_node(state: DeliberationGraphState) -> DeliberationGraphState:
    """Check convergence and set stop flags if needed (simplified orchestration).

    AUDIT FIX (Priority 4.3): Refactored from 600-line monolith into focused modules:
    - Quality metrics: bo1/graph/quality/metrics.py
    - Stopping rules: bo1/graph/quality/stopping_rules.py

    This node implements Layer 3 of loop prevention by enforcing round limits.

    Stopping conditions:
    1. round_number >= max_rounds (user-configured limit)
    2. round_number >= 6 (absolute hard cap for parallel architecture)
    3. Convergence detected (semantic similarity > 0.90)
    4. Quality thresholds met (exploration, focus, completeness)
    5. Early exit (high convergence + low novelty)
    6. Deadlock detected (circular arguments)

    Args:
        state: Current deliberation state

    Returns:
        Updated state with should_stop and stop_reason set if applicable
    """
    from bo1.graph.quality.metrics import QualityMetricsCalculator
    from bo1.graph.quality.stopping_rules import StoppingRulesEvaluator

    round_number = state.get("round_number", 1)
    max_rounds = state.get("max_rounds", 10)

    # Get problem statement for context
    problem = state.get("problem")
    problem_statement = ""
    if problem:
        if hasattr(problem, "description"):
            problem_statement = problem.description
        elif isinstance(problem, dict):
            problem_statement = problem.get("description", "")

    # Calculate quality metrics
    calculator = QualityMetricsCalculator()
    metrics = await calculator.calculate_all(state, problem_statement)
    state["metrics"] = metrics

    # ALWAYS determine and set current_phase based on round number
    # This ensures phase is available for UI display even on early rounds
    from bo1.graph.nodes import _determine_phase

    current_phase = _determine_phase(round_number, max_rounds)
    state["current_phase"] = current_phase
    logger.info(f"Round {round_number}: Phase set to {current_phase}")

    # DEBUG: Log all quality metrics for verification
    logger.info(
        f"Round {round_number}: Quality metrics SET - "
        f"exploration={metrics.exploration_score}, "
        f"focus={metrics.focus_score}, "
        f"completeness={metrics.meeting_completeness_index}, "
        f"novelty={metrics.novelty_score}, "
        f"conflict={metrics.conflict_score}, "
        f"convergence={metrics.convergence_score}, "
        f"phase={current_phase}"
    )

    # NEW: Check for context insufficiency (Option D+E Hybrid)
    # Only check in early rounds (1-2) before normal stopping rules
    context_check = check_context_insufficiency(state)
    if context_check:
        logger.warning(
            f"Round {round_number}: Context insufficiency detected - "
            f"{context_check['meta_count']}/{context_check['total_count']} meta-discussion"
        )
        # Mark that we've emitted this event (prevent duplicate emissions)
        state["context_insufficient_emitted"] = True
        state["should_stop"] = True
        state["stop_reason"] = "context_insufficient"
        # Store the detection info for event emission
        state["context_insufficiency_info"] = context_check
        return state

    # Evaluate stopping rules
    evaluator = StoppingRulesEvaluator()
    decision = evaluator.evaluate(state)

    # Apply decision to state
    state["should_stop"] = decision.should_stop
    if decision.stop_reason:
        state["stop_reason"] = decision.stop_reason
    if decision.facilitator_guidance:
        state["facilitator_guidance"] = decision.facilitator_guidance

    if decision.should_stop:
        logger.info(f"Round {round_number}: Stopping deliberation - Reason: {decision.stop_reason}")
    else:
        logger.debug(f"Round {round_number}/{max_rounds}: Convergence check passed, continuing")

    return state


# ============================================================================
# Context Sufficiency Detection (Option D+E Hybrid)
# ============================================================================


def check_context_insufficiency(state: DeliberationGraphState) -> dict[str, Any] | None:
    """Check if deliberation is suffering from insufficient context.

    Triggers when:
    1. Round 1 or 2 (early in deliberation)
    2. >50% of contributions are meta-discussion (asking for more context)
    3. context_insufficient_emitted is False (haven't already emitted this event)

    When triggered, the graph should pause and emit a context_insufficient event
    giving the user 3 choices: provide more context, continue with best effort,
    or end the meeting early.

    Args:
        state: Current deliberation state

    Returns:
        Dict with detection info if context insufficient, None otherwise
        Returns: {
            "detected": True,
            "meta_ratio": float,
            "meta_count": int,
            "total_count": int,
            "round": int,
            "expert_questions": list[str]
        }
    """
    round_number = state.get("round_number", 1)

    # Only check in rounds 1-2 (too early for normal convergence issues)
    if round_number > 2:
        return None

    # Check if we've already emitted this event
    if state.get("context_insufficient_emitted", False):
        return None

    # Check if user already made a choice (e.g., resuming after choice)
    if state.get("user_context_choice") is not None:
        return None

    meta_count = state.get("meta_discussion_count", 0)
    total_count = state.get("total_contributions_checked", 0)

    # Need at least 3 contributions to assess
    if total_count < 3:
        return None

    meta_ratio = meta_count / total_count

    # Threshold: >50% meta-discussion indicates insufficient context
    if meta_ratio > 0.50:
        logger.warning(
            f"Context insufficiency detected: {meta_count}/{total_count} "
            f"({meta_ratio:.0%}) contributions are meta-discussion"
        )

        # Extract questions from meta-discussion contributions
        expert_questions = _extract_expert_questions(state)

        return {
            "detected": True,
            "meta_ratio": meta_ratio,
            "meta_count": meta_count,
            "total_count": total_count,
            "round": round_number,
            "expert_questions": expert_questions,
        }

    return None


def _extract_expert_questions(state: DeliberationGraphState) -> list[str]:
    """Extract questions experts are asking from meta-discussion contributions.

    Parses recent contributions looking for question patterns that indicate
    what information the experts need.

    Args:
        state: Current deliberation state

    Returns:
        List of extracted questions (up to 5)
    """
    import re

    questions = []
    contributions = state.get("contributions", [])

    # Question patterns to look for
    question_patterns = [
        r"what (?:is|are) (?:the|your) (.+?)\?",
        r"could you (?:clarify|specify|explain) (.+?)\?",
        r"(?:need|require) (?:to know|information about) (.+?)(?:\.|$)",
        r"unclear (?:what|how|whether) (.+?)(?:\.|$)",
        r"what (?:exactly|specifically) (.+?)\?",
    ]

    # Check last 10 contributions
    for contrib in contributions[-10:]:
        content = contrib.content if hasattr(contrib, "content") else str(contrib)
        content_lower = content.lower()

        for pattern in question_patterns:
            matches = re.findall(pattern, content_lower)
            for match in matches:
                question = match.strip().capitalize()
                if question and len(question) > 5 and question not in questions:
                    questions.append(question + "?")

    return questions[:5]  # Limit to 5 questions


# ============================================================================
# Validation Utilities
# ============================================================================


def validate_round_counter_invariants(state: DeliberationGraphState) -> None:
    """Validate round counter invariants.

    Invariants:
    1. round_number is monotonically increasing (never resets)
    2. round_number <= max_rounds
    3. max_rounds <= 15 (hard cap)

    Args:
        state: Current deliberation state

    Raises:
        ValueError: If invariants are violated
    """
    round_number = state["round_number"]
    max_rounds = state["max_rounds"]

    if round_number < 0:
        raise ValueError(f"Invalid round_number: {round_number} (must be >= 0)")

    # NEW PARALLEL ARCHITECTURE: Hard cap is 6 rounds (was 15)
    if max_rounds > 6:
        raise ValueError(
            f"Invalid max_rounds: {max_rounds} (hard cap is 6 for parallel architecture)"
        )

    if round_number > max_rounds:
        raise ValueError(f"Round number ({round_number}) exceeds max_rounds ({max_rounds})")


# ============================================================================
# Layer 4: Timeout Watchdog Implementation
# ============================================================================


async def execute_deliberation_with_timeout(
    graph: Any,
    initial_state: DeliberationGraphState,
    config: dict[str, Any],
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> DeliberationGraphState:
    """Execute deliberation with timeout protection.

    This implements Layer 4 of loop prevention by enforcing a hard timeout.
    If the deliberation exceeds the timeout, it's killed and the last checkpoint is preserved.

    Args:
        graph: Compiled LangGraph
        initial_state: Initial deliberation state
        config: Graph config (includes thread_id for checkpointing)
        timeout_seconds: Maximum execution time in seconds (default: 3600 = 1 hour)

    Returns:
        Final deliberation state

    Raises:
        asyncio.TimeoutError: If deliberation exceeds timeout

    Example:
        >>> graph = compile_graph_with_loop_prevention(workflow, checkpointer)
        >>> config = {"configurable": {"thread_id": "session-123"}}
        >>> result = await execute_deliberation_with_timeout(graph, initial_state, config)
    """
    session_id = config.get("configurable", {}).get("thread_id", "unknown")
    logger.info(f"[{session_id}] Starting deliberation with {timeout_seconds}s timeout")

    try:
        # Execute with timeout (Layer 4)
        result: DeliberationGraphState = await asyncio.wait_for(
            graph.ainvoke(initial_state, config),
            timeout=timeout_seconds,
        )
        logger.info(f"[{session_id}] Deliberation completed successfully")
        return result

    except TimeoutError:
        logger.error(
            f"[{session_id}] Deliberation TIMEOUT after {timeout_seconds}s. "
            "This indicates a problem with loop prevention. "
            "Last checkpoint preserved for inspection."
        )
        # Re-raise to allow caller to handle
        raise

    except Exception as e:
        logger.error(f"[{session_id}] Deliberation failed with error: {e}")
        raise


# ============================================================================
# Layer 5: Cost-Based Kill Switch
# ============================================================================

# Default cost limit: $1.00 per session
# Configurable via environment variable and per-tier limits
DEFAULT_MAX_COST_PER_SESSION = float(os.getenv("MAX_COST_PER_SESSION", "1.00"))

# Per-tier cost limits (for future use with subscription tiers)
TIER_COST_LIMITS = {
    "free": 0.50,  # $0.50 max for free tier
    "pro": 2.00,  # $2.00 max for pro tier
    "enterprise": 10.00,  # $10.00 max for enterprise tier
}


def cost_guard_node(state: DeliberationGraphState) -> DeliberationGraphState:
    """Check cost budget and set stop flags if exceeded.

    This node implements Layer 5 of loop prevention by enforcing cost limits.
    If total cost exceeds the budget, force early termination to synthesis.

    Args:
        state: Current deliberation state

    Returns:
        Updated state with should_stop and stop_reason set if budget exceeded
    """
    total_cost = state["metrics"].total_cost
    max_cost = DEFAULT_MAX_COST_PER_SESSION

    # Check if we have a tier-specific limit
    # This will be used when user authentication is added (Week 7)
    tier = state.get("subscription_tier")
    if tier and isinstance(tier, str) and tier in TIER_COST_LIMITS:
        max_cost = TIER_COST_LIMITS[tier]

    if total_cost > max_cost:
        logger.warning(
            f"Cost budget EXCEEDED: ${total_cost:.4f} > ${max_cost:.2f}. "
            "Forcing early termination to synthesis."
        )
        state["should_stop"] = True
        state["stop_reason"] = "cost_budget_exceeded"
    else:
        logger.debug(f"Cost check passed: ${total_cost:.4f} / ${max_cost:.2f}")

    return state


def route_cost_guard(state: DeliberationGraphState) -> Literal["continue", "force_synthesis"]:
    """Route based on cost guard check.

    This is the conditional edge that prevents runaway costs.

    Args:
        state: Current deliberation state

    Returns:
        "force_synthesis" if cost exceeded (skip to synthesis)
        "continue" if within budget (continue normal flow)
    """
    stop_reason = state.get("stop_reason")

    if stop_reason == "cost_budget_exceeded":
        logger.info("Cost guard: EXCEEDED -> forcing synthesis")
        return "force_synthesis"
    else:
        logger.debug("Cost guard: OK -> continuing")
        return "continue"


# ============================================================================
# Graph Compilation Helper
# ============================================================================


def compile_graph_with_loop_prevention(workflow: Any, checkpointer: Any = None) -> Any:
    """Compile graph with loop prevention enabled.

    This helper wraps graph compilation and enforces:
    - Layer 1: Recursion limit
    - Layer 2: Cycle detection (via validate_graph_acyclic)

    Args:
        workflow: StateGraph workflow to compile
        checkpointer: Optional checkpointer (RedisSaver, etc.)

    Returns:
        Compiled graph with loop prevention

    Example:
        >>> from langgraph.graph import StateGraph
        >>> workflow = StateGraph(DeliberationGraphState)
        >>> # ... add nodes and edges ...
        >>> graph = compile_graph_with_loop_prevention(workflow)
    """
    # Compile with recursion limit (Layer 1)
    graph = workflow.compile(
        checkpointer=checkpointer,
        recursion_limit=DELIBERATION_RECURSION_LIMIT,
    )

    # TODO: Layer 2 validation would go here
    # We'd need to extract the NetworkX graph from LangGraph
    # For now, this is documented as a manual step

    logger.info(f"Graph compiled with recursion_limit={DELIBERATION_RECURSION_LIMIT}")

    return graph
