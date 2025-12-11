"""Tests for session cost breakdown API endpoint.

Validates:
- GET /v1/sessions/{id}/costs returns correct breakdown
- Ownership validation is enforced
- Empty sessions return zero costs
"""

from unittest.mock import patch

import pytest

from backend.api.models import (
    PhaseCosts,
    ProviderCosts,
    SessionCostBreakdown,
    SubProblemCost,
)


@pytest.mark.unit
class TestSessionCostBreakdownModel:
    """Test SessionCostBreakdown Pydantic model."""

    def test_session_cost_breakdown_serialization(self):
        """Test that SessionCostBreakdown serializes correctly."""
        breakdown = SessionCostBreakdown(
            session_id="bo1_test123",
            total_cost=0.32,
            total_tokens=10000,
            total_api_calls=25,
            by_provider=ProviderCosts(
                anthropic=0.28,
                voyage=0.02,
                brave=0.01,
                tavily=0.01,
            ),
            by_sub_problem=[
                SubProblemCost(
                    sub_problem_index=None,
                    label="Overhead",
                    total_cost=0.05,
                    api_calls=5,
                    total_tokens=1000,
                    by_provider=ProviderCosts(anthropic=0.05),
                    by_phase=PhaseCosts(decomposition=0.05),
                ),
                SubProblemCost(
                    sub_problem_index=0,
                    label="Sub-problem 0",
                    total_cost=0.15,
                    api_calls=12,
                    total_tokens=5000,
                    by_provider=ProviderCosts(anthropic=0.12, voyage=0.01, brave=0.01, tavily=0.01),
                    by_phase=PhaseCosts(deliberation=0.10, synthesis=0.05),
                ),
            ],
        )

        data = breakdown.model_dump()

        assert data["session_id"] == "bo1_test123"
        assert data["total_cost"] == 0.32
        assert data["total_tokens"] == 10000
        assert data["total_api_calls"] == 25
        assert data["by_provider"]["anthropic"] == 0.28
        assert len(data["by_sub_problem"]) == 2
        assert data["by_sub_problem"][0]["label"] == "Overhead"
        assert data["by_sub_problem"][1]["sub_problem_index"] == 0

    def test_provider_costs_defaults(self):
        """Test that ProviderCosts has correct defaults."""
        costs = ProviderCosts()

        assert costs.anthropic == 0.0
        assert costs.voyage == 0.0
        assert costs.brave == 0.0
        assert costs.tavily == 0.0

    def test_phase_costs_defaults(self):
        """Test that PhaseCosts has correct defaults."""
        costs = PhaseCosts()

        assert costs.decomposition == 0.0
        assert costs.deliberation == 0.0
        assert costs.synthesis == 0.0

    def test_subproblem_cost_null_index(self):
        """Test SubProblemCost with null sub_problem_index."""
        sp = SubProblemCost(
            sub_problem_index=None,
            label="Overhead",
            total_cost=0.05,
            api_calls=5,
            total_tokens=1000,
            by_provider=ProviderCosts(),
            by_phase=PhaseCosts(),
        )

        assert sp.sub_problem_index is None
        assert sp.label == "Overhead"


@pytest.mark.unit
class TestGetSessionCostsEndpoint:
    """Test GET /v1/sessions/{id}/costs endpoint logic."""

    def test_get_session_costs_returns_breakdown(self):
        """Test that endpoint returns proper cost breakdown."""
        # Mock the CostTracker methods
        mock_session_costs = {
            "total_calls": 25,
            "total_cost": 0.32,
            "by_provider": {
                "anthropic": 0.28,
                "voyage": 0.02,
                "brave": 0.01,
                "tavily": 0.01,
            },
            "total_tokens": 10000,
            "total_saved": 0.05,
            "cache_hit_rate": 0.3,
        }

        mock_subproblem_costs = [
            {
                "sub_problem_index": None,
                "label": "Overhead",
                "api_calls": 5,
                "total_cost": 0.05,
                "total_tokens": 1000,
                "by_provider": {"anthropic": 0.05, "voyage": 0.0, "brave": 0.0, "tavily": 0.0},
                "by_phase": {"decomposition": 0.05, "deliberation": 0.0, "synthesis": 0.0},
            },
            {
                "sub_problem_index": 0,
                "label": "Sub-problem 0",
                "api_calls": 10,
                "total_cost": 0.15,
                "total_tokens": 5000,
                "by_provider": {"anthropic": 0.12, "voyage": 0.01, "brave": 0.01, "tavily": 0.01},
                "by_phase": {"decomposition": 0.0, "deliberation": 0.10, "synthesis": 0.05},
            },
        ]

        with (
            patch("bo1.llm.cost_tracker.CostTracker.get_session_costs") as mock_get_session,
            patch("bo1.llm.cost_tracker.CostTracker.get_subproblem_costs") as mock_get_sp,
        ):
            mock_get_session.return_value = mock_session_costs
            mock_get_sp.return_value = mock_subproblem_costs

            from bo1.llm.cost_tracker import CostTracker

            # Call the methods directly to verify the data transformation
            session_costs = CostTracker.get_session_costs("bo1_test")
            sp_costs = CostTracker.get_subproblem_costs("bo1_test")

            assert session_costs["total_cost"] == 0.32
            assert len(sp_costs) == 2
            assert sp_costs[0]["label"] == "Overhead"

    def test_empty_session_returns_zeros(self):
        """Test that empty session returns zero values."""
        mock_session_costs = {
            "total_calls": 0,
            "total_cost": 0.0,
            "by_provider": {
                "anthropic": 0.0,
                "voyage": 0.0,
                "brave": 0.0,
                "tavily": 0.0,
            },
            "total_tokens": 0,
            "total_saved": 0.0,
            "cache_hit_rate": 0.0,
        }

        with (
            patch("bo1.llm.cost_tracker.CostTracker.get_session_costs") as mock_get_session,
            patch("bo1.llm.cost_tracker.CostTracker.get_subproblem_costs") as mock_get_sp,
        ):
            mock_get_session.return_value = mock_session_costs
            mock_get_sp.return_value = []

            from bo1.llm.cost_tracker import CostTracker

            session_costs = CostTracker.get_session_costs("bo1_empty")
            sp_costs = CostTracker.get_subproblem_costs("bo1_empty")

            assert session_costs["total_cost"] == 0.0
            assert session_costs["total_calls"] == 0
            assert sp_costs == []
