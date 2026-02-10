"""Add parent_action_id and is_strategic to actions table.

Revision ID: zzzi_add_action_hierarchy
Revises: zzzh_decision_outcomes
Create Date: 2026-02-10

Enables hierarchical actions: meta-synthesis strategic actions as parents,
sub-problem tasks as children.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "zzzi_add_action_hierarchy"
down_revision: str = "zzzh_decision_outcomes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add parent_action_id FK and is_strategic flag."""
    op.add_column(
        "actions",
        sa.Column(
            "parent_action_id",
            UUID(as_uuid=True),
            sa.ForeignKey("actions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "actions",
        sa.Column(
            "is_strategic",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "idx_actions_parent_action_id",
        "actions",
        ["parent_action_id"],
        postgresql_where=sa.text("parent_action_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove hierarchy columns."""
    op.drop_index("idx_actions_parent_action_id", table_name="actions")
    op.drop_column("actions", "is_strategic")
    op.drop_column("actions", "parent_action_id")
