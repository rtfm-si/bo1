"""Tests for problem models roundtrip serialization."""

from bo1.models import Constraint, ConstraintType, Problem, SubProblem
from bo1.models.problem import SubProblemFocus


class TestProblemRoundtrip:
    """Test Problem model serialization."""

    def test_problem_roundtrip_with_subproblems(self, sample_problem_dict: dict) -> None:
        """Problem with nested SubProblems round-trips correctly."""
        problem = Problem(**sample_problem_dict)

        # Serialize to JSON
        json_str = problem.model_dump_json()

        # Deserialize back
        restored = Problem.model_validate_json(json_str)

        assert restored.title == problem.title
        assert restored.description == problem.description
        assert restored.context == problem.context
        assert len(restored.constraints) == len(problem.constraints)
        assert len(restored.sub_problems) == len(problem.sub_problems)

        # Verify nested constraints
        for orig, rest in zip(problem.constraints, restored.constraints, strict=True):
            assert rest.type == orig.type
            assert rest.description == orig.description
            assert rest.value == orig.value

        # Verify nested sub-problems
        for orig, rest in zip(problem.sub_problems, restored.sub_problems, strict=True):
            assert rest.id == orig.id
            assert rest.goal == orig.goal
            assert rest.context == orig.context
            assert rest.complexity_score == orig.complexity_score
            assert rest.dependencies == orig.dependencies

    def test_problem_is_atomic_property(self) -> None:
        """is_atomic computed property works correctly."""
        # No sub-problems = atomic
        problem = Problem(
            title="Simple",
            description="Simple problem",
            context="Context",
        )
        assert problem.is_atomic is True

        # One sub-problem = still atomic
        problem_one = Problem(
            title="One SP",
            description="One sub-problem",
            context="Context",
            sub_problems=[
                SubProblem(
                    id="sp_001",
                    goal="Goal",
                    context="Context",
                    complexity_score=3,
                )
            ],
        )
        assert problem_one.is_atomic is True

        # Multiple sub-problems = not atomic
        problem_multi = Problem(
            title="Multiple",
            description="Multiple sub-problems",
            context="Context",
            sub_problems=[
                SubProblem(id="sp_001", goal="Goal 1", context="Context", complexity_score=3),
                SubProblem(id="sp_002", goal="Goal 2", context="Context", complexity_score=4),
            ],
        )
        assert problem_multi.is_atomic is False

    def test_problem_get_sub_problem(self, sample_problem_dict: dict) -> None:
        """get_sub_problem() retrieves by ID correctly."""
        problem = Problem(**sample_problem_dict)

        sp1 = problem.get_sub_problem("sp_001")
        assert sp1 is not None
        assert sp1.goal == "Determine channel mix"

        sp2 = problem.get_sub_problem("sp_002")
        assert sp2 is not None
        assert sp2.goal == "Set CAC targets per channel"

        # Non-existent ID returns None
        assert problem.get_sub_problem("sp_999") is None


class TestConstraintTypeEnum:
    """Test ConstraintType enum completeness."""

    def test_constraint_type_enum_values(self) -> None:
        """All constraint types are covered."""
        expected = {"budget", "time", "resource", "regulatory", "technical", "ethical", "other"}
        actual = {e.value for e in ConstraintType}
        assert actual == expected

    def test_constraint_type_serialization(self) -> None:
        """ConstraintType enum serializes as string."""
        for ctype in ConstraintType:
            constraint = Constraint(type=ctype, description="Test")
            data = constraint.model_dump()
            assert data["type"] == ctype.value

            # Roundtrip
            json_str = constraint.model_dump_json()
            restored = Constraint.model_validate_json(json_str)
            assert restored.type == ctype


class TestSubProblemFocusOptional:
    """Test SubProblemFocus optional handling."""

    def test_subproblem_focus_optional(self) -> None:
        """SubProblem with None focus serializes correctly."""
        sp = SubProblem(
            id="sp_001",
            goal="Test goal",
            context="Test context",
            complexity_score=5,
        )
        assert sp.focus is None

        json_str = sp.model_dump_json()
        restored = SubProblem.model_validate_json(json_str)
        assert restored.focus is None

    def test_subproblem_focus_with_value(self) -> None:
        """SubProblem with focus data serializes correctly."""
        focus = SubProblemFocus(
            key_questions=["What is the target CAC?", "Which channels to prioritize?"],
            risks_to_mitigate=["Budget overrun", "Channel saturation"],
            alternatives_to_consider=["Organic only", "Paid only", "Hybrid"],
            required_expertise=["marketing", "finance"],
            success_criteria=["CAC < $150", "ROAS > 3x"],
        )
        sp = SubProblem(
            id="sp_001",
            goal="Test",
            context="Context",
            complexity_score=6,
            focus=focus,
        )

        json_str = sp.model_dump_json()
        restored = SubProblem.model_validate_json(json_str)

        assert restored.focus is not None
        assert restored.focus.key_questions == focus.key_questions
        assert restored.focus.risks_to_mitigate == focus.risks_to_mitigate
        assert restored.focus.alternatives_to_consider == focus.alternatives_to_consider
        assert restored.focus.required_expertise == focus.required_expertise
        assert restored.focus.success_criteria == focus.success_criteria


class TestSubProblem:
    """Test SubProblem model."""

    def test_subproblem_complexity_score_bounds(self) -> None:
        """complexity_score constrained to 1-10."""
        # Valid values
        for score in [1, 5, 10]:
            sp = SubProblem(id="sp", goal="Goal", context="Ctx", complexity_score=score)
            assert sp.complexity_score == score

    def test_subproblem_dependencies_list(self) -> None:
        """dependencies defaults to empty list and serializes."""
        sp = SubProblem(
            id="sp_002",
            goal="Goal",
            context="Context",
            complexity_score=4,
            dependencies=["sp_001"],
        )

        json_str = sp.model_dump_json()
        restored = SubProblem.model_validate_json(json_str)

        assert restored.dependencies == ["sp_001"]

    def test_subproblem_constraints_list(self) -> None:
        """SubProblem-specific constraints serialize correctly."""
        sp = SubProblem(
            id="sp_001",
            goal="Goal",
            context="Context",
            complexity_score=5,
            constraints=[
                Constraint(type=ConstraintType.BUDGET, description="Max $10K", value=10000),
                Constraint(type=ConstraintType.TIME, description="2 weeks", value="14 days"),
            ],
        )

        json_str = sp.model_dump_json()
        restored = SubProblem.model_validate_json(json_str)

        assert len(restored.constraints) == 2
        assert restored.constraints[0].type == ConstraintType.BUDGET
        assert restored.constraints[0].value == 10000
        assert restored.constraints[1].type == ConstraintType.TIME
