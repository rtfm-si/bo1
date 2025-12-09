"""merge heads

Revision ID: 26fce129eb71
Revises: 9626a52fd9bf, c1_add_session_events_sequence_index
Create Date: 2025-12-09 13:10:09.518937

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "26fce129eb71"
down_revision: str | Sequence[str] | None = ("9626a52fd9bf", "c1_add_session_events_sequence_index")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
