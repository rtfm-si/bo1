"""Tests for phase cost tracking and analytics.

This module tests the cost tracking functionality that breaks down
deliberation costs by phase.
"""

import pytest

from bo1.graph.analytics import (
    calculate_cost_breakdown,
    export_phase_metrics_csv,
    export_phase_metrics_json,
    get_most_expensive_phases,
    get_phase_costs,
    get_total_deliberation_cost,
)
from bo1.graph.state import create_initial_state
from bo1.models.problem import Problem
from bo1.models.state import DeliberationMetrics


@pytest.mark.unit
class TestPhaseCostTracking:
    """Test suite for phase cost tracking functionality."""

    @pytest.fixture
    def problem(self):
        """Create a test problem."""
        return Problem(
            title="Test Problem",
            description="Should we expand to new markets?",
            context="SaaS company with $1M ARR",
        )

    @pytest.fixture
    def state_with_costs(self, problem):
        """Create a state with phase costs."""
        import uuid

        state = create_initial_state(session_id=str(uuid.uuid4()), problem=problem, max_rounds=5)

        # Add phase costs
        metrics = DeliberationMetrics(
            total_cost=1.25,
            total_tokens=5000,
            phase_costs={
                "problem_decomposition": 0.15,
                "persona_selection": 0.10,
                "initial_round": 0.50,
                "round_1_deliberation": 0.25,
                "voting": 0.15,
                "synthesis": 0.10,
            },
        )

        state["metrics"] = metrics
        return state

    def test_get_phase_costs(self, state_with_costs):
        """Test extracting phase costs from state."""
        costs = get_phase_costs(state_with_costs)

        assert isinstance(costs, dict)
        assert "problem_decomposition" in costs
        assert costs["problem_decomposition"] == 0.15
        assert costs["persona_selection"] == 0.10
        assert costs["initial_round"] == 0.50

    def test_get_phase_costs_empty_state(self, problem):
        """Test extracting phase costs from empty state."""
        import uuid

        state = create_initial_state(session_id=str(uuid.uuid4()), problem=problem, max_rounds=5)

        costs = get_phase_costs(state)
        assert isinstance(costs, dict)
        assert len(costs) == 0

    def test_calculate_cost_breakdown(self, state_with_costs):
        """Test calculating cost breakdown with percentages."""
        breakdown = calculate_cost_breakdown(state_with_costs)

        assert isinstance(breakdown, list)
        assert len(breakdown) == 6

        # Should be sorted by cost descending
        assert breakdown[0]["phase"] == "initial_round"
        assert breakdown[0]["cost"] == 0.50
        assert breakdown[0]["percentage"] == pytest.approx(40.0, rel=0.1)

        # Check second highest
        assert breakdown[1]["phase"] == "round_1_deliberation"
        assert breakdown[1]["cost"] == 0.25
        assert breakdown[1]["percentage"] == pytest.approx(20.0, rel=0.1)

    def test_calculate_cost_breakdown_empty(self, problem):
        """Test cost breakdown with no costs."""
        import uuid

        state = create_initial_state(session_id=str(uuid.uuid4()), problem=problem, max_rounds=5)

        breakdown = calculate_cost_breakdown(state)
        assert isinstance(breakdown, list)
        assert len(breakdown) == 0

    def test_get_total_deliberation_cost(self, state_with_costs):
        """Test getting total deliberation cost."""
        total = get_total_deliberation_cost(state_with_costs)

        assert total == 1.25

    def test_get_most_expensive_phases(self, state_with_costs):
        """Test getting top N most expensive phases."""
        top_3 = get_most_expensive_phases(state_with_costs, top_n=3)

        assert len(top_3) == 3
        assert top_3[0] == ("initial_round", 0.50)
        assert top_3[1] == ("round_1_deliberation", 0.25)
        assert top_3[2][1] in [0.15, 0.10]  # Either voting or problem_decomposition

    def test_export_phase_metrics_csv(self, state_with_costs, tmp_path):
        """Test exporting phase metrics to CSV."""
        output_file = tmp_path / "costs.csv"

        export_phase_metrics_csv(state_with_costs, output_file)

        assert output_file.exists()

        # Read and verify content
        with open(output_file) as f:
            content = f.read()

        assert "phase,cost,percentage" in content
        assert "initial_round" in content
        assert "0.5" in content

    def test_export_phase_metrics_json(self, state_with_costs, tmp_path):
        """Test exporting phase metrics to JSON."""
        import json

        output_file = tmp_path / "costs.json"

        export_phase_metrics_json(state_with_costs, output_file)

        assert output_file.exists()

        # Read and verify content
        with open(output_file) as f:
            data = json.load(f)

        assert "session_id" in data
        assert data["total_cost"] == 1.25
        assert data["total_tokens"] == 5000
        assert "phase_costs" in data
        assert data["phase_costs"]["initial_round"] == 0.50
        assert "breakdown" in data
        assert len(data["breakdown"]) == 6

    def test_phase_costs_sum_to_total(self, state_with_costs):
        """Test that phase costs sum to total cost."""
        costs = get_phase_costs(state_with_costs)
        total_from_phases = sum(costs.values())
        total_cost = get_total_deliberation_cost(state_with_costs)

        assert total_from_phases == pytest.approx(total_cost, rel=0.01)

    def test_percentage_calculation_accuracy(self, state_with_costs):
        """Test that percentages are calculated correctly."""
        breakdown = calculate_cost_breakdown(state_with_costs)

        total_percentage = sum(item["percentage"] for item in breakdown)

        # Should sum to approximately 100%
        assert total_percentage == pytest.approx(100.0, rel=0.1)
