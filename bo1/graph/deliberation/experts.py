"""Expert selection logic for deliberation rounds.

This module provides functions for selecting which experts participate
in each round of deliberation, with strategies that vary by phase.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bo1.graph.state import DeliberationGraphState

logger = logging.getLogger(__name__)


async def select_experts_for_round(
    state: "DeliberationGraphState",
    phase: str,
    round_number: int,
) -> list[Any]:  # Returns list[PersonaProfile]
    """Select 2-5 experts for this round based on phase and balance.

    Selection Strategy (Adaptive based on complexity):
    - Uses metrics.recommended_experts as baseline (3-5 based on complexity)
    - Exploration: recommended_experts (broad exploration, prioritize unheard voices)
    - Challenge: max(2, recommended_experts - 1) (focused debate, avoid recent speakers)
    - Convergence: max(2, recommended_experts - 1) (synthesis, balanced representation)

    Balancing Rules:
    - No expert in >50% of recent 4 rounds
    - Each expert 15-25% of total contributions (balanced)

    Args:
        state: Current deliberation state
        phase: "exploration", "challenge", or "convergence"
        round_number: Current round number

    Returns:
        List of selected PersonaProfile objects
    """
    personas = state.get("personas", [])
    contributions = state.get("contributions", [])
    experts_per_round = state.get("experts_per_round", [])

    if not personas:
        logger.warning("No personas available for selection")
        return []

    # Get adaptive expert count from complexity assessment
    metrics = state.get("metrics")
    recommended_experts = 4  # Default fallback
    if metrics and hasattr(metrics, "recommended_experts") and metrics.recommended_experts:
        recommended_experts = metrics.recommended_experts
    logger.info(f"Using recommended_experts={recommended_experts} from complexity assessment")

    # Count contributions per expert
    contribution_counts: dict[str, int] = {}
    for contrib in contributions:
        contribution_counts[contrib.persona_code] = (
            contribution_counts.get(contrib.persona_code, 0) + 1
        )

    # Get recent speakers (last 4 rounds)
    recent_speakers: list[str] = []
    if experts_per_round:
        for round_experts in experts_per_round[-4:]:
            recent_speakers.extend(round_experts)

    # Phase-specific selection (adaptive based on complexity)
    if phase == "exploration":
        # Select recommended_experts, prioritize those who haven't spoken much
        target_count = min(recommended_experts, len(personas))

        # Sort by contribution count (fewest first)
        candidates = sorted(
            personas,
            key=lambda p: (
                contribution_counts.get(p.code, 0),  # Fewest contributions first
                p.code,  # Stable sort by code
            ),
        )

        selected = candidates[:target_count]

    elif phase == "challenge":
        # Select fewer experts for focused debate (recommended - 1, minimum 2)
        target_count = min(max(2, recommended_experts - 1), len(personas))

        # Filter out recent speakers
        candidates = [
            p
            for p in personas
            if recent_speakers.count(p.code) < 2  # Not in last 2 rounds
        ]

        if not candidates:
            # All experts spoke recently, just use all
            candidates = list(personas)

        # Sort by contribution count (fewest first)
        candidates = sorted(candidates, key=lambda p: contribution_counts.get(p.code, 0))

        selected = candidates[:target_count]

    elif phase == "convergence":
        # Select fewer experts for synthesis (recommended - 1, minimum 2)
        target_count = min(max(2, recommended_experts - 1), len(personas))

        # Select balanced set (least-contributing experts to ensure all voices heard)
        selected = sorted(personas, key=lambda p: contribution_counts.get(p.code, 0))[:target_count]

    else:
        # Default: use recommended_experts
        target_count = min(recommended_experts, len(personas))
        selected = personas[:target_count]

    logger.info(
        f"Expert selection ({phase}): {[p.code for p in selected]} "
        f"(target: {target_count if 'target_count' in locals() else 'N/A'})"
    )

    return selected
