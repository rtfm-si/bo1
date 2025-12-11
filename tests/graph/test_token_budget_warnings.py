"""Tests for token budget warnings in facilitator and synthesis nodes."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestFacilitatorTokenBudgetWarning:
    """Test token budget warnings in facilitator_decide_node."""

    def test_facilitator_constants_exist(self) -> None:
        """Verify token budget constants are defined."""
        from bo1.prompts.moderator import (
            FACILITATOR_MAX_TOKENS,
            FACILITATOR_TOKEN_WARNING_THRESHOLD,
        )

        assert FACILITATOR_MAX_TOKENS == 1000
        assert FACILITATOR_TOKEN_WARNING_THRESHOLD == 0.9

    @pytest.mark.asyncio
    async def test_facilitator_token_warning_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify warning is logged when facilitator exceeds threshold."""
        from bo1.agents.facilitator import FacilitatorDecision
        from bo1.graph.nodes.moderation import facilitator_decide_node
        from bo1.llm.client import TokenUsage
        from bo1.llm.response import LLMResponse

        # Mock state
        mock_state = {
            "session_id": "test_session",
            "round_number": 2,
            "max_rounds": 6,
            "personas": [],
            "pending_research_queries": [],
        }

        # Create mock LLM response with high token count (above 90% of 1000)
        mock_response = LLMResponse(
            content="test response",
            model="claude-sonnet-4-20250514",
            token_usage=TokenUsage(input_tokens=500, output_tokens=950),  # 95% of budget
            duration_ms=1000,
        )

        mock_decision = FacilitatorDecision(
            action="continue",
            reasoning="Continue discussion",
            next_speaker="expert_1",
        )

        with (
            patch("bo1.graph.nodes.moderation.FacilitatorAgent") as mock_facilitator_cls,
            caplog.at_level(logging.WARNING),
        ):
            mock_facilitator = MagicMock()
            mock_facilitator.decide_next_action = AsyncMock(
                return_value=(mock_decision, mock_response)
            )
            mock_facilitator_cls.return_value = mock_facilitator

            await facilitator_decide_node(mock_state)

            # Check warning was logged
            assert "[TOKEN_BUDGET]" in caplog.text
            assert "Facilitator output tokens (950)" in caplog.text
            assert ">= 90% of budget (1000)" in caplog.text

    @pytest.mark.asyncio
    async def test_facilitator_no_warning_under_threshold(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Verify no warning when under threshold."""
        from bo1.agents.facilitator import FacilitatorDecision
        from bo1.graph.nodes.moderation import facilitator_decide_node
        from bo1.llm.client import TokenUsage
        from bo1.llm.response import LLMResponse

        mock_state = {
            "session_id": "test_session",
            "round_number": 2,
            "max_rounds": 6,
            "personas": [],
            "pending_research_queries": [],
        }

        # Token count below threshold (50% of budget)
        mock_response = LLMResponse(
            content="test response",
            model="claude-sonnet-4-20250514",
            token_usage=TokenUsage(input_tokens=500, output_tokens=500),  # 50% of budget
            duration_ms=1000,
        )

        mock_decision = FacilitatorDecision(
            action="continue",
            reasoning="Continue discussion",
            next_speaker="expert_1",
        )

        with (
            patch("bo1.graph.nodes.moderation.FacilitatorAgent") as mock_facilitator_cls,
            caplog.at_level(logging.WARNING),
        ):
            mock_facilitator = MagicMock()
            mock_facilitator.decide_next_action = AsyncMock(
                return_value=(mock_decision, mock_response)
            )
            mock_facilitator_cls.return_value = mock_facilitator

            await facilitator_decide_node(mock_state)

            # No TOKEN_BUDGET warning should appear
            assert "[TOKEN_BUDGET]" not in caplog.text


class TestSynthesisTokenBudgetWarning:
    """Test token budget warnings in synthesis nodes."""

    def test_synthesis_constants_exist(self) -> None:
        """Verify token budget constants are defined."""
        from bo1.prompts.synthesis import (
            META_SYNTHESIS_MAX_TOKENS,
            SYNTHESIS_MAX_TOKENS,
            SYNTHESIS_TOKEN_WARNING_THRESHOLD,
        )

        assert SYNTHESIS_MAX_TOKENS == 4000
        assert META_SYNTHESIS_MAX_TOKENS == 2000
        assert SYNTHESIS_TOKEN_WARNING_THRESHOLD == 0.9

    @pytest.mark.asyncio
    async def test_synthesis_token_warning_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify warning is logged when synthesis exceeds threshold."""
        from bo1.graph.nodes.synthesis import synthesize_node
        from bo1.llm.client import TokenUsage
        from bo1.llm.response import LLMResponse
        from bo1.models.problem import Problem
        from bo1.models.state import ContributionMessage

        # Create minimal valid state
        mock_state = {
            "session_id": "test_session",
            "problem": Problem(
                title="Test Problem",
                description="Test problem description",
                context="Test context",
            ),
            "contributions": [
                ContributionMessage(
                    persona_name="Expert 1",
                    persona_code="expert_1",
                    content="Test contribution",
                    round_number=1,
                ),
            ],
            "votes": [
                {
                    "persona_name": "Expert 1",
                    "recommendation": "PROCEED",
                    "confidence": 0.8,
                    "reasoning": "Good idea",
                },
            ],
            "round_summaries": [],
            "round_number": 1,
            "sub_problem_index": 0,
        }

        # Mock LLM response with high token count (above 90% of 4000)
        mock_response = LLMResponse(
            content="## Synthesis content here",
            model="claude-sonnet-4-20250514",
            token_usage=TokenUsage(input_tokens=2000, output_tokens=3800),  # 95% of budget
            duration_ms=2000,
        )

        with (
            patch("bo1.llm.broker.PromptBroker") as mock_broker_cls,
            caplog.at_level(logging.WARNING),
        ):
            mock_broker = MagicMock()
            mock_broker.call = AsyncMock(return_value=mock_response)
            mock_broker_cls.return_value = mock_broker

            await synthesize_node(mock_state)

            # Check warning was logged
            assert "[TOKEN_BUDGET]" in caplog.text
            assert "Synthesis output tokens (3800)" in caplog.text
            assert ">= 90% of budget (4000)" in caplog.text
