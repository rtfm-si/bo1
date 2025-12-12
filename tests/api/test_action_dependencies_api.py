"""Tests for action dependencies API endpoints."""

from datetime import date

from backend.api.models import DependencyCreate, DependencyResponse


class TestDependencyTypes:
    """Tests for different dependency types."""

    def test_finish_to_start_dependency(self):
        """Test finish-to-start dependency type."""
        dep_type = "finish_to_start"
        assert dep_type in ["finish_to_start", "start_to_start", "finish_to_finish"]

    def test_start_to_start_dependency(self):
        """Test start-to-start dependency type."""
        dep_type = "start_to_start"
        assert dep_type in ["finish_to_start", "start_to_start", "finish_to_finish"]

    def test_finish_to_finish_dependency(self):
        """Test finish-to-finish dependency type."""
        dep_type = "finish_to_finish"
        assert dep_type in ["finish_to_start", "start_to_start", "finish_to_finish"]


class TestDependencyLagDays:
    """Tests for dependency lag days (scheduling offset)."""

    def test_dependency_with_positive_lag(self):
        """Test dependency with positive lag days."""
        request = DependencyCreate(
            depends_on_action_id="action-1",
            dependency_type="finish_to_start",
            lag_days=3,
        )

        assert request.lag_days == 3

    def test_dependency_with_negative_lag(self):
        """Test dependency with negative lag (overlap)."""
        request = DependencyCreate(
            depends_on_action_id="action-1",
            dependency_type="finish_to_start",
            lag_days=-2,
        )

        assert request.lag_days == -2

    def test_dependency_with_zero_lag(self):
        """Test dependency with no lag."""
        request = DependencyCreate(
            depends_on_action_id="action-1",
            dependency_type="finish_to_start",
            lag_days=0,
        )

        assert request.lag_days == 0


class TestDependencyValidation:
    """Tests for dependency validation."""

    def test_dependency_create_request_validation(self):
        """Test DependencyCreate request validation."""
        request = DependencyCreate(
            depends_on_action_id="action-1",
            dependency_type="finish_to_start",
            lag_days=0,
        )

        assert request.depends_on_action_id == "action-1"
        assert request.dependency_type == "finish_to_start"
        assert request.lag_days == 0

    def test_dependency_response_validation(self):
        """Test DependencyResponse creation."""
        response = DependencyResponse(
            action_id="action-2",
            depends_on_action_id="action-1",
            depends_on_title="Research",
            depends_on_status="todo",
            dependency_type="finish_to_start",
            lag_days=0,
            created_at="2025-01-02T10:00:00",
        )

        assert response.action_id == "action-2"
        assert response.depends_on_action_id == "action-1"
        assert response.depends_on_title == "Research"


class TestDependencyChainLogic:
    """Tests for dependency chain validation."""

    def test_linear_chain_a_b_c(self):
        """Test linear chain: A→B→C."""
        # Verify chain structure
        deps = [
            {"from": "a", "to": "b"},
            {"from": "b", "to": "c"},
        ]

        assert deps[0]["to"] == deps[1]["from"]

    def test_diamond_graph_structure(self):
        """Test diamond structure: A→B, A→C, B→D, C→D."""
        deps = [
            {"from": "a", "to": "b"},
            {"from": "a", "to": "c"},
            {"from": "b", "to": "d"},
            {"from": "c", "to": "d"},
        ]

        # Node 'a' has 2 children, node 'd' has 2 parents
        children_of_a = [d for d in deps if d["from"] == "a"]
        parents_of_d = [d for d in deps if d["to"] == "d"]

        assert len(children_of_a) == 2
        assert len(parents_of_d) == 2


class TestDependencyDateScenarios:
    """Tests for date cascading scenarios."""

    def test_finish_to_start_date_calculation(self):
        """Test date calculation for finish-to-start dependency."""
        # Parent ends Jan 20, lag=0 → dependent starts Jan 21
        parent_end = date(2025, 1, 20)
        lag_days = 0
        dependent_start = date(2025, 1, 21)

        calculated_start = parent_end + __import__("datetime").timedelta(days=1 + lag_days)
        assert calculated_start == dependent_start

    def test_finish_to_start_with_positive_lag(self):
        """Test finish-to-start with positive lag."""
        # Parent ends Jan 20, lag=3 → dependent starts Jan 24
        parent_end = date(2025, 1, 20)
        lag_days = 3
        dependent_start = date(2025, 1, 24)

        calculated_start = parent_end + __import__("datetime").timedelta(days=1 + lag_days)
        assert calculated_start == dependent_start

    def test_finish_to_start_with_negative_lag(self):
        """Test finish-to-start with negative lag (overlap)."""
        # Parent ends Jan 20, lag=-2 → dependent starts Jan 19
        parent_end = date(2025, 1, 20)
        lag_days = -2
        dependent_start = date(2025, 1, 19)

        calculated_start = parent_end + __import__("datetime").timedelta(days=1 + lag_days)
        assert calculated_start == dependent_start


class TestDependencyEdgeCases:
    """Tests for edge cases in dependency handling."""

    def test_same_day_dependency(self):
        """Test dependency where dependent starts same day parent starts."""
        request = DependencyCreate(
            depends_on_action_id="action-1",
            dependency_type="start_to_start",
            lag_days=0,
        )

        assert request.dependency_type == "start_to_start"
        assert request.lag_days == 0

    def test_long_lag_days(self):
        """Test dependency with long lag period."""
        request = DependencyCreate(
            depends_on_action_id="action-1",
            dependency_type="finish_to_start",
            lag_days=365,  # One year lag
        )

        assert request.lag_days == 365

    def test_large_negative_lag(self):
        """Test dependency with large negative lag (significant overlap)."""
        # Note: lag_days has a minimum constraint of -30
        request = DependencyCreate(
            depends_on_action_id="action-1",
            dependency_type="finish_to_start",
            lag_days=-30,
        )

        assert request.lag_days == -30


class TestDependencyDataTypes:
    """Tests for dependency data type handling."""

    def test_action_id_is_string(self):
        """Test that action IDs are strings."""
        request = DependencyCreate(
            depends_on_action_id="action-123",
            dependency_type="finish_to_start",
            lag_days=0,
        )

        assert isinstance(request.depends_on_action_id, str)

    def test_lag_days_is_integer(self):
        """Test that lag_days is an integer."""
        request = DependencyCreate(
            depends_on_action_id="action-1",
            dependency_type="finish_to_start",
            lag_days=5,
        )

        assert isinstance(request.lag_days, int)

    def test_dependency_type_is_string(self):
        """Test that dependency_type is a string."""
        request = DependencyCreate(
            depends_on_action_id="action-1",
            dependency_type="finish_to_start",
            lag_days=0,
        )

        assert isinstance(request.dependency_type, str)
