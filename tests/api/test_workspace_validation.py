"""Tests for workspace access validation.

Verifies:
- require_workspace_access returns 403 on wrong workspace
- require_workspace_access returns 404 on non-existent workspace
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from backend.api.middleware.workspace_auth import (
    require_workspace_access,
    require_workspace_role,
)


class TestWorkspaceAccessValidation:
    """Test workspace access validation."""

    def test_workspace_id_validated_returns_404_not_found(self):
        """Access check should return 404 for non-existent workspace."""
        fake_workspace_id = uuid.uuid4()
        fake_user_id = "user_123"

        with patch("backend.api.middleware.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                require_workspace_access(fake_workspace_id, fake_user_id)

            assert exc_info.value.status_code == 404
            detail = exc_info.value.detail
            message = detail["message"].lower() if isinstance(detail, dict) else detail.lower()
            assert "not found" in message

    def test_workspace_id_validated_returns_403_not_member(self):
        """Access check should return 403 if user is not a member."""
        fake_workspace_id = uuid.uuid4()
        fake_user_id = "user_123"

        with (
            patch("backend.api.middleware.workspace_auth.workspace_repository") as mock_repo,
            patch("backend.api.middleware.workspace_auth.is_member") as mock_is_member,
        ):
            mock_repo.get_workspace.return_value = {"id": fake_workspace_id, "name": "Test"}
            mock_is_member.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                require_workspace_access(fake_workspace_id, fake_user_id)

            assert exc_info.value.status_code == 403
            detail = exc_info.value.detail
            message = detail["message"].lower() if isinstance(detail, dict) else detail.lower()
            assert "access" in message

    def test_workspace_id_validated_allows_member(self):
        """Access check should succeed if user is a member."""
        fake_workspace_id = uuid.uuid4()
        fake_user_id = "user_123"

        with (
            patch("backend.api.middleware.workspace_auth.workspace_repository") as mock_repo,
            patch("backend.api.middleware.workspace_auth.is_member") as mock_is_member,
        ):
            mock_repo.get_workspace.return_value = {"id": fake_workspace_id, "name": "Test"}
            mock_is_member.return_value = True

            # Should not raise
            require_workspace_access(fake_workspace_id, fake_user_id)


class TestWorkspaceRoleValidation:
    """Test workspace role validation."""

    def test_role_check_returns_404_not_found(self):
        """Role check should return 404 for non-existent workspace."""
        from backend.api.workspaces.models import MemberRole

        fake_workspace_id = uuid.uuid4()
        fake_user_id = "user_123"

        with patch("backend.api.middleware.workspace_auth.workspace_repository") as mock_repo:
            mock_repo.get_workspace.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                require_workspace_role(fake_workspace_id, fake_user_id, MemberRole.ADMIN)

            assert exc_info.value.status_code == 404

    def test_role_check_returns_403_insufficient_role(self):
        """Role check should return 403 if user has insufficient role."""
        from backend.api.workspaces.models import MemberRole

        fake_workspace_id = uuid.uuid4()
        fake_user_id = "user_123"

        with (
            patch("backend.api.middleware.workspace_auth.workspace_repository") as mock_repo,
            patch("backend.api.middleware.workspace_auth.check_role") as mock_check_role,
        ):
            mock_repo.get_workspace.return_value = {"id": fake_workspace_id, "name": "Test"}
            mock_check_role.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                require_workspace_role(fake_workspace_id, fake_user_id, MemberRole.ADMIN)

            assert exc_info.value.status_code == 403
            detail = exc_info.value.detail
            message = detail["message"].lower() if isinstance(detail, dict) else detail.lower()
            assert "role" in message
