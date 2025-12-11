"""Unit tests for state serialization roundtrip.

Tests serialize_state_for_checkpoint and deserialize_state_from_checkpoint
for edge cases: empty collections, None values, missing keys, extra keys,
and SubProblemResult serialization.
"""

import pytest

from bo1.graph.state import (
    DeliberationGraphState,
    create_initial_state,
    deserialize_state_from_checkpoint,
    serialize_state_for_checkpoint,
)
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import (
    ContributionMessage,
    ContributionType,
    DeliberationMetrics,
    DeliberationPhase,
    SubProblemResult,
)


@pytest.fixture
def sample_problem() -> Problem:
    """Create a sample problem with sub-problems."""
    return Problem(
        title="Scaling Strategy",
        description="How should we scale?",
        context="B2B SaaS with 100 users",
        sub_problems=[
            SubProblem(
                id="sp1",
                goal="Define target market",
                context="Need to understand ideal customer",
                complexity_score=5,
                dependencies=[],
            ),
            SubProblem(
                id="sp2",
                goal="Choose tech stack",
                context="Evaluate options for scalability",
                complexity_score=7,
                dependencies=["sp1"],
            ),
        ],
    )


@pytest.fixture
def sample_persona() -> PersonaProfile:
    """Create a sample persona from catalog."""
    from bo1.data import get_persona_by_code

    persona_data = get_persona_by_code("growth_hacker")
    if not persona_data:
        pytest.skip("growth_hacker persona not found in catalog")
    return PersonaProfile(**persona_data)


@pytest.fixture
def sample_contribution() -> ContributionMessage:
    """Create a sample contribution."""
    return ContributionMessage(
        persona_code="ceo",
        persona_name="CEO",
        content="We should focus on enterprise.",
        round_number=1,
        contribution_type=ContributionType.INITIAL,
    )


@pytest.fixture
def sample_sub_problem_result() -> SubProblemResult:
    """Create a sample sub-problem result."""
    return SubProblemResult(
        sub_problem_id="sp1",
        sub_problem_goal="Define target market",
        synthesis="Target SMB market first.",
        votes=[],
        contribution_count=5,
        cost=0.05,
        duration_seconds=120.5,
        expert_panel=["ceo", "cfo"],
        expert_summaries={"ceo": "Recommended SMB focus."},
    )


class TestSerializeDeserializeRoundtrip:
    """Test full roundtrip serialization."""

    def test_roundtrip_full_state(
        self,
        sample_problem: Problem,
        sample_persona: PersonaProfile,
        sample_contribution: ContributionMessage,
        sample_sub_problem_result: SubProblemResult,
    ) -> None:
        """Full state survives serialize/deserialize roundtrip."""
        state = create_initial_state(
            session_id="test_123",
            problem=sample_problem,
            personas=[sample_persona],
            max_rounds=5,
        )
        # Add contributions and sub_problem_results
        state["contributions"] = [sample_contribution]
        state["sub_problem_results"] = [sample_sub_problem_result]
        state["current_sub_problem"] = sample_problem.sub_problems[0]

        # Serialize
        serialized = serialize_state_for_checkpoint(state)

        # All Pydantic models should be dicts now
        assert isinstance(serialized["problem"], dict)
        assert isinstance(serialized["personas"][0], dict)
        assert isinstance(serialized["contributions"][0], dict)
        assert isinstance(serialized["metrics"], dict)
        assert isinstance(serialized["sub_problem_results"][0], dict)
        assert isinstance(serialized["current_sub_problem"], dict)

        # Deserialize
        deserialized = deserialize_state_from_checkpoint(serialized)

        # All should be Pydantic models again
        assert isinstance(deserialized["problem"], Problem)
        assert isinstance(deserialized["personas"][0], PersonaProfile)
        assert isinstance(deserialized["contributions"][0], ContributionMessage)
        assert isinstance(deserialized["metrics"], DeliberationMetrics)
        assert isinstance(deserialized["sub_problem_results"][0], SubProblemResult)
        assert isinstance(deserialized["current_sub_problem"], SubProblem)

        # Verify data integrity
        assert deserialized["problem"].title == "Scaling Strategy"
        assert len(deserialized["problem"].sub_problems) == 2
        assert deserialized["personas"][0].code == "growth_hacker"
        assert deserialized["contributions"][0].content == "We should focus on enterprise."
        assert deserialized["sub_problem_results"][0].synthesis == "Target SMB market first."


class TestEmptyCollections:
    """Test handling of empty collections."""

    def test_empty_lists_preserved(self, sample_problem: Problem) -> None:
        """Empty lists are preserved as [] not None."""
        state = create_initial_state(
            session_id="test_empty",
            problem=sample_problem,
        )
        # Ensure empty lists
        assert state["personas"] == []
        assert state["contributions"] == []
        assert state["sub_problem_results"] == []

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        # Empty lists should remain empty lists
        assert deserialized["personas"] == []
        assert deserialized["contributions"] == []
        assert deserialized["sub_problem_results"] == []


class TestNoneValues:
    """Test handling of None values."""

    def test_none_values_preserved(self, sample_problem: Problem) -> None:
        """None values are preserved, not omitted."""
        state = create_initial_state(
            session_id="test_none",
            problem=sample_problem,
        )
        # Set explicit None values
        state["current_sub_problem"] = None
        state["synthesis"] = None
        state["facilitator_decision"] = None

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        assert deserialized.get("current_sub_problem") is None
        assert deserialized.get("synthesis") is None
        assert deserialized.get("facilitator_decision") is None


class TestForwardCompatibility:
    """Test forward compatibility (old code, new checkpoint)."""

    def test_deserialize_handles_extra_keys(self, sample_problem: Problem) -> None:
        """Extra keys in checkpoint are preserved (new fields)."""
        state = create_initial_state(
            session_id="test_forward",
            problem=sample_problem,
        )
        serialized = serialize_state_for_checkpoint(state)

        # Simulate a checkpoint from newer code with extra field
        serialized["future_field"] = {"data": "from_future"}

        deserialized = deserialize_state_from_checkpoint(serialized)

        # Extra field should be preserved
        assert deserialized["future_field"] == {"data": "from_future"}


class TestBackwardCompatibility:
    """Test backward compatibility (new code, old checkpoint)."""

    def test_deserialize_handles_missing_keys(self) -> None:
        """Missing keys don't cause errors (old checkpoints)."""
        # Minimal checkpoint from old code version - Problem has required fields
        minimal_checkpoint = {
            "session_id": "test_backward",
            "problem": {
                "title": "Test",
                "description": "Test problem",
                "context": "Test context",
                "sub_problems": [],
            },
            "phase": DeliberationPhase.INTAKE,
            "round_number": 0,
            "max_rounds": 5,
            # Missing: personas, contributions, metrics, sub_problem_results, etc.
        }

        deserialized = deserialize_state_from_checkpoint(minimal_checkpoint)

        # Should not raise, missing fields stay missing
        assert deserialized["session_id"] == "test_backward"
        assert isinstance(deserialized["problem"], Problem)
        # These fields are absent, not None
        assert "personas" not in deserialized
        assert "contributions" not in deserialized
        assert "sub_problem_results" not in deserialized


class TestMixedTypes:
    """Test handling of mixed Pydantic/dict in lists."""

    def test_mixed_pydantic_dict_in_contributions(
        self,
        sample_problem: Problem,
        sample_contribution: ContributionMessage,
    ) -> None:
        """Lists with mixed Pydantic/dict items handled correctly."""
        state: DeliberationGraphState = {
            "session_id": "test_mixed",
            "problem": sample_problem,
            "personas": [],
            "contributions": [
                sample_contribution,  # Pydantic
                {  # Already a dict (e.g., partially deserialized)
                    "persona_code": "cfo",
                    "persona_name": "CFO",
                    "content": "Budget concerns.",
                    "round_number": 1,
                },
            ],
            "round_summaries": [],
            "phase": DeliberationPhase.DISCUSSION,
            "round_number": 1,
            "max_rounds": 5,
            "metrics": DeliberationMetrics(),
            "sub_problem_results": [],
        }

        serialized = serialize_state_for_checkpoint(state)

        # Both should be dicts after serialization
        assert isinstance(serialized["contributions"][0], dict)
        assert isinstance(serialized["contributions"][1], dict)

        deserialized = deserialize_state_from_checkpoint(serialized)

        # Both should be Pydantic after deserialization
        assert isinstance(deserialized["contributions"][0], ContributionMessage)
        assert isinstance(deserialized["contributions"][1], ContributionMessage)


class TestSubProblemResultSerialization:
    """Test SubProblemResult serialization specifically."""

    def test_sub_problem_result_roundtrip(
        self,
        sample_sub_problem_result: SubProblemResult,
    ) -> None:
        """SubProblemResult survives roundtrip with all fields."""
        state: DeliberationGraphState = {
            "session_id": "test_spr",
            "sub_problem_results": [sample_sub_problem_result],
            "phase": DeliberationPhase.COMPLETE,
            "round_number": 3,
            "max_rounds": 5,
        }

        serialized = serialize_state_for_checkpoint(state)
        assert isinstance(serialized["sub_problem_results"][0], dict)
        assert serialized["sub_problem_results"][0]["expert_panel"] == ["ceo", "cfo"]

        deserialized = deserialize_state_from_checkpoint(serialized)
        result = deserialized["sub_problem_results"][0]

        assert isinstance(result, SubProblemResult)
        assert result.sub_problem_id == "sp1"
        assert result.synthesis == "Target SMB market first."
        assert result.expert_panel == ["ceo", "cfo"]
        assert result.expert_summaries == {"ceo": "Recommended SMB focus."}
        assert result.cost == 0.05
        assert result.duration_seconds == 120.5

    def test_multiple_sub_problem_results(
        self,
        sample_sub_problem_result: SubProblemResult,
    ) -> None:
        """Multiple SubProblemResults serialize/deserialize correctly."""
        spr2 = SubProblemResult(
            sub_problem_id="sp2",
            sub_problem_goal="Choose tech stack",
            synthesis="Use Python + FastAPI.",
            votes=[],
            contribution_count=8,
            cost=0.08,
            duration_seconds=200.0,
        )

        state: DeliberationGraphState = {
            "session_id": "test_multi_spr",
            "sub_problem_results": [sample_sub_problem_result, spr2],
            "phase": DeliberationPhase.COMPLETE,
            "round_number": 5,
            "max_rounds": 5,
        }

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        assert len(deserialized["sub_problem_results"]) == 2
        assert deserialized["sub_problem_results"][0].sub_problem_id == "sp1"
        assert deserialized["sub_problem_results"][1].sub_problem_id == "sp2"
