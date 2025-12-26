"""Tests for project autogeneration API endpoints.

Tests:
- GET /api/v1/projects/autogenerate-suggestions
- POST /api/v1/projects/autogenerate
- GET /api/v1/projects/unassigned-count
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from backend.services.project_autogen import (
    MIN_ACTIONS_FOR_AUTOGEN,
    AutogenProjectSuggestion,
    create_projects_from_suggestions,
    get_autogen_suggestions,
    get_unassigned_action_count,
)


@pytest.fixture
def mock_db_session():
    """Mock database session context manager."""
    with patch("backend.services.project_autogen.db_session") as mock:
        conn_mock = MagicMock()
        cursor_mock = MagicMock()
        conn_mock.cursor.return_value.__enter__ = MagicMock(return_value=cursor_mock)
        conn_mock.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock.return_value.__enter__ = MagicMock(return_value=conn_mock)
        mock.return_value.__exit__ = MagicMock(return_value=False)
        yield cursor_mock


@pytest.fixture
def sample_actions():
    """Sample unassigned actions for testing."""
    return [
        {
            "id": str(uuid4()),
            "title": "Set up marketing campaign",
            "description": "Create landing page and email sequence",
            "status": "todo",
            "priority": "high",
            "category": "marketing",
            "what_and_how": "Build landing page in Webflow",
            "success_criteria": "100 signups",
            "source_session_id": "bo1_test123",
            "session_problem": "How to launch product?",
        },
        {
            "id": str(uuid4()),
            "title": "Design social media assets",
            "description": "Create graphics for campaign",
            "status": "todo",
            "priority": "medium",
            "category": "marketing",
            "what_and_how": "Use Figma templates",
            "success_criteria": "5 posts designed",
            "source_session_id": "bo1_test123",
            "session_problem": "How to launch product?",
        },
        {
            "id": str(uuid4()),
            "title": "Set up analytics",
            "description": "Install tracking pixels",
            "status": "todo",
            "priority": "high",
            "category": "implementation",
            "what_and_how": "Add GTM and GA4",
            "success_criteria": "All pages tracked",
            "source_session_id": "bo1_test456",
            "session_problem": "Improve data tracking",
        },
    ]


class TestGetUnassignedActionCount:
    """Tests for get_unassigned_action_count function."""

    def test_returns_count(self, mock_db_session):
        """Should return count of unassigned actions."""
        mock_db_session.fetchone.return_value = {"count": 5}

        count = get_unassigned_action_count("user123")

        assert count == 5
        mock_db_session.execute.assert_called_once()

    def test_returns_zero_when_no_results(self, mock_db_session):
        """Should return 0 when no results."""
        mock_db_session.fetchone.return_value = None

        count = get_unassigned_action_count("user123")

        assert count == 0

    def test_passes_user_id_to_db_session_for_rls(self):
        """Should pass user_id to db_session for RLS context."""
        with patch("backend.services.project_autogen.db_session") as mock_db:
            conn_mock = MagicMock()
            cursor_mock = MagicMock()
            cursor_mock.fetchone.return_value = {"count": 3}
            conn_mock.cursor.return_value.__enter__ = MagicMock(return_value=cursor_mock)
            conn_mock.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=conn_mock)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            get_unassigned_action_count("user-abc-123")

            # Verify db_session called with user_id for RLS context
            mock_db.assert_called_once_with(user_id="user-abc-123")

    def test_returns_zero_on_db_error(self):
        """Should return 0 and log error when database fails."""
        with patch("backend.services.project_autogen.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(
                side_effect=Exception("DB connection failed")
            )
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            count = get_unassigned_action_count("user123")

            assert count == 0


class TestGetAutogenSuggestions:
    """Tests for get_autogen_suggestions function."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_too_few_actions(self, mock_db_session):
        """Should return empty list when fewer than MIN_ACTIONS_FOR_AUTOGEN actions."""
        mock_db_session.fetchall.return_value = [
            {"id": str(uuid4()), "title": "Action 1"},
        ]

        suggestions = await get_autogen_suggestions("user123")

        assert suggestions == []

    @pytest.mark.asyncio
    async def test_calls_llm_with_actions(self, mock_db_session, sample_actions):
        """Should call LLM when enough actions exist."""
        mock_db_session.fetchall.return_value = sample_actions

        with patch("backend.services.project_autogen._get_client") as mock_client:
            mock_llm = AsyncMock()
            mock_llm.call.return_value = (
                '{"suggestions": []}',
                {"input_tokens": 100, "output_tokens": 50},
            )
            mock_client.return_value = mock_llm

            suggestions = await get_autogen_suggestions("user123")

            mock_llm.call.assert_called_once()
            assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    async def test_parses_valid_suggestions(self, mock_db_session, sample_actions):
        """Should parse valid LLM response into suggestions."""
        mock_db_session.fetchall.return_value = sample_actions

        llm_response = f'''{{
            "suggestions": [
                {{
                    "name": "Marketing Launch",
                    "description": "Launch marketing campaign",
                    "action_ids": ["{sample_actions[0]["id"]}", "{sample_actions[1]["id"]}"],
                    "confidence": 0.85,
                    "rationale": "Both actions relate to marketing"
                }}
            ]
        }}'''

        with patch("backend.services.project_autogen._get_client") as mock_client:
            mock_llm = AsyncMock()
            mock_llm.call.return_value = (llm_response, {})
            mock_client.return_value = mock_llm

            suggestions = await get_autogen_suggestions("user123")

            assert len(suggestions) == 1
            assert suggestions[0].name == "Marketing Launch"
            assert suggestions[0].confidence == 0.85
            assert len(suggestions[0].action_ids) == 2

    @pytest.mark.asyncio
    async def test_filters_low_confidence_suggestions(self, mock_db_session, sample_actions):
        """Should filter out suggestions below minimum confidence."""
        mock_db_session.fetchall.return_value = sample_actions

        llm_response = f'''{{
            "suggestions": [
                {{
                    "name": "Low Confidence Project",
                    "description": "Weak grouping",
                    "action_ids": ["{sample_actions[0]["id"]}"],
                    "confidence": 0.5,
                    "rationale": "Not very sure"
                }}
            ]
        }}'''

        with patch("backend.services.project_autogen._get_client") as mock_client:
            mock_llm = AsyncMock()
            mock_llm.call.return_value = (llm_response, {})
            mock_client.return_value = mock_llm

            suggestions = await get_autogen_suggestions("user123")

            assert len(suggestions) == 0

    @pytest.mark.asyncio
    async def test_validates_action_ids(self, mock_db_session, sample_actions):
        """Should filter out invalid action IDs from suggestions."""
        mock_db_session.fetchall.return_value = sample_actions

        # Include an invalid action ID
        llm_response = f'''{{
            "suggestions": [
                {{
                    "name": "Mixed Valid Invalid",
                    "description": "Some valid, some invalid",
                    "action_ids": ["{sample_actions[0]["id"]}", "invalid-uuid-12345"],
                    "confidence": 0.85,
                    "rationale": "Testing"
                }}
            ]
        }}'''

        with patch("backend.services.project_autogen._get_client") as mock_client:
            mock_llm = AsyncMock()
            mock_llm.call.return_value = (llm_response, {})
            mock_client.return_value = mock_llm

            suggestions = await get_autogen_suggestions("user123")

            assert len(suggestions) == 1
            assert len(suggestions[0].action_ids) == 1
            assert suggestions[0].action_ids[0] == sample_actions[0]["id"]

    @pytest.mark.asyncio
    async def test_prevents_duplicate_action_ids_across_suggestions(
        self, mock_db_session, sample_actions
    ):
        """Should prevent same action ID appearing in multiple suggestions."""
        mock_db_session.fetchall.return_value = sample_actions

        # Both suggestions try to claim the same action
        llm_response = f'''{{
            "suggestions": [
                {{
                    "name": "First Project",
                    "description": "First",
                    "action_ids": ["{sample_actions[0]["id"]}", "{sample_actions[1]["id"]}"],
                    "confidence": 0.9,
                    "rationale": "First"
                }},
                {{
                    "name": "Second Project",
                    "description": "Second tries to reuse action",
                    "action_ids": ["{sample_actions[0]["id"]}", "{sample_actions[2]["id"]}"],
                    "confidence": 0.8,
                    "rationale": "Second"
                }}
            ]
        }}'''

        with patch("backend.services.project_autogen._get_client") as mock_client:
            mock_llm = AsyncMock()
            mock_llm.call.return_value = (llm_response, {})
            mock_client.return_value = mock_llm

            suggestions = await get_autogen_suggestions("user123")

            # First suggestion gets action 0 and 1
            # Second suggestion only gets action 2 (0 is already used)
            assert len(suggestions) == 2
            all_action_ids = []
            for s in suggestions:
                all_action_ids.extend(s.action_ids)

            # No duplicates
            assert len(all_action_ids) == len(set(all_action_ids))


class TestCreateProjectsFromSuggestions:
    """Tests for create_projects_from_suggestions function."""

    @pytest.mark.asyncio
    async def test_creates_projects_from_suggestions(self):
        """Should create projects and assign actions."""
        suggestions = [
            AutogenProjectSuggestion(
                id="sug1",
                name="Test Project",
                description="Test description",
                action_ids=["action1", "action2"],
                confidence=0.85,
                rationale="Testing",
            )
        ]

        with patch("backend.services.project_autogen.ProjectRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.create.return_value = {"id": "proj1", "name": "Test Project"}
            mock_repo.get.return_value = {
                "id": "proj1",
                "name": "Test Project",
                "status": "planning",
                "progress_percent": 0,
            }
            mock_repo_class.return_value = mock_repo

            with patch("backend.services.project_autogen.db_session"):
                created = await create_projects_from_suggestions(suggestions, "user123")

            assert len(created) == 1
            mock_repo.create.assert_called_once()
            assert mock_repo.assign_action.call_count == 2
            mock_repo.recalculate_progress.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_empty_suggestions(self):
        """Should return empty list when no suggestions provided."""
        created = await create_projects_from_suggestions([], "user123")
        assert created == []

    @pytest.mark.asyncio
    async def test_handles_project_creation_failure(self):
        """Should continue with other suggestions if one fails."""
        suggestions = [
            AutogenProjectSuggestion(
                id="sug1",
                name="Failing Project",
                description="Will fail",
                action_ids=["action1"],
                confidence=0.85,
                rationale="Testing failure",
            ),
            AutogenProjectSuggestion(
                id="sug2",
                name="Succeeding Project",
                description="Will succeed",
                action_ids=["action2"],
                confidence=0.85,
                rationale="Testing success",
            ),
        ]

        with patch("backend.services.project_autogen.ProjectRepository") as mock_repo_class:
            mock_repo = MagicMock()
            # First call returns None (failure), second succeeds
            mock_repo.create.side_effect = [
                None,
                {"id": "proj2", "name": "Succeeding Project"},
            ]
            mock_repo.get.return_value = {
                "id": "proj2",
                "name": "Succeeding Project",
                "status": "planning",
                "progress_percent": 0,
            }
            mock_repo_class.return_value = mock_repo

            with patch("backend.services.project_autogen.db_session"):
                created = await create_projects_from_suggestions(suggestions, "user123")

            # Only one project created successfully
            assert len(created) == 1
            assert created[0]["name"] == "Succeeding Project"


class TestAutogenAPIEndpoints:
    """Integration tests for autogen API endpoints.

    Note: Full API integration tests would require TestClient setup.
    These are placeholder tests - actual integration testing is done via E2E.
    """

    def test_endpoints_exist(self):
        """Verify API endpoints are defined in the router."""
        from backend.api.projects import router

        paths = [route.path for route in router.routes]
        # Paths include router prefix /v1/projects
        assert "/v1/projects/autogenerate-suggestions" in paths
        assert "/v1/projects/autogenerate" in paths
        assert "/v1/projects/unassigned-count" in paths

    def test_unassigned_count_endpoint_has_response_model(self):
        """Verify unassigned-count endpoint has response_model defined."""
        from backend.api.models import UnassignedCountResponse
        from backend.api.projects import router

        for route in router.routes:
            if route.path == "/v1/projects/unassigned-count":
                assert route.response_model == UnassignedCountResponse
                break
        else:
            pytest.fail("unassigned-count endpoint not found")


class TestUnassignedCountResponse:
    """Tests for UnassignedCountResponse model."""

    def test_response_model_validation(self):
        """Verify UnassignedCountResponse validates correctly."""
        from backend.api.models import UnassignedCountResponse

        response = UnassignedCountResponse(
            unassigned_count=5,
            min_required=3,
            can_autogenerate=True,
        )
        assert response.unassigned_count == 5
        assert response.min_required == 3
        assert response.can_autogenerate is True

    def test_response_model_serialization(self):
        """Verify response model serializes to expected JSON structure."""
        from backend.api.models import UnassignedCountResponse

        response = UnassignedCountResponse(
            unassigned_count=2,
            min_required=3,
            can_autogenerate=False,
        )
        data = response.model_dump()
        assert data == {
            "unassigned_count": 2,
            "min_required": 3,
            "can_autogenerate": False,
        }


class TestMinActionsThreshold:
    """Tests for MIN_ACTIONS_FOR_AUTOGEN constant."""

    def test_min_actions_is_reasonable(self):
        """MIN_ACTIONS_FOR_AUTOGEN should be a reasonable value."""
        assert MIN_ACTIONS_FOR_AUTOGEN >= 2
        assert MIN_ACTIONS_FOR_AUTOGEN <= 10
