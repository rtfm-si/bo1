"""Recommendation models for Board of One.

Defines recommendation structure and aggregation mechanisms.
Replaces the old binary voting system with flexible expert recommendations.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from .types import Confidence, Weight


class Recommendation(BaseModel):
    """Expert recommendation with full flexibility.

    Supports both binary decisions ("Approve X") and strategy
    recommendations ("60% X, 40% Y hybrid").
    """

    # DB-assigned fields (optional for API compatibility, populated on read)
    id: int | None = Field(default=None, description="Database-assigned ID")
    session_id: str | None = Field(default=None, description="Session identifier")
    sub_problem_index: int | None = Field(default=None, description="Sub-problem index")
    user_id: str | None = Field(default=None, description="User identifier for RLS")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")

    # Core recommendation fields
    persona_code: str = Field(..., description="Code of the persona making the recommendation")
    persona_name: str = Field(..., description="Display name of the persona")
    recommendation: str = Field(
        ..., description="Free-form recommendation (specific and actionable)"
    )
    reasoning: str = Field(..., description="Full explanation (2-3 paragraphs)")
    confidence: Confidence = Field(..., description="Confidence in this recommendation (0-1)")
    conditions: list[str] = Field(
        default_factory=list,
        description="Critical conditions or caveats",
    )
    weight: Weight = Field(default=1.0, description="Weighting for this persona's recommendation")

    # Optional fields for richer recommendations
    alternatives_considered: list[str] | None = Field(
        default=None, description="Other options discussed"
    )
    risk_assessment: str | None = Field(default=None, description="Key risks identified")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "persona_code": "finance_strategist",
                    "persona_name": "Maria Santos",
                    "recommendation": "60% salary, 40% dividends hybrid approach",
                    "reasoning": "This structure balances tax efficiency with cash flow needs. The salary component provides stability while dividends offer flexibility for reinvestment.",
                    "confidence": 0.85,
                    "conditions": [
                        "Review quarterly and rebalance as needed",
                        "Ensure compliance with local tax regulations",
                    ],
                    "weight": 1.2,
                    "alternatives_considered": [
                        "100% salary (more stable but less tax efficient)",
                        "100% dividends (tax efficient but unpredictable)",
                    ],
                    "risk_assessment": "Tax law changes could impact dividend treatment",
                },
                {
                    "persona_code": "growth_hacker",
                    "persona_name": "Zara Chen",
                    "recommendation": "Approve investment in SEO",
                    "reasoning": "SEO provides long-term sustainable growth with better ROI than paid ads for our market segment.",
                    "confidence": 0.75,
                    "conditions": ["Start with $10K test budget", "Measure results monthly"],
                    "weight": 1.0,
                },
            ]
        }
    )


class ConsensusLevel(str, Enum):
    """Level of consensus reached."""

    UNANIMOUS = "unanimous"  # 100% agreement
    STRONG = "strong"  # ≥75% agreement
    MODERATE = "moderate"  # ≥60% agreement
    WEAK = "weak"  # ≥50% agreement
    NO_CONSENSUS = "no_consensus"  # <50% agreement


class RecommendationAggregation(BaseModel):
    """Aggregated recommendations (AI-synthesized)."""

    total_recommendations: int = Field(..., description="Total number of recommendations")
    consensus_recommendation: str = Field(
        ..., description="AI-synthesized consensus recommendation"
    )
    confidence_level: str = Field(..., description='Confidence level: "high" | "medium" | "low"')
    alternative_approaches: list[str] = Field(
        default_factory=list, description="Distinct alternative approaches proposed"
    )
    critical_conditions: list[str] = Field(
        default_factory=list, description="Conditions mentioned by multiple experts"
    )
    dissenting_views: list[str] = Field(
        default_factory=list, description="Minority perspectives to preserve"
    )
    confidence_weighted_score: Confidence = Field(
        ..., description="Confidence-weighted score for metrics"
    )
    average_confidence: Confidence = Field(
        ..., description="Average confidence across all recommendations"
    )

    # Legacy fields for backward compatibility with metrics
    consensus_level: ConsensusLevel = Field(
        default=ConsensusLevel.MODERATE, description="Categorical consensus level"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "total_recommendations": 4,
                    "consensus_recommendation": "Hybrid compensation structure: 60% salary, 40% dividends",
                    "confidence_level": "high",
                    "alternative_approaches": [
                        "Pure salary until profitability (Ahmad's suggestion)",
                        "70/30 split with quarterly rebalancing (Aisha's variant)",
                    ],
                    "critical_conditions": [
                        "Quarterly review and rebalancing",
                        "Legal compliance verification",
                        "Monitor tax law changes",
                    ],
                    "dissenting_views": [
                        "Ahmad Ibrahim: Prefers pure salary until company reaches profitability to avoid complexity"
                    ],
                    "confidence_weighted_score": 0.82,
                    "average_confidence": 0.80,
                    "consensus_level": "strong",
                }
            ]
        }
    )
