"""Tests for BaseAgent enhancements (cost tracking, error handling)."""

import pytest

from bo1.agents.base import BaseAgent
from bo1.llm.broker import PromptRequest
from bo1.llm.response import LLMResponse


class MockAgent(BaseAgent):
    """Test agent implementation."""

    def get_default_model(self) -> str:
        """Return default model."""
        return "claude-haiku-4-5-20251001"


@pytest.mark.asyncio
async def test_base_agent_cost_tracking(mock_broker):
    """Test that BaseAgent tracks costs across calls."""
    agent = MockAgent(broker=mock_broker)

    # Initial state
    assert agent.total_cost == 0.0
    assert agent.call_count == 0

    # Make first call
    request = PromptRequest(
        system="test system",
        user_message="test message",
        model="claude-haiku-4-5-20251001",
        phase="test",
    )
    response1 = await agent._call_llm(request)

    # Check tracking
    assert agent.call_count == 1
    assert agent.total_cost == response1.cost_total
    first_cost = response1.cost_total

    # Make second call
    response2 = await agent._call_llm(request)

    # Check accumulation
    assert agent.call_count == 2
    assert agent.total_cost == first_cost + response2.cost_total


@pytest.mark.asyncio
async def test_base_agent_get_cost_stats(mock_broker):
    """Test cost statistics reporting."""
    agent = MockAgent(broker=mock_broker)

    # Make a few calls
    request = PromptRequest(
        system="test system",
        user_message="test message",
        model="claude-haiku-4-5-20251001",
        phase="test",
    )

    await agent._call_llm(request)
    await agent._call_llm(request)
    await agent._call_llm(request)

    # Get stats
    stats = agent.get_cost_stats()

    assert "total_cost" in stats
    assert "call_count" in stats
    assert "avg_cost_per_call" in stats
    assert stats["call_count"] == 3
    assert stats["avg_cost_per_call"] == stats["total_cost"] / 3


@pytest.mark.asyncio
async def test_base_agent_reset_cost_tracking(mock_broker):
    """Test cost tracking reset."""
    agent = MockAgent(broker=mock_broker)

    # Make some calls
    request = PromptRequest(
        system="test system",
        user_message="test message",
        model="claude-haiku-4-5-20251001",
        phase="test",
    )
    await agent._call_llm(request)
    await agent._call_llm(request)

    assert agent.call_count > 0
    assert agent.total_cost > 0

    # Reset
    agent.reset_cost_tracking()

    assert agent.call_count == 0
    assert agent.total_cost == 0.0


@pytest.mark.asyncio
async def test_base_agent_error_handling(monkeypatch):
    """Test that BaseAgent logs errors with context."""
    agent = MockAgent()

    # Mock broker to raise error
    async def mock_call_error(request: PromptRequest) -> LLMResponse:
        raise ValueError("Test error")

    monkeypatch.setattr(agent.broker, "call", mock_call_error)

    # Make call that will fail
    request = PromptRequest(
        system="test system",
        user_message="test message",
        model="claude-haiku-4-5-20251001",
        phase="test",
    )

    # Should raise but log with context
    with pytest.raises(ValueError, match="Test error"):
        await agent._call_llm(request)

    # Cost should not be incremented on error
    assert agent.call_count == 0
    assert agent.total_cost == 0.0


@pytest.mark.asyncio
async def test_create_and_call_prompt_uses_call_llm(mock_broker):
    """Test that _create_and_call_prompt uses _call_llm for consistency."""
    agent = MockAgent(broker=mock_broker)

    # Use _create_and_call_prompt
    response = await agent._create_and_call_prompt(
        system="test system",
        user_message="test message",
        phase="test",
        prefill="{",
        temperature=0.7,
    )

    # Should have tracked cost (proves it went through _call_llm)
    assert agent.call_count == 1
    assert agent.total_cost == response.cost_total


def test_base_agent_model_initialization():
    """Test that BaseAgent initializes with correct model."""
    # Default model
    agent = MockAgent()
    assert agent.model == "claude-haiku-4-5-20251001"

    # Override model
    agent = MockAgent(model="custom-model")
    assert agent.model == "custom-model"
