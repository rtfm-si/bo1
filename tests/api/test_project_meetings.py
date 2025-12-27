"""Tests for project meetings API endpoint.

Tests:
- Model validation for CreateProjectMeetingRequest
- 404 if project not found
- 403 if user not in workspace
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi import HTTPException


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {"user_id": "test-user-123", "subscription_tier": "free"}


@pytest.fixture
def mock_project():
    """Mock project data."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": "test-user-123",
        "name": "Test Project",
        "description": "A test project for meetings",
        "status": "active",
        "progress_percent": 50,
        "total_actions": 4,
        "completed_actions": 2,
    }


class TestCreateProjectMeeting:
    """Tests for POST /api/v1/projects/{id}/meetings endpoint."""

    @pytest.mark.asyncio
    @patch("backend.api.projects.project_repository")
    async def test_create_meeting_project_not_found(
        self,
        mock_project_repo,
        mock_user,
    ):
        """Test 404 when project not found."""
        from backend.api.models import CreateProjectMeetingRequest
        from backend.api.projects import create_project_meeting

        mock_project_repo.get.return_value = None

        request = CreateProjectMeetingRequest()
        with pytest.raises(HTTPException) as exc_info:
            await create_project_meeting(
                project_id="nonexistent",
                request=request,
                user=mock_user,
            )

        assert exc_info.value.status_code == 404
        detail = exc_info.value.detail
        msg = detail if isinstance(detail, str) else detail.get("message", "")
        assert "not found" in msg.lower()

    @pytest.mark.asyncio
    @patch("backend.api.projects.project_repository")
    async def test_create_meeting_access_denied(
        self,
        mock_project_repo,
        mock_user,
        mock_project,
    ):
        """Test 403 when user doesn't own project."""
        from backend.api.models import CreateProjectMeetingRequest
        from backend.api.projects import create_project_meeting

        # Different user owns the project
        mock_project["user_id"] = "other-user-456"
        mock_project_repo.get.return_value = mock_project

        request = CreateProjectMeetingRequest()
        with pytest.raises(HTTPException) as exc_info:
            await create_project_meeting(
                project_id=mock_project["id"],
                request=request,
                user=mock_user,
            )

        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail
        msg = detail if isinstance(detail, str) else detail.get("message", "")
        assert "denied" in msg.lower()


class TestCreateProjectMeetingModel:
    """Tests for CreateProjectMeetingRequest model."""

    def test_default_values(self):
        """Test model default values."""
        from backend.api.models import CreateProjectMeetingRequest

        request = CreateProjectMeetingRequest()
        assert request.problem_statement is None
        assert request.include_project_context is True

    def test_custom_values(self):
        """Test model with custom values."""
        from backend.api.models import CreateProjectMeetingRequest

        request = CreateProjectMeetingRequest(
            problem_statement="How do we fix the bug?",
            include_project_context=False,
        )
        assert request.problem_statement == "How do we fix the bug?"
        assert request.include_project_context is False

    def test_problem_statement_validation(self):
        """Test problem statement minimum length validation."""
        from pydantic import ValidationError

        from backend.api.models import CreateProjectMeetingRequest

        # Too short
        with pytest.raises(ValidationError):
            CreateProjectMeetingRequest(problem_statement="Short")

        # Just long enough
        request = CreateProjectMeetingRequest(problem_statement="A" * 10)
        assert len(request.problem_statement) == 10
