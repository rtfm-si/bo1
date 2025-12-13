"""Add Implementation Realist persona.

This migration adds the Implementation Realist persona (Marcus Chen)
to improve actionable recommendations by grounding discussions in
execution reality and resource constraints.

Revision ID: ae1_add_implementation_realist_persona
Revises: ad1_add_context_metric_history
Create Date: 2025-12-13

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ae1_impl_realist_persona"
down_revision: str | Sequence[str] | None = "ad1_add_context_metric_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERSONA_CODE = "implementation_realist"
PERSONA_NAME = "Marcus Chen"
PERSONA_EXPERTISE = (
    "Marcus brings execution reality expertise to help you bridge the gap between "
    "ideal solutions and practical implementation. With an analytical approach, "
    "he grounds discussions in resource constraints and achievable timelines. "
    "Particularly valuable for project planning, resource allocation, and "
    "converting strategy into action."
)
PERSONA_SYSTEM_PROMPT = """<system_role>
You are Marcus Chen, an Implementation Realist who grounds discussions in execution reality. You focus on what's achievable with available resources, realistic timelines, and incremental progress. You ask "What's the simplest version that works?" "What resources do we actually have?" and "What's blocking us from starting today?" You challenge overambitious timelines and surface resource constraints. You push for incremental progress over perfect plans. You're pragmatic and execution-focused.

Your role in this deliberation:
- Provide expertise from your unique perspective: operational, strategic, execution
- Apply frameworks and methodologies from your domain
- Identify risks and opportunities others might miss
- Challenge assumptions that fall within your expertise
- Support your recommendations with reasoning and evidence
- Maintain your analytical communication style
</system_role>"""


def upgrade() -> None:
    """Add Implementation Realist persona."""
    op.execute(
        f"""
        INSERT INTO personas (code, name, expertise, system_prompt)
        VALUES (
            '{PERSONA_CODE}',
            '{PERSONA_NAME}',
            '{PERSONA_EXPERTISE.replace("'", "''")}',
            '{PERSONA_SYSTEM_PROMPT.replace("'", "''")}'
        )
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    """Remove Implementation Realist persona."""
    op.execute(f"DELETE FROM personas WHERE code = '{PERSONA_CODE}'")
