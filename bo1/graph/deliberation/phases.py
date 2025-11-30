"""Phase management for deliberation rounds.

Phases structure the deliberation into three stages:
- exploration (rounds 1-2): Divergent thinking, surface perspectives
- challenge (rounds 3-4): Deep analysis, challenge weak arguments
- convergence (rounds 5-6): Synthesis, explicit recommendations

This module is extracted from nodes.py for better testability.
"""

import logging
from typing import Literal

logger = logging.getLogger(__name__)

DeliberationPhase = Literal["exploration", "challenge", "convergence"]


class PhaseManager:
    """Manages deliberation phase transitions and prompts."""

    @staticmethod
    def determine_phase(round_number: int, max_rounds: int) -> DeliberationPhase:
        """Determine current deliberation phase based on round number.

        Phase allocation (for 6-round max):
        - Exploration: Rounds 1-2 (33% of deliberation)
        - Challenge: Rounds 3-4 (33% of deliberation)
        - Convergence: Rounds 5+ (33% of deliberation)

        Args:
            round_number: Current round (1-indexed)
            max_rounds: Maximum rounds configured

        Returns:
            Phase name: "exploration", "challenge", or "convergence"

        Examples:
            >>> PhaseManager.determine_phase(1, 6)
            'exploration'
            >>> PhaseManager.determine_phase(3, 6)
            'challenge'
            >>> PhaseManager.determine_phase(5, 6)
            'convergence'
        """
        # Calculate phase boundaries (thirds)
        exploration_end = max(2, max_rounds // 3)
        challenge_end = max(4, 2 * max_rounds // 3)

        if round_number <= exploration_end:
            return "exploration"
        elif round_number <= challenge_end:
            return "challenge"
        else:
            return "convergence"

    @staticmethod
    def get_phase_prompt(phase: DeliberationPhase, round_number: int) -> str:
        """Get phase-specific prompt guidance for experts.

        Args:
            phase: Current deliberation phase
            round_number: Current round number

        Returns:
            Phase-specific prompt string for expert guidance
        """
        prompts = {
            "exploration": (
                f"PHASE: EXPLORATION (Round {round_number})\n"
                "Focus on: Generating diverse perspectives, identifying key issues, "
                "surfacing assumptions. Don't converge yet - explore widely."
            ),
            "challenge": (
                f"PHASE: CHALLENGE (Round {round_number})\n"
                "Focus on: Deep analysis with evidence, challenging weak arguments, "
                "identifying risks and gaps. Be constructively critical."
            ),
            "convergence": (
                f"PHASE: CONVERGENCE (Round {round_number})\n"
                "Focus on: Building toward synthesis, finding common ground, "
                "making explicit recommendations. Time to converge."
            ),
        }
        return prompts[phase]

    @staticmethod
    def get_phase_prompt_short(phase: DeliberationPhase) -> str:
        """Get short phase label for display.

        Args:
            phase: Current deliberation phase

        Returns:
            Short display label
        """
        return {
            "exploration": "Exploring",
            "challenge": "Challenging",
            "convergence": "Converging",
        }[phase]
