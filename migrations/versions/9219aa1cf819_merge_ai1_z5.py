"""merge_ai1_z5

Revision ID: 9219aa1cf819
Revises: ai1_add_dynamic_persona_flag, z5_add_kanban_columns
Create Date: 2025-12-16 22:16:18.315572

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "9219aa1cf819"
down_revision: str | Sequence[str] | None = (
    "ai1_add_dynamic_persona_flag",
    "z5_add_kanban_columns",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
