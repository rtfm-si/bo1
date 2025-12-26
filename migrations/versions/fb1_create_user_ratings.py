"""Create user_ratings table for thumbs up/down feedback on meetings and actions.

Stores user satisfaction ratings for completed meetings and actions.

Revision ID: fb1_create_user_ratings
Revises: tc3_add_policy_type_consent
Create Date: 2025-12-26
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fb1_create_user_ratings"
down_revision: str | Sequence[str] | None = "tc3_add_policy_type_consent"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user_ratings table with indexes and RLS."""
    # Create the table
    op.execute("""
        CREATE TABLE user_ratings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            entity_type TEXT NOT NULL CHECK (entity_type IN ('meeting', 'action')),
            entity_id UUID NOT NULL,
            rating INTEGER NOT NULL CHECK (rating IN (-1, 1)),
            comment TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

            -- One rating per user per entity
            CONSTRAINT unique_user_entity_rating UNIQUE (user_id, entity_type, entity_id)
        )
    """)

    # Add comment
    op.execute("""
        COMMENT ON TABLE user_ratings IS
        'Thumbs up/down ratings for meetings and actions. rating: -1=down, +1=up'
    """)

    # Create indexes
    op.create_index(
        "idx_user_ratings_entity",
        "user_ratings",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "idx_user_ratings_user",
        "user_ratings",
        ["user_id"],
    )
    op.create_index(
        "idx_user_ratings_rating_created",
        "user_ratings",
        ["rating", "created_at"],
    )

    # Enable RLS
    op.execute("ALTER TABLE user_ratings ENABLE ROW LEVEL SECURITY")

    # RLS policy: users can read/write their own ratings
    op.execute("""
        CREATE POLICY user_ratings_user_policy ON user_ratings
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', true))
        WITH CHECK (user_id = current_setting('app.current_user_id', true))
    """)

    # Admin policy: admins can read all ratings
    op.execute("""
        CREATE POLICY user_ratings_admin_read_policy ON user_ratings
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM users
                WHERE id = current_setting('app.current_user_id', true)
                AND is_admin = true
            )
        )
    """)


def downgrade() -> None:
    """Drop user_ratings table."""
    op.execute("DROP POLICY IF EXISTS user_ratings_admin_read_policy ON user_ratings")
    op.execute("DROP POLICY IF EXISTS user_ratings_user_policy ON user_ratings")
    op.drop_index("idx_user_ratings_rating_created", table_name="user_ratings")
    op.drop_index("idx_user_ratings_user", table_name="user_ratings")
    op.drop_index("idx_user_ratings_entity", table_name="user_ratings")
    op.drop_table("user_ratings")
