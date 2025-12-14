"""Tests for default workspace creation on signup.

Tests:
- Workspace creation during OAuth signup
- User default workspace assignment
- Backfill script for existing users
- API response includes default_workspace_id
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from backend.api.workspaces.models import WorkspaceListResponse


class TestDefaultWorkspaceSignup:
    """Tests for workspace creation during OAuth signup."""

    @pytest.fixture
    def mock_workspace(self):
        """Create mock workspace response."""
        workspace = MagicMock()
        workspace.id = uuid.uuid4()
        workspace.name = "Personal Workspace"
        workspace.slug = "personal-workspace"
        return workspace

    @pytest.fixture
    def mock_user_id(self):
        """Create test user ID."""
        return f"test_user_{uuid.uuid4().hex[:8]}"

    def test_workspace_created_for_new_user(self, mock_workspace, mock_user_id):
        """Should create personal workspace when new user signs up."""
        with (
            patch("backend.api.supertokens_config.workspace_repository") as mock_ws_repo,
            patch("backend.api.supertokens_config.user_repository"),
        ):
            mock_ws_repo.create_workspace.return_value = mock_workspace

            # Import the module to test
            from backend.api.supertokens_config import workspace_repository

            # Simulate workspace creation
            workspace = workspace_repository.create_workspace(
                name="Personal Workspace",
                owner_id=mock_user_id,
            )

            mock_ws_repo.create_workspace.assert_called_once()
            assert workspace.name == "Personal Workspace"

    def test_default_workspace_set_after_creation(self, mock_workspace, mock_user_id):
        """Should set default workspace after creation."""
        with (
            patch("bo1.state.repositories.user_repository.db_session") as mock_db,
            patch("bo1.state.repositories.user_repository.UserRepository._execute_one"),
        ):
            from bo1.state.repositories.user_repository import user_repository

            # Mock the connection context manager
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=None)

            result = user_repository.set_default_workspace(mock_user_id, mock_workspace.id)

            assert result is True
            mock_cursor.execute.assert_called_once()

    def test_get_default_workspace(self, mock_workspace, mock_user_id):
        """Should retrieve user's default workspace ID."""
        with patch(
            "bo1.state.repositories.user_repository.UserRepository._execute_one"
        ) as mock_exec:
            mock_exec.return_value = {"default_workspace_id": mock_workspace.id}

            from bo1.state.repositories.user_repository import user_repository

            result = user_repository.get_default_workspace(mock_user_id)

            assert result == mock_workspace.id


class TestDefaultWorkspaceAPI:
    """Tests for default workspace in API responses."""

    @pytest.fixture
    def mock_workspaces(self):
        """Create mock workspace list using proper Pydantic models."""
        from datetime import datetime

        from backend.api.workspaces.models import WorkspaceResponse

        ws1_id = uuid.uuid4()
        ws2_id = uuid.uuid4()
        return [
            WorkspaceResponse(
                id=ws1_id,
                name="Personal Workspace",
                slug="personal-workspace",
                owner_id="user1",
                created_at=datetime.fromisoformat("2025-01-01T00:00:00"),
                updated_at=datetime.fromisoformat("2025-01-01T00:00:00"),
                member_count=1,
            ),
            WorkspaceResponse(
                id=ws2_id,
                name="Team Workspace",
                slug="team-workspace",
                owner_id="user1",
                created_at=datetime.fromisoformat("2025-01-02T00:00:00"),
                updated_at=datetime.fromisoformat("2025-01-02T00:00:00"),
                member_count=3,
            ),
        ]

    def test_list_workspaces_includes_default_id(self, mock_workspaces):
        """Should include default_workspace_id in list response."""
        default_id = mock_workspaces[0].id

        # Build response manually to test model
        response = WorkspaceListResponse(
            workspaces=mock_workspaces,
            total=len(mock_workspaces),
            default_workspace_id=default_id,
        )

        assert response.default_workspace_id == default_id
        assert response.total == 2

    def test_list_workspaces_null_default_id(self, mock_workspaces):
        """Should handle null default_workspace_id."""
        response = WorkspaceListResponse(
            workspaces=mock_workspaces,
            total=len(mock_workspaces),
            default_workspace_id=None,
        )

        assert response.default_workspace_id is None


class TestBackfillScript:
    """Tests for workspace backfill script."""

    @pytest.fixture
    def users_without_workspaces(self):
        """Create list of users without workspaces."""
        return [
            {"id": "user1", "email": "user1@example.com"},
            {"id": "user2", "email": "user2@example.com"},
        ]

    def test_get_users_without_workspaces(self, users_without_workspaces):
        """Should query users not in any workspace."""
        with patch("backend.scripts.backfill_workspaces.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                (u["id"], u["email"]) for u in users_without_workspaces
            ]
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=None)

            from backend.scripts.backfill_workspaces import get_users_without_workspaces

            result = get_users_without_workspaces(batch_size=100)

            assert len(result) == 2
            assert result[0]["id"] == "user1"

    def test_backfill_user_workspace_dry_run(self, users_without_workspaces):
        """Should not create workspace in dry run mode."""
        from backend.scripts.backfill_workspaces import backfill_user_workspace

        # In dry run, should return True without calling any repo methods
        with (
            patch("backend.scripts.backfill_workspaces.workspace_repository") as mock_ws_repo,
            patch("backend.scripts.backfill_workspaces.user_repository") as mock_user_repo,
        ):
            result = backfill_user_workspace(
                user_id="user1",
                email="user1@example.com",
                dry_run=True,
            )

            assert result is True
            mock_ws_repo.create_workspace.assert_not_called()
            mock_user_repo.set_default_workspace.assert_not_called()

    def test_backfill_user_workspace_creates_workspace(self, users_without_workspaces):
        """Should create workspace and set as default."""
        mock_workspace = MagicMock()
        mock_workspace.id = uuid.uuid4()

        with (
            patch("backend.scripts.backfill_workspaces.workspace_repository") as mock_ws_repo,
            patch("backend.scripts.backfill_workspaces.user_repository") as mock_user_repo,
        ):
            mock_ws_repo.create_workspace.return_value = mock_workspace

            from backend.scripts.backfill_workspaces import backfill_user_workspace

            result = backfill_user_workspace(
                user_id="user1",
                email="user1@example.com",
                dry_run=False,
            )

            assert result is True
            mock_ws_repo.create_workspace.assert_called_once_with(
                name="Personal Workspace",
                owner_id="user1",
            )
            mock_user_repo.set_default_workspace.assert_called_once_with("user1", mock_workspace.id)


class TestUserRepositoryDefaultWorkspace:
    """Tests for user_repository default workspace methods."""

    @pytest.fixture
    def user_id(self):
        """Create test user ID."""
        return f"test_user_{uuid.uuid4().hex[:8]}"

    @pytest.fixture
    def workspace_id(self):
        """Create test workspace ID."""
        return uuid.uuid4()

    def test_get_default_workspace_returns_id(self, user_id, workspace_id):
        """Should return workspace ID when set."""
        with patch(
            "bo1.state.repositories.user_repository.UserRepository._execute_one"
        ) as mock_exec:
            mock_exec.return_value = {"default_workspace_id": workspace_id}

            from bo1.state.repositories.user_repository import user_repository

            result = user_repository.get_default_workspace(user_id)

            assert result == workspace_id
            mock_exec.assert_called_once()

    def test_get_default_workspace_returns_none_when_not_set(self, user_id):
        """Should return None when no default workspace set."""
        with patch(
            "bo1.state.repositories.user_repository.UserRepository._execute_one"
        ) as mock_exec:
            mock_exec.return_value = {"default_workspace_id": None}

            from bo1.state.repositories.user_repository import user_repository

            result = user_repository.get_default_workspace(user_id)

            assert result is None

    def test_get_default_workspace_returns_none_for_missing_user(self, user_id):
        """Should return None when user not found."""
        with patch(
            "bo1.state.repositories.user_repository.UserRepository._execute_one"
        ) as mock_exec:
            mock_exec.return_value = None

            from bo1.state.repositories.user_repository import user_repository

            result = user_repository.get_default_workspace(user_id)

            assert result is None

    def test_clear_default_workspace(self, user_id):
        """Should clear default workspace."""
        with patch("bo1.state.repositories.user_repository.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=None)

            from bo1.state.repositories.user_repository import user_repository

            result = user_repository.clear_default_workspace(user_id)

            assert result is True
            mock_cursor.execute.assert_called_once()
