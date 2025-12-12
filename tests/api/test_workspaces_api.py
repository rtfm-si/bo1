"""Tests for workspaces API routes and authorization."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.api.workspaces.models import MemberRole


class TestWorkspaceAccessChecker:
    """Tests for WorkspaceAccessChecker dependency."""

    @pytest.fixture
    def workspace_id(self):
        """Create test workspace ID."""
        return uuid.uuid4()

    @pytest.fixture
    def user(self):
        """Create test user."""
        return {"user_id": "test_user_1", "email": "test@example.com"}

    def test_access_allowed_for_member(self, workspace_id, user):
        """Should allow access for workspace member."""
        from backend.api.middleware.workspace_auth import require_workspace_access

        mock_workspace = MagicMock()
        mock_workspace.id = workspace_id

        with patch("backend.api.middleware.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace
            # Also patch is_member in this module
            with patch("backend.api.middleware.workspace_auth.is_member") as mock_is_member:
                mock_is_member.return_value = True

                # Should not raise
                require_workspace_access(workspace_id, user["user_id"])
                mock_is_member.assert_called_once()

    def test_access_denied_for_non_member(self, workspace_id, user):
        """Should deny access for non-member."""
        from backend.api.middleware.workspace_auth import require_workspace_access

        mock_workspace = MagicMock()
        mock_workspace.id = workspace_id

        with patch("backend.api.middleware.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace
            with patch("backend.api.middleware.workspace_auth.is_member") as mock_is_member:
                mock_is_member.return_value = False

                with pytest.raises(HTTPException) as exc_info:
                    require_workspace_access(workspace_id, user["user_id"])

                assert exc_info.value.status_code == 403

    def test_workspace_not_found(self, workspace_id, user):
        """Should return 404 for non-existent workspace."""
        from backend.api.middleware.workspace_auth import require_workspace_access

        with patch("backend.api.middleware.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                require_workspace_access(workspace_id, user["user_id"])

            assert exc_info.value.status_code == 404


class TestWorkspaceRoleChecker:
    """Tests for WorkspaceRoleChecker dependency."""

    @pytest.fixture
    def workspace_id(self):
        """Create test workspace ID."""
        return uuid.uuid4()

    @pytest.fixture
    def user(self):
        """Create test user."""
        return {"user_id": "test_user_1", "email": "test@example.com"}

    def test_role_allowed_for_owner(self, workspace_id, user):
        """Owner should meet all role requirements."""
        from backend.api.middleware.workspace_auth import require_workspace_role

        mock_workspace = MagicMock()
        mock_workspace.id = workspace_id

        with patch("backend.api.middleware.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace

            with patch("backend.api.middleware.workspace_auth.check_role") as mock_check:
                mock_check.return_value = True

                # Should not raise
                require_workspace_role(workspace_id, user["user_id"], MemberRole.ADMIN)

    def test_role_denied_for_member_when_admin_required(self, workspace_id, user):
        """Member should be denied when admin is required."""
        from backend.api.middleware.workspace_auth import require_workspace_role

        mock_workspace = MagicMock()
        mock_workspace.id = workspace_id

        with patch("backend.api.middleware.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace

            with patch("backend.api.middleware.workspace_auth.check_role") as mock_check:
                mock_check.return_value = False

                with pytest.raises(HTTPException) as exc_info:
                    require_workspace_role(workspace_id, user["user_id"], MemberRole.ADMIN)

                assert exc_info.value.status_code == 403


class TestWorkspacePermissionChecker:
    """Tests for WorkspacePermissionChecker dependency."""

    @pytest.fixture
    def workspace_id(self):
        """Create test workspace ID."""
        return uuid.uuid4()

    @pytest.fixture
    def user(self):
        """Create test user."""
        return {"user_id": "test_user_1", "email": "test@example.com"}

    def test_permission_allowed(self, workspace_id, user):
        """Should allow when user has permission."""
        from backend.api.middleware.workspace_auth import require_workspace_permission
        from backend.services.workspace_auth import Permission

        mock_workspace = MagicMock()
        mock_workspace.id = workspace_id

        with patch("backend.api.middleware.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace

            with patch("backend.api.middleware.workspace_auth.check_permission") as mock_check:
                mock_check.return_value = True

                # Should not raise
                require_workspace_permission(workspace_id, user["user_id"], Permission.EDIT)

    def test_permission_denied(self, workspace_id, user):
        """Should deny when user lacks permission."""
        from backend.api.middleware.workspace_auth import require_workspace_permission
        from backend.services.workspace_auth import Permission

        mock_workspace = MagicMock()
        mock_workspace.id = workspace_id

        with patch("backend.api.middleware.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace

            with patch("backend.api.middleware.workspace_auth.check_permission") as mock_check:
                mock_check.return_value = False

                with pytest.raises(HTTPException) as exc_info:
                    require_workspace_permission(workspace_id, user["user_id"], Permission.DELETE)

                assert exc_info.value.status_code == 403


class TestWorkspaceModels:
    """Tests for workspace Pydantic models."""

    def test_workspace_create_validation(self):
        """Should validate workspace creation data."""
        from backend.api.workspaces.models import WorkspaceCreate

        ws = WorkspaceCreate(name="Test Workspace", slug="test-workspace")
        assert ws.name == "Test Workspace"
        assert ws.slug == "test-workspace"

    def test_workspace_create_name_required(self):
        """Name should be required."""
        from pydantic import ValidationError

        from backend.api.workspaces.models import WorkspaceCreate

        with pytest.raises(ValidationError):
            WorkspaceCreate(slug="test")

    def test_workspace_update_partial(self):
        """Should allow partial updates."""
        from backend.api.workspaces.models import WorkspaceUpdate

        # Only updating name
        update = WorkspaceUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.slug is None

    def test_workspace_invite_validation(self):
        """Should validate invite data."""
        from backend.api.workspaces.models import WorkspaceInvite

        invite = WorkspaceInvite(email="test@example.com", role=MemberRole.MEMBER)
        assert invite.email == "test@example.com"
        assert invite.role == MemberRole.MEMBER

    def test_member_role_values(self):
        """Should have correct role values."""
        assert MemberRole.MEMBER.value == "member"
        assert MemberRole.ADMIN.value == "admin"
        assert MemberRole.OWNER.value == "owner"


class TestWorkspaceContextExtraction:
    """Tests for workspace context extraction from request."""

    @pytest.fixture
    def user(self):
        """Create test user."""
        return {"user_id": "test_user_1", "email": "test@example.com"}

    @pytest.mark.asyncio
    async def test_extract_from_path_parameter(self, user):
        """Should extract workspace_id from path parameter."""
        from backend.api.middleware.workspace_auth import get_workspace_context

        workspace_id = uuid.uuid4()

        result = await get_workspace_context(workspace_id=workspace_id, user=user)
        assert result == workspace_id

    @pytest.mark.asyncio
    async def test_extract_from_header(self, user):
        """Should extract workspace_id from header when path is None."""
        from backend.api.middleware.workspace_auth import get_workspace_context

        workspace_id = uuid.uuid4()

        result = await get_workspace_context(
            workspace_id=None, x_workspace_id=str(workspace_id), user=user
        )
        assert result == workspace_id

    @pytest.mark.asyncio
    async def test_path_takes_precedence_over_header(self, user):
        """Path parameter should take precedence over header."""
        from backend.api.middleware.workspace_auth import get_workspace_context

        path_id = uuid.uuid4()
        header_id = uuid.uuid4()

        result = await get_workspace_context(
            workspace_id=path_id, x_workspace_id=str(header_id), user=user
        )
        assert result == path_id

    @pytest.mark.asyncio
    async def test_returns_none_when_no_workspace(self, user):
        """Should return None when no workspace context provided."""
        from backend.api.middleware.workspace_auth import get_workspace_context

        result = await get_workspace_context(workspace_id=None, x_workspace_id=None, user=user)
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_header_format(self, user):
        """Should raise 400 for invalid header format."""
        from backend.api.middleware.workspace_auth import get_workspace_context

        with pytest.raises(HTTPException) as exc_info:
            await get_workspace_context(workspace_id=None, x_workspace_id="not-a-uuid", user=user)

        assert exc_info.value.status_code == 400
