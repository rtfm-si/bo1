"""Meeting quality configuration and critical aspects definition.

This module defines the 8 critical decision aspects and configuration presets
for different meeting types (tactical vs strategic).
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# ============================================================================
# Critical Decision Aspects
# ============================================================================

# The 8 critical aspects that should be explored in any decision
CRITICAL_ASPECTS = [
    "problem_clarity",
    "objectives",
    "options_alternatives",
    "key_assumptions",
    "risks_failure_modes",
    "constraints",
    "stakeholders_impact",
    "dependencies_unknowns",
]

# Detailed descriptions and examples for each aspect
ASPECT_DESCRIPTIONS = {
    "problem_clarity": {
        "description": "Is the problem well-defined and measurable?",
        "examples": {
            "none": "Problem statement is vague or undefined",
            "shallow": "Problem mentioned but not quantified ('improve sales')",
            "deep": "Problem clearly defined with metrics ('increase MRR from $50K to $75K by Q2')",
        },
    },
    "objectives": {
        "description": "Are success criteria and objectives clear?",
        "examples": {
            "none": "No discussion of what success looks like",
            "shallow": "Generic goals mentioned ('be successful', 'grow')",
            "deep": "Specific, measurable objectives with timelines ('10% MRR growth within 6 months')",
        },
    },
    "options_alternatives": {
        "description": "Have alternative approaches been considered?",
        "examples": {
            "none": "Only one option discussed, no alternatives",
            "shallow": "Alternatives mentioned but not compared ('could also do B')",
            "deep": "Multiple options compared with pros/cons analysis (Option A vs B vs C)",
        },
    },
    "key_assumptions": {
        "description": "Have critical assumptions been identified and validated?",
        "examples": {
            "none": "No assumptions explicitly stated",
            "shallow": "Some assumptions mentioned but not validated ('assuming market exists')",
            "deep": "Key assumptions listed with validation plan ('Assume 5% conversion, will test with landing page')",
        },
    },
    "risks_failure_modes": {
        "description": "What could go wrong? What are the failure scenarios?",
        "examples": {
            "none": "No risk discussion",
            "shallow": "Generic concerns mentioned ('might be risky', 'could fail')",
            "deep": "Specific risks identified with likelihood and mitigation ('30% chance of regulatory delay, mitigate with early FDA consultation')",
        },
    },
    "constraints": {
        "description": "What are the limitations (time, money, resources)?",
        "examples": {
            "none": "No constraints discussed",
            "shallow": "Vague constraints mentioned ('limited budget', 'tight timeline')",
            "deep": "Specific constraints with numbers ('$500K budget, 6-month timeline, 2 engineers available')",
        },
    },
    "stakeholders_impact": {
        "description": "Who is affected and how?",
        "examples": {
            "none": "No stakeholder discussion",
            "shallow": "Stakeholders mentioned but impact unclear ('will affect customers')",
            "deep": "Detailed stakeholder analysis ('Premium customers lose feature, expect 5% churn, mitigate with grandfather clause')",
        },
    },
    "dependencies_unknowns": {
        "description": "What external factors or unknowns could affect this?",
        "examples": {
            "none": "No dependencies identified",
            "shallow": "Vague dependencies mentioned ('depends on engineering')",
            "deep": "Specific dependencies with blockers ('Requires API integration complete by Jan 15, currently blocked on vendor')",
        },
    },
}


def get_aspect_description(aspect_name: str) -> dict[str, Any]:
    """Get description and examples for an aspect.

    Args:
        aspect_name: Name of the aspect (must be in CRITICAL_ASPECTS)

    Returns:
        Dictionary with description and examples

    Raises:
        ValueError: If aspect_name is not in CRITICAL_ASPECTS
    """
    if aspect_name not in ASPECT_DESCRIPTIONS:
        raise ValueError(f"Unknown aspect: {aspect_name}. Must be one of {CRITICAL_ASPECTS}")
    return ASPECT_DESCRIPTIONS[aspect_name]


# ============================================================================
# Meeting Configuration Schema
# ============================================================================


class MeetingConfig(BaseModel):
    """Configuration for meeting quality assessment.

    Controls thresholds, weights, and rules for different meeting types.
    """

    meeting_type: Literal["tactical", "strategic", "default"] = Field(
        ...,
        description="Type of meeting: tactical (faster, less exploration), strategic (deeper, more thorough), or default (balanced)",
    )

    weights: dict[str, float] = Field(
        ...,
        description="Weights for composite index calculation (must sum to 1.0): exploration, convergence, focus, low_novelty",
    )

    thresholds: dict[str, Any] = Field(
        ...,
        description="Thresholds for each metric (exploration, convergence, focus, novelty, composite)",
    )

    round_limits: dict[str, int] = Field(..., description="Round limits: min_rounds, max_rounds")

    rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional rules for meeting quality (coverage requirements, early consensus checks, stall detection)",
    )

    @field_validator("weights")
    @classmethod
    def validate_weights_sum_to_one(cls, v: dict[str, float]) -> dict[str, float]:
        """Ensure weights sum to 1.0."""
        total = sum(v.values())
        if not (0.99 <= total <= 1.01):  # Allow small floating point error
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        return v

    @field_validator("thresholds")
    @classmethod
    def validate_thresholds_in_range(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Ensure all score thresholds are in 0-1 range."""
        for category, values in v.items():
            if isinstance(values, dict):
                for key, threshold in values.items():
                    if isinstance(threshold, (int, float)) and not (0.0 <= threshold <= 1.0):
                        raise ValueError(
                            f"Threshold {category}.{key} must be in [0, 1], got {threshold}"
                        )
        return v


# ============================================================================
# Preset Configurations
# ============================================================================


TACTICAL_CONFIG = MeetingConfig(
    meeting_type="tactical",
    weights={"exploration": 0.30, "convergence": 0.40, "focus": 0.20, "low_novelty": 0.10},
    thresholds={
        "exploration": {"min_to_allow_end": 0.5, "target_good": 0.65},
        "convergence": {"min_to_allow_end": 0.65, "target_good": 0.80},
        "focus": {"min_acceptable": 0.70, "target_good": 0.85},
        "novelty": {"novelty_floor_recent": 0.20},
        "composite": {"min_index_to_recommend_end": 0.65},
        "progress": {
            "min_delta_convergence_over_2_rounds": 0.05,
            "min_delta_exploration_over_2_rounds": 0.03,
        },
    },
    round_limits={"min_rounds": 2, "max_rounds": 7},
    rules={
        "require_exploration_coverage": {
            "enabled": True,
            "required_aspects_deep": ["problem_clarity", "objectives"],
            "min_fraction_deep_overall": 0.5,
        },
        "early_consensus_requires_extra_check": {
            "enabled": True,
            "early_round_cutoff": 4,
            "convergence_high": 0.75,
            "exploration_low": 0.50,
        },
    },
)


STRATEGIC_CONFIG = MeetingConfig(
    meeting_type="strategic",
    weights={"exploration": 0.40, "convergence": 0.30, "focus": 0.20, "low_novelty": 0.10},
    thresholds={
        "exploration": {"min_to_allow_end": 0.65, "target_good": 0.80},
        "convergence": {"min_to_allow_end": 0.55, "target_good": 0.70},
        "focus": {"min_acceptable": 0.60, "target_good": 0.80},
        "novelty": {"novelty_floor_recent": 0.30},
        "composite": {"min_index_to_recommend_end": 0.72},
        "progress": {
            "min_delta_convergence_over_2_rounds": 0.04,
            "min_delta_exploration_over_2_rounds": 0.04,
        },
    },
    round_limits={"min_rounds": 3, "max_rounds": 10},
    rules={
        "require_exploration_coverage": {
            "enabled": True,
            "required_aspects_deep": ["problem_clarity", "objectives", "risks_failure_modes"],
            "min_fraction_deep_overall": 0.6,
        },
        "early_consensus_requires_extra_check": {
            "enabled": True,
            "early_round_cutoff": 5,
            "convergence_high": 0.70,
            "exploration_low": 0.55,
        },
    },
)


DEFAULT_CONFIG = MeetingConfig(
    meeting_type="default",
    weights={"exploration": 0.35, "convergence": 0.35, "focus": 0.20, "low_novelty": 0.10},
    thresholds={
        "exploration": {"min_to_allow_end": 0.60, "target_good": 0.75},
        "convergence": {"min_to_allow_end": 0.60, "target_good": 0.75},
        "focus": {"min_acceptable": 0.60, "target_good": 0.80},
        "novelty": {"novelty_floor_recent": 0.25},
        "composite": {"min_index_to_recommend_end": 0.70},
        "progress": {
            "min_delta_convergence_over_2_rounds": 0.05,
            "min_delta_exploration_over_2_rounds": 0.05,
        },
    },
    round_limits={"min_rounds": 3, "max_rounds": 10},
    rules={
        "require_exploration_coverage": {
            "enabled": True,
            "required_aspects_deep": ["problem_clarity", "objectives", "risks_failure_modes"],
            "min_fraction_deep_overall": 0.6,
        },
        "early_consensus_requires_extra_check": {
            "enabled": True,
            "early_round_cutoff": 5,
            "convergence_high": 0.70,
            "exploration_low": 0.55,
        },
        "stalled_debate_detection": {
            "enabled": True,
            "rounds_before_check": 5,
            "low_novelty_recent": 0.30,
            "min_delta_convergence_over_2_rounds": 0.05,
        },
    },
)


# ============================================================================
# Config Selection Logic
# ============================================================================


def get_meeting_config(state: dict[str, Any]) -> MeetingConfig:
    """Select appropriate meeting config based on state.

    Args:
        state: Deliberation state dictionary (can be DeliberationGraphState or dict)

    Returns:
        MeetingConfig (tactical, strategic, or default)

    Example:
        >>> state = {"meeting_type": "strategic"}
        >>> config = get_meeting_config(state)
        >>> config.meeting_type
        'strategic'
    """
    # Check if meeting type is explicitly set
    meeting_type = state.get("meeting_type")
    if meeting_type == "tactical":
        return TACTICAL_CONFIG
    elif meeting_type == "strategic":
        return STRATEGIC_CONFIG
    elif meeting_type == "default":
        return DEFAULT_CONFIG

    # Fallback heuristics based on problem description
    problem = state.get("problem")
    if problem:
        # Extract problem description
        if hasattr(problem, "description"):
            description = problem.description.lower()
        elif isinstance(problem, dict):
            description = problem.get("description", "").lower()
        else:
            description = str(problem).lower()

        # Heuristic 1: High financial stakes → strategic (check first, highest priority)
        if any(marker in description for marker in ["$1m", "$1 million", "million", "series"]):
            return STRATEGIC_CONFIG

        # Heuristic 2: Strategic keywords
        strategic_keywords = [
            "strategy",
            "vision",
            "long-term",
            "roadmap",
            "expansion",
            "acquisition",
        ]
        if any(keyword in description for keyword in strategic_keywords):
            return STRATEGIC_CONFIG

        # Heuristic 3: Tactical keywords
        tactical_keywords = ["should we", "build", "implement", "hire", "launch", "pricing"]
        if any(keyword in description for keyword in tactical_keywords):
            return TACTICAL_CONFIG

    # Default fallback
    return DEFAULT_CONFIG
