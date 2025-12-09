"""Tests for adaptive expert count functionality.

Tests the complexity scoring and target expert count calculation
for cost optimization based on problem complexity.
"""

from bo1.graph.utils import calculate_problem_complexity, calculate_target_expert_count


class TestCalculateProblemComplexity:
    """Test suite for problem complexity calculation."""

    def test_no_problem_returns_default(self) -> None:
        """When no problem in state, return default middle complexity."""
        state = {}
        assert calculate_problem_complexity(state) == 0.5

    def test_no_sub_problems_returns_low(self) -> None:
        """When problem has no sub-problems, return low complexity."""
        state = {"problem": {"sub_problems": []}}
        assert calculate_problem_complexity(state) == 0.3

    def test_single_simple_sub_problem(self) -> None:
        """Single sub-problem with low complexity score."""
        state = {"problem": {"sub_problems": [{"id": "sp_001", "complexity_score": 3}]}}
        complexity = calculate_problem_complexity(state)
        # 1 sub-problem = 0 num_factor
        # complexity 3 = (3-1)/9 * 0.4 = 0.089
        # no batches = 0 batch_factor
        assert 0.05 < complexity < 0.15

    def test_multiple_complex_sub_problems(self) -> None:
        """Multiple sub-problems with high complexity scores."""
        state = {
            "problem": {
                "sub_problems": [
                    {"id": "sp_001", "complexity_score": 8},
                    {"id": "sp_002", "complexity_score": 9},
                    {"id": "sp_003", "complexity_score": 7},
                ]
            }
        }
        complexity = calculate_problem_complexity(state)
        # 3 sub-problems = (3-1)/4 * 0.4 = 0.2 num_factor
        # avg complexity 8 = (8-1)/9 * 0.4 = 0.31 complexity_factor
        # no batches = 0 batch_factor
        assert 0.4 < complexity < 0.7

    def test_with_execution_batches(self) -> None:
        """Execution batches increase complexity."""
        state = {
            "problem": {
                "sub_problems": [
                    {"id": "sp_001", "complexity_score": 5},
                    {"id": "sp_002", "complexity_score": 5},
                ]
            },
            "execution_batches": [["sp_001"], ["sp_002"]],  # 2 batches
        }
        complexity_with_batches = calculate_problem_complexity(state)

        # Compare without batches
        state_no_batches = {
            "problem": {
                "sub_problems": [
                    {"id": "sp_001", "complexity_score": 5},
                    {"id": "sp_002", "complexity_score": 5},
                ]
            }
        }
        complexity_without = calculate_problem_complexity(state_no_batches)

        assert complexity_with_batches > complexity_without

    def test_handles_problem_object(self) -> None:
        """Works with Problem Pydantic model (not just dict)."""
        from bo1.models.problem import Problem, SubProblem

        problem = Problem(
            title="Test",
            description="Test problem",
            context="",
            sub_problems=[
                SubProblem(
                    id="sp_001",
                    goal="Goal 1",
                    context="",
                    complexity_score=6,
                    dependencies=[],
                )
            ],
        )
        state = {"problem": problem}
        complexity = calculate_problem_complexity(state)
        assert 0.1 < complexity < 0.4

    def test_complexity_clamped_to_0_1(self) -> None:
        """Complexity score is always between 0 and 1."""
        # Very complex problem
        state = {
            "problem": {
                "sub_problems": [{"id": f"sp_{i:03d}", "complexity_score": 10} for i in range(5)]
            },
            "execution_batches": [["sp_000"], ["sp_001"], ["sp_002"], ["sp_003"]],
        }
        complexity = calculate_problem_complexity(state)
        assert 0.0 <= complexity <= 1.0


class TestCalculateTargetExpertCount:
    """Test suite for target expert count calculation."""

    def test_simple_problem_gets_min_experts(self) -> None:
        """Low complexity score should return minimum experts."""
        # Below threshold (0.4)
        assert calculate_target_expert_count(0.2) == 3
        assert calculate_target_expert_count(0.3) == 3
        assert calculate_target_expert_count(0.39) == 3

    def test_complex_problem_gets_more_experts(self) -> None:
        """High complexity score should return more experts."""
        # Above threshold (0.4)
        assert calculate_target_expert_count(0.7) >= 4
        assert calculate_target_expert_count(0.9) >= 4

    def test_very_complex_gets_max_experts(self) -> None:
        """Very high complexity should return maximum experts."""
        assert calculate_target_expert_count(1.0) == 5

    def test_custom_min_max(self) -> None:
        """Custom min/max expert counts work correctly."""
        # Simple with custom range
        assert calculate_target_expert_count(0.2, min_experts=2, max_experts=4) == 2

        # Complex with custom range
        assert calculate_target_expert_count(1.0, min_experts=2, max_experts=4) == 4

    def test_custom_threshold(self) -> None:
        """Custom threshold changes when min experts apply."""
        # With threshold 0.3, score 0.35 should give more than min
        result = calculate_target_expert_count(0.35, threshold_simple=0.3)
        assert result == 3  # Just barely above threshold, gets min

        # With threshold 0.5, score 0.45 should give min
        result = calculate_target_expert_count(0.45, threshold_simple=0.5)
        assert result == 3  # Below threshold

    def test_returns_integer(self) -> None:
        """Result is always an integer."""
        for score in [0.0, 0.25, 0.5, 0.75, 1.0]:
            result = calculate_target_expert_count(score)
            assert isinstance(result, int)
            assert 3 <= result <= 5


class TestIntegration:
    """Integration tests combining complexity and expert count."""

    def test_simple_problem_end_to_end(self) -> None:
        """Simple problem should get 3 experts."""
        state = {"problem": {"sub_problems": [{"id": "sp_001", "complexity_score": 3}]}}
        complexity = calculate_problem_complexity(state)
        target = calculate_target_expert_count(complexity)
        assert target == 3

    def test_complex_problem_end_to_end(self) -> None:
        """Complex problem should get 4-5 experts."""
        state = {
            "problem": {
                "sub_problems": [
                    {"id": "sp_001", "complexity_score": 8},
                    {"id": "sp_002", "complexity_score": 9},
                    {"id": "sp_003", "complexity_score": 8},
                    {"id": "sp_004", "complexity_score": 7},
                ]
            },
            "execution_batches": [["sp_001"], ["sp_002", "sp_003"], ["sp_004"]],
        }
        complexity = calculate_problem_complexity(state)
        target = calculate_target_expert_count(complexity)
        assert target >= 4
