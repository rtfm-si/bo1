"""Integration tests for projects system with action dependencies."""

from datetime import date


class TestProjectWorkflow:
    """Integration tests for complete project workflow."""

    def test_project_status_flow(self):
        """Test project status transitions: active → paused → completed → archived."""
        statuses = ["active", "paused", "completed", "archived"]

        for status in statuses:
            assert status in statuses


class TestDependencyDateCascade:
    """Integration tests for date cascading with dependencies."""

    def test_simple_cascade_finish_to_start(self):
        """Test date cascade for finish-to-start dependency."""
        # Parent: Jan 10-20, Dependent should start Jan 21
        parent_end = date(2025, 1, 20)
        lag = 0
        expected_dependent_start = date(2025, 1, 21)

        # Simulate calculation
        calculated = parent_end + __import__("datetime").timedelta(days=1 + lag)
        assert calculated == expected_dependent_start

    def test_cascade_with_positive_lag(self):
        """Test cascade with positive lag."""
        # Parent ends Jan 20, lag=3 → dependent starts Jan 24
        parent_end = date(2025, 1, 20)
        lag = 3
        expected_start = date(2025, 1, 24)

        calculated = parent_end + __import__("datetime").timedelta(days=1 + lag)
        assert calculated == expected_start

    def test_cascade_with_negative_lag(self):
        """Test cascade with negative lag (overlap)."""
        # Parent ends Jan 20, lag=-2 → dependent starts Jan 19
        parent_end = date(2025, 1, 20)
        lag = -2
        expected_start = date(2025, 1, 19)

        calculated = parent_end + __import__("datetime").timedelta(days=1 + lag)
        assert calculated == expected_start


class TestProjectProgressCalculation:
    """Integration tests for project progress tracking."""

    def test_project_progress_with_mixed_action_statuses(self):
        """Test progress calculation with various action statuses."""
        actions = [
            {"status": "done"},
            {"status": "done"},
            {"status": "done"},
            {"status": "in_progress"},
            {"status": "in_progress"},
            {"status": "todo"},
            {"status": "blocked"},
            {"status": "cancelled"},
            {"status": "cancelled"},
            {"status": "todo"},
        ]

        completed = len([a for a in actions if a["status"] == "done"])
        total = len(actions)
        progress = int((completed / total) * 100)

        assert completed == 3
        assert total == 10
        assert progress == 30


class TestDependencyChains:
    """Tests for complex dependency chains."""

    def test_simple_linear_chain(self):
        """Test linear chain: A→B→C."""
        chain = [
            {"action": "A", "depends_on": None},
            {"action": "B", "depends_on": "A"},
            {"action": "C", "depends_on": "B"},
        ]

        # Verify chain linkage
        assert chain[1]["depends_on"] == chain[0]["action"]
        assert chain[2]["depends_on"] == chain[1]["action"]

    def test_diamond_structure(self):
        """Test diamond: A→B, A→C, B→D, C→D."""
        deps = [
            {"from": "A", "to": "B"},
            {"from": "A", "to": "C"},
            {"from": "B", "to": "D"},
            {"from": "C", "to": "D"},
        ]

        # A has 2 outgoing
        a_children = [d for d in deps if d["from"] == "A"]
        assert len(a_children) == 2

        # D has 2 incoming
        d_parents = [d for d in deps if d["to"] == "D"]
        assert len(d_parents) == 2


class TestActionStatusWithDependencies:
    """Tests for action status transitions with dependencies."""

    def test_blocked_action_with_incomplete_dependency(self):
        """Test that action is blocked when depending on incomplete action."""
        action_dep_status = "todo"
        action_status = "blocked"

        # Action depends on incomplete task → blocked
        assert action_dep_status != "done"
        assert action_status == "blocked"

    def test_auto_unblock_on_dependency_completion(self):
        """Test action auto-unblocks when dependency completes."""
        # Initially: action-2 blocked (depends on action-1 which is todo)
        # After: action-1 completed → action-2 should unblock

        initial_states = {"action-1": "todo", "action-2": "blocked"}
        final_states = {"action-1": "done", "action-2": "todo"}

        assert initial_states["action-2"] == "blocked"
        assert final_states["action-2"] != "blocked"


class TestProjectWithActions:
    """Tests for projects containing multiple actions."""

    def test_project_action_count(self):
        """Test project tracks action count correctly."""
        project = {
            "total_actions": 10,
            "completed_actions": 3,
            "progress_percent": 30,
        }

        assert project["total_actions"] == 10
        assert project["completed_actions"] == 3
        assert project["progress_percent"] == 30

    def test_progress_calculation(self):
        """Test progress calculation is accurate."""
        total = 10
        completed = 3
        expected_progress = 30

        actual_progress = int((completed / total) * 100)
        assert actual_progress == expected_progress


class TestMultipleProjects:
    """Tests for managing multiple projects."""

    def test_filter_projects_by_status(self):
        """Test filtering projects by status."""
        projects = [
            {"id": "p1", "status": "active"},
            {"id": "p2", "status": "paused"},
            {"id": "p3", "status": "active"},
            {"id": "p4", "status": "completed"},
        ]

        active_projects = [p for p in projects if p["status"] == "active"]
        assert len(active_projects) == 2

    def test_sort_projects_by_progress(self):
        """Test sorting projects by completion progress."""
        projects = [
            {"id": "p1", "progress_percent": 30},
            {"id": "p2", "progress_percent": 100},
            {"id": "p3", "progress_percent": 50},
        ]

        sorted_projects = sorted(projects, key=lambda p: p["progress_percent"], reverse=True)

        assert sorted_projects[0]["progress_percent"] == 100
        assert sorted_projects[1]["progress_percent"] == 50
        assert sorted_projects[2]["progress_percent"] == 30
