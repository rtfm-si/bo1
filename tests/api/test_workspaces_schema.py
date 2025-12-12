"""Tests for workspaces and workspace_members schema.

Tests:
- Migration runs and tables are created
- Unique slug constraint
- Member role validation
- Composite unique (workspace_id, user_id)
- Foreign key constraints
"""

import uuid

import pytest
from psycopg2 import IntegrityError
from psycopg2.errors import UniqueViolation

from backend.api.workspaces.models import MemberRole
from bo1.state.database import db_session


class TestWorkspacesSchema:
    """Test workspaces table schema."""

    def test_workspaces_table_exists(self):
        """Verify workspaces table was created by migration."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'workspaces'
                    )
                    """
                )
                assert cur.fetchone()["exists"] is True

    def test_workspace_members_table_exists(self):
        """Verify workspace_members table was created by migration."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'workspace_members'
                    )
                    """
                )
                assert cur.fetchone()["exists"] is True

    def test_workspaces_columns(self):
        """Verify workspaces table has expected columns."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'workspaces'
                    ORDER BY column_name
                    """
                )
                columns = {row["column_name"]: row for row in cur.fetchall()}

                assert "id" in columns
                assert "name" in columns
                assert "slug" in columns
                assert "owner_id" in columns
                assert "created_at" in columns
                assert "updated_at" in columns

    def test_workspace_members_columns(self):
        """Verify workspace_members table has expected columns."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'workspace_members'
                    ORDER BY column_name
                    """
                )
                columns = {row["column_name"]: row for row in cur.fetchall()}

                assert "id" in columns
                assert "workspace_id" in columns
                assert "user_id" in columns
                assert "role" in columns
                assert "invited_by" in columns
                assert "joined_at" in columns


class TestSlugConstraint:
    """Test unique slug constraint on workspaces."""

    def test_unique_slug_enforced(self, test_user_id):
        """Verify duplicate slugs are rejected."""
        workspace_id_1 = str(uuid.uuid4())
        workspace_id_2 = str(uuid.uuid4())
        slug = f"test-workspace-{uuid.uuid4().hex[:8]}"

        with db_session() as conn:
            with conn.cursor() as cur:
                # Insert first workspace
                cur.execute(
                    """
                    INSERT INTO workspaces (id, name, slug, owner_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (workspace_id_1, "Test 1", slug, test_user_id),
                )

                # Attempt duplicate slug
                with pytest.raises(UniqueViolation):
                    cur.execute(
                        """
                        INSERT INTO workspaces (id, name, slug, owner_id)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (workspace_id_2, "Test 2", slug, test_user_id),
                    )


class TestMemberRoleValidation:
    """Test member role values."""

    def test_valid_roles_accepted(self, test_user_id):
        """Verify valid role values are accepted."""
        workspace_id = str(uuid.uuid4())

        with db_session() as conn:
            with conn.cursor() as cur:
                # Create workspace
                cur.execute(
                    """
                    INSERT INTO workspaces (id, name, slug, owner_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (workspace_id, "Test", f"test-{uuid.uuid4().hex[:8]}", test_user_id),
                )

                # Test all valid roles - just insert one with test_user_id
                # (can't create fake users since user_id has FK constraint)
                member_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO workspace_members (id, workspace_id, user_id, role)
                    VALUES (%s, %s, %s, %s)
                    RETURNING role
                    """,
                    (member_id, workspace_id, test_user_id, MemberRole.MEMBER.value),
                )
                result = cur.fetchone()
                assert result["role"] == MemberRole.MEMBER.value

                # Update to test other roles work
                for role in [MemberRole.ADMIN, MemberRole.OWNER]:
                    cur.execute(
                        "UPDATE workspace_members SET role = %s WHERE id = %s RETURNING role",
                        (role.value, member_id),
                    )
                    result = cur.fetchone()
                    assert result["role"] == role.value


class TestCompositeUnique:
    """Test composite unique constraint on workspace_members."""

    def test_duplicate_membership_rejected(self, test_user_id):
        """Verify user can only be in a workspace once."""
        workspace_id = str(uuid.uuid4())
        member_id_1 = str(uuid.uuid4())
        member_id_2 = str(uuid.uuid4())

        with db_session() as conn:
            with conn.cursor() as cur:
                # Create workspace
                cur.execute(
                    """
                    INSERT INTO workspaces (id, name, slug, owner_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (workspace_id, "Test", f"test-{uuid.uuid4().hex[:8]}", test_user_id),
                )

                # Add member
                cur.execute(
                    """
                    INSERT INTO workspace_members (id, workspace_id, user_id, role)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (member_id_1, workspace_id, test_user_id, "member"),
                )

                # Attempt duplicate membership
                with pytest.raises(UniqueViolation):
                    cur.execute(
                        """
                        INSERT INTO workspace_members (id, workspace_id, user_id, role)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (member_id_2, workspace_id, test_user_id, "admin"),
                    )


class TestForeignKeyConstraints:
    """Test foreign key constraints."""

    def test_workspace_owner_fk(self):
        """Verify workspace owner_id references users."""
        workspace_id = str(uuid.uuid4())

        with db_session() as conn:
            with conn.cursor() as cur:
                # Attempt to create workspace with non-existent owner
                with pytest.raises(IntegrityError):
                    cur.execute(
                        """
                        INSERT INTO workspaces (id, name, slug, owner_id)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (workspace_id, "Test", f"test-{uuid.uuid4().hex[:8]}", "nonexistent-user"),
                    )
                    conn.commit()

    def test_member_workspace_fk(self, test_user_id):
        """Verify workspace_members.workspace_id references workspaces."""
        member_id = str(uuid.uuid4())
        fake_workspace_id = str(uuid.uuid4())

        with db_session() as conn:
            with conn.cursor() as cur:
                # Attempt to add member to non-existent workspace
                with pytest.raises(IntegrityError):
                    cur.execute(
                        """
                        INSERT INTO workspace_members (id, workspace_id, user_id, role)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (member_id, fake_workspace_id, test_user_id, "member"),
                    )
                    conn.commit()

    def test_cascade_delete_workspace(self, test_user_id):
        """Verify deleting workspace cascades to members."""
        workspace_id = str(uuid.uuid4())
        member_id = str(uuid.uuid4())

        with db_session() as conn:
            with conn.cursor() as cur:
                # Create workspace and member
                cur.execute(
                    """
                    INSERT INTO workspaces (id, name, slug, owner_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (workspace_id, "Test", f"test-{uuid.uuid4().hex[:8]}", test_user_id),
                )
                cur.execute(
                    """
                    INSERT INTO workspace_members (id, workspace_id, user_id, role)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (member_id, workspace_id, test_user_id, "owner"),
                )

                # Delete workspace
                cur.execute("DELETE FROM workspaces WHERE id = %s", (workspace_id,))

                # Verify member was deleted
                cur.execute(
                    "SELECT COUNT(*) FROM workspace_members WHERE id = %s",
                    (member_id,),
                )
                assert cur.fetchone()["count"] == 0


class TestSessionsWorkspaceFk:
    """Test workspace FK on sessions table."""

    def test_sessions_workspace_id_column_exists(self):
        """Verify sessions.workspace_id column was added."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns
                        WHERE table_name = 'sessions' AND column_name = 'workspace_id'
                    )
                    """
                )
                assert cur.fetchone()["exists"] is True


class TestDatasetsWorkspaceFk:
    """Test workspace FK on datasets table."""

    def test_datasets_workspace_id_column_exists(self):
        """Verify datasets.workspace_id column was added."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns
                        WHERE table_name = 'datasets' AND column_name = 'workspace_id'
                    )
                    """
                )
                assert cur.fetchone()["exists"] is True


class TestIndexes:
    """Test that expected indexes exist."""

    def test_workspace_members_workspace_id_index(self):
        """Verify index on workspace_members.workspace_id."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM pg_indexes
                        WHERE indexname = 'ix_workspace_members_workspace_id'
                    )
                    """
                )
                assert cur.fetchone()["exists"] is True

    def test_workspace_slug_index(self):
        """Verify index on workspaces.slug."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM pg_indexes
                        WHERE indexname = 'ix_workspaces_slug'
                    )
                    """
                )
                assert cur.fetchone()["exists"] is True

    def test_sessions_workspace_id_index(self):
        """Verify index on sessions.workspace_id."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM pg_indexes
                        WHERE indexname = 'ix_sessions_workspace_id'
                    )
                    """
                )
                assert cur.fetchone()["exists"] is True

    def test_datasets_workspace_id_index(self):
        """Verify index on datasets.workspace_id."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM pg_indexes
                        WHERE indexname = 'ix_datasets_workspace_id'
                    )
                    """
                )
                assert cur.fetchone()["exists"] is True
