"""Constants module for Board of One deliberation system.

This module centralizes magic numbers and thresholds used throughout the codebase,
making them easier to tune and maintain.
"""


class DeliberationPhases:
    """Phase definitions and round thresholds for deliberation progression."""

    EARLY_ROUNDS_MAX = 4
    """Maximum round number for early phase (1-4)"""

    MIDDLE_ROUNDS_MIN = 5
    """Start of middle phase"""

    MIDDLE_ROUNDS_MAX = 7
    """End of middle phase"""

    LATE_ROUNDS_MIN = 8
    """Start of late phase (8+)"""


class ThresholdValues:
    """Consensus and analysis thresholds for deliberation quality metrics."""

    CONVERGENCE_TARGET = 0.85
    """Target convergence score to consider consensus reached"""

    NOVELTY_THRESHOLD = 0.30
    """Maximum novelty score for convergence (below this = low new ideas)"""

    NOVELTY_LATE_ROUNDS_MAX = 0.30
    """Maximum novelty threshold for late rounds"""

    CONFLICT_DEADLOCK = 0.80
    """Conflict score indicating deadlock (high disagreement)"""

    AGREEMENT_KEYWORDS_RATIO = 0.15
    """Threshold for premature consensus detection (% of agreement keywords)"""

    SIMILARITY_THRESHOLD = 0.85
    """Minimum similarity score for detecting convergence"""


class ComplexityScores:
    """Problem complexity score ranges (1-10 scale)."""

    MIN = 1
    """Minimum valid complexity score"""

    MAX = 10
    """Maximum valid complexity score"""

    SIMPLE_MAX = 3
    """Maximum score for simple problems (1-3)"""

    MODERATE_MAX = 6
    """Maximum score for moderate problems (4-6)"""

    # Complex problems: 7-10 (by exclusion)


class Lengths:
    """Maximum counts for various deliberation components."""

    MAX_SUB_PROBLEMS = 5
    """Maximum number of sub-problems from decomposition"""

    MAX_DELIBERATION_ROUNDS = 15
    """Hard cap on deliberation rounds"""

    MIN_DELIBERATION_ROUNDS = 5
    """Minimum rounds for simple problems"""

    MODERATE_DELIBERATION_ROUNDS = 7
    """Target rounds for moderate complexity"""

    COMPLEX_DELIBERATION_ROUNDS = 10
    """Target rounds for complex problems"""


class TokenLimits:
    """Token limits for various LLM operations."""

    SUMMARY_TARGET = 100
    """Target token count for round summaries"""

    CONTRIBUTION_AVERAGE = 200
    """Average tokens per persona contribution"""

    RESPONSE_PREVIEW_LENGTH = 200
    """Characters to show in response previews (for logging)"""

    SNIPPET_MAX_LENGTH = 300
    """Maximum length for extracted snippets"""


class VotingThresholds:
    """Thresholds for voting and consensus detection."""

    UNANIMOUS_THRESHOLD = 0.95
    """Percentage for unanimous consensus (95%+)"""

    STRONG_MAJORITY_THRESHOLD = 0.75
    """Percentage for strong majority (75%+)"""

    SIMPLE_MAJORITY_THRESHOLD = 0.50
    """Percentage for simple majority (50%+)"""
