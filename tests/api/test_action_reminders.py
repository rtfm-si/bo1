"""Tests for action reminder functionality."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from backend.services.action_reminders import (
    DEFAULT_REMINDER_FREQUENCY_DAYS,
    calculate_deadline_reminder,
    calculate_start_reminder,
    get_pending_reminders,
    get_reminder_settings,
    get_user_default_frequency,
    set_user_default_frequency,
    should_send_reminder,
    snooze_reminder,
    update_reminder_settings,
)
from bo1.state.database import db_session


@pytest.fixture
def test_user_id(request):
    """Create a test user and return their ID."""
    user_id = str(uuid.uuid4())

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, auth_provider, subscription_tier, created_at, updated_at)
                VALUES (%s, %s, 'test', 'free', NOW(), NOW())
                RETURNING id
                """,
                (user_id, f"test-{user_id[:8]}@example.com"),
            )

    def cleanup():
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM actions WHERE user_id = %s", (user_id,))
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))

    request.addfinalizer(cleanup)
    return user_id


@pytest.fixture
def test_action_id(test_user_id, request):
    """Create a test action and return its ID."""
    action_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    with db_session() as conn:
        with conn.cursor() as cur:
            # Create a session first
            cur.execute(
                """
                INSERT INTO sessions (id, user_id, problem_statement, status, created_at, updated_at)
                VALUES (%s, %s, 'Test problem', 'completed', NOW(), NOW())
                """,
                (session_id, test_user_id),
            )

            # Create an action with reminder-related fields
            cur.execute(
                """
                INSERT INTO actions (
                    id, user_id, source_session_id, title, description, status,
                    priority, category, confidence, sort_order,
                    target_start_date, target_end_date,
                    reminders_enabled, reminder_frequency_days,
                    created_at, updated_at
                )
                VALUES (
                    %s, %s, %s, 'Test Action', 'Test description', 'todo',
                    'medium', 'implementation', 0.8, 0,
                    %s, %s,
                    true, 3,
                    NOW(), NOW()
                )
                RETURNING id
                """,
                (
                    action_id,
                    test_user_id,
                    session_id,
                    (datetime.utcnow() - timedelta(days=2)).date(),  # Start date 2 days ago
                    (datetime.utcnow() + timedelta(days=2)).date(),  # End date 2 days from now
                ),
            )

    def cleanup():
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM actions WHERE id = %s", (action_id,))
                cur.execute("DELETE FROM sessions WHERE id = %s", (session_id,))

    request.addfinalizer(cleanup)
    return action_id


class TestCalculateStartReminder:
    """Tests for calculate_start_reminder function."""

    def test_returns_date_for_overdue_todo_action(self):
        """Should return reminder date when start date passed and action is todo."""
        start_date = datetime.utcnow() - timedelta(days=3)
        action = {
            "status": "todo",
            "reminders_enabled": True,
            "target_start_date": start_date,
        }

        result = calculate_start_reminder(action)

        assert result is not None
        assert result == start_date

    def test_returns_none_for_in_progress_action(self):
        """Should return None when action is already in progress."""
        action = {
            "status": "in_progress",
            "reminders_enabled": True,
            "target_start_date": datetime.utcnow() - timedelta(days=1),
        }

        result = calculate_start_reminder(action)

        assert result is None

    def test_returns_none_when_reminders_disabled(self):
        """Should return None when reminders are disabled."""
        action = {
            "status": "todo",
            "reminders_enabled": False,
            "target_start_date": datetime.utcnow() - timedelta(days=1),
        }

        result = calculate_start_reminder(action)

        assert result is None

    def test_returns_none_for_future_start_date(self):
        """Should return None when start date is in the future."""
        action = {
            "status": "todo",
            "reminders_enabled": True,
            "target_start_date": datetime.utcnow() + timedelta(days=1),
        }

        result = calculate_start_reminder(action)

        assert result is None


class TestCalculateDeadlineReminder:
    """Tests for calculate_deadline_reminder function."""

    def test_returns_date_for_approaching_deadline(self):
        """Should return reminder date when deadline is approaching."""
        deadline = datetime.utcnow() + timedelta(days=2)
        action = {
            "status": "in_progress",
            "reminders_enabled": True,
            "target_end_date": deadline,
            "updated_at": datetime.utcnow() - timedelta(days=3),  # Not recently updated
        }

        result = calculate_deadline_reminder(action, warning_days=3)

        assert result is not None
        assert result == deadline

    def test_returns_none_for_done_action(self):
        """Should return None when action is done."""
        action = {
            "status": "done",
            "reminders_enabled": True,
            "target_end_date": datetime.utcnow() + timedelta(days=1),
        }

        result = calculate_deadline_reminder(action)

        assert result is None

    def test_returns_none_for_distant_deadline(self):
        """Should return None when deadline is far away."""
        action = {
            "status": "in_progress",
            "reminders_enabled": True,
            "target_end_date": datetime.utcnow() + timedelta(days=10),
        }

        result = calculate_deadline_reminder(action, warning_days=3)

        assert result is None

    def test_returns_none_for_recently_updated_action(self):
        """Should return None when action was recently updated."""
        action = {
            "status": "in_progress",
            "reminders_enabled": True,
            "target_end_date": datetime.utcnow() + timedelta(days=2),
            "updated_at": datetime.utcnow() - timedelta(hours=12),  # Updated today
        }

        result = calculate_deadline_reminder(action, warning_days=3)

        assert result is None


class TestShouldSendReminder:
    """Tests for should_send_reminder function."""

    def test_returns_true_for_no_previous_reminder(self):
        """Should return True when no reminder has been sent."""
        action = {
            "reminders_enabled": True,
            "reminder_frequency_days": 3,
            "last_reminder_sent_at": None,
            "snoozed_until": None,
        }

        result = should_send_reminder(action)

        assert result is True

    def test_returns_false_when_recently_sent(self):
        """Should return False when reminder was recently sent."""
        action = {
            "reminders_enabled": True,
            "reminder_frequency_days": 3,
            "last_reminder_sent_at": datetime.utcnow() - timedelta(days=1),
            "snoozed_until": None,
        }

        result = should_send_reminder(action)

        assert result is False

    def test_returns_true_when_frequency_passed(self):
        """Should return True when enough time has passed since last reminder."""
        action = {
            "reminders_enabled": True,
            "reminder_frequency_days": 3,
            "last_reminder_sent_at": datetime.utcnow() - timedelta(days=4),
            "snoozed_until": None,
        }

        result = should_send_reminder(action)

        assert result is True

    def test_returns_false_when_snoozed(self):
        """Should return False when reminder is snoozed."""
        action = {
            "reminders_enabled": True,
            "reminder_frequency_days": 3,
            "last_reminder_sent_at": None,
            "snoozed_until": datetime.utcnow() + timedelta(days=1),
        }

        result = should_send_reminder(action)

        assert result is False


class TestReminderSettingsAPI:
    """Tests for reminder settings API functions."""

    def test_get_reminder_settings(self, test_user_id, test_action_id):
        """Should retrieve reminder settings for an action."""
        settings = get_reminder_settings(test_action_id, test_user_id)

        assert settings is not None
        assert settings.action_id == test_action_id
        assert settings.reminders_enabled is True
        assert settings.reminder_frequency_days == 3

    def test_get_reminder_settings_wrong_user(self, test_user_id, test_action_id):
        """Should return None for wrong user."""
        wrong_user_id = str(uuid.uuid4())

        settings = get_reminder_settings(test_action_id, wrong_user_id)

        assert settings is None

    def test_update_reminder_settings(self, test_user_id, test_action_id):
        """Should update reminder settings."""
        settings = update_reminder_settings(
            action_id=test_action_id,
            user_id=test_user_id,
            reminders_enabled=False,
            reminder_frequency_days=7,
        )

        assert settings is not None
        assert settings.reminders_enabled is False
        assert settings.reminder_frequency_days == 7

    def test_snooze_reminder(self, test_user_id, test_action_id):
        """Should snooze reminder for action."""
        result = snooze_reminder(test_action_id, test_user_id, snooze_days=3)

        assert result is True

        # Verify snooze was applied
        settings = get_reminder_settings(test_action_id, test_user_id)
        assert settings.snoozed_until is not None


class TestUserReminderPreferences:
    """Tests for user reminder preference functions."""

    def test_get_default_frequency(self, test_user_id):
        """Should return default frequency for user."""
        freq = get_user_default_frequency(test_user_id)

        assert freq == DEFAULT_REMINDER_FREQUENCY_DAYS

    def test_set_default_frequency(self, test_user_id):
        """Should set default frequency for user."""
        result = set_user_default_frequency(test_user_id, 7)

        assert result == 7

        # Verify it was set
        freq = get_user_default_frequency(test_user_id)
        assert freq == 7

    def test_set_frequency_clamps_to_valid_range(self, test_user_id):
        """Should clamp frequency to valid range."""
        # Too low
        result = set_user_default_frequency(test_user_id, 0)
        assert result == 1

        # Too high
        result = set_user_default_frequency(test_user_id, 30)
        assert result == 14


class TestGetPendingReminders:
    """Tests for get_pending_reminders function."""

    def test_returns_overdue_start_reminder(self, test_user_id, test_action_id):
        """Should return action with overdue start date."""
        reminders = get_pending_reminders(test_user_id, limit=10)

        # Should find the test action since it has an overdue start date
        action_ids = [r.action_id for r in reminders]
        assert test_action_id in action_ids

    def test_returns_deadline_approaching_reminder(self, test_user_id):
        """Should return action with approaching deadline."""
        # Create an action with approaching deadline
        action_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sessions (id, user_id, problem_statement, status, created_at, updated_at)
                    VALUES (%s, %s, 'Deadline test', 'completed', NOW(), NOW())
                    """,
                    (session_id, test_user_id),
                )

                cur.execute(
                    """
                    INSERT INTO actions (
                        id, user_id, source_session_id, title, description, status,
                        priority, category, confidence, sort_order,
                        target_end_date, reminders_enabled, reminder_frequency_days,
                        updated_at, created_at
                    )
                    VALUES (
                        %s, %s, %s, 'Deadline Test', 'Test', 'in_progress',
                        'high', 'implementation', 0.9, 0,
                        %s, true, 3,
                        NOW() - INTERVAL '5 days', NOW()
                    )
                    """,
                    (
                        action_id,
                        test_user_id,
                        session_id,
                        (datetime.now(UTC) + timedelta(days=1)).date(),  # Due tomorrow
                    ),
                )

        try:
            reminders = get_pending_reminders(test_user_id, limit=10)
            action_ids = [r.action_id for r in reminders]
            assert action_id in action_ids

            # Check reminder type
            reminder = next(r for r in reminders if r.action_id == action_id)
            assert reminder.reminder_type == "deadline_approaching"
        finally:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM actions WHERE id = %s", (action_id,))
                    cur.execute("DELETE FROM sessions WHERE id = %s", (session_id,))

    def test_respects_limit(self, test_user_id):
        """Should respect the limit parameter."""
        reminders = get_pending_reminders(test_user_id, limit=1)

        assert len(reminders) <= 1


# =============================================================================
# HTTP API Endpoint Tests
# =============================================================================


class TestReminderSettingsHTTPEndpoints:
    """Tests for reminder-settings HTTP API endpoints.

    These tests verify that the actual HTTP endpoints work correctly,
    including proper RLS context being set via db_session(user_id=...).
    """

    @pytest.fixture
    def api_client(self, test_user_id):
        """Create test client with auth override for the test user."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from backend.api.actions import router
        from backend.api.middleware.auth import get_current_user

        def mock_user_override():
            return {"user_id": test_user_id, "email": f"test-{test_user_id[:8]}@example.com"}

        app = FastAPI()
        app.dependency_overrides[get_current_user] = mock_user_override
        app.include_router(router, prefix="/api")
        return TestClient(app)

    @pytest.fixture
    def wrong_user_client(self):
        """Create test client with different user (for ownership tests)."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from backend.api.actions import router
        from backend.api.middleware.auth import get_current_user

        wrong_user_id = str(uuid.uuid4())

        def mock_wrong_user_override():
            return {"user_id": wrong_user_id, "email": f"wrong-{wrong_user_id[:8]}@example.com"}

        app = FastAPI()
        app.dependency_overrides[get_current_user] = mock_wrong_user_override
        app.include_router(router, prefix="/api")
        return TestClient(app)

    def test_get_reminder_settings_http(self, api_client, test_action_id):
        """GET /actions/{id}/reminder-settings should return settings."""
        response = api_client.get(f"/api/v1/actions/{test_action_id}/reminder-settings")

        assert response.status_code == 200
        data = response.json()
        assert data["action_id"] == test_action_id
        assert data["reminders_enabled"] is True
        assert data["reminder_frequency_days"] == 3

    def test_get_reminder_settings_http_wrong_user(self, wrong_user_client, test_action_id):
        """GET should return 404 for action owned by different user."""
        response = wrong_user_client.get(f"/api/v1/actions/{test_action_id}/reminder-settings")

        assert response.status_code == 404
        detail = response.json()["detail"]
        # detail can be string or structured dict with "message" key
        msg = detail if isinstance(detail, str) else detail.get("message", "")
        assert "not found" in msg.lower()

    def test_get_reminder_settings_http_nonexistent(self, api_client):
        """GET should return 404 for nonexistent action."""
        fake_id = str(uuid.uuid4())
        response = api_client.get(f"/api/v1/actions/{fake_id}/reminder-settings")

        assert response.status_code == 404

    def test_patch_reminder_settings_http(self, api_client, test_action_id):
        """PATCH /actions/{id}/reminder-settings should update settings."""
        response = api_client.patch(
            f"/api/v1/actions/{test_action_id}/reminder-settings",
            json={"reminders_enabled": False, "reminder_frequency_days": 7},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reminders_enabled"] is False
        assert data["reminder_frequency_days"] == 7

    def test_patch_reminder_settings_http_wrong_user(self, wrong_user_client, test_action_id):
        """PATCH should return 404 for action owned by different user."""
        response = wrong_user_client.patch(
            f"/api/v1/actions/{test_action_id}/reminder-settings",
            json={"reminders_enabled": False},
        )

        assert response.status_code == 404

    def test_patch_reminder_settings_partial(self, api_client, test_action_id):
        """PATCH should allow partial updates (only reminders_enabled)."""
        response = api_client.patch(
            f"/api/v1/actions/{test_action_id}/reminder-settings",
            json={"reminders_enabled": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reminders_enabled"] is False
        # frequency should remain unchanged
        assert data["reminder_frequency_days"] == 3

    def test_patch_reminder_settings_frequency_validation(self, api_client, test_action_id):
        """PATCH should reject invalid frequency values (outside 1-14 range)."""
        # Test too high - should be rejected by Pydantic validation
        response = api_client.patch(
            f"/api/v1/actions/{test_action_id}/reminder-settings",
            json={"reminder_frequency_days": 30},
        )
        assert response.status_code == 422  # Validation error

        # Test too low
        response = api_client.patch(
            f"/api/v1/actions/{test_action_id}/reminder-settings",
            json={"reminder_frequency_days": 0},
        )
        assert response.status_code == 422  # Validation error

        # Test valid value at boundary
        response = api_client.patch(
            f"/api/v1/actions/{test_action_id}/reminder-settings",
            json={"reminder_frequency_days": 14},
        )
        assert response.status_code == 200
        assert response.json()["reminder_frequency_days"] == 14
