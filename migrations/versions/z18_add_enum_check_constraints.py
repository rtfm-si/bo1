"""Add CHECK constraints to enum columns.

Enforces valid enum values at the database level for:
- sessions.status (SessionStatus)
- sessions.phase (DeliberationPhase)
- actions.status (ActionStatus)
- actions.priority (ActionPriority)
- projects.status (ProjectStatus)
- contributions.status (ContributionStatus)

Uses NOT VALID + VALIDATE CONSTRAINT pattern to avoid table locks.

Revision ID: z18_add_enum_check_constraints
Revises: z17_user_context_rls
Create Date: 2025-12-23
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z18_enum_check_constraints"
down_revision: str | Sequence[str] | None = "z17_user_context_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add CHECK constraints to enum columns."""
    # Sessions table constraints
    # status: created, running, completed, failed, killed (from SessionStatus)
    # Also include legacy values: deleted, paused
    op.execute("""
        ALTER TABLE sessions
        ADD CONSTRAINT sessions_status_check
        CHECK (status IN ('created', 'running', 'completed', 'failed', 'killed', 'deleted', 'paused'))
        NOT VALID
    """)
    op.execute("ALTER TABLE sessions VALIDATE CONSTRAINT sessions_status_check")

    # phase: includes current DeliberationPhase values plus legacy values found in DB
    # Current: intake, decomposition, selection, initial_round, discussion, voting, synthesis, complete
    # Legacy: problem_decomposition, context_collection, convergence, exploration, identify_gaps,
    #         clarification_needed, challenge, recommendations
    op.execute("""
        ALTER TABLE sessions
        ADD CONSTRAINT sessions_phase_check
        CHECK (phase IN (
            'intake', 'decomposition', 'selection', 'initial_round',
            'discussion', 'voting', 'synthesis', 'complete',
            'problem_decomposition', 'context_collection', 'convergence',
            'exploration', 'identify_gaps', 'clarification_needed',
            'challenge', 'recommendations'
        ))
        NOT VALID
    """)
    op.execute("ALTER TABLE sessions VALIDATE CONSTRAINT sessions_phase_check")

    # Actions table constraints
    # status: todo, in_progress, blocked, in_review, done, cancelled (from ActionStatus)
    op.execute("""
        ALTER TABLE actions
        ADD CONSTRAINT actions_status_check
        CHECK (status IN ('todo', 'in_progress', 'blocked', 'in_review', 'done', 'cancelled'))
        NOT VALID
    """)
    op.execute("ALTER TABLE actions VALIDATE CONSTRAINT actions_status_check")

    # priority: high, medium, low (from ActionPriority)
    # Also include legacy value: critical
    op.execute("""
        ALTER TABLE actions
        ADD CONSTRAINT actions_priority_check
        CHECK (priority IN ('high', 'medium', 'low', 'critical'))
        NOT VALID
    """)
    op.execute("ALTER TABLE actions VALIDATE CONSTRAINT actions_priority_check")

    # Projects table constraints
    # status: active, paused, completed, archived (from ProjectStatus)
    op.execute("""
        ALTER TABLE projects
        ADD CONSTRAINT projects_status_check
        CHECK (status IN ('active', 'paused', 'completed', 'archived'))
        NOT VALID
    """)
    op.execute("ALTER TABLE projects VALIDATE CONSTRAINT projects_status_check")

    # Contributions table constraints
    # status: in_flight, committed, rolled_back (from ContributionStatus)
    op.execute("""
        ALTER TABLE contributions
        ADD CONSTRAINT contributions_status_check
        CHECK (status IN ('in_flight', 'committed', 'rolled_back'))
        NOT VALID
    """)
    op.execute("ALTER TABLE contributions VALIDATE CONSTRAINT contributions_status_check")


def downgrade() -> None:
    """Remove CHECK constraints from enum columns."""
    op.execute("ALTER TABLE contributions DROP CONSTRAINT IF EXISTS contributions_status_check")
    op.execute("ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_status_check")
    op.execute("ALTER TABLE actions DROP CONSTRAINT IF EXISTS actions_priority_check")
    op.execute("ALTER TABLE actions DROP CONSTRAINT IF EXISTS actions_status_check")
    op.execute("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_phase_check")
    op.execute("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_status_check")
