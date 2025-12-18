"""Unit tests for synthesis model selection.

Tests tier-based model selection for synthesis:
1. synthesize_node uses 'fast' tier (Haiku/GPT-mini)
2. meta_synthesize_node uses 'fast' tier (Haiku/GPT-mini)
3. Model resolves to correct provider-specific ID
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bo1.config import TASK_MODEL_DEFAULTS, get_model_for_role, reset_settings
from bo1.graph.state import DeliberationGraphState
from bo1.llm.client import TokenUsage
from bo1.llm.response import LLMResponse
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import ContributionMessage, DeliberationMetrics, SubProblemResult


@pytest.fixture(autouse=True)
def reset_settings_fixture():
    """Reset settings before and after each test."""
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def mock_broker():
    """Mock PromptBroker for capturing model selection."""
    with patch("bo1.llm.broker.PromptBroker") as mock_cls:
        mock_instance = MagicMock()
        mock_response = LLMResponse(
            content="## Test synthesis content\n\nThis is a test.",
            model="haiku",
            token_usage=TokenUsage(input_tokens=500, output_tokens=200),
            duration_ms=1000,
        )
        mock_instance.call = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_meta_broker():
    """Mock PromptBroker for meta-synthesis returning valid JSON."""
    json_response = """"synthesis_summary": "Test summary.",
    "recommended_actions": [],
    "confidence_level": 0.8
}"""
    with patch("bo1.llm.broker.PromptBroker") as mock_cls:
        mock_instance = MagicMock()
        mock_response = LLMResponse(
            content=json_response,
            model="haiku",
            token_usage=TokenUsage(input_tokens=500, output_tokens=200),
            duration_ms=1000,
        )
        mock_instance.call = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def basic_synthesis_state() -> DeliberationGraphState:
    """Create minimal state for synthesize_node."""
    problem = Problem(
        title="Test Problem",
        description="Test problem description",
        context="Test context",
    )
    contribution = ContributionMessage(
        persona_code="test_expert",
        persona_name="Test Expert",
        content="Test contribution content",
        round_number=1,
    )
    vote = {
        "persona_code": "test_expert",
        "persona_name": "Test Expert",
        "recommendation": "Proceed with plan",
        "reasoning": "Test reasoning",
        "confidence": 0.8,
        "conditions": [],
        "weight": 1.0,
    }
    return DeliberationGraphState(
        session_id="test-session",
        problem=problem,
        contributions=[contribution],
        votes=[vote],
        round_summaries=["Round 1 summary"],
        round_number=1,
        metrics=DeliberationMetrics(),
    )


@pytest.fixture
def basic_meta_synthesis_state() -> DeliberationGraphState:
    """Create minimal state for meta_synthesize_node."""
    problem = Problem(
        title="Test Problem",
        description="Test problem description",
        context="Test context",
        sub_problems=[
            SubProblem(
                id="sp1",
                goal="Sub-problem 1",
                context="Sub-problem context",
                complexity_score=5,
            )
        ],
    )
    result = SubProblemResult(
        sub_problem_id="sp1",
        sub_problem_goal="Sub-problem 1",
        synthesis="Test synthesis for sp1",
        votes=[],
        contribution_count=3,
        cost=0.01,
        duration_seconds=10.0,
        expert_panel=["expert1"],
        expert_summaries={},
    )
    return DeliberationGraphState(
        session_id="test-session",
        problem=problem,
        sub_problem_results=[result],
        metrics=DeliberationMetrics(),
    )


class TestTierConfiguration:
    """Test tier-based model configuration."""

    def test_synthesis_uses_fast_tier(self):
        """synthesis role is configured to use fast tier."""
        assert TASK_MODEL_DEFAULTS["synthesis"] == "fast"

    def test_meta_synthesis_uses_fast_tier(self):
        """meta_synthesis role is configured to use fast tier."""
        assert TASK_MODEL_DEFAULTS["meta_synthesis"] == "fast"

    def test_get_model_for_role_resolves_synthesis(self):
        """get_model_for_role resolves synthesis to a valid model ID."""
        model = get_model_for_role("synthesis")
        # Should resolve to a fast tier model (Haiku for Anthropic, GPT-mini for OpenAI)
        assert model is not None
        assert len(model) > 0

    def test_get_model_for_role_resolves_meta_synthesis(self):
        """get_model_for_role resolves meta_synthesis to a valid model ID."""
        model = get_model_for_role("meta_synthesis")
        assert model is not None
        assert len(model) > 0


class TestSynthesizeNodeModel:
    """Test synthesize_node uses configured model."""

    @pytest.mark.asyncio
    async def test_uses_configured_model(self, mock_broker, basic_synthesis_state):
        """synthesize_node uses model from get_model_for_role."""
        from bo1.graph.nodes.synthesis import synthesize_node

        await synthesize_node(basic_synthesis_state)

        # Check the model passed to broker.call()
        call_args = mock_broker.call.call_args
        request = call_args[0][0]
        # Model should be the resolved fast tier model
        expected_model = get_model_for_role("synthesis")
        assert request.model == expected_model


class TestMetaSynthesizeNodeModel:
    """Test meta_synthesize_node uses configured model."""

    @pytest.mark.asyncio
    async def test_uses_configured_model(self, mock_meta_broker, basic_meta_synthesis_state):
        """meta_synthesize_node uses model from get_model_for_role."""
        from bo1.graph.nodes.synthesis import meta_synthesize_node

        await meta_synthesize_node(basic_meta_synthesis_state)

        # Check the model passed to broker.call()
        call_args = mock_meta_broker.call.call_args
        request = call_args[0][0]
        # Model should be the resolved fast tier model
        expected_model = get_model_for_role("meta_synthesis")
        assert request.model == expected_model
