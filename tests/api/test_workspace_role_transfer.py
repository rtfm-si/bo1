"""Tests for workspace role transfer and management API."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from backend.api.workspaces.models import MemberRole


class TestCanTransferOwnership:
    """Tests for can_transfer_ownership validation."""

    @pytest.fixture
    def workspace_id(self):
        """Create test workspace ID."""
        return uuid.uuid4()

    @pytest.fixture
    def owner_id(self):
        """Create owner user ID."""
        return "owner_123"

    @pytest.fixture
    def target_id(self):
        """Create target user ID."""
        return "target_456"

    def test_owner_can_transfer_to_member(self, workspace_id, owner_id, target_id):
        """Owner should be able to transfer to a workspace member."""
        from backend.services.workspace_auth import can_transfer_ownership

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace
            mock_repo.is_member.return_value = True

            with patch("backend.services.workspace_auth.is_member") as mock_is_member:
                mock_is_member.return_value = True

                can_do, error = can_transfer_ownership(workspace_id, owner_id, target_id)

                assert can_do is True
                assert error is None

    def test_non_owner_cannot_transfer(self, workspace_id, owner_id, target_id):
        """Non-owner should not be able to transfer ownership."""
        from backend.services.workspace_auth import can_transfer_ownership

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        non_owner_id = "not_the_owner"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace

            can_do, error = can_transfer_ownership(workspace_id, non_owner_id, target_id)

            assert can_do is False
            assert "Only the owner can transfer ownership" in error

    def test_cannot_transfer_to_non_member(self, workspace_id, owner_id, target_id):
        """Cannot transfer to someone not in the workspace."""
        from backend.services.workspace_auth import can_transfer_ownership

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace

            with patch("backend.services.workspace_auth.is_member") as mock_is_member:
                mock_is_member.return_value = False

                can_do, error = can_transfer_ownership(workspace_id, owner_id, target_id)

                assert can_do is False
                assert "must be a workspace member" in error

    def test_cannot_transfer_to_self(self, workspace_id, owner_id):
        """Owner cannot transfer ownership to themselves."""
        from backend.services.workspace_auth import can_transfer_ownership

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace

            with patch("backend.services.workspace_auth.is_member") as mock_is_member:
                mock_is_member.return_value = True

                can_do, error = can_transfer_ownership(workspace_id, owner_id, owner_id)

                assert can_do is False
                assert "Cannot transfer ownership to yourself" in error


class TestCanPromoteMember:
    """Tests for can_promote_member validation."""

    @pytest.fixture
    def workspace_id(self):
        """Create test workspace ID."""
        return uuid.uuid4()

    @pytest.fixture
    def owner_id(self):
        """Create owner user ID."""
        return "owner_123"

    @pytest.fixture
    def member_id(self):
        """Create member user ID."""
        return "member_456"

    def test_owner_can_promote_member(self, workspace_id, owner_id, member_id):
        """Owner should be able to promote a member to admin."""
        from backend.services.workspace_auth import can_promote_member

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace
            mock_repo.get_member_role.return_value = MemberRole.MEMBER

            can_do, error = can_promote_member(workspace_id, owner_id, member_id)

            assert can_do is True
            assert error is None

    def test_non_owner_cannot_promote(self, workspace_id, owner_id, member_id):
        """Non-owner should not be able to promote members."""
        from backend.services.workspace_auth import can_promote_member

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        admin_id = "admin_789"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace

            can_do, error = can_promote_member(workspace_id, admin_id, member_id)

            assert can_do is False
            assert "Only the owner can promote" in error

    def test_cannot_promote_admin(self, workspace_id, owner_id, member_id):
        """Cannot promote someone who is already admin."""
        from backend.services.workspace_auth import can_promote_member

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace
            mock_repo.get_member_role.return_value = MemberRole.ADMIN

            can_do, error = can_promote_member(workspace_id, owner_id, member_id)

            assert can_do is False
            assert "already admin" in error

    def test_cannot_promote_self(self, workspace_id, owner_id):
        """Cannot promote yourself."""
        from backend.services.workspace_auth import can_promote_member

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace

            can_do, error = can_promote_member(workspace_id, owner_id, owner_id)

            assert can_do is False
            assert "Cannot promote yourself" in error


class TestCanDemoteAdmin:
    """Tests for can_demote_admin validation."""

    @pytest.fixture
    def workspace_id(self):
        """Create test workspace ID."""
        return uuid.uuid4()

    @pytest.fixture
    def owner_id(self):
        """Create owner user ID."""
        return "owner_123"

    @pytest.fixture
    def admin_id(self):
        """Create admin user ID."""
        return "admin_456"

    def test_owner_can_demote_admin(self, workspace_id, owner_id, admin_id):
        """Owner should be able to demote an admin to member."""
        from backend.services.workspace_auth import can_demote_admin

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace
            mock_repo.get_member_role.return_value = MemberRole.ADMIN

            can_do, error = can_demote_admin(workspace_id, owner_id, admin_id)

            assert can_do is True
            assert error is None

    def test_non_owner_cannot_demote(self, workspace_id, owner_id, admin_id):
        """Non-owner should not be able to demote admins."""
        from backend.services.workspace_auth import can_demote_admin

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        other_admin_id = "other_admin_789"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace

            can_do, error = can_demote_admin(workspace_id, other_admin_id, admin_id)

            assert can_do is False
            assert "Only the owner can demote" in error

    def test_cannot_demote_member(self, workspace_id, owner_id, admin_id):
        """Cannot demote someone who is already a member."""
        from backend.services.workspace_auth import can_demote_admin

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace
            mock_repo.get_member_role.return_value = MemberRole.MEMBER

            can_do, error = can_demote_admin(workspace_id, owner_id, admin_id)

            assert can_do is False
            assert "not admin" in error

    def test_cannot_demote_owner(self, workspace_id, owner_id):
        """Cannot demote the workspace owner."""
        from backend.services.workspace_auth import can_demote_admin

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace

            can_do, error = can_demote_admin(workspace_id, owner_id, owner_id)

            assert can_do is False
            assert "Cannot demote the workspace owner" in error


class TestWorkspaceRepositoryRoleMethods:
    """Tests for workspace repository role management methods."""

    @pytest.fixture
    def workspace_id(self):
        """Create test workspace ID."""
        return uuid.uuid4()

    def test_transfer_ownership_updates_roles(self, workspace_id):
        """Transfer ownership should update both workspace and member roles."""
        from bo1.state.repositories.workspace_repository import WorkspaceRepository

        repo = WorkspaceRepository()
        old_owner = "old_owner_123"
        new_owner = "new_owner_456"

        # Mock the execute methods
        with patch.object(repo, "_execute_count") as mock_execute:
            mock_execute.return_value = 1  # All updates succeed

            with patch.object(repo, "log_role_change") as mock_log:
                result = repo.transfer_ownership(workspace_id, old_owner, new_owner)

                assert result is True
                # Should have 3 execute calls: demote old owner, promote new owner, update workspace
                assert mock_execute.call_count == 3
                # Should log 2 role changes
                assert mock_log.call_count == 2

    def test_transfer_ownership_fails_gracefully(self, workspace_id):
        """Transfer ownership should return False if workspace update fails."""
        from bo1.state.repositories.workspace_repository import WorkspaceRepository

        repo = WorkspaceRepository()
        old_owner = "old_owner_123"
        new_owner = "new_owner_456"

        with patch.object(repo, "_execute_count") as mock_execute:
            # First two calls succeed (member role updates), third fails (workspace update)
            mock_execute.side_effect = [1, 1, 0]

            with patch.object(repo, "log_role_change"):
                result = repo.transfer_ownership(workspace_id, old_owner, new_owner)

                assert result is False

    def test_log_role_change_creates_audit_record(self, workspace_id):
        """log_role_change should insert an audit record."""
        from bo1.state.repositories.workspace_repository import WorkspaceRepository

        repo = WorkspaceRepository()

        with patch.object(repo, "_execute_count") as mock_execute:
            mock_execute.return_value = 1

            repo.log_role_change(
                workspace_id=workspace_id,
                user_id="user_123",
                old_role=MemberRole.MEMBER,
                new_role=MemberRole.ADMIN,
                changed_by="owner_456",
                change_type="promote",
            )

            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert "INSERT INTO workspace_role_changes" in call_args[0][0]

    def test_get_role_history_returns_records(self, workspace_id):
        """get_role_history should return audit records."""
        from bo1.state.repositories.workspace_repository import WorkspaceRepository

        repo = WorkspaceRepository()

        mock_rows = [
            {
                "id": uuid.uuid4(),
                "workspace_id": workspace_id,
                "user_id": "user_123",
                "user_email": "user@example.com",
                "old_role": "member",
                "new_role": "admin",
                "change_type": "promote",
                "changed_by": "owner_456",
                "changed_by_email": "owner@example.com",
                "changed_at": "2024-01-15T10:30:00",
            }
        ]

        with patch.object(repo, "_execute_query") as mock_query:
            mock_query.return_value = mock_rows

            result = repo.get_role_history(workspace_id, limit=50)

            assert len(result) == 1
            assert result[0]["user_email"] == "user@example.com"
            assert result[0]["change_type"] == "promote"
