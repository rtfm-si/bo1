"""Tests for the voting → recommendations migration.

Verifies that the new recommendation system works correctly.
"""

from bo1.models.recommendations import (
    ConsensusLevel,
    Recommendation,
    RecommendationAggregation,
)


def test_recommendation_model():
    """Test that Recommendation model works correctly."""
    rec = Recommendation(
        persona_code="test",
        persona_name="Test Expert",
        recommendation="Use 60% salary, 40% dividends hybrid approach",
        reasoning="This balances tax efficiency with cash flow stability.",
        confidence=0.85,
        conditions=["Review quarterly", "Monitor tax law changes"],
        weight=1.0,
    )

    assert rec.persona_code == "test"
    assert rec.persona_name == "Test Expert"
    assert rec.recommendation == "Use 60% salary, 40% dividends hybrid approach"
    assert rec.confidence == 0.85
    assert len(rec.conditions) == 2
    assert rec.weight == 1.0


def test_recommendation_aggregation_model():
    """Test that RecommendationAggregation model works correctly."""
    agg = RecommendationAggregation(
        total_recommendations=4,
        consensus_recommendation="Hybrid compensation: 60% salary, 40% dividends",
        confidence_level="high",
        alternative_approaches=["Pure salary until profitability"],
        critical_conditions=["Quarterly review", "Legal compliance"],
        dissenting_views=["Ahmad: Prefers pure salary"],
        confidence_weighted_score=0.82,
        average_confidence=0.80,
        consensus_level=ConsensusLevel.STRONG,
    )

    assert agg.total_recommendations == 4
    assert "60%" in agg.consensus_recommendation
    assert agg.confidence_level == "high"
    assert len(agg.alternative_approaches) == 1
    assert len(agg.critical_conditions) == 2
    assert agg.consensus_level == ConsensusLevel.STRONG


def test_backward_compatibility():
    """Test that Recommendation and RecommendationAggregation work correctly."""
    from bo1.models.recommendations import Recommendation, RecommendationAggregation

    # Test Recommendation model
    vote = Recommendation(
        persona_code="test",
        persona_name="Test Expert",
        recommendation="Approve investment in SEO",
        reasoning="Long-term ROI is better than paid ads.",
        confidence=0.75,
        conditions=["Start with $10K budget"],
        weight=1.0,
    )

    assert vote.recommendation == "Approve investment in SEO"

    # Test RecommendationAggregation model
    agg = RecommendationAggregation(
        total_recommendations=3,
        consensus_recommendation="Approve SEO investment",
        confidence_level="medium",
        confidence_weighted_score=0.72,
        average_confidence=0.70,
        consensus_level=ConsensusLevel.MODERATE,
    )

    assert agg.total_recommendations == 3


def test_consensus_level_enum():
    """Test that ConsensusLevel enum works correctly."""
    assert ConsensusLevel.UNANIMOUS.value == "unanimous"
    assert ConsensusLevel.STRONG.value == "strong"
    assert ConsensusLevel.MODERATE.value == "moderate"
    assert ConsensusLevel.WEAK.value == "weak"
    assert ConsensusLevel.NO_CONSENSUS.value == "no_consensus"
