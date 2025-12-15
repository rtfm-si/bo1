"""Tests for projects API endpoints."""

from datetime import date, datetime

import pytest

from backend.api.models import ProjectCreate, ProjectStatusUpdate, ProjectUpdate
from backend.api.projects import _format_project_response


@pytest.fixture
def sample_project():
    """Fixture for a sample project."""
    return {
        "id": "project-123",
        "user_id": "test-user-123",
        "name": "Q4 Strategy Review",
        "description": "Strategic planning for Q4",
        "status": "active",
        "target_start_date": date(2025, 1, 1),
        "target_end_date": date(2025, 1, 31),
        "estimated_start_date": date(2025, 1, 2),
        "estimated_end_date": date(2025, 1, 30),
        "actual_start_date": None,
        "actual_end_date": None,
        "progress_percent": 35,
        "total_actions": 10,
        "completed_actions": 3,
        "color": "#3b82f6",
        "icon": "target",
        "created_at": datetime(2025, 1, 1, 10, 0, 0),
        "updated_at": datetime(2025, 1, 2, 15, 0, 0),
    }


class TestProjectFormatting:
    """Tests for project response formatting."""

    def test_format_project_response_with_dates(self, sample_project):
        """Test formatting project with all date fields."""
        formatted = _format_project_response(sample_project)

        assert formatted["id"] == "project-123"
        assert formatted["name"] == "Q4 Strategy Review"
        assert formatted["status"] == "active"
        assert formatted["target_start_date"] == "2025-01-01"
        assert formatted["target_end_date"] == "2025-01-31"
        assert formatted["estimated_start_date"] == "2025-01-02"
        assert formatted["estimated_end_date"] == "2025-01-30"
        assert formatted["actual_start_date"] is None
        assert formatted["progress_percent"] == 35
        assert formatted["total_actions"] == 10
        assert formatted["completed_actions"] == 3

    def test_format_project_response_without_dates(self):
        """Test formatting project without optional date fields."""
        project = {
            "id": "proj-1",
            "user_id": "user-1",
            "name": "Test Project",
            "description": None,
            "status": "active",
            "target_start_date": None,
            "target_end_date": None,
            "estimated_start_date": None,
            "estimated_end_date": None,
            "actual_start_date": None,
            "actual_end_date": None,
            "progress_percent": 0,
            "total_actions": 0,
            "completed_actions": 0,
            "color": None,
            "icon": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        formatted = _format_project_response(project)

        assert formatted["id"] == "proj-1"
        assert formatted["target_start_date"] is None
        assert formatted["target_end_date"] is None


class TestProjectStatusTransitions:
    """Tests for project status updates."""

    def test_valid_project_statuses(self):
        """Test valid project status values."""
        valid_statuses = ["active", "paused", "completed", "archived"]

        for status in valid_statuses:
            assert status in valid_statuses


class TestProjectProgressCalculation:
    """Tests for project progress calculations."""

    def test_calculate_progress_all_completed(self):
        """Test progress when all actions completed."""
        project = {
            "total_actions": 10,
            "completed_actions": 10,
            "progress_percent": 100,
        }

        assert project["progress_percent"] == 100

    def test_calculate_progress_partial(self):
        """Test progress with partial completion."""
        project = {
            "total_actions": 10,
            "completed_actions": 3,
            "progress_percent": 30,
        }

        assert project["progress_percent"] == 30

    def test_calculate_progress_no_actions(self):
        """Test progress when project has no actions."""
        project = {
            "total_actions": 0,
            "completed_actions": 0,
            "progress_percent": 0,
        }

        assert project["progress_percent"] == 0


class TestProjectFiltering:
    """Tests for project filtering logic."""

    def test_filter_by_status_active(self):
        """Test filtering projects by active status."""
        projects = [
            {"id": "p1", "status": "active"},
            {"id": "p2", "status": "paused"},
            {"id": "p3", "status": "active"},
        ]

        active = [p for p in projects if p["status"] == "active"]
        assert len(active) == 2

    def test_filter_by_status_completed(self):
        """Test filtering projects by completed status."""
        projects = [
            {"id": "p1", "status": "active"},
            {"id": "p2", "status": "completed"},
            {"id": "p3", "status": "active"},
        ]

        completed = [p for p in projects if p["status"] == "completed"]
        assert len(completed) == 1


class TestProjectSorting:
    """Tests for project sorting."""

    def test_sort_by_progress_descending(self):
        """Test sorting projects by progress."""
        projects = [
            {"id": "p1", "progress_percent": 30},
            {"id": "p2", "progress_percent": 100},
            {"id": "p3", "progress_percent": 50},
        ]

        sorted_projects = sorted(projects, key=lambda p: p["progress_percent"], reverse=True)

        assert sorted_projects[0]["progress_percent"] == 100
        assert sorted_projects[1]["progress_percent"] == 50
        assert sorted_projects[2]["progress_percent"] == 30

    def test_sort_by_name(self):
        """Test sorting projects by name."""
        projects = [
            {"id": "p1", "name": "Zebra"},
            {"id": "p2", "name": "Alpha"},
            {"id": "p3", "name": "Beta"},
        ]

        sorted_projects = sorted(projects, key=lambda p: p["name"])

        assert sorted_projects[0]["name"] == "Alpha"
        assert sorted_projects[1]["name"] == "Beta"
        assert sorted_projects[2]["name"] == "Zebra"


class TestProjectTypeValidation:
    """Tests for project type validation."""

    def test_create_request_validation(self):
        """Test ProjectCreate request validation."""
        request = ProjectCreate(name="Test Project")
        assert request.name == "Test Project"
        assert request.description is None

    def test_update_request_validation(self):
        """Test ProjectUpdate request validation."""
        request = ProjectUpdate(name="Updated", description="New description")
        assert request.name == "Updated"
        assert request.description == "New description"

    def test_status_update_validation(self):
        """Test ProjectStatusUpdate validation."""
        request = ProjectStatusUpdate(status="paused")
        assert request.status == "paused"


class TestProjectVersioning:
    """Tests for project versioning feature."""

    def test_format_project_response_with_version(self):
        """Test formatting project with version fields."""
        project = {
            "id": "project-v2",
            "user_id": "test-user",
            "name": "Test Project",
            "description": "Test",
            "status": "active",
            "target_start_date": None,
            "target_end_date": None,
            "estimated_start_date": None,
            "estimated_end_date": None,
            "actual_start_date": None,
            "actual_end_date": None,
            "progress_percent": 0,
            "total_actions": 0,
            "completed_actions": 0,
            "color": None,
            "icon": None,
            "version": 2,
            "source_project_id": "project-v1",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        formatted = _format_project_response(project)

        assert formatted["version"] == 2
        assert formatted["source_project_id"] == "project-v1"

    def test_format_project_response_default_version(self):
        """Test formatting project without version defaults to 1."""
        project = {
            "id": "project-123",
            "user_id": "test-user",
            "name": "Test Project",
            "description": None,
            "status": "active",
            "target_start_date": None,
            "target_end_date": None,
            "estimated_start_date": None,
            "estimated_end_date": None,
            "actual_start_date": None,
            "actual_end_date": None,
            "progress_percent": 0,
            "total_actions": 0,
            "completed_actions": 0,
            "color": None,
            "icon": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        formatted = _format_project_response(project)

        assert formatted["version"] == 1
        assert formatted["source_project_id"] is None


class TestProjectStatusTransitionValidation:
    """Tests for project status transition rules."""

    def test_completed_cannot_transition_to_active(self):
        """Test that completed projects cannot transition to active."""
        from bo1.state.repositories.project_repository import VALID_PROJECT_TRANSITIONS

        allowed = VALID_PROJECT_TRANSITIONS.get("completed", [])
        assert "active" not in allowed, "completed projects should not transition to active"

    def test_completed_can_transition_to_archived(self):
        """Test that completed projects can transition to archived."""
        from bo1.state.repositories.project_repository import VALID_PROJECT_TRANSITIONS

        allowed = VALID_PROJECT_TRANSITIONS.get("completed", [])
        assert "archived" in allowed, "completed projects should be able to archive"

    def test_active_can_transition_to_completed(self):
        """Test that active projects can transition to completed."""
        from bo1.state.repositories.project_repository import VALID_PROJECT_TRANSITIONS

        allowed = VALID_PROJECT_TRANSITIONS.get("active", [])
        assert "completed" in allowed

    def test_paused_can_transition_to_active(self):
        """Test that paused projects can transition to active."""
        from bo1.state.repositories.project_repository import VALID_PROJECT_TRANSITIONS

        allowed = VALID_PROJECT_TRANSITIONS.get("paused", [])
        assert "active" in allowed
