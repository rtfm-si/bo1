"""Tests for workspace invitation API endpoints."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.api.workspaces.models import InvitationStatus, MemberRole


class TestInvitationRepository:
    """Tests for InvitationRepository CRUD operations."""

    @pytest.fixture
    def workspace_id(self):
        """Create test workspace ID."""
        return uuid.uuid4()

    @pytest.fixture
    def invitation_id(self):
        """Create test invitation ID."""
        return uuid.uuid4()

    def test_create_invitation(self, workspace_id):
        """Should create an invitation with correct data."""
        from backend.services.invitation_repository import InvitationRepository

        repo = InvitationRepository()
        email = "newuser@example.com"
        role = MemberRole.MEMBER
        invited_by = "user_1"

        with patch.object(repo, "_execute_returning") as mock_exec:
            mock_exec.return_value = {
                "id": uuid.uuid4(),
                "workspace_id": workspace_id,
                "email": email,
                "role": role.value,
                "status": "pending",
                "expires_at": datetime.now(UTC) + timedelta(days=7),
                "invited_by": invited_by,
                "created_at": datetime.now(UTC),
                "accepted_at": None,
            }

            invitation = repo.create_invitation(
                workspace_id=workspace_id,
                email=email,
                role=role,
                invited_by=invited_by,
            )

            assert invitation.email == email
            assert invitation.role == role
            assert invitation.status == InvitationStatus.PENDING
            mock_exec.assert_called_once()

    def test_get_invitation_by_token(self, workspace_id):
        """Should retrieve invitation by token."""
        from backend.services.invitation_repository import InvitationRepository

        repo = InvitationRepository()
        token = str(uuid.uuid4())

        with patch.object(repo, "_execute_one") as mock_exec:
            mock_exec.return_value = {
                "id": uuid.uuid4(),
                "workspace_id": workspace_id,
                "email": "test@example.com",
                "role": "member",
                "status": "pending",
                "expires_at": datetime.now(UTC) + timedelta(days=7),
                "invited_by": "user_1",
                "created_at": datetime.now(UTC),
                "accepted_at": None,
                "workspace_name": "Test Workspace",
                "inviter_email": "owner@example.com",
            }

            invitation = repo.get_invitation_by_token(token)

            assert invitation is not None
            assert invitation.workspace_name == "Test Workspace"

    def test_get_invitation_by_invalid_token(self):
        """Should return None for invalid token format."""
        from backend.services.invitation_repository import InvitationRepository

        repo = InvitationRepository()
        invitation = repo.get_invitation_by_token("invalid-not-uuid")
        assert invitation is None

    def test_has_pending_invitation(self, workspace_id):
        """Should check for existing pending invitation."""
        from backend.services.invitation_repository import InvitationRepository

        repo = InvitationRepository()
        email = "test@example.com"

        with patch.object(repo, "_execute_one") as mock_exec:
            mock_exec.return_value = {"1": 1}
            result = repo.has_pending_invitation(workspace_id, email)
            assert result is True

            mock_exec.return_value = None
            result = repo.has_pending_invitation(workspace_id, email)
            assert result is False

    def test_list_pending_invitations(self, workspace_id):
        """Should list pending invitations for workspace."""
        from backend.services.invitation_repository import InvitationRepository

        repo = InvitationRepository()

        with patch.object(repo, "_execute_query") as mock_exec:
            mock_exec.return_value = [
                {
                    "id": uuid.uuid4(),
                    "workspace_id": workspace_id,
                    "email": "user1@example.com",
                    "role": "member",
                    "status": "pending",
                    "expires_at": datetime.now(UTC) + timedelta(days=7),
                    "invited_by": "owner",
                    "created_at": datetime.now(UTC),
                    "accepted_at": None,
                    "inviter_email": "owner@example.com",
                },
                {
                    "id": uuid.uuid4(),
                    "workspace_id": workspace_id,
                    "email": "user2@example.com",
                    "role": "admin",
                    "status": "pending",
                    "expires_at": datetime.now(UTC) + timedelta(days=7),
                    "invited_by": "owner",
                    "created_at": datetime.now(UTC),
                    "accepted_at": None,
                    "inviter_email": "owner@example.com",
                },
            ]

            invitations = repo.list_pending_invitations(workspace_id)
            assert len(invitations) == 2
            assert invitations[0].email == "user1@example.com"
            assert invitations[1].role == MemberRole.ADMIN

    def test_accept_invitation(self):
        """Should mark invitation as accepted."""
        from backend.services.invitation_repository import InvitationRepository

        repo = InvitationRepository()
        token = str(uuid.uuid4())
        user_id = "user_1"

        with patch.object(repo, "_execute_returning") as mock_exec:
            mock_exec.return_value = {"id": uuid.uuid4()}
            result = repo.accept_invitation(token, user_id)
            assert result is True

            mock_exec.return_value = None
            result = repo.accept_invitation(token, user_id)
            assert result is False

    def test_decline_invitation(self):
        """Should mark invitation as declined."""
        from backend.services.invitation_repository import InvitationRepository

        repo = InvitationRepository()
        token = str(uuid.uuid4())

        with patch.object(repo, "_execute_returning") as mock_exec:
            mock_exec.return_value = {"id": uuid.uuid4()}
            result = repo.decline_invitation(token)
            assert result is True

    def test_revoke_invitation(self, workspace_id, invitation_id):
        """Should revoke pending invitation."""
        from backend.services.invitation_repository import InvitationRepository

        repo = InvitationRepository()

        with patch.object(repo, "_execute_returning") as mock_exec:
            mock_exec.return_value = {"id": invitation_id}
            result = repo.revoke_invitation(invitation_id, workspace_id)
            assert result is True


class TestInvitationService:
    """Tests for invitation service business logic."""

    @pytest.fixture
    def workspace_id(self):
        """Create test workspace ID."""
        return uuid.uuid4()

    @pytest.fixture
    def mock_workspace(self, workspace_id):
        """Create mock workspace."""
        mock = MagicMock()
        mock.id = workspace_id
        mock.name = "Test Workspace"
        return mock

    def test_send_invitation_success(self, workspace_id, mock_workspace):
        """Should create and send invitation successfully."""
        from backend.services import invitation_service
        from backend.services.invitation_repository import invitation_repository

        mock_invitation = MagicMock()
        mock_invitation.id = uuid.uuid4()
        mock_invitation.email = "test@example.com"
        mock_invitation.expires_at = datetime.now(UTC) + timedelta(days=7)

        with (
            patch.object(invitation_repository, "create_invitation", return_value=mock_invitation),
            patch.object(
                invitation_repository, "get_invitation_token", return_value=str(uuid.uuid4())
            ),
            patch.object(invitation_repository, "has_pending_invitation", return_value=False),
            patch("backend.services.invitation_service.workspace_repository") as mock_ws_repo,
            patch("backend.services.invitation_service.send_email"),
            patch("backend.services.invitation_service.user_repository") as mock_user_repo,
        ):
            mock_ws_repo.get_workspace.return_value = mock_workspace
            mock_ws_repo.is_member.return_value = False
            mock_user_repo.get_by_email.return_value = None
            mock_user_repo.get_by_id.return_value = {"email": "owner@example.com"}

            result = invitation_service.send_invitation(
                workspace_id=workspace_id,
                email="test@example.com",
                role=MemberRole.MEMBER,
                invited_by="owner_user_id",
            )

            assert result == mock_invitation

    def test_send_invitation_already_member(self, workspace_id, mock_workspace):
        """Should raise AlreadyMemberError if user is member."""
        from backend.services import invitation_service
        from backend.services.invitation_service import AlreadyMemberError

        with (
            patch("backend.services.invitation_service.workspace_repository") as mock_ws_repo,
            patch("backend.services.invitation_service.user_repository") as mock_user_repo,
        ):
            mock_ws_repo.get_workspace.return_value = mock_workspace
            mock_ws_repo.is_member.return_value = True
            mock_user_repo.get_by_email.return_value = {"id": "existing_user"}

            with pytest.raises(AlreadyMemberError):
                invitation_service.send_invitation(
                    workspace_id=workspace_id,
                    email="test@example.com",
                    role=MemberRole.MEMBER,
                    invited_by="owner_user_id",
                )

    def test_send_invitation_duplicate(self, workspace_id, mock_workspace):
        """Should raise DuplicateInvitationError for pending invite."""
        from backend.services import invitation_service
        from backend.services.invitation_repository import invitation_repository
        from backend.services.invitation_service import DuplicateInvitationError

        with (
            patch.object(invitation_repository, "has_pending_invitation", return_value=True),
            patch("backend.services.invitation_service.workspace_repository") as mock_ws_repo,
            patch("backend.services.invitation_service.user_repository") as mock_user_repo,
        ):
            mock_ws_repo.get_workspace.return_value = mock_workspace
            mock_ws_repo.is_member.return_value = False
            mock_user_repo.get_by_email.return_value = None

            with pytest.raises(DuplicateInvitationError):
                invitation_service.send_invitation(
                    workspace_id=workspace_id,
                    email="test@example.com",
                    role=MemberRole.MEMBER,
                    invited_by="owner_user_id",
                )

    def test_accept_invitation_success(self, workspace_id):
        """Should accept invitation and add user to workspace."""
        from backend.services import invitation_service
        from backend.services.invitation_repository import invitation_repository

        mock_invitation = MagicMock()
        mock_invitation.email = "user@example.com"
        mock_invitation.status.value = "pending"
        mock_invitation.expires_at = datetime.now(UTC) + timedelta(days=1)
        mock_invitation.workspace_id = workspace_id
        mock_invitation.role = MemberRole.MEMBER
        mock_invitation.invited_by = "owner"

        with (
            patch.object(
                invitation_repository, "get_invitation_by_token", return_value=mock_invitation
            ),
            patch.object(invitation_repository, "accept_invitation", return_value=True),
            patch("backend.services.invitation_service.workspace_repository") as mock_ws_repo,
        ):
            mock_ws_repo.is_member.return_value = False

            invitation_service.accept_invitation(
                token="test-token",  # noqa: S106
                user_id="user_id",
                user_email="user@example.com",
            )

            mock_ws_repo.add_member.assert_called_once()

    def test_accept_invitation_expired(self, workspace_id):
        """Should raise InvitationExpiredError for expired invitation."""
        from backend.services import invitation_service
        from backend.services.invitation_repository import invitation_repository
        from backend.services.invitation_service import InvitationExpiredError

        mock_invitation = MagicMock()
        mock_invitation.email = "user@example.com"
        mock_invitation.status.value = "pending"
        mock_invitation.expires_at = datetime.now(UTC) - timedelta(days=1)

        with patch.object(
            invitation_repository, "get_invitation_by_token", return_value=mock_invitation
        ):
            with pytest.raises(InvitationExpiredError):
                invitation_service.accept_invitation(
                    token="test-token",  # noqa: S106
                    user_id="user_id",
                    user_email="user@example.com",
                )

    def test_accept_invitation_email_mismatch(self, workspace_id):
        """Should raise InvitationInvalidError for email mismatch."""
        from backend.services import invitation_service
        from backend.services.invitation_repository import invitation_repository
        from backend.services.invitation_service import InvitationInvalidError

        mock_invitation = MagicMock()
        mock_invitation.email = "different@example.com"
        mock_invitation.status.value = "pending"
        mock_invitation.expires_at = datetime.now(UTC) + timedelta(days=1)

        with patch.object(
            invitation_repository, "get_invitation_by_token", return_value=mock_invitation
        ):
            with pytest.raises(InvitationInvalidError):
                invitation_service.accept_invitation(
                    token="test-token",  # noqa: S106
                    user_id="user_id",
                    user_email="user@example.com",
                )

    def test_decline_invitation_success(self):
        """Should decline invitation."""
        from backend.services import invitation_service
        from backend.services.invitation_repository import invitation_repository

        mock_invitation = MagicMock()
        mock_invitation.status.value = "pending"

        with (
            patch.object(
                invitation_repository, "get_invitation_by_token", return_value=mock_invitation
            ),
            patch.object(invitation_repository, "decline_invitation", return_value=True),
        ):
            result = invitation_service.decline_invitation("test-token")
            assert result is True


class TestInvitationAPIEndpoints:
    """Tests for invitation API endpoint handlers."""

    @pytest.fixture
    def workspace_id(self):
        """Create test workspace ID."""
        return uuid.uuid4()

    @pytest.fixture
    def user(self):
        """Create test user."""
        return {"user_id": "test_user_1", "email": "test@example.com"}

    @pytest.mark.asyncio
    async def test_send_invitation_admin_cannot_invite_admin(self, workspace_id, user):
        """Admin users should not be able to invite other admins."""
        from backend.api.workspaces.invitations import send_invitation
        from backend.api.workspaces.models import InvitationCreate

        request = InvitationCreate(email="new@example.com", role=MemberRole.ADMIN)

        with (
            patch("backend.api.workspaces.invitations.invitation_service"),
            patch(
                "bo1.state.repositories.workspace_repository.workspace_repository"
            ) as mock_ws_repo,
        ):
            mock_ws_repo.get_member_role.return_value = MemberRole.ADMIN

            with pytest.raises(HTTPException) as exc_info:
                await send_invitation(request, workspace_id, user)

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_send_invitation_cannot_invite_owner(self, workspace_id, user):
        """Cannot invite users as owners."""
        from backend.api.workspaces.invitations import send_invitation
        from backend.api.workspaces.models import InvitationCreate

        request = InvitationCreate(email="new@example.com", role=MemberRole.OWNER)

        with pytest.raises(HTTPException) as exc_info:
            await send_invitation(request, workspace_id, user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_pending_invitations_empty_email(self, user):
        """Should return empty list if user has no email."""
        from backend.api.workspaces.invitations import get_pending_invitations

        user_no_email = {"user_id": "test_user_1"}

        result = await get_pending_invitations(user_no_email)

        assert result.invitations == []
        assert result.total == 0
