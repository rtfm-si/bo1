"""Stopping rules evaluator for deliberation quality control.

AUDIT FIX (Priority 4.3): Extracted from loop_prevention.py check_convergence_node.
This module provides focused, testable stopping rule evaluation.

Evaluates:
- Hard caps (round limits)
- Convergence thresholds
- Early exit conditions
- Deadlock detection
- Multi-criteria quality thresholds
"""

import logging
from dataclasses import dataclass
from typing import Any

from bo1.graph.state import DeliberationGraphState

logger = logging.getLogger(__name__)

# Constants from loop_prevention.py
CONVERGENCE_THRESHOLD = 0.90  # Increased from 0.85 (Issue #3 fix)
MIN_PARTICIPATION_RATE = 0.60  # 60% of personas must contribute in recent rounds
MIN_NOVELTY_THRESHOLD = 0.15  # If novelty < 0.15, ideas are repeating
HARD_CAP_ROUNDS = 6  # Parallel architecture: 3-5 experts per round = 18-30 total contributions


@dataclass
class StoppingDecision:
    """Result of stopping rules evaluation.

    AUDIT FIX (Priority 4.3): Standardized decision format.
    """

    should_stop: bool
    stop_reason: str | None = None
    facilitator_guidance: dict[str, Any] | None = None


class StoppingRulesEvaluator:
    """Evaluates stopping rules for deliberation.

    AUDIT FIX (Priority 4.3): Extracted from check_convergence_node monolith.
    Each stopping condition is isolated for testability and maintainability.
    """

    def evaluate(
        self,
        state: DeliberationGraphState,
    ) -> StoppingDecision:
        """Evaluate all stopping rules and return decision.

        Args:
            state: Current deliberation state

        Returns:
            StoppingDecision with should_stop flag and reasoning
        """
        round_number = state.get("round_number", 1)
        max_rounds = state.get("max_rounds", 10)

        # Check 1: Hard cap (absolute maximum rounds)
        hard_cap_result = self.check_hard_cap(round_number)
        if hard_cap_result:
            return hard_cap_result

        # Check 2: User-configured max rounds
        max_rounds_result = self.check_max_rounds(round_number, max_rounds)
        if max_rounds_result:
            return max_rounds_result

        # Check 3: Early exit (high convergence + low novelty)
        early_exit_result = self.check_early_exit(state)
        if early_exit_result:
            return early_exit_result

        # Check 4: Deadlock detection
        deadlock_result = self.check_deadlock(state)
        if deadlock_result:
            return deadlock_result

        # Check 5: Stalled disagreement (high conflict + low novelty)
        stalled_result = self.check_stalled_disagreement(state)
        if stalled_result:
            return stalled_result

        # Check 6: Convergence threshold
        convergence_result = self.check_convergence_threshold(state)
        if convergence_result:
            return convergence_result

        # Check 7: Multi-criteria quality thresholds (if enough contributions)
        contributions = state.get("contributions", [])
        if len(contributions) >= 3:
            quality_result = self.check_quality_thresholds(state)
            if quality_result:
                return quality_result

        # No stopping condition met - continue deliberation
        return StoppingDecision(should_stop=False)

    def check_hard_cap(self, round_number: int) -> StoppingDecision | None:
        """Check if hard cap on rounds has been reached.

        Args:
            round_number: Current round number

        Returns:
            StoppingDecision if hard cap reached, None otherwise
        """
        if round_number >= HARD_CAP_ROUNDS:
            logger.warning(
                f"Round {round_number}: Hit absolute hard cap ({HARD_CAP_ROUNDS} rounds) "
                f"for parallel architecture"
            )
            return StoppingDecision(
                should_stop=True,
                stop_reason=f"hard_cap_{HARD_CAP_ROUNDS}_rounds",
            )
        return None

    def check_max_rounds(self, round_number: int, max_rounds: int) -> StoppingDecision | None:
        """Check if user-configured max rounds has been reached.

        Args:
            round_number: Current round number
            max_rounds: User-configured maximum rounds

        Returns:
            StoppingDecision if max rounds reached, None otherwise
        """
        if round_number >= max_rounds:
            logger.info(f"Round {round_number}: Hit max_rounds limit ({max_rounds})")
            return StoppingDecision(
                should_stop=True,
                stop_reason="max_rounds",
            )
        return None

    def check_early_exit(self, state: DeliberationGraphState) -> StoppingDecision | None:
        """Check if early exit conditions are met (high convergence + low novelty).

        Args:
            state: Current deliberation state

        Returns:
            StoppingDecision if early exit warranted, None otherwise
        """
        if should_exit_early(state):
            round_number = state.get("round_number", 1)
            metrics = state.get("metrics")
            convergence = metrics.convergence_score if metrics else 0.0
            novelty = metrics.novelty_score if metrics else 0.5

            logger.info(
                f"Round {round_number}: Early exit triggered "
                f"(convergence={convergence:.2f}, novelty={novelty:.2f})"
            )
            return StoppingDecision(
                should_stop=True,
                stop_reason="early_convergence",
            )
        return None

    def check_deadlock(self, state: DeliberationGraphState) -> StoppingDecision | None:
        """Check if deadlock has been detected (circular arguments).

        Args:
            state: Current deliberation state

        Returns:
            StoppingDecision if deadlock detected, None otherwise
        """
        deadlock_info = detect_deadlock(state)
        if deadlock_info["deadlock"]:
            round_number = state.get("round_number", 1)
            deadlock_type = deadlock_info["type"]
            resolution = deadlock_info["resolution"]

            logger.warning(
                f"Round {round_number}: Deadlock detected (type={deadlock_type}) - {resolution}"
            )

            if resolution == "force_voting":
                # Skip remaining rounds, go straight to voting
                return StoppingDecision(
                    should_stop=True,
                    stop_reason="deadlock_detected",
                )
            elif resolution == "facilitator_intervention":
                # Continue but with special facilitator guidance
                return StoppingDecision(
                    should_stop=False,
                    facilitator_guidance={
                        "type": "deadlock_intervention",
                        "issue": "Circular argument pattern detected among experts",
                        "action": "Call on different experts or ask for new perspectives",
                    },
                )
        return None

    def check_stalled_disagreement(self, state: DeliberationGraphState) -> StoppingDecision | None:
        """Check for stalled disagreement (high conflict + low novelty for 2+ rounds).

        Stalled disagreement indicates experts are stuck in an impasse:
        - High conflict (>0.70): Strong disagreement persists
        - Low novelty (<0.40): Same arguments being repeated

        Args:
            state: Current deliberation state

        Returns:
            StoppingDecision if stalled, None otherwise
        """
        stalled_info = detect_stalled_disagreement(state)

        if not stalled_info["stalled"]:
            return None

        round_number = state.get("round_number", 1)
        rounds_stuck = stalled_info["rounds_stuck"]
        resolution = stalled_info["resolution"]

        if resolution == "force_synthesis":
            # Stuck for 3+ rounds - force early synthesis
            logger.warning(
                f"Round {round_number}: Stalled disagreement for {rounds_stuck} rounds - "
                f"forcing early synthesis"
            )
            return StoppingDecision(
                should_stop=True,
                stop_reason="stalled_disagreement",
            )
        elif resolution == "guidance":
            # Stuck for 2+ rounds - provide impasse guidance to facilitator
            logger.info(
                f"Round {round_number}: Stalled disagreement detected ({rounds_stuck} rounds) - "
                f"providing impasse guidance"
            )
            return StoppingDecision(
                should_stop=False,
                facilitator_guidance={
                    "type": "impasse_intervention",
                    "issue": f"Experts stuck in disagreement for {rounds_stuck} rounds "
                    f"(high conflict, low novelty)",
                    "conflict_score": stalled_info.get("conflict_score", 0.0),
                    "novelty_score": stalled_info.get("novelty_score", 0.0),
                    "resolution_options": [
                        "Find common ground on shared facts and goals",
                        "Disagree-and-commit: acknowledge disagreement, recommend majority view",
                        "Propose conditional recommendations (if X then A, if Y then B)",
                    ],
                    "action": "Guide experts toward resolution using one of the above strategies",
                },
            )

        return None

    def check_convergence_threshold(self, state: DeliberationGraphState) -> StoppingDecision | None:
        """Check if convergence threshold has been met with diversity safeguards.

        Args:
            state: Current deliberation state

        Returns:
            StoppingDecision if convergence threshold met, None otherwise
        """
        metrics = state.get("metrics")
        if not metrics:
            return None

        round_number = state.get("round_number", 1)
        convergence_score = metrics.convergence_score if metrics.convergence_score else 0.0
        novelty = metrics.novelty_score if metrics.novelty_score else 0.5

        # Check if convergence threshold is met
        if convergence_score > CONVERGENCE_THRESHOLD and round_number >= 3:
            # Diversity safeguards before stopping

            # Check 1: Recent participation rate
            recent_contributors = _get_recent_contributors(state, last_n_rounds=2)
            personas = state.get("personas", [])
            all_personas = {
                p.code if hasattr(p, "code") else p["code"]  # type: ignore[index]
                for p in personas
            }
            participation_rate = len(recent_contributors) / len(all_personas) if all_personas else 0

            if participation_rate < MIN_PARTICIPATION_RATE:
                logger.info(
                    f"Round {round_number}: Convergence high ({convergence_score:.2f}) but low "
                    f"participation ({participation_rate:.0%} < {MIN_PARTICIPATION_RATE:.0%}) - continuing"
                )
                return StoppingDecision(should_stop=False)

            # Check 2: Novelty trend
            if novelty > MIN_NOVELTY_THRESHOLD:
                logger.info(
                    f"Round {round_number}: Convergence high ({convergence_score:.2f}) but novelty "
                    f"still present ({novelty:.2f} > {MIN_NOVELTY_THRESHOLD:.2f}) - continuing"
                )
                return StoppingDecision(should_stop=False)

            # Both checks passed - safe to stop
            logger.info(
                f"Round {round_number}: Convergence detected "
                f"(score: {convergence_score:.2f}, threshold: {CONVERGENCE_THRESHOLD:.2f}, "
                f"participation: {participation_rate:.0%}, novelty: {novelty:.2f})"
            )
            return StoppingDecision(
                should_stop=True,
                stop_reason="consensus",
            )
        else:
            logger.debug(
                f"Round {round_number}: Convergence score {convergence_score:.2f} "
                f"(threshold: {CONVERGENCE_THRESHOLD:.2f}, min rounds: 3)"
            )

        return None

    def check_quality_thresholds(self, state: DeliberationGraphState) -> StoppingDecision | None:
        """Check multi-criteria quality thresholds (exploration, focus, completeness).

        Args:
            state: Current deliberation state

        Returns:
            StoppingDecision if quality thresholds indicate stopping, None otherwise
        """
        from bo1.graph.meeting_config import get_meeting_config

        round_number = state.get("round_number", 1)
        metrics = state.get("metrics")
        if not metrics:
            return None

        # Get meeting config (tactical vs strategic thresholds)
        config = get_meeting_config(dict(state))

        # Apply multi-criteria stopping rules
        can_end, blockers = should_allow_end(state, config)
        should_recommend, rationale = should_recommend_end(state, config)
        should_target, focus_prompts = should_continue_targeted(state, config)

        if not can_end:
            # Cannot end yet - guardrails violated
            logger.info(f"Round {round_number}: Cannot end yet - Blockers: {blockers}")
            return StoppingDecision(
                should_stop=False,
                facilitator_guidance={
                    "type": "must_continue",
                    "blockers": blockers,
                    "focus_prompts": focus_prompts[:3] if focus_prompts else [],
                },
            )

        if should_recommend:
            # High quality threshold met - recommend ending
            meeting_completeness = metrics.meeting_completeness_index or 0.0
            exploration_score = metrics.exploration_score or 0.0
            convergence_score = metrics.convergence_score or 0.0

            logger.info(
                f"Round {round_number}: Recommend ending - Meeting quality high "
                f"(completeness={meeting_completeness:.2f}, exploration={exploration_score:.2f}, "
                f"convergence={convergence_score:.2f})"
            )
            return StoppingDecision(
                should_stop=True,
                stop_reason="quality_threshold_met",
            )

        if should_target:
            # Continue with targeted exploration
            exploration_score = metrics.exploration_score or 0.0
            aspect_coverage = metrics.aspect_coverage or []

            logger.info(
                f"Round {round_number}: Continuing with targeted focus - "
                f"Missing aspects or low exploration (E={exploration_score:.2f})"
            )
            return StoppingDecision(
                should_stop=False,
                facilitator_guidance={
                    "type": "targeted_exploration",
                    "focus_prompts": focus_prompts[:3] if focus_prompts else [],
                    "missing_aspects": [
                        a.name for a in aspect_coverage if a.level in ["none", "shallow"]
                    ],
                },
            )

        return None


# ============================================================================
# Stopping Rule Helper Functions (Moved from loop_prevention.py)
# ============================================================================


def should_exit_early(state: DeliberationGraphState) -> bool:
    """Check if we can safely exit before max rounds.

    AUDIT FIX (Priority 4.3): Moved from loop_prevention.py to stopping_rules.py.
    This is a stopping rule evaluation, not loop prevention logic.

    Research finding from CONSENSUS_BUILDING_RESEARCH.md:
    - If convergence > 0.85 AND novelty < 0.30 for 2+ rounds → safe to exit
    - ~0.5% of discussions benefit from extended debate past convergence
    - Enables 20-30% reduction in average deliberation time

    Cost savings:
    - Expected 33-50% reduction in persona calls for converged discussions
    - Typical session: 5 personas × 5 rounds = 25 calls → early exit at round 3 = 15 calls
    - Savings tracked via bo1_early_exit_total Prometheus counter

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
        # Track early exit for cost savings analysis
        try:
            from backend.api.middleware.metrics import record_early_exit

            record_early_exit(reason="convergence_high")
        except ImportError:
            pass  # Metrics not available in test environment
        return True

    return False


def detect_deadlock(state: DeliberationGraphState) -> dict[str, Any]:
    """Detect if deliberation is stuck in deadlock (Issue #14 - Deadlock detection).

    AUDIT FIX (Priority 4.3): Moved from loop_prevention.py to stopping_rules.py.
    This is a stopping condition detection, not loop prevention logic.

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

    AUDIT FIX (Priority 4.3): Moved from loop_prevention.py to stopping_rules.py.
    This is a helper for participation rate check in stopping rules.

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


def should_allow_end(state: DeliberationGraphState, config: Any) -> tuple[bool, list[str]]:
    """Check if deliberation is ALLOWED to end (guardrails).

    AUDIT FIX (Priority 4.3): Moved from loop_prevention.py to stopping_rules.py.
    This is a stopping rule, not loop prevention logic.

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

    AUDIT FIX (Priority 4.3): Moved from loop_prevention.py to stopping_rules.py.
    This is a stopping rule, not loop prevention logic.

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

    AUDIT FIX (Priority 4.3): Moved from loop_prevention.py to stopping_rules.py.
    This is a stopping rule guidance, not loop prevention logic.

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


# ============================================================================
# Stalled Disagreement Detection (Productive Disagreement fix)
# ============================================================================

# Thresholds for stalled disagreement
STALLED_CONFLICT_THRESHOLD = 0.70  # High conflict level
STALLED_NOVELTY_THRESHOLD = 0.40  # Low novelty (repeating arguments)
STALLED_ROUNDS_FOR_GUIDANCE = 2  # Rounds before providing impasse guidance
STALLED_ROUNDS_FOR_SYNTHESIS = 3  # Rounds before forcing early synthesis


def detect_stalled_disagreement(state: DeliberationGraphState) -> dict[str, Any]:
    """Detect if deliberation is stuck in stalled disagreement.

    Stalled disagreement occurs when:
    - conflict_score > 0.70 (high disagreement)
    - novelty_score < 0.40 (experts repeating same arguments)
    - This pattern persists for 2+ consecutive rounds

    Args:
        state: Current deliberation state

    Returns:
        Dict with stalled disagreement info:
        - stalled: bool (True if stalled disagreement detected)
        - rounds_stuck: int (number of consecutive rounds in this state)
        - resolution: str (recommended action: "guidance" or "force_synthesis")

    Example:
        >>> stalled_info = detect_stalled_disagreement(state)
        >>> if stalled_info["stalled"]:
        ...     print(f"Impasse detected: {stalled_info['rounds_stuck']} rounds")
    """
    metrics = state.get("metrics")
    if not metrics:
        return {"stalled": False, "rounds_stuck": 0, "resolution": None}

    conflict_score = metrics.conflict_score if metrics.conflict_score is not None else 0.0
    novelty_score = metrics.novelty_score if metrics.novelty_score is not None else 0.5

    # Get current counter from state
    rounds_stuck = state.get("high_conflict_low_novelty_rounds", 0)

    # Check if current round meets stalled criteria
    is_stalled_pattern = (
        conflict_score > STALLED_CONFLICT_THRESHOLD and novelty_score < STALLED_NOVELTY_THRESHOLD
    )

    if not is_stalled_pattern:
        # Pattern broken - not stalled
        return {"stalled": False, "rounds_stuck": 0, "resolution": None}

    # Pattern detected - check how many rounds we've been stuck
    if rounds_stuck >= STALLED_ROUNDS_FOR_SYNTHESIS:
        # Stuck for 3+ rounds - force early synthesis
        logger.warning(
            f"[STALLED_DISAGREEMENT] {rounds_stuck} consecutive rounds with "
            f"conflict={conflict_score:.2f} > {STALLED_CONFLICT_THRESHOLD}, "
            f"novelty={novelty_score:.2f} < {STALLED_NOVELTY_THRESHOLD} - forcing synthesis"
        )
        return {
            "stalled": True,
            "rounds_stuck": rounds_stuck,
            "resolution": "force_synthesis",
            "conflict_score": conflict_score,
            "novelty_score": novelty_score,
        }
    elif rounds_stuck >= STALLED_ROUNDS_FOR_GUIDANCE:
        # Stuck for 2+ rounds - provide impasse guidance
        logger.info(
            f"[STALLED_DISAGREEMENT] {rounds_stuck} consecutive rounds with "
            f"conflict={conflict_score:.2f} > {STALLED_CONFLICT_THRESHOLD}, "
            f"novelty={novelty_score:.2f} < {STALLED_NOVELTY_THRESHOLD} - providing guidance"
        )
        return {
            "stalled": True,
            "rounds_stuck": rounds_stuck,
            "resolution": "guidance",
            "conflict_score": conflict_score,
            "novelty_score": novelty_score,
        }

    # Pattern detected but not enough rounds yet - just tracking
    return {
        "stalled": False,
        "rounds_stuck": rounds_stuck,
        "resolution": None,
        "conflict_score": conflict_score,
        "novelty_score": novelty_score,
    }


def update_stalled_disagreement_counter(state: DeliberationGraphState) -> int:
    """Update the stalled disagreement counter based on current metrics.

    Call this at the end of each round to track consecutive stalled rounds.

    Args:
        state: Current deliberation state

    Returns:
        Updated counter value (to be stored in state)
    """
    metrics = state.get("metrics")
    if not metrics:
        return 0

    conflict_score = metrics.conflict_score if metrics.conflict_score is not None else 0.0
    novelty_score = metrics.novelty_score if metrics.novelty_score is not None else 0.5

    current_count = state.get("high_conflict_low_novelty_rounds", 0)

    # Check if current round meets stalled criteria
    is_stalled_pattern = (
        conflict_score > STALLED_CONFLICT_THRESHOLD and novelty_score < STALLED_NOVELTY_THRESHOLD
    )

    if is_stalled_pattern:
        # Increment counter
        new_count = current_count + 1
        logger.debug(
            f"[STALLED_COUNTER] Incrementing: {current_count} -> {new_count} "
            f"(conflict={conflict_score:.2f}, novelty={novelty_score:.2f})"
        )
        return new_count
    else:
        # Reset counter - pattern broken
        if current_count > 0:
            logger.debug(
                f"[STALLED_COUNTER] Resetting: {current_count} -> 0 "
                f"(conflict={conflict_score:.2f}, novelty={novelty_score:.2f})"
            )
        return 0
