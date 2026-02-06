"""Contribution pruning for token optimization.

Extracted from state.py for maintainability.
Prunes old contributions to reduce token usage while preserving context.
"""

import logging
from typing import TYPE_CHECKING

from bo1.models.state import ContributionMessage

if TYPE_CHECKING:
    from bo1.graph.state import DeliberationGraphState

logger = logging.getLogger(__name__)


def prune_contributions_for_phase(
    state: "DeliberationGraphState",
    retain_count: int | None = None,
) -> list[ContributionMessage]:
    """Prune old contributions to reduce token usage.

    Called at synthesis node entry after convergence phase. Pruning is safe
    because synthesis uses round_summaries for context (not raw contributions).

    Pruning strategy:
    - Keep last `retain_count` contributions (default: 6 = ~2 rounds)
    - Preserve all contributions from the current round (by round_number)
    - Log pruned count for observability

    Safety:
    - Never prune if len(contributions) <= retain_count
    - Only prune if phase >= SYNTHESIS (post-convergence)

    Args:
        state: Current graph state
        retain_count: Number of contributions to retain (default: from config)

    Returns:
        Pruned contributions list (or original if no pruning needed)
    """
    from bo1.constants import ContributionPruning
    from bo1.models.state import DeliberationPhase

    if retain_count is None:
        retain_count = ContributionPruning.RETENTION_COUNT

    contributions = state.get("contributions", [])
    current_phase = state.get("phase")
    current_round = state.get("round_number", 0)
    session_id = state.get("session_id")

    # Safety: Don't prune if already small
    if len(contributions) <= retain_count:
        logger.debug(
            f"prune_contributions_for_phase: No pruning needed "
            f"(contributions={len(contributions)} <= retain_count={retain_count})"
        )
        return contributions

    # Safety: Only prune at synthesis phase or later
    if current_phase not in (DeliberationPhase.SYNTHESIS, DeliberationPhase.COMPLETE):
        logger.debug(
            f"prune_contributions_for_phase: Skipping pruning "
            f"(phase={current_phase}, expected SYNTHESIS or COMPLETE)"
        )
        return contributions

    # Preserve contributions from current round
    current_round_contributions = [c for c in contributions if c.round_number == current_round]
    other_contributions = [c for c in contributions if c.round_number != current_round]

    # Calculate how many non-current-round contributions to keep
    slots_for_others = max(0, retain_count - len(current_round_contributions))

    # Keep the most recent non-current-round contributions
    retained_others = other_contributions[-slots_for_others:] if slots_for_others > 0 else []

    # Combine: current round + retained others (in chronological order)
    pruned = retained_others + current_round_contributions

    pruned_count = len(contributions) - len(pruned)
    if pruned_count > 0:
        logger.info(
            f"prune_contributions_for_phase: session={session_id}, "
            f"pruned={pruned_count}, retained={len(pruned)} "
            f"(current_round={len(current_round_contributions)}, "
            f"previous={len(retained_others)})"
        )

    return pruned


def prune_contributions_after_round(
    contributions: list[ContributionMessage],
    round_summaries: list[str],
    current_round: int,
    session_id: str | None = None,
    retain_count: int | None = None,
    rounds_to_retain: int | None = None,
) -> tuple[list[ContributionMessage], int]:
    """Prune old contributions after a round summary is generated.

    Called at end of each round after summary is created. Safe because
    round summaries capture the content of pruned contributions.

    Pruning strategy:
    - Only prune contributions from rounds older than `rounds_to_retain`
    - Keep at least `retain_count` contributions for synthesis fallback
    - Only prune if round summary exists for the round being pruned
    - Log pruning metrics for observability

    Safety:
    - Never prune if round_summaries is empty for older rounds
    - Always retain RETENTION_COUNT contributions minimum
    - Only prune rounds older than ROUNDS_TO_RETAIN

    Args:
        contributions: Full list of contributions
        round_summaries: List of round summaries (index = round-1)
        current_round: Current round number (1-indexed)
        session_id: Session ID for logging
        retain_count: Minimum contributions to retain (default: from config)
        rounds_to_retain: Rounds to keep raw contributions for (default: from config)

    Returns:
        Tuple of (pruned_contributions, pruned_count)
    """
    from bo1.constants import ContributionPruning

    if retain_count is None:
        retain_count = ContributionPruning.RETENTION_COUNT
    if rounds_to_retain is None:
        rounds_to_retain = ContributionPruning.ROUNDS_TO_RETAIN

    # Check if pruning is enabled
    if not ContributionPruning.PRUNE_AFTER_ROUND_SUMMARY:
        return contributions, 0

    # Safety: Don't prune if already small enough
    if len(contributions) <= retain_count:
        logger.debug(
            f"prune_contributions_after_round: No pruning needed "
            f"(contributions={len(contributions)} <= retain_count={retain_count})"
        )
        return contributions, 0

    # Calculate cutoff round: prune contributions from rounds older than this
    cutoff_round = current_round - rounds_to_retain
    if cutoff_round < 1:
        logger.debug(
            f"prune_contributions_after_round: No pruning needed "
            f"(current_round={current_round}, cutoff_round={cutoff_round})"
        )
        return contributions, 0

    # Check if we have summaries for rounds we want to prune
    # round_summaries is 0-indexed (index 0 = round 1 summary)
    if len(round_summaries) < cutoff_round:
        logger.debug(
            f"prune_contributions_after_round: Skipping - missing summaries for pruned rounds "
            f"(summaries={len(round_summaries)}, need={cutoff_round})"
        )
        return contributions, 0

    # Separate contributions by whether they should be pruned
    # Handle both ContributionMessage objects and dicts
    to_retain = []
    to_prune = []
    for c in contributions:
        # Defensive: handle both ContributionMessage objects and dicts (e.g., from deserialization)
        c_round = c.round_number if hasattr(c, "round_number") else c.get("round_number", 0)  # type: ignore[attr-defined]
        if c_round > cutoff_round:
            to_retain.append(c)
        else:
            to_prune.append(c)

    # Ensure we keep at least retain_count contributions
    if len(to_retain) < retain_count:
        # Keep some from to_prune (most recent first)
        need = retain_count - len(to_retain)
        to_retain = to_prune[-need:] + to_retain
        to_prune = to_prune[:-need] if need < len(to_prune) else []

    pruned_count = len(to_prune)
    if pruned_count > 0:
        # Estimate bytes saved (~200 tokens/contribution, ~4 chars/token)
        bytes_saved_estimate = pruned_count * 200 * 4
        logger.info(
            f"prune_contributions_after_round: session={session_id}, "
            f"round={current_round}, pruned={pruned_count}, retained={len(to_retain)}, "
            f"cutoff_round={cutoff_round}, bytes_saved_est={bytes_saved_estimate}"
        )

    return to_retain, pruned_count
