"""Clean empty/invalid insight responses from clarifications.

Removes null, empty, and invalid insight responses (none, n/a, etc.)
from the clarifications JSONB column in user_context.

Revision ID: e3_clean_empty_insights
Revises: e2_add_metric_volatility
Create Date: 2025-12-15

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3_clean_empty_insights"
down_revision: str | None = "e2_add_metric_volatility"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Invalid response patterns to remove
# These are stored lowercase in the SQL array
INVALID_PATTERNS = [
    "none",
    "n/a",
    "na",
    "no",
    "not applicable",
    "not available",
    "nothing",
    "null",
    "unknown",
    "skip",
    "skipped",
    "-",
    "—",
    "...",
    ".",
]


def upgrade() -> None:
    """Remove empty/invalid insight responses from clarifications.

    This migration:
    1. Iterates through all user_context rows with clarifications
    2. For each clarification entry, checks if the answer is invalid
    3. Removes entries with null/empty/invalid answers
    4. Logs removed entries count for monitoring
    """
    # Build SQL array of invalid patterns
    patterns_sql = ", ".join(f"'{p}'" for p in INVALID_PATTERNS)

    op.execute(f"""
    CREATE OR REPLACE FUNCTION clean_empty_insights()
    RETURNS TABLE(user_id uuid, removed_count int) AS $$
    DECLARE
        row RECORD;
        cleaned_clarifications JSONB;
        question TEXT;
        entry JSONB;
        answer TEXT;
        removed INT;
        invalid_patterns TEXT[] := ARRAY[{patterns_sql}];
    BEGIN
        FOR row IN
            SELECT uc.id, uc.user_id, uc.clarifications
            FROM user_context uc
            WHERE uc.clarifications IS NOT NULL
              AND uc.clarifications != '{{}}'::jsonb
        LOOP
            cleaned_clarifications := '{{}}'::jsonb;
            removed := 0;

            -- Iterate through each clarification entry
            FOR question, entry IN SELECT * FROM jsonb_each(row.clarifications) LOOP
                -- Extract answer from entry (new format has 'answer' key)
                IF jsonb_typeof(entry) = 'object' AND entry ? 'answer' THEN
                    answer := entry ->> 'answer';
                ELSE
                    -- Legacy string format
                    answer := entry::text;
                    -- Remove surrounding quotes from text cast
                    answer := trim(both '"' from answer);
                END IF;

                -- Normalize answer for comparison
                answer := lower(trim(answer));

                -- Check if answer is valid
                IF answer IS NULL OR answer = '' THEN
                    -- Skip null/empty answers
                    removed := removed + 1;
                ELSIF length(answer) < 5 AND answer = ANY(invalid_patterns) THEN
                    -- Skip short invalid patterns
                    removed := removed + 1;
                ELSIF answer = ANY(invalid_patterns) THEN
                    -- Skip exact matches to invalid patterns
                    removed := removed + 1;
                ELSIF rtrim(answer, '.,!?;:') = ANY(invalid_patterns) THEN
                    -- Skip invalid patterns with trailing punctuation
                    removed := removed + 1;
                ELSE
                    -- Keep valid entries
                    cleaned_clarifications := cleaned_clarifications || jsonb_build_object(question, entry);
                END IF;
            END LOOP;

            -- Update row if any entries were removed
            IF removed > 0 THEN
                UPDATE user_context
                SET clarifications = cleaned_clarifications
                WHERE id = row.id;

                user_id := row.user_id;
                removed_count := removed;
                RETURN NEXT;
            END IF;
        END LOOP;
    END;
    $$ LANGUAGE plpgsql;

    -- Execute and log results
    DO $$
    DECLARE
        total_removed INT := 0;
        result RECORD;
    BEGIN
        FOR result IN SELECT * FROM clean_empty_insights() LOOP
            total_removed := total_removed + result.removed_count;
            RAISE NOTICE 'User %: removed % invalid insights', result.user_id, result.removed_count;
        END LOOP;
        RAISE NOTICE 'Total invalid insights removed: %', total_removed;
    END $$;

    DROP FUNCTION clean_empty_insights();
    """)


def downgrade() -> None:
    """No downgrade - removed data cannot be recovered.

    This is a data cleanup migration. The removed entries were invalid
    and should not have been stored in the first place.
    """
    pass
