"""Tests for project generator service.

Tests:
- Title normalization and extraction
- Similarity matching for deduplication
- Project-worthiness filtering
- Project generation flow
"""

from unittest.mock import patch

from backend.services.project_generator import (
    calculate_similarity,
    extract_project_title,
    find_similar_project,
    generate_project_from_action,
    is_action_project_worthy,
    normalize_title,
)


class TestNormalizeTitle:
    """Tests for title normalization."""

    def test_basic_normalization(self):
        """Test basic title normalization."""
        assert normalize_title("Implement User Auth") == "user auth"
        assert normalize_title("Create Dashboard") == "dashboard"
        assert normalize_title("Build Payment System") == "payment system"

    def test_strips_action_verbs(self):
        """Test that common action verbs are stripped."""
        assert normalize_title("Implement Feature X") == "feature x"
        assert normalize_title("Create New API") == "new api"
        assert normalize_title("Build User Portal") == "user portal"
        assert normalize_title("Deploy to Production") == "to production"
        # Note: CI/CD becomes cicd after removing the / punctuation
        assert normalize_title("Setup CI/CD") == "cicd"

    def test_removes_punctuation(self):
        """Test punctuation removal."""
        assert normalize_title("Hello, World!") == "hello world"
        assert normalize_title("API (v2)") == "api v2"

    def test_normalizes_whitespace(self):
        """Test whitespace normalization."""
        assert normalize_title("  Multiple   Spaces  ") == "multiple spaces"

    def test_empty_string(self):
        """Test empty string handling."""
        assert normalize_title("") == ""
        assert normalize_title("   ") == ""


class TestExtractProjectTitle:
    """Tests for project title extraction from action titles."""

    def test_strips_action_verbs(self):
        """Test that action verbs are stripped for project names."""
        assert extract_project_title("Implement User Authentication") == "User Authentication"
        assert extract_project_title("Create Payment Gateway") == "Payment Gateway"
        assert extract_project_title("Build Customer Portal") == "Customer Portal"

    def test_preserves_non_verb_starts(self):
        """Test that titles not starting with verbs are preserved."""
        assert extract_project_title("User Authentication System") == "User Authentication System"
        assert extract_project_title("API Gateway v2") == "API Gateway v2"

    def test_title_cases_lowercase(self):
        """Test that all-lowercase titles get title-cased."""
        assert extract_project_title("implement user auth") == "User Auth"

    def test_empty_handling(self):
        """Test empty title handling."""
        assert extract_project_title("") == "Untitled Project"
        # "Implement" alone doesn't start with "Implement " (with space), so kept as-is
        assert extract_project_title("Implement") == "Implement"
        # Trailing spaces are stripped first, so "Implement " becomes "Implement"
        assert extract_project_title("Implement ") == "Implement"


class TestCalculateSimilarity:
    """Tests for title similarity calculation."""

    def test_identical_titles(self):
        """Test that identical titles have similarity 1.0."""
        assert calculate_similarity("User Auth", "User Auth") == 1.0

    def test_normalized_identical(self):
        """Test that normalized-identical titles match highly."""
        score = calculate_similarity("Implement User Auth", "Create User Auth")
        assert score >= 0.9

    def test_different_titles(self):
        """Test that different titles have low similarity."""
        score = calculate_similarity("User Auth", "Payment Gateway")
        assert score < 0.5

    def test_partial_match(self):
        """Test partial title matches."""
        score = calculate_similarity("User Authentication", "User Auth System")
        assert 0.5 < score < 1.0

    def test_empty_string(self):
        """Test empty string handling."""
        assert calculate_similarity("", "Something") == 0.0
        assert calculate_similarity("Something", "") == 0.0


class TestIsActionProjectWorthy:
    """Tests for project-worthiness filtering."""

    def test_short_titles_rejected(self):
        """Test that short titles are rejected."""
        action = {"title": "Fix bug", "description": ""}
        assert not is_action_project_worthy(action)

    def test_tactical_keywords_rejected(self):
        """Test that tactical keywords are rejected."""
        actions = [
            {"title": "Fix bug in login flow", "description": ""},
            {"title": "Quick fix for API timeout", "description": ""},
            {"title": "Hotfix for production issue", "description": ""},
            {"title": "Minor update to config", "description": ""},
        ]
        for action in actions:
            assert not is_action_project_worthy(action)

    def test_long_descriptions_accepted(self):
        """Test that actions with long descriptions are accepted."""
        action = {
            "title": "Build authentication system",
            "description": "A" * 101,  # > 100 chars
        }
        assert is_action_project_worthy(action)

    def test_success_criteria_accepted(self):
        """Test that actions with success criteria are accepted."""
        action = {
            "title": "Build authentication system",
            "description": "",
            "success_criteria": ["Users can log in", "Sessions expire properly"],
        }
        assert is_action_project_worthy(action)

    def test_what_and_how_accepted(self):
        """Test that actions with what_and_how are accepted."""
        action = {
            "title": "Build authentication system",
            "description": "",
            "what_and_how": ["Use OAuth2", "Implement JWT tokens"],
        }
        assert is_action_project_worthy(action)

    def test_long_titles_accepted(self):
        """Test that long titles (>= 20 chars) are accepted."""
        action = {
            "title": "Build customer portal for enterprise clients",
            "description": "",
        }
        assert is_action_project_worthy(action)


class TestFindSimilarProject:
    """Tests for finding similar existing projects."""

    @patch("backend.services.project_generator.project_repository")
    def test_finds_similar_project(self, mock_repo):
        """Test finding a similar project."""
        mock_repo.get_by_user.return_value = (
            1,
            [
                {"id": "proj-1", "name": "User Authentication"},
                {"id": "proj-2", "name": "Payment Gateway"},
            ],
        )

        # Use a very similar title to ensure match
        result = find_similar_project("user-1", "User Authentication System")

        assert result is not None
        assert result["id"] == "proj-1"

    @patch("backend.services.project_generator.project_repository")
    def test_no_similar_project(self, mock_repo):
        """Test when no similar project exists."""
        mock_repo.get_by_user.return_value = (
            1,
            [{"id": "proj-1", "name": "Something Completely Different"}],
        )

        result = find_similar_project("user-1", "User Authentication")

        assert result is None

    @patch("backend.services.project_generator.project_repository")
    def test_empty_projects(self, mock_repo):
        """Test when user has no projects."""
        mock_repo.get_by_user.return_value = (0, [])

        result = find_similar_project("user-1", "User Authentication")

        assert result is None


class TestGenerateProjectFromAction:
    """Tests for project generation flow."""

    @patch("backend.services.project_generator.project_repository")
    @patch("backend.services.project_generator.action_repository")
    def test_generates_new_project(self, mock_action_repo, mock_project_repo):
        """Test generating a new project from action."""
        # Setup mocks
        mock_action_repo.get.return_value = {
            "id": "action-1",
            "user_id": "user-1",
            "title": "Build customer authentication portal",
            "description": "A comprehensive auth system",
            "project_id": None,
            "source_session_id": "session-1",
        }
        mock_project_repo.get_by_user.return_value = (0, [])
        mock_project_repo.create.return_value = {
            "id": "new-proj-1",
            "name": "Customer Authentication Portal",
        }

        result = generate_project_from_action("action-1", "user-1")

        assert result is not None
        assert result["id"] == "new-proj-1"
        mock_project_repo.create.assert_called_once()
        mock_project_repo.assign_action.assert_called_once()
        mock_project_repo.link_session.assert_called_once()

    @patch("backend.services.project_generator.project_repository")
    @patch("backend.services.project_generator.action_repository")
    def test_links_to_existing_project(self, mock_action_repo, mock_project_repo):
        """Test linking to an existing similar project."""
        mock_action_repo.get.return_value = {
            "id": "action-1",
            "user_id": "user-1",
            "title": "Implement customer authentication system",
            "description": "",
            "project_id": None,
            "success_criteria": ["Works"],
        }
        # Use very similar project name so similarity >= 0.8
        mock_project_repo.get_by_user.return_value = (
            1,
            [{"id": "existing-proj", "name": "Customer Authentication System"}],
        )

        result = generate_project_from_action("action-1", "user-1")

        assert result is not None
        assert result["id"] == "existing-proj"
        mock_project_repo.create.assert_not_called()
        mock_project_repo.assign_action.assert_called_once_with(
            "action-1", "existing-proj", "user-1"
        )

    @patch("backend.services.project_generator.action_repository")
    def test_skips_if_action_not_found(self, mock_action_repo):
        """Test that missing actions are skipped."""
        mock_action_repo.get.return_value = None

        result = generate_project_from_action("action-1", "user-1")

        assert result is None

    @patch("backend.services.project_generator.action_repository")
    def test_skips_if_wrong_user(self, mock_action_repo):
        """Test that actions belonging to other users are skipped."""
        mock_action_repo.get.return_value = {
            "id": "action-1",
            "user_id": "other-user",
        }

        result = generate_project_from_action("action-1", "user-1")

        assert result is None

    @patch("backend.services.project_generator.action_repository")
    def test_skips_if_already_has_project(self, mock_action_repo):
        """Test that actions already assigned to projects are skipped."""
        mock_action_repo.get.return_value = {
            "id": "action-1",
            "user_id": "user-1",
            "project_id": "existing-project",
        }

        result = generate_project_from_action("action-1", "user-1")

        assert result is None

    @patch("backend.services.project_generator.action_repository")
    def test_skips_if_not_project_worthy(self, mock_action_repo):
        """Test that tactical actions are skipped."""
        mock_action_repo.get.return_value = {
            "id": "action-1",
            "user_id": "user-1",
            "title": "Fix bug",  # Too short
            "description": "",
            "project_id": None,
        }

        result = generate_project_from_action("action-1", "user-1")

        assert result is None
