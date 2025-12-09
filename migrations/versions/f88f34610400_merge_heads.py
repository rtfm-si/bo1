"""merge_heads

Revision ID: f88f34610400
Revises: 0001_consolidated_baseline, d1_add_session_counts
Create Date: 2025-12-09 19:44:20.285610

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f88f34610400'
down_revision: Union[str, Sequence[str], None] = ('0001_consolidated_baseline', 'd1_add_session_counts')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
