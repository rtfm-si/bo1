"""Tests for model selection and A/B testing in broker.py.

Tests the get_model_for_phase() function with A/B test support.
"""

import os
from unittest.mock import patch

from bo1.constants import ModelSelectionConfig
from bo1.llm.broker import get_model_for_phase


class TestGetModelForPhaseDefault:
    """Tests for default model selection without A/B testing."""

    def test_convergence_check_returns_fast(self) -> None:
        """Convergence check phase always uses fast tier."""
        result = get_model_for_phase("convergence_check")
        assert result == "fast"

    def test_drift_check_returns_fast(self) -> None:
        """Drift check phase always uses fast tier."""
        result = get_model_for_phase("drift_check")
        assert result == "fast"

    def test_format_validation_returns_fast(self) -> None:
        """Format validation phase always uses fast tier."""
        result = get_model_for_phase("format_validation")
        assert result == "fast"

    def test_synthesis_returns_core(self) -> None:
        """Synthesis phase always uses core tier."""
        result = get_model_for_phase("synthesis")
        assert result == "core"

    def test_contribution_round_1_returns_fast(self) -> None:
        """Round 1 contributions use fast tier by default."""
        result = get_model_for_phase("contribution", round_number=1)
        assert result == "fast"

    def test_contribution_round_2_returns_fast(self) -> None:
        """Round 2 contributions use fast tier by default."""
        result = get_model_for_phase("contribution", round_number=2)
        assert result == "fast"

    def test_contribution_round_3_returns_core(self) -> None:
        """Round 3 contributions use core tier by default (challenge phase)."""
        result = get_model_for_phase("contribution", round_number=3)
        assert result == "core"

    def test_contribution_round_4_returns_core(self) -> None:
        """Round 4 contributions use core tier."""
        result = get_model_for_phase("contribution", round_number=4)
        assert result == "core"


class TestGetModelForPhaseABDisabled:
    """Tests when A/B testing is disabled."""

    @patch.dict(os.environ, {"HAIKU_AB_TEST_ENABLED": "false"}, clear=False)
    def test_ignores_session_id_when_disabled(self) -> None:
        """Session ID is ignored when A/B test is disabled."""
        # Clear any cached values
        result = get_model_for_phase("contribution", round_number=3, session_id="test-session-123")
        # Default limit is 2, so round 3 should use core
        assert result == "core"

    @patch.dict(os.environ, {"HAIKU_AB_TEST_ENABLED": ""}, clear=False)
    def test_empty_env_disables_ab_test(self) -> None:
        """Empty HAIKU_AB_TEST_ENABLED disables A/B testing."""
        result = get_model_for_phase("contribution", round_number=3, session_id="test-session-123")
        assert result == "core"


class TestGetModelForPhaseABTestGroup:
    """Tests for A/B test group assignment."""

    @patch.dict(
        os.environ,
        {
            "HAIKU_AB_TEST_ENABLED": "true",
            "HAIKU_AB_TEST_LIMIT": "3",
            "HAIKU_AB_TEST_PERCENTAGE": "50",
        },
        clear=False,
    )
    def test_test_group_uses_extended_limit(self) -> None:
        """Sessions in test group use extended round limit."""
        # Find a session_id that hashes to test group (< 50)
        # sha256("test-session-abc")[:8] hashes to a value < 50
        test_session = "test-session-abc"
        ab_group = ModelSelectionConfig.get_ab_group(test_session)

        if ab_group == "test":
            result = get_model_for_phase("contribution", round_number=3, session_id=test_session)
            # Test group should use fast tier for round 3
            assert result == "fast"

    @patch.dict(
        os.environ,
        {
            "HAIKU_AB_TEST_ENABLED": "true",
            "HAIKU_AB_TEST_LIMIT": "3",
            "HAIKU_AB_TEST_PERCENTAGE": "50",
        },
        clear=False,
    )
    def test_control_group_uses_default_limit(self) -> None:
        """Sessions in control group use default round limit."""
        # Find a session_id that hashes to control group (>= 50)
        control_session = "control-session-xyz"
        ab_group = ModelSelectionConfig.get_ab_group(control_session)

        if ab_group == "control":
            result = get_model_for_phase("contribution", round_number=3, session_id=control_session)
            # Control group should use core tier for round 3
            assert result == "core"


class TestGetModelForPhaseABDeterministic:
    """Tests for deterministic A/B group assignment."""

    @patch.dict(
        os.environ,
        {"HAIKU_AB_TEST_ENABLED": "true", "HAIKU_AB_TEST_PERCENTAGE": "50"},
        clear=False,
    )
    def test_same_session_always_same_group(self) -> None:
        """Same session_id always returns same A/B group."""
        session_id = "deterministic-test-session"

        # Call multiple times
        results = [ModelSelectionConfig.get_ab_group(session_id) for _ in range(10)]

        # All results should be the same
        assert len(set(results)) == 1

    @patch.dict(
        os.environ,
        {"HAIKU_AB_TEST_ENABLED": "true", "HAIKU_AB_TEST_PERCENTAGE": "50"},
        clear=False,
    )
    def test_different_sessions_get_different_groups(self) -> None:
        """Different session IDs get distributed across groups."""
        groups = []
        for i in range(100):
            session_id = f"session-{i}"
            groups.append(ModelSelectionConfig.get_ab_group(session_id))

        # With 100 sessions and 50% split, both groups should have members
        assert "test" in groups
        assert "control" in groups


class TestModelSelectionConfigABGroup:
    """Tests for ModelSelectionConfig.get_ab_group()."""

    @patch.dict(os.environ, {"HAIKU_AB_TEST_ENABLED": "false"}, clear=False)
    def test_returns_none_when_disabled(self) -> None:
        """Returns 'none' when A/B test is disabled."""
        result = ModelSelectionConfig.get_ab_group("any-session")
        assert result == "none"

    @patch.dict(os.environ, {"HAIKU_AB_TEST_ENABLED": "true"}, clear=False)
    def test_returns_none_when_no_session_id(self) -> None:
        """Returns 'none' when session_id is None."""
        result = ModelSelectionConfig.get_ab_group(None)
        assert result == "none"

    @patch.dict(os.environ, {"HAIKU_AB_TEST_ENABLED": "true"}, clear=False)
    def test_returns_none_for_empty_session_id(self) -> None:
        """Returns 'none' when session_id is empty string."""
        result = ModelSelectionConfig.get_ab_group("")
        assert result == "none"

    @patch.dict(
        os.environ,
        {"HAIKU_AB_TEST_ENABLED": "true", "HAIKU_AB_TEST_PERCENTAGE": "0"},
        clear=False,
    )
    def test_zero_percentage_all_control(self) -> None:
        """0% test percentage puts all sessions in control group."""
        result = ModelSelectionConfig.get_ab_group("any-session-id")
        assert result == "control"

    @patch.dict(
        os.environ,
        {"HAIKU_AB_TEST_ENABLED": "true", "HAIKU_AB_TEST_PERCENTAGE": "100"},
        clear=False,
    )
    def test_100_percentage_all_test(self) -> None:
        """100% test percentage puts all sessions in test group."""
        result = ModelSelectionConfig.get_ab_group("any-session-id")
        assert result == "test"


class TestModelSelectionConfigEnvVars:
    """Tests for ModelSelectionConfig environment variable handling."""

    @patch.dict(os.environ, {"HAIKU_ROUND_LIMIT": "4"}, clear=False)
    def test_custom_haiku_round_limit(self) -> None:
        """Custom HAIKU_ROUND_LIMIT is respected."""
        result = ModelSelectionConfig.get_haiku_round_limit()
        assert result == 4

    @patch.dict(os.environ, {}, clear=True)
    def test_default_haiku_round_limit(self) -> None:
        """Default HAIKU_ROUND_LIMIT is 2."""
        result = ModelSelectionConfig.get_haiku_round_limit()
        assert result == 2

    @patch.dict(os.environ, {"HAIKU_AB_TEST_LIMIT": "5"}, clear=False)
    def test_custom_ab_test_limit(self) -> None:
        """Custom HAIKU_AB_TEST_LIMIT is respected."""
        result = ModelSelectionConfig.get_ab_test_limit()
        assert result == 5

    @patch.dict(os.environ, {}, clear=True)
    def test_default_ab_test_limit(self) -> None:
        """Default HAIKU_AB_TEST_LIMIT is 3."""
        result = ModelSelectionConfig.get_ab_test_limit()
        assert result == 3

    @patch.dict(os.environ, {"HAIKU_AB_TEST_PERCENTAGE": "75"}, clear=False)
    def test_custom_ab_test_percentage(self) -> None:
        """Custom HAIKU_AB_TEST_PERCENTAGE is respected."""
        result = ModelSelectionConfig.get_ab_test_percentage()
        assert result == 75


class TestGetModelForPhaseMetricsEmitted:
    """Tests for metrics emission during model selection."""

    @patch("bo1.llm.broker.logger")
    @patch.dict(
        os.environ,
        {"HAIKU_AB_TEST_ENABLED": "true", "HAIKU_AB_TEST_PERCENTAGE": "50"},
        clear=False,
    )
    def test_logs_model_selection_with_session_id(self, mock_logger) -> None:
        """Logs model selection details when session_id is provided."""
        session_id = "logged-session-123"
        get_model_for_phase("contribution", round_number=2, session_id=session_id)

        # Check that debug logging was called
        mock_logger.debug.assert_called()

    @patch("bo1.llm.broker.logger")
    def test_no_log_without_session_id(self, mock_logger) -> None:
        """No logging when session_id is not provided."""
        get_model_for_phase("contribution", round_number=2)

        # debug should not be called with model_selection message
        for call in mock_logger.debug.call_args_list:
            if len(call.args) > 0:
                assert "model_selection" not in str(call.args[0])
