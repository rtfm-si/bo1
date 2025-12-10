"""Tests for data_analysis_node."""

from unittest.mock import AsyncMock, patch

import pytest

from bo1.graph.nodes.data_analysis import data_analysis_node
from bo1.graph.state import DeliberationGraphState


class TestDataAnalysisNode:
    """Tests for data_analysis_node function."""

    @pytest.mark.asyncio
    async def test_no_facilitator_decision(self) -> None:
        """Test node handles missing facilitator decision."""
        state = DeliberationGraphState(
            session_id="test-123",
            facilitator_decision=None,
            attached_datasets=[],
            data_analysis_results=[],
        )

        result = await data_analysis_node(state)

        assert result["facilitator_decision"] is None
        assert result["current_node"] == "data_analysis"

    @pytest.mark.asyncio
    async def test_no_dataset_id(self) -> None:
        """Test node handles missing dataset_id in decision."""
        state = DeliberationGraphState(
            session_id="test-123",
            facilitator_decision={
                "action": "analyze_data",
                "reasoning": "Need data analysis",
                "dataset_id": None,
                "analysis_questions": [],
            },
            attached_datasets=[],
            data_analysis_results=[],
        )

        result = await data_analysis_node(state)

        assert result["facilitator_decision"] is None
        assert result["current_node"] == "data_analysis"

    @pytest.mark.asyncio
    async def test_dataset_not_attached(self) -> None:
        """Test node handles dataset not in attached_datasets."""
        state = DeliberationGraphState(
            session_id="test-123",
            facilitator_decision={
                "action": "analyze_data",
                "reasoning": "Need data analysis",
                "dataset_id": "dataset-abc",
                "analysis_questions": ["What are top products?"],
            },
            attached_datasets=["dataset-xyz"],  # Different dataset
            data_analysis_results=[],
            round_number=1,
        )

        result = await data_analysis_node(state)

        # Should add error result
        assert len(result["data_analysis_results"]) == 1
        assert result["data_analysis_results"][0]["dataset_id"] == "dataset-abc"
        assert "not attached" in result["data_analysis_results"][0]["error"]
        assert result["facilitator_decision"] is None

    @pytest.mark.asyncio
    async def test_generates_default_question_from_reasoning(self) -> None:
        """Test node generates default question when none provided."""
        state = DeliberationGraphState(
            session_id="test-123",
            facilitator_decision={
                "action": "analyze_data",
                "reasoning": "We need to understand sales patterns",
                "dataset_id": "dataset-abc",
                "analysis_questions": [],  # Empty questions
            },
            attached_datasets=["dataset-abc"],
            data_analysis_results=[],
            round_number=1,
            user_id="user-123",
        )

        # Mock the agent to avoid API calls
        mock_results = [
            {
                "question": "test",
                "error": None,
                "query_result": {},
                "chart_result": None,
                "cost": 0.01,
            }
        ]
        with patch("bo1.agents.data_analyst.DataAnalysisAgent") as mock_agent_class:
            mock_instance = mock_agent_class.return_value
            mock_instance.analyze_dataset = AsyncMock(return_value=mock_results)

            result = await data_analysis_node(state)

        # Should have attempted analysis with generated question
        assert len(result["data_analysis_results"]) == 1
        # The question should be derived from reasoning
        questions = result["data_analysis_results"][0].get("questions", [])
        assert len(questions) == 1
        assert "sales patterns" in questions[0].lower()

    @pytest.mark.asyncio
    async def test_clears_facilitator_decision(self) -> None:
        """Test node clears facilitator decision to prevent loops."""
        state = DeliberationGraphState(
            session_id="test-123",
            facilitator_decision={
                "action": "analyze_data",
                "reasoning": "Analysis needed",
                "dataset_id": "dataset-abc",
                "analysis_questions": ["Test question"],
            },
            attached_datasets=["dataset-abc"],
            data_analysis_results=[],
            round_number=2,
            user_id="user-123",
        )

        # Mock the agent to avoid API calls
        mock_results = [
            {
                "question": "Test question",
                "error": None,
                "query_result": {},
                "chart_result": None,
                "cost": 0.0,
            }
        ]
        with patch("bo1.agents.data_analyst.DataAnalysisAgent") as mock_agent_class:
            mock_instance = mock_agent_class.return_value
            mock_instance.analyze_dataset = AsyncMock(return_value=mock_results)

            result = await data_analysis_node(state)

        # Must clear decision
        assert result["facilitator_decision"] is None

    @pytest.mark.asyncio
    async def test_preserves_existing_results(self) -> None:
        """Test node preserves existing data_analysis_results."""
        existing_result = {
            "dataset_id": "dataset-old",
            "questions": ["Old question"],
            "results": [],
            "round": 1,
        }

        state = DeliberationGraphState(
            session_id="test-123",
            facilitator_decision={
                "action": "analyze_data",
                "reasoning": "More analysis",
                "dataset_id": "dataset-new",
                "analysis_questions": ["New question"],
            },
            attached_datasets=["dataset-new"],
            data_analysis_results=[existing_result],
            round_number=2,
            user_id="user-123",
        )

        # Mock the agent to avoid API calls
        mock_results = [
            {
                "question": "New question",
                "error": None,
                "query_result": {},
                "chart_result": None,
                "cost": 0.0,
            }
        ]
        with patch("bo1.agents.data_analyst.DataAnalysisAgent") as mock_agent_class:
            mock_instance = mock_agent_class.return_value
            mock_instance.analyze_dataset = AsyncMock(return_value=mock_results)

            result = await data_analysis_node(state)

        # Should have both old and new results
        assert len(result["data_analysis_results"]) == 2
        assert result["data_analysis_results"][0] == existing_result
