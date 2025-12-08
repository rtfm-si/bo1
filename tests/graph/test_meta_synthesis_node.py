"""Unit tests for meta_synthesize_node.

Tests for meta-synthesis covering:
1. Successful JSON action plan synthesis
2. JSON parse fallback to plain text
3. Missing data error handling
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bo1.graph.nodes.synthesis import meta_synthesize_node
from bo1.graph.state import DeliberationGraphState
from bo1.llm.client import TokenUsage
from bo1.llm.response import LLMResponse
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import SubProblemResult


@pytest.fixture
def mock_broker_success():
    """Mock PromptBroker returning valid JSON action plan."""
    # Valid JSON action plan (minus opening brace which is prefilled)
    json_response = """"synthesis_summary": "Invest 70% in SEO, 30% in paid ads for balanced growth.",
    "recommended_actions": [
        {
            "action": "Launch SEO campaign",
            "priority": "high",
            "timeline": "Q1 2025",
            "rationale": "Long-term sustainable growth",
            "success_metrics": ["Organic traffic +50%", "DA increase to 40"],
            "risks": ["6-month lag time", "Algorithm changes"]
        }
    ],
    "confidence_level": 0.85
}"""

    # Patch at source module since import is inside the function
    with patch("bo1.llm.broker.PromptBroker") as mock_cls:
        mock_instance = MagicMock()
        mock_response = LLMResponse(
            content=json_response,
            model="claude-sonnet-4-20250514",
            token_usage=TokenUsage(input_tokens=500, output_tokens=200),
            duration_ms=2000,
        )
        mock_instance.call = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_broker_invalid_json():
    """Mock PromptBroker returning invalid JSON."""
    # Patch at source module since import is inside the function
    with patch("bo1.llm.broker.PromptBroker") as mock_cls:
        mock_instance = MagicMock()
        mock_response = LLMResponse(
            content="This is plain text, not JSON at all...",
            model="claude-sonnet-4-20250514",
            token_usage=TokenUsage(input_tokens=500, output_tokens=100),
            duration_ms=1500,
        )
        mock_instance.call = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def base_state_with_results() -> DeliberationGraphState:
    """Create state with problem and sub_problem_results."""
    problem = Problem(
        title="Marketing Investment Strategy",
        description="Should we invest $50K in SEO or paid ads?",
        context="B2B SaaS startup with $2M ARR",
        sub_problems=[
            SubProblem(
                id="sp_001",
                goal="Analyze SEO ROI potential",
                context="Current organic traffic is low",
                complexity_score=5,
            ),
            SubProblem(
                id="sp_002",
                goal="Analyze paid ads ROI potential",
                context="Have run some Google Ads before",
                complexity_score=4,
            ),
        ],
    )

    sub_problem_results = [
        SubProblemResult(
            sub_problem_id="sp_001",
            sub_problem_goal="Analyze SEO ROI potential",
            synthesis="SEO offers 3-5x ROI over 12 months but requires patience.",
            votes=[
                {"persona_name": "Growth Expert", "recommendation": "PROCEED", "confidence": 0.8}
            ],
            contribution_count=5,
            cost=0.15,
            duration_seconds=120.0,
            expert_panel=["growth_hacker", "finance_strategist"],
        ),
        SubProblemResult(
            sub_problem_id="sp_002",
            sub_problem_goal="Analyze paid ads ROI potential",
            synthesis="Paid ads offer immediate results but higher CAC.",
            votes=[
                {
                    "persona_name": "Marketing Expert",
                    "recommendation": "PROCEED_WITH_CAUTION",
                    "confidence": 0.6,
                }
            ],
            contribution_count=4,
            cost=0.12,
            duration_seconds=100.0,
            expert_panel=["growth_hacker", "product_manager"],
        ),
    ]

    return {
        "session_id": "test-meta-synthesis",
        "problem": problem,
        "sub_problem_results": sub_problem_results,
        "personas": [],
        "contributions": [],
        "round_summaries": [],
        "round_number": 0,
        "phase_costs": {},
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_meta_synthesize_node_success(mock_broker_success, base_state_with_results):
    """Test meta-synthesis with valid JSON action plan."""
    result = await meta_synthesize_node(base_state_with_results)

    # Verify broker was called
    mock_broker_success.call.assert_called_once()

    # Verify result structure
    assert "synthesis" in result
    assert "phase" in result
    assert result["current_node"] == "meta_synthesis"

    # Verify synthesis contains action plan content
    synthesis = result["synthesis"]
    assert "Action Plan" in synthesis or "SEO" in synthesis
    assert "Deliberation Summary" in synthesis


@pytest.mark.unit
@pytest.mark.asyncio
async def test_meta_synthesize_node_json_fallback(
    mock_broker_invalid_json, base_state_with_results
):
    """Test meta-synthesis falls back gracefully on invalid JSON."""
    result = await meta_synthesize_node(base_state_with_results)

    # Should not raise exception
    assert "synthesis" in result
    assert "phase" in result

    # Fallback synthesis should contain the plain text
    synthesis = result["synthesis"]
    assert "plain text" in synthesis.lower() or "Deliberation Summary" in synthesis


@pytest.mark.unit
@pytest.mark.asyncio
async def test_meta_synthesize_node_missing_problem():
    """Test meta-synthesis raises error when problem is missing."""
    state: DeliberationGraphState = {
        "session_id": "test-missing-problem",
        "problem": None,  # type: ignore
        "sub_problem_results": [
            SubProblemResult(
                sub_problem_id="sp_001",
                sub_problem_goal="Test goal",
                synthesis="Test synthesis",
                votes=[],
                contribution_count=1,
                cost=0.01,
                duration_seconds=10.0,
                expert_panel=[],
            )
        ],
        "personas": [],
        "contributions": [],
        "round_summaries": [],
        "round_number": 0,
        "phase_costs": {},
    }

    with pytest.raises(ValueError, match="without problem"):
        await meta_synthesize_node(state)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_meta_synthesize_node_missing_results():
    """Test meta-synthesis raises error when sub_problem_results is empty."""
    problem = Problem(
        title="Test Problem",
        description="Test description",
        context="Test context",
    )

    state: DeliberationGraphState = {
        "session_id": "test-missing-results",
        "problem": problem,
        "sub_problem_results": [],  # Empty
        "personas": [],
        "contributions": [],
        "round_summaries": [],
        "round_number": 0,
        "phase_costs": {},
    }

    with pytest.raises(ValueError, match="without sub_problem_results"):
        await meta_synthesize_node(state)
