"""Tests for enum CHECK constraints (z18 migration).

Verifies that CHECK constraints exist and enforce valid enum values.
"""

from bo1.state.database import db_session


class TestEnumConstraints:
    """Tests for CHECK constraints on enum columns."""

    def test_sessions_status_constraint_exists(self) -> None:
        """Verify sessions_status_check constraint exists."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM pg_constraint
                WHERE conname = 'sessions_status_check'
                AND conrelid = 'sessions'::regclass
            """)
            assert cursor.fetchone() is not None

    def test_sessions_phase_constraint_exists(self) -> None:
        """Verify sessions_phase_check constraint exists."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM pg_constraint
                WHERE conname = 'sessions_phase_check'
                AND conrelid = 'sessions'::regclass
            """)
            assert cursor.fetchone() is not None

    def test_actions_status_constraint_exists(self) -> None:
        """Verify actions_status_check constraint exists."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM pg_constraint
                WHERE conname = 'actions_status_check'
                AND conrelid = 'actions'::regclass
            """)
            assert cursor.fetchone() is not None

    def test_actions_priority_constraint_exists(self) -> None:
        """Verify actions_priority_check constraint exists."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM pg_constraint
                WHERE conname = 'actions_priority_check'
                AND conrelid = 'actions'::regclass
            """)
            assert cursor.fetchone() is not None

    def test_projects_status_constraint_exists(self) -> None:
        """Verify projects_status_check constraint exists."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM pg_constraint
                WHERE conname = 'projects_status_check'
                AND conrelid = 'projects'::regclass
            """)
            assert cursor.fetchone() is not None

    def test_contributions_status_constraint_exists(self) -> None:
        """Verify contributions_status_check constraint exists."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM pg_constraint
                WHERE conname = 'contributions_status_check'
                AND conrelid = 'contributions'::regclass
            """)
            assert cursor.fetchone() is not None


class TestEnumConstraintDefinitions:
    """Tests that CHECK constraint definitions contain expected values."""

    def test_sessions_status_constraint_values(self) -> None:
        """Verify sessions_status_check includes all expected values."""
        expected_values = {
            "created",
            "running",
            "completed",
            "failed",
            "killed",
            "deleted",
            "paused",
        }
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pg_get_constraintdef(oid) AS definition
                FROM pg_constraint
                WHERE conname = 'sessions_status_check'
                AND conrelid = 'sessions'::regclass
            """)
            row = cursor.fetchone()
            assert row is not None
            definition = row["definition"]
            for value in expected_values:
                assert f"'{value}'" in definition, f"Missing value: {value}"

    def test_sessions_phase_constraint_values(self) -> None:
        """Verify sessions_phase_check includes all expected values."""
        expected_values = {
            "intake",
            "decomposition",
            "selection",
            "initial_round",
            "discussion",
            "voting",
            "synthesis",
            "complete",
            "problem_decomposition",
            "context_collection",
            "convergence",
            "exploration",
            "identify_gaps",
            "clarification_needed",
        }
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pg_get_constraintdef(oid) AS definition
                FROM pg_constraint
                WHERE conname = 'sessions_phase_check'
                AND conrelid = 'sessions'::regclass
            """)
            row = cursor.fetchone()
            assert row is not None
            definition = row["definition"]
            for value in expected_values:
                assert f"'{value}'" in definition, f"Missing value: {value}"

    def test_actions_status_constraint_values(self) -> None:
        """Verify actions_status_check includes all expected values."""
        expected_values = {"todo", "in_progress", "blocked", "in_review", "done", "cancelled"}
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pg_get_constraintdef(oid) AS definition
                FROM pg_constraint
                WHERE conname = 'actions_status_check'
                AND conrelid = 'actions'::regclass
            """)
            row = cursor.fetchone()
            assert row is not None
            definition = row["definition"]
            for value in expected_values:
                assert f"'{value}'" in definition, f"Missing value: {value}"

    def test_actions_priority_constraint_values(self) -> None:
        """Verify actions_priority_check includes all expected values including legacy 'critical'."""
        expected_values = {"high", "medium", "low", "critical"}
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pg_get_constraintdef(oid) AS definition
                FROM pg_constraint
                WHERE conname = 'actions_priority_check'
                AND conrelid = 'actions'::regclass
            """)
            row = cursor.fetchone()
            assert row is not None
            definition = row["definition"]
            for value in expected_values:
                assert f"'{value}'" in definition, f"Missing value: {value}"

    def test_projects_status_constraint_values(self) -> None:
        """Verify projects_status_check includes all expected values."""
        expected_values = {"active", "paused", "completed", "archived"}
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pg_get_constraintdef(oid) AS definition
                FROM pg_constraint
                WHERE conname = 'projects_status_check'
                AND conrelid = 'projects'::regclass
            """)
            row = cursor.fetchone()
            assert row is not None
            definition = row["definition"]
            for value in expected_values:
                assert f"'{value}'" in definition, f"Missing value: {value}"

    def test_contributions_status_constraint_values(self) -> None:
        """Verify contributions_status_check includes all expected values."""
        expected_values = {"in_flight", "committed", "rolled_back"}
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pg_get_constraintdef(oid) AS definition
                FROM pg_constraint
                WHERE conname = 'contributions_status_check'
                AND conrelid = 'contributions'::regclass
            """)
            row = cursor.fetchone()
            assert row is not None
            definition = row["definition"]
            for value in expected_values:
                assert f"'{value}'" in definition, f"Missing value: {value}"

    def test_contributions_constraint_propagated_to_partitions(self) -> None:
        """Verify CHECK constraint is propagated to contributions partition tables."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM pg_constraint
                WHERE conname = 'contributions_status_check'
                AND conrelid::regclass::text LIKE 'contributions_202%'
            """)
            row = cursor.fetchone()
            assert row is not None
            # Should have multiple partitions with the constraint
            assert row["count"] >= 1, "Constraint not propagated to partitions"
