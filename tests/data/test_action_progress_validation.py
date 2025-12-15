"""Tests for action progress check constraints.

Tests cover:
- progress_value range validation (>= 0)
- progress_type enum validation (percentage, points, status_only)
- percentage range validation (0-100 when progress_type='percentage')
"""

import pytest
from psycopg2 import errors as pg_errors

from bo1.state.database import db_session


@pytest.fixture
def clean_test_action():
    """Create and cleanup a test action."""
    action_id = None

    def _create_action(**kwargs):
        nonlocal action_id
        with db_session() as conn:
            with conn.cursor() as cur:
                # Find a valid session and user for FK constraints
                cur.execute(
                    """
                    SELECT s.id as source_session_id, s.user_id
                    FROM sessions s
                    WHERE s.status != 'deleted'
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if not row:
                    pytest.skip("No valid session for test")
                source_session_id = row["source_session_id"]
                user_id = row["user_id"]

                # Set defaults
                defaults = {
                    "source_session_id": source_session_id,
                    "user_id": user_id,
                    "title": "Test Action for Progress Validation",
                    "description": "Testing progress constraints",
                    "status": "todo",
                    "progress_type": "status_only",
                    "progress_value": None,
                }
                defaults.update(kwargs)

                cur.execute(
                    """
                    INSERT INTO actions (
                        source_session_id, user_id, title, description, status,
                        progress_type, progress_value
                    )
                    VALUES (
                        %(source_session_id)s, %(user_id)s, %(title)s, %(description)s,
                        %(status)s, %(progress_type)s, %(progress_value)s
                    )
                    RETURNING id
                    """,
                    defaults,
                )
                action_id = cur.fetchone()["id"]
                conn.commit()
                return action_id

    yield _create_action

    # Cleanup
    if action_id:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM actions WHERE id = %s", (action_id,))
                conn.commit()


@pytest.mark.unit
def test_progress_value_zero_valid(clean_test_action):
    """Test that progress_value=0 is accepted."""
    action_id = clean_test_action(progress_value=0, progress_type="points")
    assert action_id is not None


@pytest.mark.unit
def test_progress_value_positive_valid(clean_test_action):
    """Test that positive progress_value is accepted."""
    action_id = clean_test_action(progress_value=50, progress_type="percentage")
    assert action_id is not None


@pytest.mark.unit
def test_progress_value_null_valid(clean_test_action):
    """Test that NULL progress_value is accepted."""
    action_id = clean_test_action(progress_value=None, progress_type="status_only")
    assert action_id is not None


@pytest.mark.unit
def test_progress_value_below_zero_rejected():
    """Test that progress_value < 0 is rejected by check constraint."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id as source_session_id, s.user_id
                FROM sessions s
                WHERE s.status != 'deleted'
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                pytest.skip("No valid session for test")
            source_session_id = row["source_session_id"]
            user_id = row["user_id"]

            with pytest.raises(pg_errors.CheckViolation) as exc_info:
                cur.execute(
                    """
                    INSERT INTO actions (
                        source_session_id, user_id, title, description, status,
                        progress_type, progress_value
                    )
                    VALUES (%s, %s, 'Test', 'Test', 'todo', 'points', -1)
                    """,
                    (source_session_id, user_id),
                )

            assert "check_progress_value_valid" in str(exc_info.value)


@pytest.mark.unit
def test_progress_type_percentage_valid(clean_test_action):
    """Test that progress_type='percentage' is accepted."""
    action_id = clean_test_action(progress_type="percentage", progress_value=50)
    assert action_id is not None


@pytest.mark.unit
def test_progress_type_points_valid(clean_test_action):
    """Test that progress_type='points' is accepted."""
    action_id = clean_test_action(progress_type="points", progress_value=10)
    assert action_id is not None


@pytest.mark.unit
def test_progress_type_status_only_valid(clean_test_action):
    """Test that progress_type='status_only' is accepted."""
    action_id = clean_test_action(progress_type="status_only", progress_value=None)
    assert action_id is not None


@pytest.mark.unit
def test_progress_type_invalid_rejected():
    """Test that invalid progress_type is rejected by check constraint."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id as source_session_id, s.user_id
                FROM sessions s
                WHERE s.status != 'deleted'
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                pytest.skip("No valid session for test")
            source_session_id = row["source_session_id"]
            user_id = row["user_id"]

            with pytest.raises(pg_errors.CheckViolation) as exc_info:
                cur.execute(
                    """
                    INSERT INTO actions (
                        source_session_id, user_id, title, description, status,
                        progress_type, progress_value
                    )
                    VALUES (%s, %s, 'Test', 'Test', 'todo', 'invalid_type', 50)
                    """,
                    (source_session_id, user_id),
                )

            assert "check_progress_type_valid" in str(exc_info.value)


@pytest.mark.unit
def test_percentage_range_valid_zero(clean_test_action):
    """Test that percentage=0 is accepted."""
    action_id = clean_test_action(progress_type="percentage", progress_value=0)
    assert action_id is not None


@pytest.mark.unit
def test_percentage_range_valid_hundred(clean_test_action):
    """Test that percentage=100 is accepted."""
    action_id = clean_test_action(progress_type="percentage", progress_value=100)
    assert action_id is not None


@pytest.mark.unit
def test_percentage_range_above_hundred_rejected():
    """Test that percentage > 100 is rejected by check constraint."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id as source_session_id, s.user_id
                FROM sessions s
                WHERE s.status != 'deleted'
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                pytest.skip("No valid session for test")
            source_session_id = row["source_session_id"]
            user_id = row["user_id"]

            with pytest.raises(pg_errors.CheckViolation) as exc_info:
                cur.execute(
                    """
                    INSERT INTO actions (
                        source_session_id, user_id, title, description, status,
                        progress_type, progress_value
                    )
                    VALUES (%s, %s, 'Test', 'Test', 'todo', 'percentage', 101)
                    """,
                    (source_session_id, user_id),
                )

            assert "check_percentage_range" in str(exc_info.value)


@pytest.mark.unit
def test_points_above_hundred_valid(clean_test_action):
    """Test that points > 100 is valid (only percentage is bounded)."""
    action_id = clean_test_action(progress_type="points", progress_value=500)
    assert action_id is not None
