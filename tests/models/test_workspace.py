"""Tests for Workspace and WorkspaceMember models."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from bo1.models import Workspace, WorkspaceMember, WorkspaceRole


class TestWorkspaceRoundtrip:
    """Test Workspace model serialization roundtrips."""

    @pytest.fixture
    def sample_workspace_dict(self) -> dict:
        """Realistic Workspace data matching DB schema."""
        return {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Acme Corp",
            "slug": "acme-corp",
            "owner_id": "user_test_123",
            "created_at": datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC),
            "updated_at": datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC),
        }

    def test_workspace_roundtrip_serialization(self, sample_workspace_dict: dict) -> None:
        """Workspace -> JSON -> Workspace preserves all fields."""
        workspace = Workspace.from_db_row(sample_workspace_dict)

        json_str = workspace.model_dump_json()
        restored = Workspace.model_validate_json(json_str)

        assert restored.id == workspace.id
        assert restored.name == workspace.name
        assert restored.slug == workspace.slug
        assert restored.owner_id == workspace.owner_id

    def test_workspace_from_db_row_mapping(self, sample_workspace_dict: dict) -> None:
        """from_db_row() correctly maps all DB columns."""
        workspace = Workspace.from_db_row(sample_workspace_dict)

        assert workspace.id == sample_workspace_dict["id"]
        assert workspace.name == sample_workspace_dict["name"]
        assert workspace.slug == sample_workspace_dict["slug"]
        assert workspace.owner_id == sample_workspace_dict["owner_id"]
        assert workspace.created_at == sample_workspace_dict["created_at"]
        assert workspace.updated_at == sample_workspace_dict["updated_at"]

    def test_workspace_from_db_row_uuid_handling(self) -> None:
        """from_db_row() handles UUID objects correctly."""
        row = {
            "id": UUID("123e4567-e89b-12d3-a456-426614174000"),
            "name": "Test Workspace",
            "slug": "test-workspace",
            "owner_id": "u1",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        workspace = Workspace.from_db_row(row)
        assert workspace.id == "123e4567-e89b-12d3-a456-426614174000"


class TestWorkspaceMemberRoundtrip:
    """Test WorkspaceMember model serialization roundtrips."""

    @pytest.fixture
    def sample_member_dict(self) -> dict:
        """Realistic WorkspaceMember data matching DB schema."""
        return {
            "id": "789e0123-e89b-12d3-a456-426614174000",
            "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "user_test_456",
            "role": "member",
            "invited_by": "user_test_123",
            "joined_at": datetime(2025, 1, 10, 11, 0, 0, tzinfo=UTC),
        }

    def test_workspace_member_roundtrip_serialization(self, sample_member_dict: dict) -> None:
        """WorkspaceMember -> JSON -> WorkspaceMember preserves all fields."""
        member = WorkspaceMember.from_db_row(sample_member_dict)

        json_str = member.model_dump_json()
        restored = WorkspaceMember.model_validate_json(json_str)

        assert restored.id == member.id
        assert restored.workspace_id == member.workspace_id
        assert restored.user_id == member.user_id
        assert restored.role == member.role
        assert restored.invited_by == member.invited_by

    def test_workspace_member_from_db_row_mapping(self, sample_member_dict: dict) -> None:
        """from_db_row() correctly maps all DB columns."""
        member = WorkspaceMember.from_db_row(sample_member_dict)

        assert member.id == sample_member_dict["id"]
        assert member.workspace_id == sample_member_dict["workspace_id"]
        assert member.user_id == sample_member_dict["user_id"]
        assert member.role == WorkspaceRole.MEMBER
        assert member.invited_by == sample_member_dict["invited_by"]
        assert member.joined_at == sample_member_dict["joined_at"]

    def test_workspace_member_from_db_row_with_enum_role(self) -> None:
        """from_db_row() handles WorkspaceRole enum correctly."""
        row = {
            "id": "789e0123-e89b-12d3-a456-426614174000",
            "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "u1",
            "role": WorkspaceRole.ADMIN,  # Already enum
            "joined_at": datetime.now(UTC),
        }
        member = WorkspaceMember.from_db_row(row)
        assert member.role == WorkspaceRole.ADMIN


class TestWorkspaceRoleEnum:
    """Test WorkspaceRole enum values."""

    def test_workspace_role_enum_values(self) -> None:
        """WorkspaceRole enum has all expected values."""
        assert WorkspaceRole.OWNER.value == "owner"
        assert WorkspaceRole.ADMIN.value == "admin"
        assert WorkspaceRole.MEMBER.value == "member"

    def test_workspace_role_all_roles_mapped(self) -> None:
        """All workspace roles can be instantiated from string."""
        for role_str in ["owner", "admin", "member"]:
            role = WorkspaceRole(role_str)
            assert role.value == role_str

    def test_workspace_member_role_serialization(self) -> None:
        """WorkspaceRole round-trips as string value."""
        for role in WorkspaceRole:
            member = WorkspaceMember(
                id="123e4567-e89b-12d3-a456-426614174000",
                workspace_id="456e7890-e89b-12d3-a456-426614174000",
                user_id="u1",
                role=role,
                joined_at=datetime.now(UTC),
            )

            data = member.model_dump()
            assert data["role"] == role.value

            json_str = member.model_dump_json()
            restored = WorkspaceMember.model_validate_json(json_str)
            assert restored.role == role


class TestWorkspaceMemberOptionalFields:
    """Test optional fields on WorkspaceMember."""

    def test_workspace_member_invited_by_optional(self) -> None:
        """invited_by field is optional (owner has no inviter)."""
        member = WorkspaceMember(
            id="123e4567-e89b-12d3-a456-426614174000",
            workspace_id="456e7890-e89b-12d3-a456-426614174000",
            user_id="u1",
            role=WorkspaceRole.OWNER,
            joined_at=datetime.now(UTC),
            # invited_by is None for owner
        )
        assert member.invited_by is None

    def test_workspace_member_from_db_row_without_invited_by(self) -> None:
        """from_db_row() handles missing invited_by."""
        row = {
            "id": "789e0123-e89b-12d3-a456-426614174000",
            "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "u1",
            "role": "owner",
            "joined_at": datetime.now(UTC),
        }
        member = WorkspaceMember.from_db_row(row)
        assert member.invited_by is None


class TestWorkspaceUUIDHandling:
    """Test UUID handling for workspace models."""

    def test_workspace_member_from_db_row_uuid_handling(self) -> None:
        """from_db_row() handles UUID objects correctly for member."""
        row = {
            "id": UUID("789e0123-e89b-12d3-a456-426614174000"),
            "workspace_id": UUID("123e4567-e89b-12d3-a456-426614174000"),
            "user_id": "u1",
            "role": "member",
            "joined_at": datetime.now(UTC),
        }
        member = WorkspaceMember.from_db_row(row)
        assert member.id == "789e0123-e89b-12d3-a456-426614174000"
        assert member.workspace_id == "123e4567-e89b-12d3-a456-426614174000"

    def test_workspace_string_uuid_passthrough(self) -> None:
        """String UUIDs pass through unchanged."""
        workspace = Workspace(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="Test",
            slug="test",
            owner_id="u1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert workspace.id == "123e4567-e89b-12d3-a456-426614174000"
