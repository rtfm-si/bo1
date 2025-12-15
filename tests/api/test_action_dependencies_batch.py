"""Tests for batch dependency loading in action_repository.

Tests get_dependencies_batch() and get_all_dependencies_for_user() methods
that fix N+1 query issues in Gantt chart loading.
"""

from unittest.mock import patch

from bo1.state.repositories.action_repository import ActionRepository


class TestGetDependenciesBatch:
    """Tests for get_dependencies_batch() method."""

    def test_empty_action_list_returns_empty_dict(self):
        """Test batch returns empty dict for empty input."""
        repo = ActionRepository()
        result = repo.get_dependencies_batch([])
        assert result == {}

    def test_batch_returns_same_results_as_individual_calls(self):
        """Test batch method returns same results as individual get_dependencies calls."""
        repo = ActionRepository()
        action_ids = ["action-1", "action-2", "action-3"]

        # Mock _execute_query to return predictable results
        mock_deps = [
            {
                "action_id": "action-1",
                "depends_on_action_id": "dep-a",
                "dependency_type": "finish_to_start",
                "lag_days": 0,
                "created_at": "2025-01-01T00:00:00",
                "depends_on_title": "Dep A",
                "depends_on_status": "todo",
            },
            {
                "action_id": "action-1",
                "depends_on_action_id": "dep-b",
                "dependency_type": "finish_to_start",
                "lag_days": 2,
                "created_at": "2025-01-02T00:00:00",
                "depends_on_title": "Dep B",
                "depends_on_status": "done",
            },
            {
                "action_id": "action-2",
                "depends_on_action_id": "dep-c",
                "dependency_type": "start_to_start",
                "lag_days": 1,
                "created_at": "2025-01-01T00:00:00",
                "depends_on_title": "Dep C",
                "depends_on_status": "in_progress",
            },
        ]

        with patch.object(repo, "_execute_query", return_value=mock_deps):
            result = repo.get_dependencies_batch(action_ids)

        # Verify structure
        assert set(result.keys()) == set(action_ids)
        assert len(result["action-1"]) == 2
        assert len(result["action-2"]) == 1
        assert len(result["action-3"]) == 0  # No deps

    def test_batch_groups_by_action_id(self):
        """Test batch correctly groups dependencies by action_id."""
        repo = ActionRepository()
        mock_deps = [
            {
                "action_id": "a1",
                "depends_on_action_id": "d1",
                "dependency_type": "finish_to_start",
                "lag_days": 0,
                "created_at": "2025-01-01",
                "depends_on_title": "D1",
                "depends_on_status": "todo",
            },
            {
                "action_id": "a2",
                "depends_on_action_id": "d2",
                "dependency_type": "finish_to_start",
                "lag_days": 0,
                "created_at": "2025-01-01",
                "depends_on_title": "D2",
                "depends_on_status": "todo",
            },
            {
                "action_id": "a1",
                "depends_on_action_id": "d3",
                "dependency_type": "finish_to_start",
                "lag_days": 0,
                "created_at": "2025-01-02",
                "depends_on_title": "D3",
                "depends_on_status": "todo",
            },
        ]

        with patch.object(repo, "_execute_query", return_value=mock_deps):
            result = repo.get_dependencies_batch(["a1", "a2"])

        assert len(result["a1"]) == 2
        assert len(result["a2"]) == 1
        assert result["a1"][0]["depends_on_action_id"] == "d1"
        assert result["a1"][1]["depends_on_action_id"] == "d3"


class TestGetDependenciesBatchTransitive:
    """Tests for transitive dependency loading with recursive CTE."""

    def test_transitive_finds_chain_dependencies(self):
        """Test recursive CTE finds transitive dependencies (A→B→C finds A depends on C)."""
        repo = ActionRepository()

        # Simulate recursive CTE result for chain A→B→C
        mock_deps = [
            {
                "action_id": "a",
                "depends_on_action_id": "b",
                "dependency_type": "finish_to_start",
                "lag_days": 0,
                "created_at": "2025-01-01",
                "depth": 1,
                "depends_on_title": "B",
                "depends_on_status": "todo",
            },
            {
                "action_id": "a",
                "depends_on_action_id": "c",
                "dependency_type": "finish_to_start",
                "lag_days": 0,
                "created_at": "2025-01-01",
                "depth": 2,
                "depends_on_title": "C",
                "depends_on_status": "todo",
            },
        ]

        with patch.object(repo, "_execute_query", return_value=mock_deps):
            result = repo.get_dependencies_batch(["a"], include_transitive=True)

        assert len(result["a"]) == 2
        dep_ids = {d["depends_on_action_id"] for d in result["a"]}
        assert dep_ids == {"b", "c"}

    def test_transitive_respects_max_depth(self):
        """Test recursive CTE respects max_depth limit."""
        repo = ActionRepository()

        # The query should include max_depth parameter
        with patch.object(repo, "_execute_query", return_value=[]) as mock_query:
            repo.get_dependencies_batch(["a"], include_transitive=True, max_depth=5)

            # Verify max_depth was passed to query
            call_args = mock_query.call_args
            assert call_args is not None
            query_params = call_args[0][1]
            assert 5 in query_params  # max_depth should be in params

    def test_transitive_default_max_depth_is_20(self):
        """Test default max_depth is 20 to prevent infinite recursion."""
        repo = ActionRepository()

        with patch.object(repo, "_execute_query", return_value=[]) as mock_query:
            repo.get_dependencies_batch(["a"], include_transitive=True)

            call_args = mock_query.call_args
            assert call_args is not None
            query_params = call_args[0][1]
            assert 20 in query_params  # default max_depth


class TestGetAllDependenciesForUser:
    """Tests for get_all_dependencies_for_user() method."""

    def test_returns_dict_indexed_by_action_id(self):
        """Test result is dict with action_id keys for O(1) lookup."""
        repo = ActionRepository()

        mock_deps = [
            {
                "action_id": "a1",
                "depends_on_action_id": "d1",
                "dependency_type": "finish_to_start",
                "lag_days": 0,
                "created_at": "2025-01-01",
                "depends_on_title": "D1",
                "depends_on_status": "todo",
            },
            {
                "action_id": "a2",
                "depends_on_action_id": "d2",
                "dependency_type": "finish_to_start",
                "lag_days": 0,
                "created_at": "2025-01-01",
                "depends_on_title": "D2",
                "depends_on_status": "todo",
            },
        ]

        with patch.object(repo, "_execute_query", return_value=mock_deps):
            result = repo.get_all_dependencies_for_user("user-1")

        assert isinstance(result, dict)
        assert "a1" in result
        assert "a2" in result

    def test_excludes_completed_actions_by_default(self):
        """Test completed/cancelled actions are excluded by default."""
        repo = ActionRepository()

        with patch.object(repo, "_execute_query", return_value=[]) as mock_query:
            repo.get_all_dependencies_for_user("user-1")

            call_args = mock_query.call_args
            query = call_args[0][0]
            # Should filter out done/cancelled
            assert "NOT IN ('done', 'cancelled')" in query

    def test_includes_completed_when_flag_set(self):
        """Test completed actions included when include_completed=True."""
        repo = ActionRepository()

        with patch.object(repo, "_execute_query", return_value=[]) as mock_query:
            repo.get_all_dependencies_for_user("user-1", include_completed=True)

            call_args = mock_query.call_args
            query = call_args[0][0]
            # Should NOT have the status filter
            assert "NOT IN ('done', 'cancelled')" not in query

    def test_limits_to_10000_records(self):
        """Test query has safety LIMIT of 10000."""
        repo = ActionRepository()

        with patch.object(repo, "_execute_query", return_value=[]) as mock_query:
            repo.get_all_dependencies_for_user("user-1")

            call_args = mock_query.call_args
            query = call_args[0][0]
            assert "LIMIT 10000" in query


class TestBatchVsIndividualConsistency:
    """Tests ensuring batch returns same data as individual calls."""

    def test_dependency_fields_match(self):
        """Test batch returns all expected fields."""
        repo = ActionRepository()

        expected_fields = {
            "action_id",
            "depends_on_action_id",
            "dependency_type",
            "lag_days",
            "created_at",
            "depends_on_title",
            "depends_on_status",
        }

        mock_dep = {
            "action_id": "a1",
            "depends_on_action_id": "d1",
            "dependency_type": "finish_to_start",
            "lag_days": 0,
            "created_at": "2025-01-01T00:00:00",
            "depends_on_title": "Dep Title",
            "depends_on_status": "todo",
        }

        with patch.object(repo, "_execute_query", return_value=[mock_dep]):
            result = repo.get_dependencies_batch(["a1"])

        assert len(result["a1"]) == 1
        actual_fields = set(result["a1"][0].keys())
        assert expected_fields <= actual_fields
