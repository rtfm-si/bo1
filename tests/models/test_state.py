"""Tests for state models roundtrip serialization."""

from bo1.models import ContributionMessage, ContributionType, DeliberationPhase
from bo1.models.state import (
    AspectCoverage,
    DeliberationMetrics,
    DeliberationPhaseType,
    SubProblemResult,
)


class TestContributionMessageRoundtrip:
    """Test ContributionMessage model serialization."""

    def test_contribution_message_roundtrip(self, sample_contribution_dict: dict) -> None:
        """ContributionMessage with all fields round-trips correctly."""
        # Create from dict (simulating direct construction)
        msg = ContributionMessage(
            id=sample_contribution_dict["id"],
            session_id=sample_contribution_dict["session_id"],
            persona_code=sample_contribution_dict["persona_code"],
            persona_name=sample_contribution_dict["persona_name"],
            content=sample_contribution_dict["content"],
            thinking=sample_contribution_dict["thinking"],
            round_number=sample_contribution_dict["round_number"],
            phase=DeliberationPhaseType.EXPLORATION,
            cost=sample_contribution_dict["cost"],
            token_count=sample_contribution_dict["tokens"],
            model=sample_contribution_dict["model"],
            contribution_type=ContributionType.INITIAL,
        )

        # Serialize to JSON (embedding excluded)
        json_str = msg.model_dump_json()

        # Deserialize back
        restored = ContributionMessage.model_validate_json(json_str)

        assert restored.id == msg.id
        assert restored.session_id == msg.session_id
        assert restored.persona_code == msg.persona_code
        assert restored.persona_name == msg.persona_name
        assert restored.content == msg.content
        assert restored.thinking == msg.thinking
        assert restored.round_number == msg.round_number
        assert restored.phase == msg.phase
        assert restored.cost == msg.cost
        assert restored.token_count == msg.token_count
        assert restored.model == msg.model
        assert restored.contribution_type == msg.contribution_type

    def test_contribution_message_from_db_row(self, sample_contribution_dict: dict) -> None:
        """from_db_row() correctly maps DB column names to model fields."""
        msg = ContributionMessage.from_db_row(sample_contribution_dict)

        assert msg.id == sample_contribution_dict["id"]
        assert msg.session_id == sample_contribution_dict["session_id"]
        assert msg.persona_code == sample_contribution_dict["persona_code"]
        assert msg.persona_name == sample_contribution_dict["persona_name"]
        assert msg.content == sample_contribution_dict["content"]
        assert msg.thinking == sample_contribution_dict["thinking"]
        assert msg.round_number == sample_contribution_dict["round_number"]
        assert msg.phase == DeliberationPhaseType.EXPLORATION
        assert msg.cost == sample_contribution_dict["cost"]
        # Note: DB column is 'tokens', model field is 'token_count'
        assert msg.token_count == sample_contribution_dict["tokens"]
        assert msg.model == sample_contribution_dict["model"]

    def test_contribution_message_from_db_row_minimal(self) -> None:
        """from_db_row() handles minimal data (only required fields)."""
        row = {
            "persona_code": "ceo",
            "content": "Test content",
            "round_number": 0,
        }
        msg = ContributionMessage.from_db_row(row)

        assert msg.persona_code == "ceo"
        assert msg.persona_name == "ceo"  # Falls back to code
        assert msg.content == "Test content"
        assert msg.round_number == 0
        assert msg.id is None
        assert msg.session_id is None

    def test_tokens_used_alias(self) -> None:
        """tokens_used property returns token_count for backward compat."""
        msg = ContributionMessage(
            persona_code="test",
            persona_name="Test",
            content="test",
            round_number=0,
            token_count=150,
        )
        assert msg.tokens_used == 150

        # When token_count is None
        msg2 = ContributionMessage(
            persona_code="test",
            persona_name="Test",
            content="test",
            round_number=0,
        )
        assert msg2.tokens_used == 0


class TestDeliberationPhaseTypeEnum:
    """Test DeliberationPhaseType enum matches DB values."""

    def test_deliberation_phase_type_enum_values(self) -> None:
        """All DB phase values are covered."""
        expected_values = {"exploration", "challenge", "convergence"}
        actual_values = {e.value for e in DeliberationPhaseType}
        assert actual_values == expected_values

    def test_phase_string_to_enum(self) -> None:
        """Phase strings convert to enum correctly."""
        assert DeliberationPhaseType("exploration") == DeliberationPhaseType.EXPLORATION
        assert DeliberationPhaseType("challenge") == DeliberationPhaseType.CHALLENGE
        assert DeliberationPhaseType("convergence") == DeliberationPhaseType.CONVERGENCE


class TestDeliberationPhaseEnum:
    """Test DeliberationPhase workflow enum."""

    def test_deliberation_phase_values(self) -> None:
        """All workflow phase values are present."""
        expected = {
            "intake",
            "decomposition",
            "selection",
            "initial_round",
            "discussion",
            "voting",
            "synthesis",
            "complete",
        }
        actual = {e.value for e in DeliberationPhase}
        assert actual == expected


class TestDeliberationMetrics:
    """Test DeliberationMetrics model serialization."""

    def test_deliberation_metrics_optional_fields(self) -> None:
        """Optional score fields handle None correctly."""
        metrics = DeliberationMetrics()

        # All optional scores should be None by default
        assert metrics.convergence_score is None
        assert metrics.novelty_score is None
        assert metrics.conflict_score is None
        assert metrics.exploration_score is None
        assert metrics.focus_score is None
        assert metrics.meeting_completeness_index is None
        assert metrics.complexity_score is None

        # Roundtrip
        json_str = metrics.model_dump_json()
        restored = DeliberationMetrics.model_validate_json(json_str)

        assert restored.convergence_score is None
        assert restored.exploration_score is None

    def test_deliberation_metrics_with_values(self) -> None:
        """Metrics with values serialize correctly."""
        metrics = DeliberationMetrics(
            total_cost=0.50,
            total_tokens=5000,
            cache_hits=3,
            convergence_score=0.85,
            exploration_score=0.72,
            focus_score=0.90,
            complexity_score=0.65,
            recommended_rounds=5,
            recommended_experts=4,
        )

        json_str = metrics.model_dump_json()
        restored = DeliberationMetrics.model_validate_json(json_str)

        assert restored.total_cost == 0.50
        assert restored.total_tokens == 5000
        assert restored.cache_hits == 3
        assert restored.convergence_score == 0.85
        assert restored.exploration_score == 0.72
        assert restored.focus_score == 0.90
        assert restored.complexity_score == 0.65
        assert restored.recommended_rounds == 5
        assert restored.recommended_experts == 4


class TestAspectCoverage:
    """Test AspectCoverage nested model."""

    def test_aspect_coverage_roundtrip(self) -> None:
        """AspectCoverage serializes correctly."""
        coverage = AspectCoverage(
            name="risks_failure_modes",
            level="deep",
            notes="Maria identified 3 major risks with mitigation strategies",
        )

        json_str = coverage.model_dump_json()
        restored = AspectCoverage.model_validate_json(json_str)

        assert restored.name == coverage.name
        assert restored.level == coverage.level
        assert restored.notes == coverage.notes

    def test_aspect_coverage_level_values(self) -> None:
        """Level field accepts valid values."""
        for level in ["none", "shallow", "deep"]:
            coverage = AspectCoverage(name="test", level=level)
            assert coverage.level == level


class TestSubProblemResult:
    """Test SubProblemResult model."""

    def test_sub_problem_result_roundtrip(self) -> None:
        """SubProblemResult with all fields round-trips."""
        result = SubProblemResult(
            sub_problem_id="sp_001",
            sub_problem_goal="Determine target CAC",
            synthesis="Based on deliberation, target CAC should be <$150...",
            votes=[],
            contribution_count=15,
            cost=0.12,
            duration_seconds=180.5,
            expert_panel=["maria", "zara", "chen"],
            expert_summaries={
                "maria": "Recommended CAC <$150",
                "zara": "Emphasized testing paid channels",
            },
        )

        json_str = result.model_dump_json()
        restored = SubProblemResult.model_validate_json(json_str)

        assert restored.sub_problem_id == result.sub_problem_id
        assert restored.sub_problem_goal == result.sub_problem_goal
        assert restored.synthesis == result.synthesis
        assert restored.contribution_count == result.contribution_count
        assert restored.cost == result.cost
        assert restored.duration_seconds == result.duration_seconds
        assert restored.expert_panel == result.expert_panel
        assert restored.expert_summaries == result.expert_summaries
