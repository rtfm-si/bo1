"""Utility functions for prompt composition and management.

This module contains helper functions used across different prompt modules.
"""

from typing import Any

from bo1.config import TokenBudgets

# =============================================================================
# Response Prefilling Support
# =============================================================================


def get_prefill_text(persona_name: str) -> str:
    """Get the prefill text for response to maintain character consistency.

    According to the framework, prefilling helps maintain character by
    starting the assistant's response with the persona name and <thinking> tag.

    Args:
        persona_name: Name of the persona

    Returns:
        Prefill string to use in assistant message
    """
    return f"[{persona_name}]\n\n<thinking>"


# =============================================================================
# Adaptive Round Configuration
# =============================================================================


def get_round_phase_config(round_number: int, max_rounds: int) -> dict[str, Any]:
    """Get configuration for current round phase.

    Implements adaptive prompting strategy aligned with consensus building research:
    - Initial round: Full exploration, no constraints
    - Early rounds (2-4): Divergent thinking, loose prompts
    - Middle rounds (5-7): Analytical focus, moderate constraints
    - Late rounds (8+): Convergent thinking, strict prompts for consensus

    Args:
        round_number: Current round (1-indexed)
        max_rounds: Maximum rounds for this deliberation

    Returns:
        Dictionary with phase configuration:
        - phase: "initial" | "early" | "middle" | "late"
        - temperature: LLM temperature (1.0 → 0.7)
        - max_tokens: Response length limit (2000 → 800)
        - directive: Phase-specific instruction for persona
        - tone: Expected tone ("exploratory" | "divergent" | "analytical" | "convergent")

    Example:
        >>> config = get_round_phase_config(round_number=3, max_rounds=10)
        >>> config["phase"]
        'early'
        >>> config["max_tokens"]
        1500
    """
    progress = round_number / max_rounds

    if round_number <= 1:
        # Initial round: Full exploration
        # Base 0.85 + adjustment 0.0 = 0.85 (exploratory)
        return {
            "phase": "initial",
            "temperature": 0.85,
            "max_tokens": TokenBudgets.for_phase("initial"),
            "directive": "Provide your complete perspective on this problem. Consider all angles and share your full analysis.",
            "tone": "exploratory",
        }
    elif progress <= 0.4:  # Early rounds (2-4 of 10)
        # Divergent thinking: Explore alternatives
        # Base 0.85 + adjustment +0.15 = 1.0 (maximum creativity)
        return {
            "phase": "early",
            "temperature": 0.85,
            "max_tokens": TokenBudgets.for_phase("early"),
            "directive": "Explore different angles and perspectives. What concerns, risks, or alternatives haven't been discussed yet?",
            "tone": "divergent",
        }
    elif progress <= 0.7:  # Middle rounds (5-7 of 10)
        # Analysis phase: Evidence and reasoning
        # Base 0.75 + adjustment 0.0 = 0.75 (analytical)
        return {
            "phase": "middle",
            "temperature": 0.75,
            "max_tokens": TokenBudgets.for_phase("middle"),
            "directive": "Build on the discussion with evidence and analysis. Address gaps, uncertainties, or claims that need verification.",
            "tone": "analytical",
        }
    else:  # Late rounds (8+ of 10)
        # Convergent thinking: Move toward consensus
        # Base 0.65 + adjustment -0.10 = 0.55 (focused convergence)
        return {
            "phase": "late",
            "temperature": 0.65,
            "max_tokens": TokenBudgets.for_phase("late"),
            "directive": "Work toward consensus. Acknowledge tradeoffs, find common ground, and help the group move toward a decision.",
            "tone": "convergent",
        }
