"""Tests for TokenBudgets configuration class.

Validates:
- All constants are positive integers
- DEFAULT is >= all other task-sized budgets
- Phase budgets are consistent with expected ranges
- Env var override works correctly
- for_phase() returns correct values
"""

import os
from unittest.mock import patch

from bo1.config import TokenBudgets


class TestTokenBudgetConstants:
    """Test that all token budget constants are valid."""

    def test_all_constants_are_positive_integers(self):
        """All token budgets must be positive integers."""
        constants = [
            TokenBudgets.DEFAULT,
            TokenBudgets.SYNTHESIS,
            TokenBudgets.META_SYNTHESIS,
            TokenBudgets.FACILITATOR,
            TokenBudgets.AGENT_BASE,
            TokenBudgets.DECOMPOSER_LARGE,
            TokenBudgets.SMALL_TASK,
            TokenBudgets.MEDIUM_TASK,
            TokenBudgets.LARGE_TASK,
            TokenBudgets.VOTING,
            TokenBudgets.VOTING_DETAILED,
        ]
        for value in constants:
            assert isinstance(value, int), f"Expected int, got {type(value)}"
            assert value > 0, f"Expected positive, got {value}"

    def test_default_is_largest(self):
        """DEFAULT should be >= all task-sized budgets."""
        task_budgets = [
            TokenBudgets.SMALL_TASK,
            TokenBudgets.MEDIUM_TASK,
            TokenBudgets.AGENT_BASE,
            TokenBudgets.FACILITATOR,
            TokenBudgets.META_SYNTHESIS,
        ]
        for budget in task_budgets:
            assert TokenBudgets.DEFAULT >= budget, (
                f"DEFAULT ({TokenBudgets.DEFAULT}) should be >= {budget}"
            )

    def test_budget_ordering_makes_sense(self):
        """Budget sizes should follow logical ordering."""
        assert TokenBudgets.SMALL_TASK < TokenBudgets.MEDIUM_TASK
        assert TokenBudgets.MEDIUM_TASK < TokenBudgets.LARGE_TASK
        assert TokenBudgets.LARGE_TASK <= TokenBudgets.DEFAULT

    def test_known_values(self):
        """Verify expected values haven't changed unexpectedly."""
        assert TokenBudgets.DEFAULT == 4096
        assert TokenBudgets.SYNTHESIS == 4000
        assert TokenBudgets.META_SYNTHESIS == 2000
        assert TokenBudgets.FACILITATOR == 1000
        assert TokenBudgets.AGENT_BASE == 2048
        assert TokenBudgets.SMALL_TASK == 500
        assert TokenBudgets.MEDIUM_TASK == 1500
        assert TokenBudgets.LARGE_TASK == 4000


class TestPhaseBudgets:
    """Test phase-specific token budgets."""

    def test_phase_budgets_dict_exists(self):
        """PHASE_BUDGETS dict should exist with expected phases."""
        expected_phases = ["initial", "early", "middle", "late"]
        for phase in expected_phases:
            assert phase in TokenBudgets.PHASE_BUDGETS, f"Missing phase: {phase}"

    def test_phase_budgets_are_positive(self):
        """All phase budgets must be positive integers."""
        for phase, budget in TokenBudgets.PHASE_BUDGETS.items():
            assert isinstance(budget, int), f"Phase {phase}: expected int, got {type(budget)}"
            assert budget > 0, f"Phase {phase}: expected positive, got {budget}"

    def test_phase_budgets_decrease_over_time(self):
        """Token budgets should generally decrease as deliberation progresses."""
        # Initial should be highest
        assert TokenBudgets.PHASE_BUDGETS["initial"] >= TokenBudgets.PHASE_BUDGETS["early"]
        # Late should be lowest
        assert TokenBudgets.PHASE_BUDGETS["late"] <= TokenBudgets.PHASE_BUDGETS["middle"]

    def test_for_phase_returns_correct_values(self):
        """for_phase() should return values from PHASE_BUDGETS."""
        assert TokenBudgets.for_phase("initial") == TokenBudgets.PHASE_BUDGETS["initial"]
        assert TokenBudgets.for_phase("early") == TokenBudgets.PHASE_BUDGETS["early"]
        assert TokenBudgets.for_phase("middle") == TokenBudgets.PHASE_BUDGETS["middle"]
        assert TokenBudgets.for_phase("late") == TokenBudgets.PHASE_BUDGETS["late"]

    def test_for_phase_unknown_returns_default(self):
        """Unknown phases should return DEFAULT."""
        assert TokenBudgets.for_phase("unknown_phase") == TokenBudgets.DEFAULT
        assert TokenBudgets.for_phase("") == TokenBudgets.DEFAULT
        assert TokenBudgets.for_phase("nonexistent") == TokenBudgets.DEFAULT


class TestEnvVarOverride:
    """Test environment variable override for get_default()."""

    def test_get_default_without_env(self):
        """get_default() returns DEFAULT when no env var set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove the env var if it exists
            os.environ.pop("LLM_DEFAULT_MAX_TOKENS", None)
            assert TokenBudgets.get_default() == TokenBudgets.DEFAULT

    def test_get_default_with_env_override(self):
        """get_default() returns env var value when set."""
        with patch.dict(os.environ, {"LLM_DEFAULT_MAX_TOKENS": "8192"}):
            assert TokenBudgets.get_default() == 8192

    def test_get_default_with_invalid_env(self):
        """get_default() returns DEFAULT when env var is invalid."""
        with patch.dict(os.environ, {"LLM_DEFAULT_MAX_TOKENS": "not_a_number"}):
            assert TokenBudgets.get_default() == TokenBudgets.DEFAULT

    def test_get_default_with_empty_env(self):
        """get_default() returns DEFAULT when env var is empty."""
        with patch.dict(os.environ, {"LLM_DEFAULT_MAX_TOKENS": ""}):
            assert TokenBudgets.get_default() == TokenBudgets.DEFAULT


class TestIntegrationWithPromptUtils:
    """Test that TokenBudgets integrates correctly with prompts/utils.py."""

    def test_get_round_phase_config_uses_token_budgets(self):
        """get_round_phase_config should use TokenBudgets.for_phase()."""
        from bo1.prompts.utils import get_round_phase_config

        # Test initial phase (round 1)
        config = get_round_phase_config(1, 10)
        assert config["max_tokens"] == TokenBudgets.for_phase("initial")

        # Test early phase (round 3)
        config = get_round_phase_config(3, 10)
        assert config["max_tokens"] == TokenBudgets.for_phase("early")

        # Test middle phase (round 6)
        config = get_round_phase_config(6, 10)
        assert config["max_tokens"] == TokenBudgets.for_phase("middle")

        # Test late phase (round 9)
        config = get_round_phase_config(9, 10)
        assert config["max_tokens"] == TokenBudgets.for_phase("late")


class TestIntegrationWithBroker:
    """Test that TokenBudgets integrates correctly with broker.py."""

    def test_prompt_request_default_max_tokens(self):
        """PromptRequest should use TokenBudgets.DEFAULT for max_tokens."""
        from bo1.llm.broker import PromptRequest

        request = PromptRequest(
            system="Test system",
            user_message="Test message",
        )
        assert request.max_tokens == TokenBudgets.DEFAULT
