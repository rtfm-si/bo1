"""Unit tests for research_node.

Tests for research node covering:
1. Proactive research (pending_research_queries)
2. Facilitator-triggered research (facilitator_decision)
3. No-decision fallback
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bo1.graph.nodes.research import research_node
from bo1.graph.state import DeliberationGraphState
from bo1.models.problem import Problem
from bo1.models.state import ContributionMessage, ContributionType


@pytest.fixture
def mock_researcher_agent():
    """Mock ResearcherAgent for isolated testing."""
    # Patch at the source module since import is inside the function
    with patch("bo1.agents.researcher.ResearcherAgent") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.research_questions = AsyncMock(
            return_value=[
                {
                    "question": "Test query",
                    "summary": "Test research summary",
                    "sources": [{"url": "https://example.com", "title": "Example"}],
                    "cached": False,
                    "cost": 0.025,
                }
            ]
        )
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_embeddings():
    """Mock embedding generation."""
    # Patch at the source module
    with patch("bo1.llm.embeddings.generate_embedding") as mock_embed:
        # Return a simple 1024-dim embedding
        mock_embed.return_value = [0.1] * 1024
        yield mock_embed


@pytest.fixture
def mock_cache_repository():
    """Mock cache_repository for isolated testing."""
    with patch("bo1.state.repositories.cache_repository") as mock_repo:
        mock_repo.find_similar.return_value = []
        yield mock_repo


@pytest.fixture
def base_state() -> DeliberationGraphState:
    """Create base state for tests."""
    problem = Problem(
        title="Marketing Investment",
        description="Should we invest in SEO or paid ads?",
        context="B2B SaaS startup",
    )
    return {
        "session_id": "test-research-session",
        "problem": problem,
        "personas": [],
        "contributions": [],
        "round_summaries": [],
        "round_number": 1,
        "phase_costs": {},
        "sub_problem_index": 0,
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_research_node_proactive_queries(mock_researcher_agent, mock_embeddings, base_state):
    """Test research node processes proactive research queries."""
    # Add pending research queries
    base_state["pending_research_queries"] = [
        {
            "question": "What is the average CAC for B2B SaaS?",
            "priority": "HIGH",
            "reason": "Finance expert needs benchmark data",
        },
        {
            "question": "What are typical conversion rates for paid ads?",
            "priority": "MEDIUM",
            "reason": "Marketing expert needs comparison",
        },
    ]

    # Call node
    result = await research_node(base_state)

    # Verify ResearcherAgent was called
    mock_researcher_agent.research_questions.assert_called_once()
    call_args = mock_researcher_agent.research_questions.call_args

    # Should have 2 questions
    assert len(call_args.kwargs["questions"]) == 2
    # Should use deep research for HIGH priority
    assert call_args.kwargs["research_depth"] == "deep"

    # Verify result structure
    assert "research_results" in result
    assert len(result["research_results"]) >= 1
    assert result["research_results"][0]["proactive"] is True
    assert result["pending_research_queries"] == []  # Cleared
    assert result["current_node"] == "research"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_research_node_facilitator_decision(
    mock_researcher_agent, mock_embeddings, mock_cache_repository, base_state
):
    """Test research node processes facilitator-triggered research."""
    # Add facilitator decision with research request
    base_state["facilitator_decision"] = {
        "action": "RESEARCH",
        "reasoning": "Need data on competitor pricing strategies",
    }

    # Call node
    result = await research_node(base_state)

    # Verify ResearcherAgent was called
    mock_researcher_agent.research_questions.assert_called_once()
    call_args = mock_researcher_agent.research_questions.call_args

    # Should extract query from reasoning
    assert "competitor pricing" in call_args.kwargs["questions"][0]["question"].lower()

    # Verify result structure
    assert "research_results" in result
    assert len(result["research_results"]) >= 1
    assert "completed_research_queries" in result
    assert result["facilitator_decision"] is None  # Cleared
    assert result["current_node"] == "research"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_research_node_no_decision_fallback(mock_embeddings, base_state):
    """Test research node handles missing decision gracefully."""
    # No facilitator_decision, no pending_research_queries
    base_state["facilitator_decision"] = None
    base_state["pending_research_queries"] = []

    # Add a contribution for fallback query generation
    base_state["contributions"] = [
        ContributionMessage(
            persona_code="finance_strategist",
            persona_name="Finance Expert",
            content="We need more data on market benchmarks.",
            contribution_type=ContributionType.RESPONSE,
            round_number=1,
        )
    ]

    # Call node
    result = await research_node(base_state)

    # Should mark as completed to prevent loops
    assert "completed_research_queries" in result
    assert len(result["completed_research_queries"]) >= 1
    assert result["facilitator_decision"] is None
    assert result["current_node"] == "research"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_research_node_basic_depth_selection(
    mock_researcher_agent, mock_cache_repository, base_state
):
    """Test research node selects basic depth for simple queries."""
    # Mock embeddings to return low similarity for deep research examples
    with patch("bo1.llm.embeddings.generate_embedding") as mock_embed:
        mock_embed.return_value = [0.1] * 1024  # Low similarity vector

        # Mock numpy to return low similarity
        with patch.object(
            __import__("numpy", fromlist=["dot", "linalg"]),
            "dot",
            return_value=0.3,
        ):
            with patch.object(
                __import__("numpy", fromlist=["linalg"]).linalg,
                "norm",
                return_value=1.0,
            ):
                base_state["facilitator_decision"] = {
                    "action": "RESEARCH",
                    "reasoning": "What is the weather forecast?",  # Simple query
                }

                await research_node(base_state)

                # Should use basic depth for non-strategic query
                call_args = mock_researcher_agent.research_questions.call_args
                assert call_args.kwargs["research_depth"] == "basic"
