"""Tests for action escalate-blocker endpoint.

Tests cover:
1. Pydantic model validation for request/response
2. Escalate service function
3. Error handling (not found, not blocked, not authorized)
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError


class TestEscalateBlockerModels:
    """Test Pydantic models for escalate blocker API."""

    def test_escalate_blocker_request_defaults(self):
        """EscalateBlockerRequest should default include_suggestions to True."""
        from backend.api.models import EscalateBlockerRequest

        request = EscalateBlockerRequest()
        assert request.include_suggestions is True

    def test_escalate_blocker_request_override(self):
        """EscalateBlockerRequest should accept include_suggestions override."""
        from backend.api.models import EscalateBlockerRequest

        request = EscalateBlockerRequest(include_suggestions=False)
        assert request.include_suggestions is False

    def test_escalate_blocker_response_validation(self):
        """EscalateBlockerResponse should require session_id and redirect_url."""
        from backend.api.models import EscalateBlockerResponse

        response = EscalateBlockerResponse(
            session_id="bo1_abc123",
            redirect_url="/meetings/bo1_abc123",
        )
        assert response.session_id == "bo1_abc123"
        assert response.redirect_url == "/meetings/bo1_abc123"

    def test_escalate_blocker_response_missing_fields(self):
        """EscalateBlockerResponse should reject missing required fields."""
        from backend.api.models import EscalateBlockerResponse

        with pytest.raises(ValidationError):
            EscalateBlockerResponse(session_id="test")  # Missing redirect_url

        with pytest.raises(ValidationError):
            EscalateBlockerResponse(redirect_url="/test")  # Missing session_id


class TestEscalateBlockedActionService:
    """Tests for escalate_blocked_action service function."""

    @pytest.mark.asyncio
    async def test_escalate_action_not_found(self):
        """Should raise ValueError when action not found."""
        from backend.services.blocker_analyzer import escalate_blocked_action

        with patch("bo1.state.repositories.action_repository.action_repository") as mock_repo:
            mock_repo.get.return_value = None

            with pytest.raises(ValueError, match="Action not found"):
                await escalate_blocked_action(
                    action_id="nonexistent",
                    user_id="user123",
                )

    @pytest.mark.asyncio
    async def test_escalate_not_authorized(self):
        """Should raise ValueError when user doesn't own action."""
        from backend.services.blocker_analyzer import escalate_blocked_action

        with patch("bo1.state.repositories.action_repository.action_repository") as mock_repo:
            mock_repo.get.return_value = {
                "id": "action123",
                "user_id": "other_user",
                "status": "blocked",
            }

            with pytest.raises(ValueError, match="Not authorized"):
                await escalate_blocked_action(
                    action_id="action123",
                    user_id="user123",
                )

    @pytest.mark.asyncio
    async def test_escalate_action_not_blocked(self):
        """Should raise ValueError when action is not blocked."""
        from backend.services.blocker_analyzer import escalate_blocked_action

        with patch("bo1.state.repositories.action_repository.action_repository") as mock_repo:
            mock_repo.get.return_value = {
                "id": "action123",
                "user_id": "user123",
                "status": "in_progress",
            }

            with pytest.raises(ValueError, match="Action is not blocked"):
                await escalate_blocked_action(
                    action_id="action123",
                    user_id="user123",
                )

    @pytest.mark.asyncio
    async def test_escalate_success_without_suggestions(self):
        """Should create session without fetching suggestions."""
        from backend.services.blocker_analyzer import escalate_blocked_action

        mock_redis = MagicMock()
        mock_redis.is_available = True
        mock_redis.create_session.return_value = "bo1_newmeet"

        mock_session_repo = MagicMock()
        mock_session_repo.create.return_value = {
            "id": "bo1_newmeet",
            "status": "created",
        }

        with (
            patch("bo1.state.repositories.action_repository.action_repository") as mock_action_repo,
            patch(
                "backend.api.dependencies.get_redis_manager",
                return_value=mock_redis,
            ),
            patch(
                "bo1.state.repositories.session_repository.SessionRepository",
                return_value=mock_session_repo,
            ),
            patch("bo1.state.repositories.project_repository.ProjectRepository"),
        ):
            mock_action_repo.get.return_value = {
                "id": "action123",
                "user_id": "user123",
                "status": "blocked",
                "title": "Test blocked action",
                "description": "Test description",
                "blocking_reason": "Waiting on external review",
                "blocked_at": None,
                "project_id": None,
            }

            result = await escalate_blocked_action(
                action_id="action123",
                user_id="user123",
                include_suggestions=False,
            )

            assert result["session_id"] == "bo1_newmeet"
            assert result["redirect_url"] == "/meetings/bo1_newmeet"

            # Verify session was created with correct problem statement
            call_kwargs = mock_session_repo.create.call_args[1]
            assert "How can we unblock: Test blocked action?" in call_kwargs["problem_statement"]

    @pytest.mark.asyncio
    async def test_escalate_truncates_long_title(self):
        """Should truncate action title to 200 chars in problem statement."""
        from backend.services.blocker_analyzer import escalate_blocked_action

        mock_redis = MagicMock()
        mock_redis.is_available = True
        mock_redis.create_session.return_value = "bo1_newmeet"

        mock_session_repo = MagicMock()
        mock_session_repo.create.return_value = {
            "id": "bo1_newmeet",
            "status": "created",
        }

        long_title = "A" * 300  # Title longer than 200 chars

        with (
            patch("bo1.state.repositories.action_repository.action_repository") as mock_action_repo,
            patch(
                "backend.api.dependencies.get_redis_manager",
                return_value=mock_redis,
            ),
            patch(
                "bo1.state.repositories.session_repository.SessionRepository",
                return_value=mock_session_repo,
            ),
            patch("bo1.state.repositories.project_repository.ProjectRepository"),
        ):
            mock_action_repo.get.return_value = {
                "id": "action123",
                "user_id": "user123",
                "status": "blocked",
                "title": long_title,
                "description": None,
                "blocking_reason": None,
                "blocked_at": None,
                "project_id": None,
            }

            await escalate_blocked_action(
                action_id="action123",
                user_id="user123",
                include_suggestions=False,
            )

            call_kwargs = mock_session_repo.create.call_args[1]
            # Title should be truncated to 200 chars
            assert (
                len(call_kwargs["problem_statement"]) <= 230
            )  # "How can we unblock: " + 200 + "?"

    @pytest.mark.asyncio
    async def test_escalate_includes_project_name(self):
        """Should include project name in context when action has project."""
        from backend.services.blocker_analyzer import escalate_blocked_action

        mock_redis = MagicMock()
        mock_redis.is_available = True
        mock_redis.create_session.return_value = "bo1_newmeet"

        mock_session_repo = MagicMock()
        mock_session_repo.create.return_value = {
            "id": "bo1_newmeet",
            "status": "created",
        }

        mock_project_repo = MagicMock()
        mock_project_repo.get.return_value = {"name": "Test Project"}

        with (
            patch("bo1.state.repositories.action_repository.action_repository") as mock_action_repo,
            patch(
                "backend.api.dependencies.get_redis_manager",
                return_value=mock_redis,
            ),
            patch(
                "bo1.state.repositories.session_repository.SessionRepository",
                return_value=mock_session_repo,
            ),
            patch(
                "bo1.state.repositories.project_repository.ProjectRepository",
                return_value=mock_project_repo,
            ),
        ):
            mock_action_repo.get.return_value = {
                "id": "action123",
                "user_id": "user123",
                "status": "blocked",
                "title": "Test action",
                "description": None,
                "blocking_reason": "Blocked",
                "blocked_at": None,
                "project_id": "project123",
            }

            await escalate_blocked_action(
                action_id="action123",
                user_id="user123",
                include_suggestions=False,
            )

            call_kwargs = mock_session_repo.create.call_args[1]
            assert call_kwargs["problem_context"]["project_name"] == "Test Project"

    @pytest.mark.asyncio
    async def test_escalate_redis_unavailable(self):
        """Should raise ValueError when Redis unavailable."""
        from backend.services.blocker_analyzer import escalate_blocked_action

        mock_redis = MagicMock()
        mock_redis.is_available = False

        with (
            patch("bo1.state.repositories.action_repository.action_repository") as mock_action_repo,
            patch(
                "backend.api.dependencies.get_redis_manager",
                return_value=mock_redis,
            ),
            patch("bo1.state.repositories.project_repository.ProjectRepository"),
        ):
            mock_action_repo.get.return_value = {
                "id": "action123",
                "user_id": "user123",
                "status": "blocked",
                "title": "Test",
                "description": None,
                "blocking_reason": None,
                "blocked_at": None,
                "project_id": None,
            }

            with pytest.raises(ValueError, match="Service temporarily unavailable"):
                await escalate_blocked_action(
                    action_id="action123",
                    user_id="user123",
                    include_suggestions=False,
                )
