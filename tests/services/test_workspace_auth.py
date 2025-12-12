"""Unit tests for workspace authorization service."""

import uuid
from unittest.mock import MagicMock, patch

from backend.api.workspaces.models import MemberRole
from backend.services.workspace_auth import (
    ROLE_PERMISSIONS,
    Permission,
    can_remove_member,
    can_transfer_ownership,
    check_permission,
    check_role,
    get_accessible_workspaces,
    is_member,
)


class TestCheckPermission:
    """Tests for check_permission function."""

    def test_owner_has_all_permissions(self):
        """Owner should have all permissions."""
        workspace_id = uuid.uuid4()
        user_id = "user_123"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_member_role.return_value = MemberRole.OWNER

            for perm in Permission:
                assert check_permission(workspace_id, user_id, perm) is True

    def test_admin_has_manage_members_permission(self):
        """Admin should have MANAGE_MEMBERS permission."""
        workspace_id = uuid.uuid4()
        user_id = "user_123"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_member_role.return_value = MemberRole.ADMIN

            assert check_permission(workspace_id, user_id, Permission.VIEW) is True
            assert check_permission(workspace_id, user_id, Permission.EDIT) is True
            assert check_permission(workspace_id, user_id, Permission.MANAGE_MEMBERS) is True
            assert check_permission(workspace_id, user_id, Permission.DELETE) is False

    def test_member_has_view_edit_only(self):
        """Member should only have VIEW and EDIT permissions."""
        workspace_id = uuid.uuid4()
        user_id = "user_123"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_member_role.return_value = MemberRole.MEMBER

            assert check_permission(workspace_id, user_id, Permission.VIEW) is True
            assert check_permission(workspace_id, user_id, Permission.EDIT) is True
            assert check_permission(workspace_id, user_id, Permission.MANAGE_MEMBERS) is False
            assert check_permission(workspace_id, user_id, Permission.DELETE) is False

    def test_non_member_has_no_permissions(self):
        """Non-member should have no permissions."""
        workspace_id = uuid.uuid4()
        user_id = "user_123"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_member_role.return_value = None

            for perm in Permission:
                assert check_permission(workspace_id, user_id, perm) is False


class TestCheckRole:
    """Tests for check_role function."""

    def test_owner_meets_all_role_requirements(self):
        """Owner should meet any role requirement."""
        workspace_id = uuid.uuid4()
        user_id = "user_123"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_member_role.return_value = MemberRole.OWNER

            assert check_role(workspace_id, user_id, MemberRole.MEMBER) is True
            assert check_role(workspace_id, user_id, MemberRole.ADMIN) is True
            assert check_role(workspace_id, user_id, MemberRole.OWNER) is True

    def test_admin_meets_member_and_admin_requirements(self):
        """Admin should meet MEMBER and ADMIN requirements."""
        workspace_id = uuid.uuid4()
        user_id = "user_123"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_member_role.return_value = MemberRole.ADMIN

            assert check_role(workspace_id, user_id, MemberRole.MEMBER) is True
            assert check_role(workspace_id, user_id, MemberRole.ADMIN) is True
            assert check_role(workspace_id, user_id, MemberRole.OWNER) is False

    def test_member_only_meets_member_requirement(self):
        """Member should only meet MEMBER requirement."""
        workspace_id = uuid.uuid4()
        user_id = "user_123"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_member_role.return_value = MemberRole.MEMBER

            assert check_role(workspace_id, user_id, MemberRole.MEMBER) is True
            assert check_role(workspace_id, user_id, MemberRole.ADMIN) is False
            assert check_role(workspace_id, user_id, MemberRole.OWNER) is False

    def test_non_member_meets_no_requirements(self):
        """Non-member should meet no role requirements."""
        workspace_id = uuid.uuid4()
        user_id = "user_123"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_member_role.return_value = None

            assert check_role(workspace_id, user_id, MemberRole.MEMBER) is False
            assert check_role(workspace_id, user_id, MemberRole.ADMIN) is False
            assert check_role(workspace_id, user_id, MemberRole.OWNER) is False


class TestIsMember:
    """Tests for is_member function."""

    def test_returns_true_for_member(self):
        """Should return True when user is a member."""
        workspace_id = uuid.uuid4()
        user_id = "user_123"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.is_member.return_value = True
            assert is_member(workspace_id, user_id) is True

    def test_returns_false_for_non_member(self):
        """Should return False when user is not a member."""
        workspace_id = uuid.uuid4()
        user_id = "user_123"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.is_member.return_value = False
            assert is_member(workspace_id, user_id) is False


class TestCanTransferOwnership:
    """Tests for can_transfer_ownership function."""

    def test_owner_can_transfer_to_member(self):
        """Owner should be able to transfer ownership to a member."""
        workspace_id = uuid.uuid4()
        owner_id = "owner_123"
        new_owner_id = "member_456"

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace
            mock_repo.is_member.return_value = True

            allowed, error = can_transfer_ownership(workspace_id, owner_id, new_owner_id)
            assert allowed is True
            assert error is None

    def test_non_owner_cannot_transfer(self):
        """Non-owner should not be able to transfer ownership."""
        workspace_id = uuid.uuid4()
        non_owner_id = "member_456"
        target_id = "member_789"

        mock_workspace = MagicMock()
        mock_workspace.owner_id = "owner_123"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace

            allowed, error = can_transfer_ownership(workspace_id, non_owner_id, target_id)
            assert allowed is False
            assert "Only the owner" in error

    def test_cannot_transfer_to_non_member(self):
        """Cannot transfer ownership to someone who is not a member."""
        workspace_id = uuid.uuid4()
        owner_id = "owner_123"
        non_member_id = "non_member_456"

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace
            mock_repo.is_member.return_value = False

            allowed, error = can_transfer_ownership(workspace_id, owner_id, non_member_id)
            assert allowed is False
            assert "must be a workspace member" in error

    def test_cannot_transfer_to_self(self):
        """Owner cannot transfer ownership to themselves."""
        workspace_id = uuid.uuid4()
        owner_id = "owner_123"

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace
            mock_repo.is_member.return_value = True

            allowed, error = can_transfer_ownership(workspace_id, owner_id, owner_id)
            assert allowed is False
            assert "yourself" in error


class TestCanRemoveMember:
    """Tests for can_remove_member function."""

    def test_admin_can_remove_member(self):
        """Admin should be able to remove a member."""
        workspace_id = uuid.uuid4()
        admin_id = "admin_123"
        member_id = "member_456"

        mock_workspace = MagicMock()
        mock_workspace.owner_id = "owner_789"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace
            mock_repo.get_member_role.return_value = MemberRole.ADMIN

            allowed, error = can_remove_member(workspace_id, admin_id, member_id)
            assert allowed is True
            assert error is None

    def test_cannot_remove_owner(self):
        """Cannot remove the workspace owner."""
        workspace_id = uuid.uuid4()
        admin_id = "admin_123"
        owner_id = "owner_456"

        mock_workspace = MagicMock()
        mock_workspace.owner_id = owner_id

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace

            allowed, error = can_remove_member(workspace_id, admin_id, owner_id)
            assert allowed is False
            assert "owner" in error.lower()

    def test_member_can_remove_self(self):
        """Member should be able to remove themselves (leave)."""
        workspace_id = uuid.uuid4()
        member_id = "member_123"

        mock_workspace = MagicMock()
        mock_workspace.owner_id = "owner_456"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace

            allowed, error = can_remove_member(workspace_id, member_id, member_id)
            assert allowed is True
            assert error is None

    def test_member_cannot_remove_others(self):
        """Member should not be able to remove other members."""
        workspace_id = uuid.uuid4()
        member1_id = "member_123"
        member2_id = "member_456"

        mock_workspace = MagicMock()
        mock_workspace.owner_id = "owner_789"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = mock_workspace
            mock_repo.get_member_role.return_value = MemberRole.MEMBER

            allowed, error = can_remove_member(workspace_id, member1_id, member2_id)
            assert allowed is False
            assert "permission" in error.lower()


class TestRolePermissionsMapping:
    """Tests for ROLE_PERMISSIONS mapping consistency."""

    def test_role_hierarchy_consistency(self):
        """Higher roles should have all permissions of lower roles."""
        member_perms = ROLE_PERMISSIONS[MemberRole.MEMBER]
        admin_perms = ROLE_PERMISSIONS[MemberRole.ADMIN]
        owner_perms = ROLE_PERMISSIONS[MemberRole.OWNER]

        # Admin should have all member permissions
        assert member_perms.issubset(admin_perms)
        # Owner should have all admin permissions
        assert admin_perms.issubset(owner_perms)

    def test_delete_is_owner_only(self):
        """DELETE permission should only be available to owner."""
        assert Permission.DELETE in ROLE_PERMISSIONS[MemberRole.OWNER]
        assert Permission.DELETE not in ROLE_PERMISSIONS[MemberRole.ADMIN]
        assert Permission.DELETE not in ROLE_PERMISSIONS[MemberRole.MEMBER]

    def test_manage_members_requires_admin(self):
        """MANAGE_MEMBERS should require at least admin role."""
        assert Permission.MANAGE_MEMBERS in ROLE_PERMISSIONS[MemberRole.OWNER]
        assert Permission.MANAGE_MEMBERS in ROLE_PERMISSIONS[MemberRole.ADMIN]
        assert Permission.MANAGE_MEMBERS not in ROLE_PERMISSIONS[MemberRole.MEMBER]


class TestGetAccessibleWorkspaces:
    """Tests for get_accessible_workspaces function."""

    def test_returns_workspace_ids(self):
        """Should return list of workspace UUIDs."""
        user_id = "user_123"
        ws1_id = uuid.uuid4()
        ws2_id = uuid.uuid4()

        mock_ws1 = MagicMock()
        mock_ws1.id = ws1_id
        mock_ws2 = MagicMock()
        mock_ws2.id = ws2_id

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_user_workspaces.return_value = [mock_ws1, mock_ws2]

            result = get_accessible_workspaces(user_id)
            assert result == [ws1_id, ws2_id]

    def test_returns_empty_list_for_no_workspaces(self):
        """Should return empty list when user has no workspaces."""
        user_id = "user_123"

        with patch("backend.services.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_user_workspaces.return_value = []

            result = get_accessible_workspaces(user_id)
            assert result == []
