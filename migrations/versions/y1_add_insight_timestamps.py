"""Add updated_at timestamp tracking to insights/clarifications

Revision ID: y1_add_insight_timestamps
Revises: x1_add_replanning_fields
Create Date: 2025-12-12

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "y1_add_insight_timestamps"
down_revision: str | Sequence[str] | None = "x1_add_replanning_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Transform clarifications JSONB structure to include updated_at timestamps.

    Old format:
    {
        "question 1": "answer 1",
        "question 2": "answer 2"
    }

    New format:
    {
        "question 1": {
            "answer": "answer 1",
            "answered_at": "2025-12-12T12:00:00Z",
            "source": "meeting"
        },
        "question 2": {
            "answer": "answer 2",
            "answered_at": "2025-12-12T12:00:00Z",
            "source": "meeting"
        }
    }
    """
    # Create a SQL function to handle the transformation
    op.execute("""
    CREATE OR REPLACE FUNCTION upgrade_clarifications_timestamps()
    RETURNS void AS $$
    DECLARE
        row RECORD;
        updated_clarifications JSONB;
        question TEXT;
        answer TEXT;
        value JSONB;
    BEGIN
        FOR row IN SELECT id, clarifications AS clarifications_data FROM user_context WHERE clarifications IS NOT NULL AND clarifications != '{}' LOOP
            updated_clarifications := '{}'::jsonb;

            -- Iterate through each key-value pair in clarifications
            FOR question, answer IN SELECT * FROM jsonb_each_text(row.clarifications_data) LOOP
                -- Check if value is already in new format (has 'answer' key)
                value := row.clarifications_data -> question;
                IF value ? 'answer' THEN
                    -- Already in new format, keep as-is
                    updated_clarifications := updated_clarifications || jsonb_build_object(
                        question,
                        value
                    );
                ELSE
                    -- Old format (string value), upgrade to new format
                    updated_clarifications := updated_clarifications || jsonb_build_object(
                        question,
                        jsonb_build_object(
                            'answer', answer,
                            'answered_at', NOW()::text,
                            'source', 'meeting'
                        )
                    );
                END IF;
            END LOOP;

            -- Update the row with transformed clarifications
            UPDATE user_context SET clarifications = updated_clarifications WHERE id = row.id;
        END LOOP;
    END;
    $$ LANGUAGE plpgsql;

    SELECT upgrade_clarifications_timestamps();
    DROP FUNCTION upgrade_clarifications_timestamps();
    """)


def downgrade() -> None:
    """Transform clarifications back to old string-value format.

    Note: This will lose the timestamp and source metadata.
    """
    op.execute("""
    CREATE OR REPLACE FUNCTION downgrade_clarifications_timestamps()
    RETURNS void AS $$
    DECLARE
        row RECORD;
        downgraded_clarifications JSONB;
        question TEXT;
        value JSONB;
    BEGIN
        FOR row IN SELECT id, clarifications AS clarifications_data FROM user_context WHERE clarifications IS NOT NULL AND clarifications != '{}' LOOP
            downgraded_clarifications := '{}'::jsonb;

            -- Iterate through each key-value pair in clarifications
            FOR question, value IN SELECT * FROM jsonb_each(row.clarifications_data) LOOP
                IF value ? 'answer' THEN
                    -- New format, downgrade to old string format
                    downgraded_clarifications := downgraded_clarifications || jsonb_build_object(
                        question,
                        value ->> 'answer'
                    );
                ELSE
                    -- Already in old format, keep as-is
                    downgraded_clarifications := downgraded_clarifications || jsonb_build_object(
                        question,
                        value::text
                    );
                END IF;
            END LOOP;

            -- Update the row with downgraded clarifications
            UPDATE user_context SET clarifications = downgraded_clarifications WHERE id = row.id;
        END LOOP;
    END;
    $$ LANGUAGE plpgsql;

    SELECT downgrade_clarifications_timestamps();
    DROP FUNCTION downgrade_clarifications_timestamps();
    """)
