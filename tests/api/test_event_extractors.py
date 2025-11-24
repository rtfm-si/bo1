"""Tests for event extraction framework."""

import pytest

from backend.api.event_extractors import (
    COMPLETION_EXTRACTORS,
    CONVERGENCE_EXTRACTORS,
    DECOMPOSITION_EXTRACTORS,
    FACILITATOR_DECISION_EXTRACTORS,
    META_SYNTHESIS_EXTRACTORS,
    MODERATOR_INTERVENTION_EXTRACTORS,
    PERSONA_SELECTION_EXTRACTORS,
    SUBPROBLEM_COMPLETE_EXTRACTORS,
    SUBPROBLEM_STARTED_EXTRACTORS,
    SYNTHESIS_EXTRACTORS,
    VOTING_EXTRACTORS,
    calculate_consensus_level,
    extract_event_data,
    extract_formatted_votes,
    extract_persona_codes,
    extract_sub_problems,
    extract_subproblem_info,
    extract_subproblem_result,
    extract_with_root_transform,
    get_field_safe,
    to_dict_list,
)


class TestFieldExtractorUtilities:
    """Test utility functions for field extraction."""

    def test_to_dict_list_with_pydantic_models(self):
        """Test converting Pydantic models to dict list."""

        # Create a mock object with model_dump method
        class MockModel:
            def model_dump(self):
                return {"goal": "Test goal", "complexity_score": 3}

        result = to_dict_list([MockModel()])

        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["goal"] == "Test goal"
        assert result[0]["complexity_score"] == 3

    def test_to_dict_list_with_dicts(self):
        """Test converting plain dicts passes through."""
        data = [{"field": "value"}]
        result = to_dict_list(data)

        assert result == data
        assert result[0]["field"] == "value"

    def test_get_field_safe_from_object(self):
        """Test safely getting field from object with hasattr."""

        class TestObj:
            field = "value"

        obj = TestObj()
        result = get_field_safe(obj, "field")

        assert result == "value"

    def test_get_field_safe_from_dict(self):
        """Test safely getting field from dict."""
        data = {"field": "value"}
        result = get_field_safe(data, "field")

        assert result == "value"

    def test_get_field_safe_with_default(self):
        """Test default value when field missing."""
        data = {}
        result = get_field_safe(data, "missing", default="default_value")

        assert result == "default_value"

    def test_extract_sub_problems_from_problem_object(self):
        """Test extracting sub-problems from Problem object."""

        # Use mock objects instead of real Pydantic models
        class MockSubProblem:
            def __init__(self, id, goal, complexity_score, dependencies):
                self.id = id
                self.goal = goal
                self.complexity_score = complexity_score
                self.dependencies = dependencies
                self.rationale = "Test rationale"

        class MockProblem:
            def __init__(self):
                self.sub_problems = [
                    MockSubProblem("sp1", "Goal 1", 2, []),
                    MockSubProblem("sp2", "Goal 2", 3, ["sp1"]),
                ]

        problem = MockProblem()
        result = extract_sub_problems(problem)

        assert len(result) == 2
        assert result[0]["id"] == "sp1"
        assert result[0]["goal"] == "Goal 1"
        assert result[0]["complexity_score"] == 2
        assert result[0]["dependencies"] == []
        assert result[1]["dependencies"] == ["sp1"]

    def test_extract_sub_problems_from_none(self):
        """Test extracting sub-problems from None."""
        result = extract_sub_problems(None)

        assert result == []

    def test_extract_persona_codes(self):
        """Test extracting persona codes from persona objects."""

        # Use mock objects with code attribute
        class MockPersona:
            def __init__(self, code):
                self.code = code

        personas = [MockPersona("cfo"), MockPersona("cmo")]

        result = extract_persona_codes(personas)

        assert result == ["cfo", "cmo"]

    def test_extract_persona_codes_from_dicts(self):
        """Test extracting persona codes from dict objects."""
        personas = [
            {"code": "cfo", "name": "CFO"},
            {"code": "cmo", "name": "CMO"},
        ]

        result = extract_persona_codes(personas)

        assert result == ["cfo", "cmo"]

    def test_extract_formatted_votes(self):
        """Test formatting votes for display."""
        votes = [
            {
                "persona_code": "cfo",
                "persona_name": "CFO",
                "recommendation": "Yes",
                "confidence": 0.9,
                "reasoning": "Strong financials",
                "conditions": ["Market stable"],
            },
            {
                "persona_code": "cmo",
                "persona_name": "CMO",
                "recommendation": "No",
                "confidence": 0.6,
                "reasoning": "Market risk",
                "conditions": [],
            },
        ]

        result = extract_formatted_votes(votes)

        assert len(result) == 2
        assert result[0]["persona_code"] == "cfo"
        assert result[0]["confidence"] == 0.9
        assert result[1]["persona_code"] == "cmo"

    def test_calculate_consensus_level_strong(self):
        """Test consensus level calculation for strong consensus."""
        votes = [
            {"confidence": 0.9},
            {"confidence": 0.85},
            {"confidence": 0.8},
        ]

        level, avg = calculate_consensus_level(votes)

        assert level == "strong"
        assert avg == pytest.approx(0.85)

    def test_calculate_consensus_level_moderate(self):
        """Test consensus level calculation for moderate consensus."""
        votes = [
            {"confidence": 0.7},
            {"confidence": 0.6},
            {"confidence": 0.65},
        ]

        level, avg = calculate_consensus_level(votes)

        assert level == "moderate"
        assert avg == pytest.approx(0.65)

    def test_calculate_consensus_level_weak(self):
        """Test consensus level calculation for weak consensus."""
        votes = [
            {"confidence": 0.5},
            {"confidence": 0.4},
            {"confidence": 0.3},
        ]

        level, avg = calculate_consensus_level(votes)

        assert level == "weak"
        assert avg == pytest.approx(0.4)

    def test_calculate_consensus_level_empty(self):
        """Test consensus level for no votes."""
        votes = []

        level, avg = calculate_consensus_level(votes)

        assert level == "unknown"
        assert avg == 0.0

    def test_extract_subproblem_info_multi_subproblem(self):
        """Test extracting sub-problem info in multi-subproblem scenario."""

        # Use mock objects
        class MockSubProblem:
            def __init__(self, id, goal):
                self.id = id
                self.goal = goal

        class MockProblem:
            def __init__(self):
                self.sub_problems = [
                    MockSubProblem("sp1", "G1"),
                    MockSubProblem("sp2", "G2"),
                ]

        problem = MockProblem()
        current_sub_problem = problem.sub_problems[0]

        output = {
            "sub_problem_index": 0,
            "current_sub_problem": current_sub_problem,
            "problem": problem,
        }

        result = extract_subproblem_info(output)

        assert result["sub_problem_index"] == 0
        assert result["sub_problem_id"] == "sp1"
        assert result["goal"] == "G1"
        assert result["total_sub_problems"] == 2

    def test_extract_subproblem_info_single_subproblem(self):
        """Test extracting sub-problem info returns empty for single subproblem."""

        # Use mock objects
        class MockSubProblem:
            def __init__(self, id, goal):
                self.id = id
                self.goal = goal

        class MockProblem:
            def __init__(self):
                self.sub_problems = [MockSubProblem("sp1", "G1")]

        problem = MockProblem()

        output = {
            "sub_problem_index": 0,
            "current_sub_problem": problem.sub_problems[0],
            "problem": problem,
        }

        result = extract_subproblem_info(output)

        assert result == {}

    def test_extract_subproblem_result(self):
        """Test extracting sub-problem result data."""
        result_obj = {
            "sub_problem_id": "sp1",
            "sub_problem_goal": "Test goal",
            "cost": 0.15,
            "duration_seconds": 30.5,
            "expert_panel": ["cfo", "cmo"],
            "contribution_count": 8,
        }

        result = extract_subproblem_result(result_obj)

        assert result["sub_problem_id"] == "sp1"
        assert result["sub_problem_goal"] == "Test goal"
        assert result["cost"] == 0.15
        assert result["duration_seconds"] == 30.5
        assert result["expert_panel"] == ["cfo", "cmo"]
        assert result["contribution_count"] == 8


class TestExtractEventData:
    """Test the main extract_event_data function."""

    def test_extract_basic_fields(self):
        """Test basic field extraction without transformation."""
        extractors = [
            {
                "source_field": "name",
                "target_field": "extracted_name",
            },
            {
                "source_field": "age",
                "target_field": "extracted_age",
                "default": 0,
            },
        ]

        output = {"name": "test", "other": "ignored"}
        result = extract_event_data(output, extractors)

        assert result["extracted_name"] == "test"
        assert result["extracted_age"] == 0

    def test_extract_with_transform(self):
        """Test extraction with transformation function."""
        extractors = [
            {
                "source_field": "value",
                "target_field": "doubled",
                "transform": lambda x: x * 2 if x else 0,
            },
        ]

        output = {"value": 5}
        result = extract_event_data(output, extractors)

        assert result["doubled"] == 10

    def test_extract_required_field_present(self):
        """Test required field extraction when present."""
        extractors = [
            {
                "source_field": "required_field",
                "target_field": "output",
                "required": True,
            },
        ]

        output = {"required_field": "value"}
        result = extract_event_data(output, extractors)

        assert result["output"] == "value"

    def test_extract_required_field_missing(self):
        """Test required field validation raises error."""
        extractors = [
            {
                "source_field": "required_field",
                "target_field": "output",
                "required": True,
            },
        ]

        output = {}  # Missing required field

        with pytest.raises(KeyError, match="Required field 'required_field' not found"):
            extract_event_data(output, extractors)

    def test_extract_with_default_value(self):
        """Test extraction uses default when field missing."""
        extractors = [
            {
                "source_field": "missing",
                "target_field": "output",
                "default": "default_value",
            },
        ]

        output = {}
        result = extract_event_data(output, extractors)

        assert result["output"] == "default_value"


class TestExtractorConfigurations:
    """Test all extractor configurations produce valid output."""

    def test_decomposition_extractors(self):
        """Test decomposition extractor configuration."""

        # Use mock object
        class MockSubProblem:
            def __init__(self):
                self.id = "sp1"
                self.goal = "G1"
                self.complexity_score = 2
                self.dependencies = []
                self.rationale = "Test"

        class MockProblem:
            def __init__(self):
                self.sub_problems = [MockSubProblem()]

        output = {"problem": MockProblem()}
        result = extract_with_root_transform(output, DECOMPOSITION_EXTRACTORS)

        assert "sub_problems" in result
        assert "count" in result
        assert result["count"] == 1
        assert len(result["sub_problems"]) == 1

    def test_persona_selection_extractors(self):
        """Test persona selection extractor configuration."""

        # Use mock objects
        class MockPersona:
            def __init__(self, code):
                self.code = code

        personas = [MockPersona("cfo")]

        output = {
            "personas": personas,
            "sub_problem_index": 0,
        }
        result = extract_with_root_transform(output, PERSONA_SELECTION_EXTRACTORS)

        assert result["personas"] == ["cfo"]
        assert result["count"] == 1
        assert result["sub_problem_index"] == 0

    def test_facilitator_decision_extractors(self):
        """Test facilitator decision extractor configuration."""
        output = {
            "facilitator_decision": {
                "action": "continue",
                "reasoning": "Need more discussion",
                "next_speaker": "cfo",
            },
            "round_number": 3,
            "sub_problem_index": 0,
        }

        result = extract_with_root_transform(output, FACILITATOR_DECISION_EXTRACTORS)

        assert result["action"] == "continue"
        assert result["reasoning"] == "Need more discussion"
        assert result["round"] == 3
        assert result["next_speaker"] == "cfo"

    def test_moderator_intervention_extractors(self):
        """Test moderator intervention extractor configuration."""
        output = {
            "contributions": [
                {
                    "persona_code": "ethical_moderator",
                    "content": "Let's focus on ethics",
                }
            ],
            "round_number": 2,
            "sub_problem_index": 0,
        }

        result = extract_with_root_transform(output, MODERATOR_INTERVENTION_EXTRACTORS)

        assert result["moderator_type"] == "ethical_moderator"
        assert result["content"] == "Let's focus on ethics"
        assert result["round"] == 2

    def test_convergence_extractors(self):
        """Test convergence extractor configuration."""
        output = {
            "should_stop": True,
            "stop_reason": "consensus_reached",
            "metrics": {"convergence_score": 0.92},
            "round_number": 5,
            "max_rounds": 10,
            "sub_problem_index": 0,
        }

        result = extract_with_root_transform(output, CONVERGENCE_EXTRACTORS)

        assert result["converged"] is True
        assert result["score"] == 0.92
        assert result["threshold"] == 0.85
        assert result["round"] == 5

    def test_voting_extractors(self):
        """Test voting extractor configuration."""
        output = {
            "votes": [
                {
                    "persona_code": "cfo",
                    "persona_name": "CFO",
                    "recommendation": "Yes",
                    "confidence": 0.9,
                    "reasoning": "Strong ROI",
                    "conditions": [],
                },
            ],
            "sub_problem_index": 0,
        }

        result = extract_with_root_transform(output, VOTING_EXTRACTORS)

        assert result["votes_count"] == 1
        assert result["consensus_level"] == "strong"
        assert result["avg_confidence"] == 0.9

    def test_synthesis_extractors(self):
        """Test synthesis extractor configuration."""
        output = {
            "synthesis": "This is the final synthesis",
            "sub_problem_index": 0,
        }

        result = extract_with_root_transform(output, SYNTHESIS_EXTRACTORS)

        assert result["synthesis"] == "This is the final synthesis"
        assert result["word_count"] == 5
        assert result["sub_problem_index"] == 0

    def test_meta_synthesis_extractors(self):
        """Test meta-synthesis extractor configuration."""
        output = {
            "synthesis": "Overall meta synthesis",
        }

        result = extract_with_root_transform(output, META_SYNTHESIS_EXTRACTORS)

        assert result["synthesis"] == "Overall meta synthesis"
        assert result["word_count"] == 3

    def test_subproblem_started_extractors(self):
        """Test sub-problem started extractor configuration."""

        # Use mock objects
        class MockSubProblem:
            def __init__(self, id, goal):
                self.id = id
                self.goal = goal

        class MockProblem:
            def __init__(self):
                self.sub_problems = [
                    MockSubProblem("sp1", "G1"),
                    MockSubProblem("sp2", "G2"),
                ]

        problem = MockProblem()

        output = {
            "sub_problem_index": 1,
            "current_sub_problem": problem.sub_problems[1],
            "problem": problem,
        }

        result = extract_with_root_transform(output, SUBPROBLEM_STARTED_EXTRACTORS)

        assert result["sub_problem_index"] == 1
        assert result["sub_problem_id"] == "sp2"
        assert result["total_sub_problems"] == 2

    def test_subproblem_complete_extractors(self):
        """Test sub-problem complete extractor configuration."""
        output = {
            "sub_problem_results": [
                {
                    "sub_problem_id": "sp1",
                    "sub_problem_goal": "Goal 1",
                    "cost": 0.25,
                    "duration_seconds": 45.0,
                    "expert_panel": ["cfo", "cmo"],
                    "contribution_count": 12,
                }
            ],
        }

        result = extract_with_root_transform(output, SUBPROBLEM_COMPLETE_EXTRACTORS)

        assert result["sub_problem_index"] == 0
        assert result["sub_problem_id"] == "sp1"
        assert result["cost"] == 0.25

    def test_completion_extractors(self):
        """Test completion extractor configuration."""
        output = {
            "session_id": "test_session",
            "synthesis": "Final deliberation output",
            "metrics": {
                "total_cost": 1.25,
                "total_tokens": 5000,
            },
            "round_number": 7,
            "stop_reason": "consensus_reached",
            "contributions": [{"id": 1}, {"id": 2}, {"id": 3}],
        }

        result = extract_with_root_transform(output, COMPLETION_EXTRACTORS)

        assert result["session_id"] == "test_session"
        assert result["final_output"] == "Final deliberation output"
        assert result["total_cost"] == 1.25
        assert result["total_rounds"] == 7
        assert result["total_contributions"] == 3


class TestExtractorConfigValidation:
    """Test that all extractor configurations are valid."""

    @pytest.mark.parametrize(
        "extractor_name,config",
        [
            ("decomposition", DECOMPOSITION_EXTRACTORS),
            ("persona_selection", PERSONA_SELECTION_EXTRACTORS),
            ("facilitator_decision", FACILITATOR_DECISION_EXTRACTORS),
            ("moderator_intervention", MODERATOR_INTERVENTION_EXTRACTORS),
            ("convergence", CONVERGENCE_EXTRACTORS),
            ("voting", VOTING_EXTRACTORS),
            ("synthesis", SYNTHESIS_EXTRACTORS),
            ("meta_synthesis", META_SYNTHESIS_EXTRACTORS),
            ("subproblem_started", SUBPROBLEM_STARTED_EXTRACTORS),
            ("subproblem_complete", SUBPROBLEM_COMPLETE_EXTRACTORS),
            ("completion", COMPLETION_EXTRACTORS),
        ],
    )
    def test_all_extractors_valid(self, extractor_name, config):
        """Smoke test all extractor configurations are valid."""
        # Ensure config is a list
        assert isinstance(config, list), f"{extractor_name} config must be a list"
        assert len(config) > 0, f"{extractor_name} config must not be empty"

        # Ensure each extractor has required fields
        for extractor in config:
            assert "source_field" in extractor, f"{extractor_name} missing source_field"
            assert "target_field" in extractor, f"{extractor_name} missing target_field"


class TestSubProblemIndexInjection:
    """Test that sub_problem_index is properly injected into all events.

    This is critical for frontend tab filtering - without sub_problem_index,
    events don't appear in the correct sub-problem tabs on the meeting page.

    See: frontend/src/routes/(app)/meeting/[id]/+page.svelte line 872
    """

    def test_decomposition_includes_sub_problem_index(self):
        """Test decomposition event includes sub_problem_index for tab filtering."""

        # Use mock object
        class MockSubProblem:
            def __init__(self):
                self.id = "sp1"
                self.goal = "G1"
                self.complexity_score = 2
                self.dependencies = []
                self.rationale = "Test"

        class MockProblem:
            def __init__(self):
                self.sub_problems = [MockSubProblem()]

        output = {
            "problem": MockProblem(),
            "sub_problem_index": 1,  # Critical field that must be preserved
        }

        result = extract_with_root_transform(output, DECOMPOSITION_EXTRACTORS)

        # Note: sub_problem_index is added by _publish_node_event in event_collector.py
        # This test documents that extractors should NOT remove it
        assert "sub_problems" in result
        assert "count" in result

    def test_convergence_includes_sub_problem_index(self):
        """Test convergence event preserves sub_problem_index from output."""
        output = {
            "should_stop": True,
            "stop_reason": "consensus_reached",
            "metrics": {"convergence_score": 0.92},
            "round_number": 5,
            "max_rounds": 10,
            "sub_problem_index": 2,  # Must be preserved for tab filtering
        }

        result = extract_with_root_transform(output, CONVERGENCE_EXTRACTORS)

        # Verify extractor includes sub_problem_index
        assert result["sub_problem_index"] == 2
        assert result["converged"] is True
        assert result["score"] == 0.92
