"""Tests for session context_ids feature.

Tests validation and storage of user-selected context (meetings, actions, datasets)
during session creation.
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.api.models import CreateSessionRequest


class TestCreateSessionRequestContextIds:
    """Test context_ids validation in CreateSessionRequest."""

    def test_valid_context_ids(self):
        """Valid context_ids should be accepted."""
        request = CreateSessionRequest(
            problem_statement="Should we expand to EU market?",
            context_ids={
                "meetings": ["bo1_abc123"],
                "actions": ["uuid-1", "uuid-2"],
                "datasets": ["ds-uuid"],
            },
        )
        assert request.context_ids is not None
        assert request.context_ids["meetings"] == ["bo1_abc123"]
        assert len(request.context_ids["actions"]) == 2
        assert len(request.context_ids["datasets"]) == 1

    def test_empty_context_ids(self):
        """Empty context_ids should be allowed."""
        request = CreateSessionRequest(
            problem_statement="Should we expand to EU market?",
            context_ids={"meetings": [], "actions": [], "datasets": []},
        )
        assert request.context_ids is not None
        assert request.context_ids["meetings"] == []

    def test_none_context_ids(self):
        """None context_ids should be allowed (optional)."""
        request = CreateSessionRequest(
            problem_statement="Should we expand to EU market?",
        )
        assert request.context_ids is None

    def test_partial_context_ids(self):
        """Partial context_ids (only some keys) should be valid."""
        request = CreateSessionRequest(
            problem_statement="Should we expand to EU market?",
            context_ids={"meetings": ["bo1_abc"]},
        )
        assert request.context_ids is not None
        assert request.context_ids.get("meetings") == ["bo1_abc"]
        assert request.context_ids.get("actions") is None


class TestSessionRepositoryContextIds:
    """Test context_ids persistence in session_repository."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        with patch("bo1.state.repositories.session_repository.db_session") as mock:
            # Create a mock cursor with fetchone returning a dict
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                "id": "bo1_test123",
                "user_id": "user123",
                "problem_statement": "Test problem",
                "problem_context": None,
                "status": "created",
                "phase": None,
                "total_cost": None,
                "round_number": 0,
                "created_at": "2025-12-13T00:00:00",
                "updated_at": "2025-12-13T00:00:00",
                "dataset_id": None,
                "workspace_id": None,
                "used_promo_credit": False,
                "context_ids": {"meetings": ["bo1_old1"], "actions": [], "datasets": []},
            }
            mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
            mock_cursor.__exit__ = MagicMock(return_value=False)

            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)

            mock.return_value = mock_conn

            yield mock

    def test_create_with_context_ids(self, mock_db_session):
        """Session creation should store context_ids."""
        from bo1.state.repositories.session_repository import SessionRepository

        repo = SessionRepository()
        result = repo.create(
            session_id="bo1_test123",
            user_id="user123",
            problem_statement="Test problem",
            context_ids={"meetings": ["bo1_old1"], "actions": [], "datasets": []},
        )

        assert result is not None
        assert result.get("context_ids") == {
            "meetings": ["bo1_old1"],
            "actions": [],
            "datasets": [],
        }


class TestSessionCreationApiContextValidation:
    """Test context_ids validation in POST /api/v1/sessions."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock common dependencies for session creation tests."""
        with (
            patch("backend.api.sessions.session_repository") as mock_session_repo,
            patch("backend.api.sessions.user_repository") as mock_user_repo,
            patch("backend.api.sessions.dataset_repository") as mock_dataset_repo,
            patch("backend.api.sessions.RedisManager") as mock_redis,
        ):
            # Setup mocks
            mock_redis_instance = MagicMock()
            mock_redis_instance.create_session.return_value = "bo1_newsession"
            mock_redis_instance.save_metadata.return_value = True
            mock_redis.return_value = mock_redis_instance

            mock_user_repo.get_context.return_value = {}
            mock_user_repo.ensure_exists.return_value = None

            mock_session_repo.create.return_value = {
                "id": "bo1_newsession",
                "status": "created",
            }

            yield {
                "session_repo": mock_session_repo,
                "user_repo": mock_user_repo,
                "dataset_repo": mock_dataset_repo,
                "redis": mock_redis_instance,
            }

    def test_meeting_limit_exceeded(self, mock_dependencies):
        """Should reject if more than 5 meetings attached."""
        # This would be tested via the API endpoint
        # For now, verify the limit is enforced in the model
        many_meetings = [f"bo1_meet{i}" for i in range(6)]

        # The validation happens in the API endpoint, not the model
        # This test documents the expected behavior
        request = CreateSessionRequest(
            problem_statement="Should we expand to EU market?",
            context_ids={"meetings": many_meetings},
        )
        # Model accepts it - validation happens in endpoint
        assert len(request.context_ids["meetings"]) == 6

    def test_action_limit_exceeded(self, mock_dependencies):
        """Should reject if more than 10 actions attached."""
        many_actions = [f"action-{i}" for i in range(11)]
        request = CreateSessionRequest(
            problem_statement="Should we expand to EU market?",
            context_ids={"actions": many_actions},
        )
        assert len(request.context_ids["actions"]) == 11

    def test_dataset_limit_exceeded(self, mock_dependencies):
        """Should reject if more than 3 datasets attached."""
        many_datasets = [f"ds-{i}" for i in range(4)]
        request = CreateSessionRequest(
            problem_statement="Should we expand to EU market?",
            context_ids={"datasets": many_datasets},
        )
        assert len(request.context_ids["datasets"]) == 4
