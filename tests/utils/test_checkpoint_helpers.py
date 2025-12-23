"""Tests for checkpoint helper functions.

Tests for safe accessors that handle corrupted checkpoint data,
particularly the case where SubProblem.id becomes a type annotation list.
"""

from unittest.mock import MagicMock

from bo1.models.problem import SubProblem
from bo1.utils.checkpoint_helpers import (
    get_attr_safe,
    get_sub_problem_goal,
    get_sub_problem_goal_safe,
    get_sub_problem_id,
    get_sub_problem_id_safe,
)


class TestGetSubProblemIdSafe:
    """Tests for get_sub_problem_id_safe() corruption handling."""

    def test_with_valid_subproblem_object(self) -> None:
        """Test with valid SubProblem object returns id string."""
        sp = SubProblem(
            id="sp_001",
            goal="Test goal",
            context="Test context",
            complexity_score=5,
        )
        result = get_sub_problem_id_safe(sp)
        assert result == "sp_001"

    def test_with_valid_dict(self) -> None:
        """Test with valid dict returns id string."""
        sp = {"id": "sp_002", "goal": "Test", "context": "ctx", "complexity_score": 3}
        result = get_sub_problem_id_safe(sp)
        assert result == "sp_002"

    def test_with_corrupted_list_value(self) -> None:
        """Test with corrupted list value returns empty string."""
        # Simulate corrupted checkpoint data where id is a type annotation path
        sp = {"id": ["bo1", "models", "problem", "SubProblem"], "goal": "Test"}
        result = get_sub_problem_id_safe(sp)
        assert result == ""

    def test_with_corrupted_list_value_logs_warning(self) -> None:
        """Test with corrupted list value logs warning."""
        mock_logger = MagicMock()
        sp = {"id": ["bo1", "models", "problem", "SubProblem"], "goal": "Test"}
        get_sub_problem_id_safe(sp, logger=mock_logger)
        mock_logger.warning.assert_called_once()
        assert "Corrupted sub_problem.id" in mock_logger.warning.call_args[0][0]

    def test_with_none(self) -> None:
        """Test with None returns empty string."""
        result = get_sub_problem_id_safe(None)
        assert result == ""

    def test_with_empty_string(self) -> None:
        """Test with empty string id returns empty string."""
        sp = {"id": "", "goal": "Test"}
        result = get_sub_problem_id_safe(sp)
        assert result == ""

    def test_with_int_id(self) -> None:
        """Test with int id returns empty string."""
        sp = {"id": 123, "goal": "Test"}
        result = get_sub_problem_id_safe(sp)
        assert result == ""

    def test_with_int_id_logs_warning(self) -> None:
        """Test with int id logs warning about invalid type."""
        mock_logger = MagicMock()
        sp = {"id": 123, "goal": "Test"}
        get_sub_problem_id_safe(sp, logger=mock_logger)
        mock_logger.warning.assert_called_once()
        assert "Invalid sub_problem.id type" in mock_logger.warning.call_args[0][0]


class TestGetSubProblemGoalSafe:
    """Tests for get_sub_problem_goal_safe() corruption handling."""

    def test_with_valid_subproblem_object(self) -> None:
        """Test with valid SubProblem object returns goal string."""
        sp = SubProblem(
            id="sp_001",
            goal="Should we expand to new markets?",
            context="Test context",
            complexity_score=5,
        )
        result = get_sub_problem_goal_safe(sp)
        assert result == "Should we expand to new markets?"

    def test_with_valid_dict(self) -> None:
        """Test with valid dict returns goal string."""
        sp = {"id": "sp_002", "goal": "Test goal", "context": "ctx"}
        result = get_sub_problem_goal_safe(sp)
        assert result == "Test goal"

    def test_with_corrupted_list_value(self) -> None:
        """Test with corrupted list value returns empty string."""
        sp = {"id": "sp_001", "goal": ["corrupted", "list", "value"]}
        result = get_sub_problem_goal_safe(sp)
        assert result == ""

    def test_with_corrupted_list_value_logs_warning(self) -> None:
        """Test with corrupted list value logs warning."""
        mock_logger = MagicMock()
        sp = {"id": "sp_001", "goal": ["corrupted", "list", "value"]}
        get_sub_problem_goal_safe(sp, logger=mock_logger)
        mock_logger.warning.assert_called_once()
        assert "Corrupted sub_problem.goal" in mock_logger.warning.call_args[0][0]

    def test_with_none(self) -> None:
        """Test with None returns empty string."""
        result = get_sub_problem_goal_safe(None)
        assert result == ""

    def test_with_empty_string(self) -> None:
        """Test with empty string goal returns empty string."""
        sp = {"id": "sp_001", "goal": ""}
        result = get_sub_problem_goal_safe(sp)
        assert result == ""


class TestGetAttrSafe:
    """Tests for the base get_attr_safe helper."""

    def test_with_dict(self) -> None:
        """Test accessing attribute from dict."""
        obj = {"name": "test", "value": 42}
        assert get_attr_safe(obj, "name") == "test"
        assert get_attr_safe(obj, "value") == 42

    def test_with_dict_missing_key(self) -> None:
        """Test missing key returns default."""
        obj = {"name": "test"}
        assert get_attr_safe(obj, "missing") is None
        assert get_attr_safe(obj, "missing", "default") == "default"

    def test_with_object(self) -> None:
        """Test accessing attribute from object."""
        sp = SubProblem(
            id="sp_001",
            goal="Test",
            context="ctx",
            complexity_score=5,
        )
        assert get_attr_safe(sp, "id") == "sp_001"
        assert get_attr_safe(sp, "goal") == "Test"

    def test_with_none(self) -> None:
        """Test None returns default."""
        assert get_attr_safe(None, "attr") is None
        assert get_attr_safe(None, "attr", "default") == "default"


class TestLegacyHelpers:
    """Tests for the original (non-safe) helpers for backward compat."""

    def test_get_sub_problem_id(self) -> None:
        """Test legacy get_sub_problem_id still works."""
        sp = {"id": "sp_legacy", "goal": "Test"}
        assert get_sub_problem_id(sp) == "sp_legacy"

    def test_get_sub_problem_goal(self) -> None:
        """Test legacy get_sub_problem_goal still works."""
        sp = {"id": "sp_001", "goal": "Legacy goal"}
        assert get_sub_problem_goal(sp) == "Legacy goal"
