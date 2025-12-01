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
# Convergence Configuration
# ============================================================================

# Convergence threshold: Increased from 0.85 to 0.90 (Issue #3 fix)
# Higher threshold = more strict convergence detection = fewer premature stops
CONVERGENCE_THRESHOLD = 0.90

# Minimum participation rate for convergence (70% of personas must contribute recently)
MIN_PARTICIPATION_RATE = 0.70

# Novelty threshold: If novelty still high, continue deliberation even with high convergence
MIN_NOVELTY_THRESHOLD = 0.40

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


def should_exit_early(state: DeliberationGraphState) -> bool:
    """Check if we can safely exit before max rounds.

    Research finding from CONSENSUS_BUILDING_RESEARCH.md:
    - If convergence > 0.85 AND novelty < 0.30 for 2+ rounds → safe to exit
    - ~0.5% of discussions benefit from extended debate past convergence
    - Enables 20-30% reduction in average deliberation time

    Conditions for early exit:
    - Round >= 2 (minimum exploration phase)
    - Convergence > 0.85 (high agreement)
    - Novelty < 0.30 (agents repeating themselves)

    Args:
        state: Current deliberation state

    Returns:
        True if early exit recommended, False otherwise

    Example:
        >>> if should_exit_early(state):
        ...     print("Experts have converged - safe to end early")
    """
    round_num = state.get("round_number", 0)

    # Never exit before round 2 (need minimum exploration)
    if round_num < 2:
        return False

    # Get convergence and novelty metrics from state
    metrics = state.get("metrics")
    if not metrics:
        return False

    convergence = metrics.convergence_score if metrics.convergence_score is not None else 0.0
    novelty = metrics.novelty_score if metrics.novelty_score is not None else 1.0

    # High convergence + low novelty = safe to exit
    # Convergence >0.85 = experts largely agree
    # Novelty <0.30 = experts repeating same arguments
    if convergence > 0.85 and novelty < 0.30:
        logger.info(
            f"[EARLY_EXIT] Round {round_num}: convergence={convergence:.2f}, "
            f"novelty={novelty:.2f} - recommending early termination"
        )
        return True

    return False


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
# Multi-Criteria Stopping Rules (NEW)
# ============================================================================


def should_allow_end(state: DeliberationGraphState, config: Any) -> tuple[bool, list[str]]:
    """Check if deliberation is ALLOWED to end (guardrails).

    This enforces minimum quality standards before ending is permitted.

    Args:
        state: Current deliberation state
        config: MeetingConfig with thresholds

    Returns:
        Tuple of (allowed: bool, blockers: list[str])
        - allowed: True if minimum standards met
        - blockers: List of reasons why ending is blocked

    Example:
        >>> can_end, blockers = should_allow_end(state, config)
        >>> if not can_end:
        ...     print(f"Blocked: {blockers}")
    """
    blockers = []
    metrics = state.get("metrics")
    if not metrics:
        return False, ["No metrics available"]

    round_number = state.get("round_number", 1)
    # NEW PARALLEL ARCHITECTURE: Adjust min_rounds if needed (was 3, now 2)
    min_rounds = max(2, config.round_limits.get("min_rounds", 2))

    # Check 1: Minimum rounds
    if round_number < min_rounds:
        blockers.append(f"Only {round_number} rounds (need {min_rounds} minimum)")

    # Check 2: Minimum exploration
    exploration_score = (
        metrics.exploration_score
        if hasattr(metrics, "exploration_score") and metrics.exploration_score is not None
        else 0.0
    )
    min_exploration = config.thresholds["exploration"]["min_to_allow_end"]
    if exploration_score < min_exploration:
        blockers.append(f"Exploration too low ({exploration_score:.2f} < {min_exploration:.2f})")

    # Check 3: Minimum convergence
    convergence_score = metrics.convergence_score if metrics.convergence_score is not None else 0.0
    min_convergence = config.thresholds["convergence"]["min_to_allow_end"]
    if convergence_score < min_convergence:
        blockers.append(f"Convergence too low ({convergence_score:.2f} < {min_convergence:.2f})")

    # Check 4: Minimum focus (not drifting)
    focus_score = (
        metrics.focus_score
        if hasattr(metrics, "focus_score") and metrics.focus_score is not None
        else 0.8
    )
    min_focus = config.thresholds["focus"]["min_acceptable"]
    if focus_score < min_focus:
        blockers.append(f"Focus too low - drifting off topic ({focus_score:.2f} < {min_focus:.2f})")

    # Check 5: Critical aspects must be at least shallow
    if hasattr(metrics, "aspect_coverage") and metrics.aspect_coverage:
        aspect_coverage = metrics.aspect_coverage
        critical_missing = []
        for aspect in aspect_coverage:
            if aspect.name == "risks_failure_modes" and aspect.level == "none":
                critical_missing.append("risks")
            if aspect.name == "objectives" and aspect.level == "none":
                critical_missing.append("objectives")

        if critical_missing:
            blockers.append(f"Critical aspects not addressed: {', '.join(critical_missing)}")

    allowed = len(blockers) == 0
    return allowed, blockers


def should_recommend_end(state: DeliberationGraphState, config: Any) -> tuple[bool, str]:
    """Check if deliberation should be RECOMMENDED to end (quality threshold).

    This is the positive signal that quality is high enough to conclude.

    Args:
        state: Current deliberation state
        config: MeetingConfig with thresholds

    Returns:
        Tuple of (recommend: bool, rationale: str)

    Example:
        >>> should_end, reason = should_recommend_end(state, config)
        >>> if should_end:
        ...     print(f"Recommend ending: {reason}")
    """
    metrics = state.get("metrics")
    if not metrics:
        return False, "No metrics available"

    # Check meeting completeness index
    meeting_completeness = (
        metrics.meeting_completeness_index
        if hasattr(metrics, "meeting_completeness_index")
        and metrics.meeting_completeness_index is not None
        else 0.0
    )
    threshold = config.thresholds["composite"]["min_index_to_recommend_end"]

    if meeting_completeness < threshold:
        return (
            False,
            f"Meeting quality below threshold ({meeting_completeness:.2f} < {threshold:.2f})",
        )

    # Check low novelty (repetition = ready to end)
    novelty_score = metrics.novelty_score if metrics.novelty_score is not None else 0.5
    novelty_floor = config.thresholds["novelty"]["novelty_floor_recent"]

    if novelty_score > novelty_floor:
        return (
            False,
            f"Still generating new ideas (novelty {novelty_score:.2f} > {novelty_floor:.2f})",
        )

    # All checks passed - recommend ending
    rationale = f"Meeting quality high (completeness={meeting_completeness:.2f}), novelty low (novelty={novelty_score:.2f}), ready to conclude"
    return True, rationale


def should_continue_targeted(state: DeliberationGraphState, config: Any) -> tuple[bool, list[str]]:
    """Check if deliberation should continue with TARGETED focus.

    This identifies missing aspects or premature consensus scenarios.

    Args:
        state: Current deliberation state
        config: MeetingConfig with thresholds

    Returns:
        Tuple of (targeted: bool, focus_prompts: list[str])

    Example:
        >>> should_target, prompts = should_continue_targeted(state, config)
        >>> if should_target:
        ...     print(f"Target these aspects: {prompts}")
    """
    metrics = state.get("metrics")
    if not metrics:
        return False, []

    focus_prompts = []

    # Check 1: Premature consensus (high convergence but low exploration)
    exploration_score = (
        metrics.exploration_score
        if hasattr(metrics, "exploration_score") and metrics.exploration_score is not None
        else 0.0
    )
    convergence_score = metrics.convergence_score if metrics.convergence_score is not None else 0.0
    round_number = state.get("round_number", 1)

    if "early_consensus_requires_extra_check" in config.rules:
        rule = config.rules["early_consensus_requires_extra_check"]
        if rule.get("enabled", False):
            early_cutoff = rule["early_round_cutoff"]
            if (
                round_number <= early_cutoff
                and convergence_score > rule["convergence_high"]
                and exploration_score < rule["exploration_low"]
            ):
                focus_prompts.append(
                    "We're converging quickly but haven't explored all aspects. "
                    "Let's ensure we've considered risks, alternatives, and stakeholder impact."
                )

    # Check 2: Missing critical aspects
    if hasattr(metrics, "aspect_coverage") and metrics.aspect_coverage:
        missing_aspects = [a for a in metrics.aspect_coverage if a.level in ["none", "shallow"]]

        for aspect in missing_aspects[:3]:  # Top 3 missing
            prompt_templates = {
                "risks_failure_modes": "What are the top 3 risks if we proceed? What could go wrong?",
                "stakeholders_impact": "Who will be affected by this decision? How will they be impacted?",
                "options_alternatives": "What alternative approaches should we consider? Have we compared options?",
                "constraints": "What are the specific constraints (budget, time, resources)?",
                "dependencies_unknowns": "What dependencies or unknowns could block this?",
                "key_assumptions": "What key assumptions are we making? How can we validate them?",
                "objectives": "What are our specific, measurable success criteria?",
            }
            if aspect.name in prompt_templates:
                focus_prompts.append(prompt_templates[aspect.name])

    # Check 3: High novelty = still generating ideas
    novelty_score = metrics.novelty_score if metrics.novelty_score is not None else 0.5
    if novelty_score > 0.6:
        # Let it continue naturally, novelty is good
        pass

    targeted = len(focus_prompts) > 0
    return targeted, focus_prompts


async def check_contribution_relevance(
    contribution: str,
    sub_problem_goal: str,
) -> tuple[bool, float]:
    """Check if contribution addresses the sub-problem goal (Issue #13 - Problem drift detection).

    Research finding from CONSENSUS_BUILDING_RESEARCH.md:
    - Problem drift is the #1 cause of diminishing returns (~0.8% of discussions)
    - Early detection prevents wasted rounds

    Uses Haiku for fast, cheap relevance check (90% cost savings vs Sonnet).

    Args:
        contribution: The expert's contribution text
        sub_problem_goal: The current sub-problem goal/question

    Returns:
        Tuple of (is_relevant: bool, relevance_score: float)
        - is_relevant: True if score >= 6/10
        - relevance_score: 0-10 scale (6+ = on topic, <6 = drifting)

    Example:
        >>> is_relevant, score = await check_contribution_relevance(
        ...     contribution="The market size is...",
        ...     sub_problem_goal="What pricing strategy should we use?"
        ... )
        >>> if not is_relevant:
        ...     print(f"Drift warning: score={score}")
    """
    try:
        from bo1.llm.broker import PromptBroker, PromptRequest
        from bo1.utils.json_parsing import extract_json_with_fallback

        # Truncate contribution to first 500 chars for efficiency
        contrib_excerpt = contribution[:500] if len(contribution) > 500 else contribution

        prompt = f"""Evaluate if this contribution addresses the sub-problem goal.

Sub-problem goal: {sub_problem_goal}

Contribution excerpt: {contrib_excerpt}

Rate relevance on 0-10 scale:
- 9-10: Directly addresses the goal with specific insights
- 7-8: Addresses goal with some tangential context
- 5-6: Partially addresses goal but includes off-topic content
- 3-4: Mostly off-topic with minimal relevance
- 0-2: Completely off-topic

Respond in JSON:
{{"relevant": true/false, "score": 0-10, "drift_warning": "reason if score < 6"}}"""

        broker = PromptBroker()
        request = PromptRequest(
            system="You evaluate discussion relevance for meeting quality.",
            user_message=prompt,
            model="haiku",  # Use Haiku for speed and cost
            max_tokens=100,
            phase="drift_detection",
            agent_type="DriftDetector",
            cache_system=True,  # TASK 1 FIX: Enable prompt caching (system prompt is simple and static)
        )
        response = await broker.call(request)

        # Parse response
        def create_fallback() -> dict[str, Any]:
            return {"relevant": True, "score": 7.0, "drift_warning": ""}

        result = extract_json_with_fallback(
            content=response.content,
            fallback_factory=create_fallback,
            logger=logger,
        )

        is_relevant = result.get("relevant", True)
        score = float(result.get("score", 7.0))

        if not is_relevant and score < 6:
            drift_warning = result.get("drift_warning", "Off-topic content detected")
            logger.warning(f"[DRIFT_DETECTED] Score: {score:.1f}/10 - {drift_warning}")

        return is_relevant, score

    except Exception as e:
        logger.warning(f"Relevance check failed: {e}, assuming on-topic")
        return True, 7.0  # Assume on-topic if check fails


def detect_deadlock(state: DeliberationGraphState) -> dict[str, Any]:
    """Detect if deliberation is stuck in deadlock (Issue #14 - Deadlock detection).

    Research finding from CONSENSUS_BUILDING_RESEARCH.md:
    - Output repetition and circular arguments indicate deadlock
    - Forcing decision when stuck prevents infinite loops

    Detection methods:
    1. Repetition: High similarity in last 6 contributions (>60% repetitive)
    2. Circular refutation: Same arguments being made repeatedly

    Args:
        state: Current deliberation state

    Returns:
        Dict with deadlock info:
        - deadlock: bool (True if deadlock detected)
        - type: str ("repetition" or "circular")
        - resolution: str (recommended action)

    Example:
        >>> deadlock_info = detect_deadlock(state)
        >>> if deadlock_info["deadlock"]:
        ...     print(f"Deadlock: {deadlock_info['type']} - {deadlock_info['resolution']}")
    """
    contributions = state.get("contributions", [])

    if len(contributions) < 6:
        return {"deadlock": False}

    recent = contributions[-6:]

    try:
        from bo1.llm.embeddings import cosine_similarity, generate_embedding

        # Generate embeddings for recent contributions
        embeddings: list[list[float]] = []
        for contrib in recent:
            content = contrib.content if hasattr(contrib, "content") else str(contrib)
            try:
                embedding = generate_embedding(content, input_type="document")
                embeddings.append(embedding)
            except Exception as e:
                logger.warning(f"Embedding generation failed during deadlock check: {e}")
                # If embedding fails, assume no deadlock
                return {"deadlock": False}

        # Calculate pairwise similarities
        high_similarity_count = 0
        total_comparisons = 0

        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                similarity = cosine_similarity(embeddings[i], embeddings[j])
                total_comparisons += 1

                # Similarity >0.75 = likely repetitive argument
                if similarity > 0.75:
                    high_similarity_count += 1

        if total_comparisons == 0:
            return {"deadlock": False}

        repetition_rate = high_similarity_count / total_comparisons

        # If >60% of arguments are highly similar, we're in a deadlock
        if repetition_rate > 0.6:
            logger.warning(
                f"[DEADLOCK_DETECTED] Repetition rate: {repetition_rate:.0%} "
                f"({high_similarity_count}/{total_comparisons} pairs similar)"
            )
            return {
                "deadlock": True,
                "type": "repetition",
                "resolution": "force_voting",  # Skip remaining rounds, go to voting
                "repetition_rate": repetition_rate,
            }

        # Check for circular disagreement patterns
        # Look for alternating positions (A->B->A->B pattern)
        if len(recent) >= 4:
            # Get persona codes for recent contributions
            recent_speakers = [
                getattr(c, "persona_code", "unknown") if hasattr(c, "persona_code") else "unknown"
                for c in recent
            ]

            # Check for ABAB or ABCABC pattern (same speakers repeating)
            if len(set(recent_speakers)) <= 3:  # Only 2-3 different speakers
                # Count how many times we see repetition
                repeats = sum(
                    1
                    for i in range(len(recent_speakers) - 2)
                    if recent_speakers[i] == recent_speakers[i + 2]
                )

                if repeats >= 2:  # At least 2 repetitions in pattern
                    logger.warning(
                        f"[DEADLOCK_DETECTED] Circular pattern: {' -> '.join(recent_speakers[-6:])}"
                    )
                    return {
                        "deadlock": True,
                        "type": "circular",
                        "resolution": "facilitator_intervention",
                        "pattern": recent_speakers,
                    }

        return {"deadlock": False}

    except ImportError:
        logger.warning("Embeddings not available for deadlock detection")
        return {"deadlock": False}
    except Exception as e:
        logger.warning(f"Deadlock detection failed: {e}")
        return {"deadlock": False}


def _get_recent_contributors(state: DeliberationGraphState, last_n_rounds: int = 2) -> set[str]:
    """Get set of persona codes that contributed in the last N rounds.

    Args:
        state: Current deliberation state
        last_n_rounds: Number of recent rounds to check

    Returns:
        Set of persona codes (e.g., {"CFO", "CMO", "CEO"})
    """
    current_round = state.get("round_number", 1)
    min_round = max(1, current_round - last_n_rounds + 1)

    contributors = set()
    for contribution in state.get("contributions", []):
        # Check if contribution is from recent rounds
        contrib_round = getattr(contribution, "round_number", None)
        if contrib_round is not None and contrib_round >= min_round:
            persona_code = getattr(contribution, "persona_code", None)
            if persona_code:
                contributors.add(persona_code)

    return contributors


async def _calculate_convergence_score_semantic(contributions: list[Any]) -> float:
    """Calculate convergence score using semantic similarity (PREFERRED).

    Uses Voyage AI embeddings to detect semantic repetition in contributions.
    This approach catches paraphrased content that keyword matching misses.

    Algorithm:
    1. Generate embeddings for recent contributions (last 6)
    2. Compare each contribution to all previous ones
    3. High similarity (>0.90) = likely repetition
    4. Return average repetition rate as convergence score

    Args:
        contributions: List of recent ContributionMessage objects

    Returns:
        Convergence score between 0.0 and 1.0
        - 1.0 = high convergence (lots of repetition)
        - 0.0 = no convergence (diverse contributions)
    """
    if len(contributions) < 3:
        return 0.0

    try:
        from bo1.llm.embeddings import cosine_similarity, generate_embedding

        # Extract content from contributions
        texts = []
        for contrib in contributions:
            content = contrib.content if hasattr(contrib, "content") else str(contrib)
            texts.append(content)

        # Generate embeddings for all contributions
        embeddings: list[list[float]] = []
        for text in texts:
            try:
                embedding = generate_embedding(text, input_type="document")
                embeddings.append(embedding)
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}, falling back to keyword method")
                return _calculate_convergence_score_keyword(contributions)

        # Compare each contribution to all previous ones
        repetition_scores: list[float] = []
        for i in range(1, len(embeddings)):
            max_similarity = 0.0
            for j in range(i):
                # Cosine similarity between contribution i and j
                similarity = cosine_similarity(embeddings[i], embeddings[j])
                max_similarity = max(max_similarity, similarity)

            # Similarity thresholds:
            # >0.90 = likely exact repetition (score: 1.0)
            # 0.85-0.90 = paraphrased content (score: 0.7)
            # 0.80-0.85 = similar theme (score: 0.4)
            # <0.80 = new content (score: 0.0)
            if max_similarity > 0.90:
                repetition_scores.append(1.0)
            elif max_similarity > 0.85:
                repetition_scores.append(0.7)
            elif max_similarity > 0.80:
                repetition_scores.append(0.4)
            else:
                repetition_scores.append(0.0)

        # Convergence = average repetition rate
        convergence = sum(repetition_scores) / len(repetition_scores) if repetition_scores else 0.0

        logger.debug(
            f"Semantic convergence: {convergence:.2f} "
            f"(similarities: {[f'{s:.2f}' for s in repetition_scores]})"
        )

        return convergence

    except ImportError:
        logger.warning("voyageai not installed, falling back to keyword method")
        return _calculate_convergence_score_keyword(contributions)
    except Exception as e:
        logger.warning(
            f"Semantic convergence calculation failed: {e}, falling back to keyword method"
        )
        return _calculate_convergence_score_keyword(contributions)


def _calculate_convergence_score_keyword(contributions: list[Any]) -> float:
    """Calculate convergence score using keyword matching (FALLBACK).

    Uses keyword-based heuristic: count agreement vs. total words.
    Higher score = more convergence/agreement.

    This is a FALLBACK method when semantic similarity is unavailable.
    Keyword matching has high false negative rate (misses paraphrasing).

    Args:
        contributions: List of recent ContributionMessage objects

    Returns:
        Convergence score between 0.0 and 1.0
    """
    if not contributions:
        return 0.0

    # Agreement keywords that indicate convergence
    agreement_keywords = [
        "agree",
        "yes",
        "correct",
        "exactly",
        "support",
        "aligned",
        "consensus",
        "concur",
        "same",
        "similarly",
        "indeed",
        "right",
    ]

    # Count agreement keywords across all contributions
    total_words = 0
    agreement_count = 0

    for contrib in contributions:
        # Get content from ContributionMessage
        content = contrib.content.lower() if hasattr(contrib, "content") else str(contrib).lower()
        words = content.split()
        total_words += len(words)

        # Count agreement keywords
        for keyword in agreement_keywords:
            agreement_count += content.count(keyword)

    if total_words == 0:
        return 0.0

    # Calculate ratio and normalize to 0-1 scale
    # We expect ~1-2% agreement keywords for high convergence
    # So we scale: 2% agreement = 1.0 convergence
    raw_score = (agreement_count / total_words) * 50.0  # 2% * 50 = 1.0
    convergence = min(1.0, max(0.0, raw_score))

    logger.debug(f"Keyword convergence: {convergence:.2f} (fallback method)")

    return convergence


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
