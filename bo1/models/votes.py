"""Voting models for Board of One.

Defines vote structure and aggregation mechanisms.
"""

from enum import Enum

from pydantic import BaseModel, Field


class VoteDecision(str, Enum):
    """Vote decision options."""

    YES = "yes"  # Support the recommendation
    NO = "no"  # Oppose the recommendation
    ABSTAIN = "abstain"  # No strong opinion
    CONDITIONAL = "conditional"  # Yes, but with conditions


class Vote(BaseModel):
    """A vote from a persona on a recommendation."""

    persona_code: str = Field(..., description="Code of the persona voting")
    persona_name: str = Field(..., description="Display name of the persona")
    decision: VoteDecision = Field(..., description="The vote decision")
    reasoning: str = Field(..., description="Reasoning behind the vote")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in this vote (0-1)"
    )
    conditions: list[str] = Field(
        default_factory=list,
        description="Conditions that must be met (if decision=conditional)",
    )
    weight: float = Field(
        default=1.0, ge=0.0, le=2.0, description="Voting weight for this persona"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "persona_code": "growth_hacker",
                    "persona_name": "Zara",
                    "decision": "yes",
                    "reasoning": "The A/B testing approach minimizes risk and provides clear data",
                    "confidence": 0.85,
                    "conditions": [],
                    "weight": 1.0,
                },
                {
                    "persona_code": "finance_strategist",
                    "persona_name": "Maria",
                    "decision": "conditional",
                    "reasoning": "Budget is tight, need to ensure positive ROI",
                    "confidence": 0.7,
                    "conditions": [
                        "CAC must be < $50",
                        "Payback period < 6 months",
                    ],
                    "weight": 1.2,
                },
            ]
        }


class ConsensusLevel(str, Enum):
    """Level of consensus reached."""

    UNANIMOUS = "unanimous"  # 100% agreement
    STRONG = "strong"  # ≥75% agreement
    MODERATE = "moderate"  # ≥60% agreement
    WEAK = "weak"  # ≥50% agreement
    NO_CONSENSUS = "no_consensus"  # <50% agreement


class VoteAggregation(BaseModel):
    """Aggregated voting results."""

    total_votes: int = Field(..., description="Total number of votes cast")
    yes_votes: int = Field(..., description="Number of yes votes")
    no_votes: int = Field(..., description="Number of no votes")
    abstain_votes: int = Field(..., description="Number of abstain votes")
    conditional_votes: int = Field(..., description="Number of conditional votes")

    simple_majority: bool = Field(..., description="Whether simple majority (>50%) was reached")
    supermajority: bool = Field(..., description="Whether supermajority (≥75%) was reached")

    consensus_level: ConsensusLevel = Field(..., description="Level of consensus")

    confidence_weighted_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence-weighted agreement score"
    )

    average_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Average confidence across all votes"
    )

    dissenting_opinions: list[str] = Field(
        default_factory=list, description="Reasoning from dissenting votes"
    )

    conditions_summary: list[str] = Field(
        default_factory=list, description="All conditions from conditional votes"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "total_votes": 5,
                    "yes_votes": 3,
                    "no_votes": 1,
                    "abstain_votes": 0,
                    "conditional_votes": 1,
                    "simple_majority": True,
                    "supermajority": False,
                    "consensus_level": "moderate",
                    "confidence_weighted_score": 0.72,
                    "average_confidence": 0.78,
                    "dissenting_opinions": [
                        "Risk is too high given current runway"
                    ],
                    "conditions_summary": [
                        "CAC must be < $50",
                        "Payback period < 6 months",
                    ],
                }
            ]
        }


def aggregate_votes(votes: list[Vote]) -> VoteAggregation:
    """Aggregate votes and calculate consensus metrics.

    Args:
        votes: List of Vote objects

    Returns:
        VoteAggregation with calculated metrics
    """
    total_votes = len(votes)

    if total_votes == 0:
        return VoteAggregation(
            total_votes=0,
            yes_votes=0,
            no_votes=0,
            abstain_votes=0,
            conditional_votes=0,
            simple_majority=False,
            supermajority=False,
            consensus_level=ConsensusLevel.NO_CONSENSUS,
            confidence_weighted_score=0.0,
            average_confidence=0.0,
        )

    # Count votes by decision
    yes_votes = sum(1 for v in votes if v.decision == VoteDecision.YES)
    no_votes = sum(1 for v in votes if v.decision == VoteDecision.NO)
    abstain_votes = sum(1 for v in votes if v.decision == VoteDecision.ABSTAIN)
    conditional_votes = sum(1 for v in votes if v.decision == VoteDecision.CONDITIONAL)

    # Calculate percentages (treating conditional as yes for majority calc)
    support_votes = yes_votes + conditional_votes
    support_percentage = support_votes / total_votes

    # Determine majorities
    simple_majority = support_percentage > 0.5
    supermajority = support_percentage >= 0.75

    # Determine consensus level
    if support_percentage == 1.0:
        consensus_level = ConsensusLevel.UNANIMOUS
    elif support_percentage >= 0.75:
        consensus_level = ConsensusLevel.STRONG
    elif support_percentage >= 0.60:
        consensus_level = ConsensusLevel.MODERATE
    elif support_percentage >= 0.50:
        consensus_level = ConsensusLevel.WEAK
    else:
        consensus_level = ConsensusLevel.NO_CONSENSUS

    # Calculate confidence-weighted score
    # Weight: yes=1, conditional=0.8, abstain=0, no=-1
    weighted_sum = 0.0
    total_weight = 0.0

    for vote in votes:
        vote_value = 0.0
        if vote.decision == VoteDecision.YES:
            vote_value = 1.0
        elif vote.decision == VoteDecision.CONDITIONAL:
            vote_value = 0.8
        elif vote.decision == VoteDecision.NO:
            vote_value = -1.0
        # ABSTAIN contributes 0

        weighted_sum += vote_value * vote.confidence * vote.weight
        total_weight += vote.weight

    confidence_weighted_score = (weighted_sum / total_weight + 1) / 2  # Normalize to 0-1

    # Calculate average confidence
    average_confidence = sum(v.confidence for v in votes) / total_votes

    # Collect dissenting opinions
    dissenting_opinions = [
        f"{v.persona_name}: {v.reasoning}"
        for v in votes
        if v.decision == VoteDecision.NO
    ]

    # Collect all conditions
    conditions_summary = []
    for vote in votes:
        if vote.decision == VoteDecision.CONDITIONAL:
            conditions_summary.extend(vote.conditions)

    return VoteAggregation(
        total_votes=total_votes,
        yes_votes=yes_votes,
        no_votes=no_votes,
        abstain_votes=abstain_votes,
        conditional_votes=conditional_votes,
        simple_majority=simple_majority,
        supermajority=supermajority,
        consensus_level=consensus_level,
        confidence_weighted_score=confidence_weighted_score,
        average_confidence=average_confidence,
        dissenting_opinions=dissenting_opinions,
        conditions_summary=conditions_summary,
    )
