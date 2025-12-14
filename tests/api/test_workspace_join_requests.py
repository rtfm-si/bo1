"""Tests for workspace join request functionality."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.api.workspaces.models import (
    JoinRequestCreate,
    JoinRequestStatus,
    MemberRole,
    WorkspaceDiscoverability,
)


class TestJoinRequestRepository:
    """Tests for join request repository methods."""

    @pytest.fixture
    def workspace_id(self):
        """Create test workspace ID."""
        return uuid.uuid4()

    @pytest.fixture
    def user_id(self):
        """Create test user ID."""
        return "test_user_123"

    @pytest.fixture
    def request_id(self):
        """Create test request ID."""
        return uuid.uuid4()

    def test_create_join_request_success(self, workspace_id, user_id):
        """Should create join request for eligible user."""
        from bo1.state.repositories.workspace_repository import WorkspaceRepository

        repo = WorkspaceRepository()

        with patch.object(repo, "is_member", return_value=False):
            with patch.object(repo, "get_pending_join_request", return_value=None):
                with patch.object(repo, "_execute_returning") as mock_exec:
                    mock_exec.return_value = {
                        "id": uuid.uuid4(),
                        "workspace_id": workspace_id,
                        "user_id": user_id,
                        "message": "Hello",
                        "status": "pending",
                        "rejection_reason": None,
                        "reviewed_by": None,
                        "reviewed_at": None,
                        "created_at": "2025-01-01T00:00:00Z",
                    }

                    result = repo.create_join_request(
                        workspace_id=workspace_id,
                        user_id=user_id,
                        message="Hello",
                    )

                    assert result.status == JoinRequestStatus.PENDING
                    assert result.message == "Hello"

    def test_create_join_request_already_member(self, workspace_id, user_id):
        """Should reject request from existing member."""
        from bo1.state.repositories.workspace_repository import WorkspaceRepository

        repo = WorkspaceRepository()

        with patch.object(repo, "is_member", return_value=True):
            with pytest.raises(ValueError, match="already a member"):
                repo.create_join_request(
                    workspace_id=workspace_id,
                    user_id=user_id,
                )

    def test_create_join_request_pending_exists(self, workspace_id, user_id):
        """Should reject when pending request already exists."""
        from bo1.state.repositories.workspace_repository import WorkspaceRepository

        repo = WorkspaceRepository()

        existing_request = MagicMock()

        with patch.object(repo, "is_member", return_value=False):
            with patch.object(repo, "get_pending_join_request", return_value=existing_request):
                with pytest.raises(ValueError, match="already has a pending"):
                    repo.create_join_request(
                        workspace_id=workspace_id,
                        user_id=user_id,
                    )

    def test_approve_request_adds_member(self, workspace_id, user_id, request_id):
        """Should add user as member when request is approved."""
        from bo1.state.repositories.workspace_repository import WorkspaceRepository

        repo = WorkspaceRepository()

        mock_request = MagicMock()
        mock_request.workspace_id = workspace_id
        mock_request.user_id = user_id
        mock_request.status = JoinRequestStatus.PENDING

        with patch.object(repo, "get_join_request", return_value=mock_request):
            with patch.object(repo, "_execute_one") as mock_exec:
                mock_exec.return_value = {
                    "id": request_id,
                    "workspace_id": workspace_id,
                    "user_id": user_id,
                    "message": None,
                    "status": "approved",
                    "rejection_reason": None,
                    "reviewed_by": "admin_user",
                    "reviewed_at": "2025-01-01T00:00:00Z",
                    "created_at": "2025-01-01T00:00:00Z",
                }
                with patch.object(repo, "_add_member_internal") as mock_add:
                    result = repo.approve_request(request_id, "admin_user")

                    assert result.status == JoinRequestStatus.APPROVED
                    mock_add.assert_called_once_with(
                        workspace_id=workspace_id,
                        user_id=user_id,
                        role=MemberRole.MEMBER,
                        invited_by="admin_user",
                    )

    def test_reject_request_with_reason(self, workspace_id, user_id, request_id):
        """Should reject request and store reason."""
        from bo1.state.repositories.workspace_repository import WorkspaceRepository

        repo = WorkspaceRepository()

        with patch.object(repo, "_execute_one") as mock_exec:
            mock_exec.return_value = {
                "id": request_id,
                "workspace_id": workspace_id,
                "user_id": user_id,
                "message": None,
                "status": "rejected",
                "rejection_reason": "Not a fit",
                "reviewed_by": "admin_user",
                "reviewed_at": "2025-01-01T00:00:00Z",
                "created_at": "2025-01-01T00:00:00Z",
            }

            result = repo.reject_request(request_id, "admin_user", "Not a fit")

            assert result.status == JoinRequestStatus.REJECTED
            assert result.rejection_reason == "Not a fit"


class TestJoinRequestEndpoints:
    """Tests for join request API endpoints."""

    @pytest.fixture
    def workspace_id(self):
        """Create test workspace ID."""
        return uuid.uuid4()

    @pytest.fixture
    def user(self):
        """Create test user."""
        return {"user_id": "test_user_123", "email": "test@example.com"}

    def test_submit_join_request_requires_request_to_join_setting(self, workspace_id, user):
        """Should only allow join requests for workspaces with request_to_join."""
        from backend.api.workspaces.routes import submit_join_request

        mock_workspace = MagicMock()
        mock_workspace.id = workspace_id

        with patch("backend.api.workspaces.routes.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace
            mock_repo.get_discoverability.return_value = WorkspaceDiscoverability.PRIVATE

            with pytest.raises(HTTPException) as exc_info:
                import asyncio

                asyncio.run(
                    submit_join_request(
                        request=JoinRequestCreate(message="Hello"),
                        workspace_id=workspace_id,
                        user=user,
                    )
                )

            assert exc_info.value.status_code == 403
            assert "does not accept join requests" in exc_info.value.detail

    def test_submit_join_request_success(self, workspace_id, user):
        """Should create join request for eligible workspace."""
        from backend.api.workspaces.routes import submit_join_request

        mock_workspace = MagicMock()
        mock_workspace.id = workspace_id
        mock_workspace.name = "Test Workspace"

        mock_request = MagicMock()
        mock_request.id = uuid.uuid4()
        mock_request.workspace_id = workspace_id
        mock_request.user_id = user["user_id"]
        mock_request.status = JoinRequestStatus.PENDING

        with patch("backend.api.workspaces.routes.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace
            mock_repo.get_discoverability.return_value = WorkspaceDiscoverability.REQUEST_TO_JOIN
            mock_repo.create_join_request.return_value = mock_request
            mock_repo.get_members.return_value = []

            with patch("backend.api.workspaces.routes._notify_admins_of_join_request"):
                import asyncio

                result = asyncio.run(
                    submit_join_request(
                        request=JoinRequestCreate(message="Hello"),
                        workspace_id=workspace_id,
                        user=user,
                    )
                )

                assert result.status == JoinRequestStatus.PENDING
                mock_repo.create_join_request.assert_called_once()


class TestDiscoverabilitySettings:
    """Tests for workspace discoverability settings."""

    @pytest.fixture
    def workspace_id(self):
        """Create test workspace ID."""
        return uuid.uuid4()

    def test_update_discoverability(self, workspace_id):
        """Should update workspace discoverability setting."""
        from bo1.state.repositories.workspace_repository import WorkspaceRepository

        repo = WorkspaceRepository()

        with patch.object(repo, "_execute_count", return_value=1):
            result = repo.update_discoverability(
                workspace_id,
                WorkspaceDiscoverability.REQUEST_TO_JOIN,
            )

            assert result is True

    def test_get_discoverability_default(self, workspace_id):
        """Should return PRIVATE as default discoverability."""
        from bo1.state.repositories.workspace_repository import WorkspaceRepository

        repo = WorkspaceRepository()

        with patch.object(repo, "_execute_one", return_value=None):
            result = repo.get_discoverability(workspace_id)

            assert result == WorkspaceDiscoverability.PRIVATE
