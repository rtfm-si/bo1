"""Tests for admin extended KPIs API endpoints.

Tests:
- GET /api/admin/extended-kpis
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.admin.extended_kpis import limiter, router
from backend.api.middleware.admin import require_admin_any


def mock_admin_override():
    """Override admin auth to always succeed."""
    return "admin-user-id"


@pytest.fixture
def app():
    """Create test app with extended_kpis router and admin auth override."""
    # Disable rate limiter for tests (to avoid Redis connection)
    original_enabled = limiter.enabled
    limiter.enabled = False

    test_app = FastAPI()
    test_app.dependency_overrides[require_admin_any] = mock_admin_override
    test_app.include_router(router, prefix="/api/admin")

    yield test_app

    # Restore original limiter state
    limiter.enabled = original_enabled


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def main_app_client():
    """Create test client using main app (for auth tests)."""
    from backend.api.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestExtendedKPIsEndpoint:
    """Tests for GET /api/admin/extended-kpis."""

    def test_returns_403_without_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.get("/api/admin/extended-kpis")
        assert response.status_code == 403

    def test_returns_extended_kpis(self, client: TestClient):
        """Admin users should get extended KPIs."""
        with patch("backend.api.admin.extended_kpis.db_session") as mock_db_session:
            # Set up mock cursor that returns different results for each query
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            # Different results for each query
            mock_cursor.fetchone.side_effect = [
                # Mentor sessions
                {"total_sessions": 100, "today": 5, "week": 25, "month": 80},
                # Data analyses
                {"total_analyses": 50, "today": 3, "week": 15, "month": 40},
                # Projects
                {
                    "total_projects": 30,
                    "active": 15,
                    "paused": 5,
                    "completed": 8,
                    "archived": 2,
                    "deleted": 3,
                },
                # Actions
                {
                    "total_actions": 200,
                    "pending": 50,
                    "in_progress": 30,
                    "completed": 100,
                    "cancelled": 20,
                    "deleted": 5,
                },
                # Meetings
                {
                    "total_meetings": 75,
                    "created": 5,
                    "running": 3,
                    "completed": 60,
                    "failed": 4,
                    "killed": 2,
                    "deleted": 1,
                    "today": 2,
                    "week": 15,
                    "month": 45,
                },
            ]

            response = client.get("/api/admin/extended-kpis")
            assert response.status_code == 200

            data = response.json()

            # Verify mentor sessions
            assert data["mentor_sessions"]["total_sessions"] == 100
            assert data["mentor_sessions"]["sessions_today"] == 5
            assert data["mentor_sessions"]["sessions_this_week"] == 25
            assert data["mentor_sessions"]["sessions_this_month"] == 80

            # Verify data analyses
            assert data["data_analyses"]["total_analyses"] == 50
            assert data["data_analyses"]["analyses_today"] == 3
            assert data["data_analyses"]["analyses_this_week"] == 15
            assert data["data_analyses"]["analyses_this_month"] == 40

            # Verify projects
            assert data["projects"]["total_projects"] == 30
            assert data["projects"]["active"] == 15
            assert data["projects"]["paused"] == 5
            assert data["projects"]["completed"] == 8
            assert data["projects"]["archived"] == 2
            assert data["projects"]["deleted"] == 3

            # Verify actions
            assert data["actions"]["total_actions"] == 200
            assert data["actions"]["pending"] == 50
            assert data["actions"]["in_progress"] == 30
            assert data["actions"]["completed"] == 100
            assert data["actions"]["cancelled"] == 20
            assert data["actions"]["deleted"] == 5

            # Verify meetings
            assert data["meetings"]["total_meetings"] == 75
            assert data["meetings"]["created"] == 5
            assert data["meetings"]["running"] == 3
            assert data["meetings"]["completed"] == 60
            assert data["meetings"]["failed"] == 4
            assert data["meetings"]["killed"] == 2
            assert data["meetings"]["deleted"] == 1
            assert data["meetings"]["meetings_today"] == 2
            assert data["meetings"]["meetings_this_week"] == 15
            assert data["meetings"]["meetings_this_month"] == 45


class TestMentorSessionStatsQuery:
    """Tests for get_mentor_session_stats function."""

    def test_counts_mentor_sessions_correctly(self):
        """Should aggregate mentor chat counts from user_usage table."""
        from backend.api.admin.extended_kpis import get_mentor_session_stats

        with patch("backend.api.admin.extended_kpis.db_session") as mock_db_session:
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            mock_cursor.fetchone.return_value = {
                "total_sessions": 500,
                "today": 10,
                "week": 50,
                "month": 200,
            }

            result = get_mentor_session_stats()

            assert result.total_sessions == 500
            assert result.sessions_today == 10
            assert result.sessions_this_week == 50
            assert result.sessions_this_month == 200


class TestActionStatsQuery:
    """Tests for get_action_stats function."""

    def test_groups_actions_by_status(self):
        """Should count actions by status correctly."""
        from backend.api.admin.extended_kpis import get_action_stats

        with patch("backend.api.admin.extended_kpis.db_session") as mock_db_session:
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            mock_cursor.fetchone.return_value = {
                "total_actions": 150,
                "pending": 40,
                "in_progress": 25,
                "completed": 75,
                "cancelled": 10,
                "deleted": 8,
            }

            result = get_action_stats()

            assert result.total_actions == 150
            assert result.pending == 40
            assert result.in_progress == 25
            assert result.completed == 75
            assert result.cancelled == 10
            assert result.deleted == 8


class TestProjectStatsQuery:
    """Tests for get_project_stats function."""

    def test_groups_projects_by_status(self):
        """Should count projects by status correctly."""
        from backend.api.admin.extended_kpis import get_project_stats

        with patch("backend.api.admin.extended_kpis.db_session") as mock_db_session:
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            mock_cursor.fetchone.return_value = {
                "total_projects": 25,
                "active": 12,
                "paused": 3,
                "completed": 7,
                "archived": 3,
                "deleted": 2,
            }

            result = get_project_stats()

            assert result.total_projects == 25
            assert result.active == 12
            assert result.paused == 3
            assert result.completed == 7
            assert result.archived == 3
            assert result.deleted == 2


class TestMeetingStatsQuery:
    """Tests for get_meeting_stats function."""

    def test_groups_meetings_by_status(self):
        """Should count meetings by status correctly."""
        from backend.api.admin.extended_kpis import get_meeting_stats

        with patch("backend.api.admin.extended_kpis.db_session") as mock_db_session:
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            mock_cursor.fetchone.return_value = {
                "total_meetings": 100,
                "created": 10,
                "running": 5,
                "completed": 70,
                "failed": 8,
                "killed": 4,
                "deleted": 3,
                "today": 5,
                "week": 25,
                "month": 60,
            }

            result = get_meeting_stats()

            assert result.total_meetings == 100
            assert result.created == 10
            assert result.running == 5
            assert result.completed == 70
            assert result.failed == 8
            assert result.killed == 4
            assert result.deleted == 3
            assert result.meetings_today == 5
            assert result.meetings_this_week == 25
            assert result.meetings_this_month == 60


class TestExtendedKPIsRequiresAdmin:
    """Tests for admin authentication on extended KPIs endpoint."""

    def test_requires_admin_api_key(self, main_app_client: TestClient):
        """Should reject requests without admin credentials."""
        response = main_app_client.get("/api/admin/extended-kpis")
        assert response.status_code == 403

    def test_accepts_valid_admin_key(self, client: TestClient):
        """Should accept requests with valid admin API key via test app with override."""
        with patch("backend.api.admin.extended_kpis.db_session") as mock_db_session:
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            # Return empty stats for each query
            mock_cursor.fetchone.side_effect = [
                {"total_sessions": 0, "today": 0, "week": 0, "month": 0},
                {"total_analyses": 0, "today": 0, "week": 0, "month": 0},
                {
                    "total_projects": 0,
                    "active": 0,
                    "paused": 0,
                    "completed": 0,
                    "archived": 0,
                    "deleted": 0,
                },
                {
                    "total_actions": 0,
                    "pending": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "cancelled": 0,
                    "deleted": 0,
                },
                {
                    "total_meetings": 0,
                    "created": 0,
                    "running": 0,
                    "completed": 0,
                    "failed": 0,
                    "killed": 0,
                    "deleted": 0,
                    "today": 0,
                    "week": 0,
                    "month": 0,
                },
            ]

            response = client.get("/api/admin/extended-kpis")
            assert response.status_code == 200
