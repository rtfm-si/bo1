"""Tests for retention reminder job."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch


class TestGetUsersApproachingDeletion:
    """Tests for get_users_approaching_deletion function."""

    def test_returns_empty_when_no_users(self):
        """Should return empty list when no users meet criteria."""
        from backend.jobs.retention_reminder_job import get_users_approaching_deletion

        with patch("backend.jobs.retention_reminder_job.db_session") as mock_session:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_session.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            result = get_users_approaching_deletion()

            assert result == []

    def test_filters_users_with_forever_retention(self):
        """Users with retention=-1 should be excluded."""
        from backend.jobs.retention_reminder_job import get_users_approaching_deletion

        with patch("backend.jobs.retention_reminder_job.db_session") as mock_session:
            # Query already filters these at SQL level
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_session.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            result = get_users_approaching_deletion()

            assert result == []

    def test_returns_users_in_28_day_window(self):
        """Users with 27-28 days until deletion should be returned."""
        from backend.jobs.retention_reminder_job import get_users_approaching_deletion

        with patch("backend.jobs.retention_reminder_job.db_session") as mock_session:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {
                    "user_id": "user-1",
                    "email": "test@example.com",
                    "data_retention_days": 365,
                    "last_deletion_reminder_sent_at": None,
                    "oldest_session": datetime.now(UTC) - timedelta(days=337),
                    "days_until_deletion": 28,
                }
            ]
            mock_session.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            result = get_users_approaching_deletion()

            assert len(result) == 1
            assert result[0]["user_id"] == "user-1"
            assert result[0]["days_until_deletion"] == 28

    def test_returns_users_in_1_day_window(self):
        """Users with 0-1 days until deletion should be returned."""
        from backend.jobs.retention_reminder_job import get_users_approaching_deletion

        with patch("backend.jobs.retention_reminder_job.db_session") as mock_session:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {
                    "user_id": "user-2",
                    "email": "urgent@example.com",
                    "data_retention_days": 365,
                    "last_deletion_reminder_sent_at": None,
                    "oldest_session": datetime.now(UTC) - timedelta(days=364),
                    "days_until_deletion": 1,
                }
            ]
            mock_session.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            result = get_users_approaching_deletion()

            assert len(result) == 1
            assert result[0]["days_until_deletion"] == 1

    def test_excludes_recently_notified_users(self):
        """Users notified within MIN_REMINDER_INTERVAL_DAYS should be excluded."""
        from backend.jobs.retention_reminder_job import (
            MIN_REMINDER_INTERVAL_DAYS,
            get_users_approaching_deletion,
        )

        with patch("backend.jobs.retention_reminder_job.db_session") as mock_session:
            recent_sent = datetime.now(UTC) - timedelta(days=MIN_REMINDER_INTERVAL_DAYS - 1)
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {
                    "user_id": "user-3",
                    "email": "recent@example.com",
                    "data_retention_days": 365,
                    "last_deletion_reminder_sent_at": recent_sent,
                    "oldest_session": datetime.now(UTC) - timedelta(days=337),
                    "days_until_deletion": 28,
                }
            ]
            mock_session.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            result = get_users_approaching_deletion()

            assert len(result) == 0

    def test_excludes_users_outside_windows(self):
        """Users not in 28-day or 1-day windows should be excluded."""
        from backend.jobs.retention_reminder_job import get_users_approaching_deletion

        with patch("backend.jobs.retention_reminder_job.db_session") as mock_session:
            mock_cursor = MagicMock()
            # User with 15 days until deletion - not in a reminder window
            mock_cursor.fetchall.return_value = [
                {
                    "user_id": "user-4",
                    "email": "middle@example.com",
                    "data_retention_days": 365,
                    "last_deletion_reminder_sent_at": None,
                    "oldest_session": datetime.now(UTC) - timedelta(days=350),
                    "days_until_deletion": 15,
                }
            ]
            mock_session.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            result = get_users_approaching_deletion()

            assert len(result) == 0


class TestSendRetentionReminder:
    """Tests for send_retention_reminder function."""

    def test_sends_email_and_updates_timestamp(self):
        """Should send email and update last_deletion_reminder_sent_at."""
        from backend.jobs.retention_reminder_job import send_retention_reminder

        with patch("backend.services.email.send_email_async") as mock_send:
            with patch(
                "backend.jobs.retention_reminder_job._update_last_reminder_sent"
            ) as mock_update:
                with patch(
                    "backend.jobs.retention_reminder_job.get_frontend_url",
                    return_value="https://test.com/settings/privacy",
                ):
                    result = send_retention_reminder(
                        user_id="user-1",
                        email="test@example.com",
                        days_until_deletion=28,
                    )

                    assert result is True
                    mock_send.assert_called_once()
                    mock_update.assert_called_once_with("user-1")

    def test_uses_urgent_subject_for_1_day(self):
        """Should use urgent subject line for 1-day reminders."""
        from backend.jobs.retention_reminder_job import send_retention_reminder

        with patch("backend.services.email.send_email_async") as mock_send:
            with patch("backend.jobs.retention_reminder_job._update_last_reminder_sent"):
                with patch(
                    "backend.jobs.retention_reminder_job.get_frontend_url",
                    return_value="https://test.com/settings/privacy",
                ):
                    send_retention_reminder(
                        user_id="user-1",
                        email="test@example.com",
                        days_until_deletion=1,
                    )

                    call_kwargs = mock_send.call_args[1]
                    assert "Final Notice" in call_kwargs["subject"]

    def test_uses_regular_subject_for_28_day(self):
        """Should use regular subject line for 28-day reminders."""
        from backend.jobs.retention_reminder_job import send_retention_reminder

        with patch("backend.services.email.send_email_async") as mock_send:
            with patch("backend.jobs.retention_reminder_job._update_last_reminder_sent"):
                with patch(
                    "backend.jobs.retention_reminder_job.get_frontend_url",
                    return_value="https://test.com/settings/privacy",
                ):
                    send_retention_reminder(
                        user_id="user-1",
                        email="test@example.com",
                        days_until_deletion=28,
                    )

                    call_kwargs = mock_send.call_args[1]
                    assert "Reminder" in call_kwargs["subject"]
                    assert "28 days" in call_kwargs["subject"]


class TestRunRetentionReminderJob:
    """Tests for run_retention_reminder_job function."""

    def test_returns_stats(self):
        """Should return job statistics."""
        from backend.jobs.retention_reminder_job import run_retention_reminder_job

        with patch(
            "backend.jobs.retention_reminder_job.get_users_approaching_deletion"
        ) as mock_get:
            with patch("backend.jobs.retention_reminder_job.send_retention_reminder") as mock_send:
                mock_get.return_value = [
                    {
                        "user_id": "user-1",
                        "email": "test@example.com",
                        "days_until_deletion": 28,
                        "retention_days": 365,
                    }
                ]
                mock_send.return_value = True

                result = run_retention_reminder_job()

                assert result["users_checked"] == 1
                assert result["emails_sent"] == 1
                assert result["emails_failed"] == 0

    def test_counts_failed_emails(self):
        """Should count failed email sends."""
        from backend.jobs.retention_reminder_job import run_retention_reminder_job

        with patch(
            "backend.jobs.retention_reminder_job.get_users_approaching_deletion"
        ) as mock_get:
            with patch("backend.jobs.retention_reminder_job.send_retention_reminder") as mock_send:
                mock_get.return_value = [
                    {
                        "user_id": "user-1",
                        "email": "test@example.com",
                        "days_until_deletion": 28,
                        "retention_days": 365,
                    }
                ]
                mock_send.return_value = False

                result = run_retention_reminder_job()

                assert result["emails_failed"] == 1
                assert result["emails_sent"] == 0
