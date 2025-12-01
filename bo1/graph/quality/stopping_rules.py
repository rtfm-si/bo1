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

        # Check 5: Convergence threshold
        convergence_result = self.check_convergence_threshold(state)
        if convergence_result:
            return convergence_result

        # Check 6: Multi-criteria quality thresholds (if enough contributions)
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
        from bo1.graph.safety.loop_prevention import should_exit_early

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
        from bo1.graph.safety.loop_prevention import detect_deadlock

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
            from bo1.graph.safety.loop_prevention import _get_recent_contributors

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
        from bo1.graph.safety.loop_prevention import (
            should_allow_end,
            should_continue_targeted,
            should_recommend_end,
        )

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
