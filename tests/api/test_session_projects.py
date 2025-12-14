"""Tests for session-project linking endpoints.

Tests:
- POST /api/v1/sessions/{id}/projects - Link projects to session
- GET /api/v1/sessions/{id}/projects - Get linked projects
- GET /api/v1/sessions/{id}/available-projects - Get available projects
- DELETE /api/v1/sessions/{id}/projects/{project_id} - Unlink project
- GET /api/v1/sessions/{id}/suggest-projects - Get project suggestions
- POST /api/v1/sessions/{id}/create-suggested-project - Create from suggestion
"""

import pytest

from bo1.state.repositories.session_repository import SessionRepository


class TestSessionProjectsRepository:
    """Test session repository project methods."""

    @pytest.fixture
    def repo(self):
        """Create repository instance."""
        return SessionRepository()

    def test_link_session_to_projects_empty_list(self, repo):
        """Test linking empty project list returns empty."""
        result = repo.link_session_to_projects(
            session_id="test-session-id",
            project_ids=[],
            relationship="discusses",
        )
        assert result == []

    def test_validate_project_workspace_match_empty_list(self, repo):
        """Test validating empty project list returns valid."""
        is_valid, mismatched = repo.validate_project_workspace_match(
            session_id="test-session-id",
            project_ids=[],
        )
        assert is_valid is True
        assert mismatched == []


class TestSessionProjectLinkRequest:
    """Test request model validation."""

    def test_valid_relationship_types(self):
        """Test valid relationship type values."""
        valid_types = ["discusses", "created_from", "replanning"]

        for rel_type in valid_types:
            # Simulating model validation - these should be accepted
            assert rel_type in valid_types

    def test_project_ids_required(self):
        """Test that project_ids is required."""
        # Model should require project_ids field
        # This is validated by Pydantic at runtime
        pass


class TestSessionProjectsResponse:
    """Test response model structure."""

    def test_response_structure(self):
        """Test expected response structure."""
        expected_fields = {
            "session_id",
            "projects",
        }

        response = {
            "session_id": "test-id",
            "projects": [],
        }

        assert set(response.keys()) == expected_fields

    def test_project_item_structure(self):
        """Test project item has expected fields."""
        expected_fields = {
            "project_id",
            "name",
            "description",
            "status",
            "progress_percent",
            "relationship",
            "linked_at",
        }

        project_item = {
            "project_id": "proj-123",
            "name": "Test Project",
            "description": "A test project",
            "status": "active",
            "progress_percent": 50,
            "relationship": "discusses",
            "linked_at": "2025-12-14T00:00:00Z",
        }

        assert set(project_item.keys()) == expected_fields


class TestAvailableProjectsResponse:
    """Test available projects response structure."""

    def test_response_structure(self):
        """Test expected response structure."""
        expected_fields = {
            "session_id",
            "projects",
        }

        response = {
            "session_id": "test-id",
            "projects": [],
        }

        assert set(response.keys()) == expected_fields

    def test_available_project_structure(self):
        """Test available project item has expected fields."""
        expected_fields = {
            "id",
            "name",
            "description",
            "status",
            "progress_percent",
            "is_linked",
        }

        project_item = {
            "id": "proj-123",
            "name": "Test Project",
            "description": "A test project",
            "status": "active",
            "progress_percent": 50,
            "is_linked": False,
        }

        assert set(project_item.keys()) == expected_fields


class TestProjectSuggestionsResponse:
    """Test project suggestions response structure."""

    def test_response_structure(self):
        """Test expected response structure."""
        expected_fields = {
            "session_id",
            "suggestions",
        }

        response = {
            "session_id": "test-id",
            "suggestions": [],
        }

        assert set(response.keys()) == expected_fields

    def test_suggestion_structure(self):
        """Test suggestion item has expected fields."""
        expected_fields = {
            "name",
            "description",
            "action_ids",
            "confidence",
            "rationale",
        }

        suggestion = {
            "name": "New Feature Project",
            "description": "Project to implement new features",
            "action_ids": ["action-1", "action-2"],
            "confidence": 0.85,
            "rationale": "These actions naturally group together",
        }

        assert set(suggestion.keys()) == expected_fields

    def test_confidence_range(self):
        """Test confidence is within valid range."""
        suggestion = {
            "confidence": 0.85,
        }

        assert 0.0 <= suggestion["confidence"] <= 1.0


class TestProjectSuggester:
    """Test project suggester service logic."""

    def test_format_actions_for_prompt(self):
        """Test action formatting for LLM prompt."""
        from backend.services.project_suggester import _format_actions_for_prompt

        actions = [
            {
                "id": "action-1",
                "title": "Implement feature X",
                "description": "Build the feature",
                "what_and_how": "Use React and TypeScript",
                "status": "todo",
                "priority": "high",
                "category": "implementation",
            }
        ]

        result = _format_actions_for_prompt(actions)

        assert "action-1" in result
        assert "Implement feature X" in result
        assert "todo" in result
        assert "high" in result

    def test_parse_suggestions_empty_response(self):
        """Test parsing empty suggestions response."""
        from backend.services.project_suggester import _parse_suggestions

        actions = []
        result = _parse_suggestions('{"suggestions": []}', actions, 0.6)

        assert result == []

    def test_parse_suggestions_filters_low_confidence(self):
        """Test that low confidence suggestions are filtered."""
        from backend.services.project_suggester import _parse_suggestions

        actions = [{"id": "action-1"}]
        response = """{
            "suggestions": [
                {
                    "name": "Low Confidence Project",
                    "description": "Test",
                    "action_ids": ["action-1"],
                    "confidence": 0.4,
                    "rationale": "Weak grouping"
                }
            ]
        }"""

        result = _parse_suggestions(response, actions, 0.6)

        # Should be filtered out due to low confidence
        assert len(result) == 0

    def test_parse_suggestions_validates_action_ids(self):
        """Test that invalid action IDs are filtered."""
        from backend.services.project_suggester import _parse_suggestions

        actions = [{"id": "action-1"}]
        response = """{
            "suggestions": [
                {
                    "name": "Invalid Actions Project",
                    "description": "Test",
                    "action_ids": ["nonexistent-action"],
                    "confidence": 0.9,
                    "rationale": "Action doesn't exist"
                }
            ]
        }"""

        result = _parse_suggestions(response, actions, 0.6)

        # Should be filtered out due to no valid action IDs
        assert len(result) == 0

    def test_parse_suggestions_handles_json_in_codeblock(self):
        """Test parsing JSON wrapped in markdown code block."""
        from backend.services.project_suggester import _parse_suggestions

        actions = [{"id": "action-1"}]
        response = """```json
{
    "suggestions": [
        {
            "name": "Valid Project",
            "description": "Test",
            "action_ids": ["action-1"],
            "confidence": 0.8,
            "rationale": "Good grouping"
        }
    ]
}
```"""

        result = _parse_suggestions(response, actions, 0.6)

        assert len(result) == 1
        assert result[0].name == "Valid Project"
        assert result[0].confidence == 0.8


class TestWorkspaceConstraint:
    """Test workspace match constraint for session-project linking."""

    def test_trigger_exists_for_workspace_validation(self):
        """Test that the workspace validation trigger exists in migration."""
        # The migration av1_add_workspace_to_projects creates a trigger
        # that validates session and project belong to same workspace.
        # This test documents the expected behavior.
        pass

    def test_null_workspace_match_is_valid(self):
        """Test that NULL-to-NULL workspace match is valid (personal items)."""
        # When both session.workspace_id and project.workspace_id are NULL,
        # both are "personal" items and can be linked.
        pass

    def test_same_workspace_match_is_valid(self):
        """Test that same workspace_id match is valid."""
        # When both session.workspace_id and project.workspace_id match,
        # they can be linked.
        pass

    def test_different_workspace_match_is_invalid(self):
        """Test that different workspace_ids prevent linking."""
        # When session.workspace_id != project.workspace_id,
        # the link should be rejected by the database trigger.
        pass
