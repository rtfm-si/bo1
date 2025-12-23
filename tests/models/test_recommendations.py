"""Tests for recommendation models roundtrip serialization."""

from datetime import UTC, datetime

from bo1.models import ConsensusLevel, Recommendation, RecommendationAggregation


class TestRecommendationDBFields:
    """Test new DB-mapped fields on Recommendation model."""

    def test_recommendation_with_db_fields(self) -> None:
        """Recommendation model accepts DB-assigned fields."""
        now = datetime.now(UTC)
        rec = Recommendation(
            id=42,
            session_id="bo1_test123",
            sub_problem_index=0,
            user_id="user_abc",
            created_at=now,
            persona_code="ceo",
            persona_name="CEO",
            recommendation="Proceed",
            reasoning="Because.",
            confidence=0.9,
        )

        assert rec.id == 42
        assert rec.session_id == "bo1_test123"
        assert rec.sub_problem_index == 0
        assert rec.user_id == "user_abc"
        assert rec.created_at == now

    def test_recommendation_db_fields_optional(self) -> None:
        """DB fields default to None when not provided."""
        rec = Recommendation(
            persona_code="ceo",
            persona_name="CEO",
            recommendation="Proceed",
            reasoning="Because.",
            confidence=0.9,
        )

        assert rec.id is None
        assert rec.session_id is None
        assert rec.sub_problem_index is None
        assert rec.user_id is None
        assert rec.created_at is None

    def test_recommendation_db_fields_roundtrip(self) -> None:
        """DB fields roundtrip through JSON serialization."""
        now = datetime.now(UTC)
        rec = Recommendation(
            id=100,
            session_id="bo1_sess_xyz",
            sub_problem_index=2,
            user_id="user_123",
            created_at=now,
            persona_code="strategist",
            persona_name="Strategic Planner",
            recommendation="Expand to new market",
            reasoning="Market research supports this.",
            confidence=0.78,
            conditions=["Complete pilot first"],
        )

        json_str = rec.model_dump_json()
        restored = Recommendation.model_validate_json(json_str)

        assert restored.id == 100
        assert restored.session_id == "bo1_sess_xyz"
        assert restored.sub_problem_index == 2
        assert restored.user_id == "user_123"
        assert restored.created_at == now
        assert restored.persona_code == "strategist"
        assert restored.recommendation == "Expand to new market"


class TestRecommendationRoundtrip:
    """Test Recommendation model serialization."""

    def test_recommendation_roundtrip(self, sample_recommendation_dict: dict) -> None:
        """Recommendation with all fields round-trips correctly."""
        rec = Recommendation(**sample_recommendation_dict)

        # Serialize to JSON
        json_str = rec.model_dump_json()

        # Deserialize back
        restored = Recommendation.model_validate_json(json_str)

        assert restored.persona_code == rec.persona_code
        assert restored.persona_name == rec.persona_name
        assert restored.recommendation == rec.recommendation
        assert restored.reasoning == rec.reasoning
        assert restored.confidence == rec.confidence
        assert restored.conditions == rec.conditions
        assert restored.weight == rec.weight
        assert restored.alternatives_considered == rec.alternatives_considered
        assert restored.risk_assessment == rec.risk_assessment

    def test_recommendation_minimal_fields(self) -> None:
        """Recommendation with only required fields serializes."""
        rec = Recommendation(
            persona_code="ceo",
            persona_name="CEO",
            recommendation="Proceed with option A",
            reasoning="Based on market analysis...",
            confidence=0.75,
        )

        json_str = rec.model_dump_json()
        restored = Recommendation.model_validate_json(json_str)

        assert restored.persona_code == "ceo"
        assert restored.recommendation == "Proceed with option A"
        assert restored.confidence == 0.75
        assert restored.weight == 1.0  # Default
        assert restored.conditions == []  # Default empty list
        assert restored.alternatives_considered is None
        assert restored.risk_assessment is None

    def test_recommendation_confidence_bounds(self) -> None:
        """confidence field constrained to 0-1."""
        # Valid boundary values
        for conf in [0.0, 0.5, 1.0]:
            rec = Recommendation(
                persona_code="test",
                persona_name="Test",
                recommendation="Test",
                reasoning="Test",
                confidence=conf,
            )
            assert rec.confidence == conf

    def test_recommendation_weight_bounds(self) -> None:
        """weight field constrained to 0-2."""
        for weight in [0.0, 1.0, 1.5, 2.0]:
            rec = Recommendation(
                persona_code="test",
                persona_name="Test",
                recommendation="Test",
                reasoning="Test",
                confidence=0.8,
                weight=weight,
            )
            assert rec.weight == weight


class TestRecommendationAggregationRoundtrip:
    """Test RecommendationAggregation model serialization."""

    def test_recommendation_aggregation_roundtrip(self) -> None:
        """RecommendationAggregation with all fields round-trips."""
        agg = RecommendationAggregation(
            total_recommendations=4,
            consensus_recommendation="Hybrid approach: 60% content, 40% paid",
            confidence_level="high",
            alternative_approaches=[
                "100% content marketing (slower)",
                "100% paid ads (expensive)",
            ],
            critical_conditions=[
                "Review monthly",
                "Set up attribution tracking",
            ],
            dissenting_views=[
                "CFO prefers conservative 80% content approach",
            ],
            confidence_weighted_score=0.82,
            average_confidence=0.78,
            consensus_level=ConsensusLevel.STRONG,
        )

        json_str = agg.model_dump_json()
        restored = RecommendationAggregation.model_validate_json(json_str)

        assert restored.total_recommendations == agg.total_recommendations
        assert restored.consensus_recommendation == agg.consensus_recommendation
        assert restored.confidence_level == agg.confidence_level
        assert restored.alternative_approaches == agg.alternative_approaches
        assert restored.critical_conditions == agg.critical_conditions
        assert restored.dissenting_views == agg.dissenting_views
        assert restored.confidence_weighted_score == agg.confidence_weighted_score
        assert restored.average_confidence == agg.average_confidence
        assert restored.consensus_level == agg.consensus_level

    def test_recommendation_aggregation_empty_lists(self) -> None:
        """Empty lists serialize correctly."""
        agg = RecommendationAggregation(
            total_recommendations=1,
            consensus_recommendation="Single recommendation",
            confidence_level="low",
            confidence_weighted_score=0.5,
            average_confidence=0.5,
        )

        json_str = agg.model_dump_json()
        restored = RecommendationAggregation.model_validate_json(json_str)

        assert restored.alternative_approaches == []
        assert restored.critical_conditions == []
        assert restored.dissenting_views == []


class TestConsensusLevelEnum:
    """Test ConsensusLevel enum completeness."""

    def test_consensus_level_enum_values(self) -> None:
        """All consensus levels are present."""
        expected = {"unanimous", "strong", "moderate", "weak", "no_consensus"}
        actual = {e.value for e in ConsensusLevel}
        assert actual == expected

    def test_consensus_level_serialization(self) -> None:
        """ConsensusLevel enum serializes as string value."""
        for level in ConsensusLevel:
            agg = RecommendationAggregation(
                total_recommendations=3,
                consensus_recommendation="Test",
                confidence_level="medium",
                confidence_weighted_score=0.7,
                average_confidence=0.7,
                consensus_level=level,
            )

            data = agg.model_dump()
            assert data["consensus_level"] == level.value

            # Roundtrip
            json_str = agg.model_dump_json()
            restored = RecommendationAggregation.model_validate_json(json_str)
            assert restored.consensus_level == level

    def test_consensus_level_default(self) -> None:
        """consensus_level defaults to MODERATE."""
        agg = RecommendationAggregation(
            total_recommendations=2,
            consensus_recommendation="Test",
            confidence_level="medium",
            confidence_weighted_score=0.6,
            average_confidence=0.6,
        )
        assert agg.consensus_level == ConsensusLevel.MODERATE
