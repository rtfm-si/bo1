"""Tests for managed competitors API endpoints."""

from datetime import UTC, datetime

from backend.api.context.models import (
    ManagedCompetitor,
    ManagedCompetitorCreate,
    ManagedCompetitorListResponse,
    ManagedCompetitorResponse,
    ManagedCompetitorUpdate,
)


class TestManagedCompetitorModels:
    """Tests for managed competitor Pydantic models."""

    def test_managed_competitor_all_fields(self):
        """Test ManagedCompetitor with all fields populated."""
        now = datetime.now(UTC)
        competitor = ManagedCompetitor(
            name="Notion",
            url="https://notion.so",
            notes="Strong in enterprise, weaker in SMB",
            added_at=now,
        )

        assert competitor.name == "Notion"
        assert competitor.url == "https://notion.so"
        assert competitor.notes == "Strong in enterprise, weaker in SMB"
        assert competitor.added_at == now

    def test_managed_competitor_minimal(self):
        """Test ManagedCompetitor with minimal fields."""
        now = datetime.now(UTC)
        competitor = ManagedCompetitor(
            name="MinimalCo",
            url=None,
            notes=None,
            added_at=now,
        )

        assert competitor.name == "MinimalCo"
        assert competitor.url is None
        assert competitor.notes is None

    def test_managed_competitor_name_validation(self):
        """Test ManagedCompetitor name length validation."""
        now = datetime.now(UTC)

        # Valid: 1 char
        competitor = ManagedCompetitor(name="A", url=None, notes=None, added_at=now)
        assert competitor.name == "A"

        # Valid: 100 chars
        long_name = "A" * 100
        competitor = ManagedCompetitor(name=long_name, url=None, notes=None, added_at=now)
        assert competitor.name == long_name

    def test_managed_competitor_create_request(self):
        """Test ManagedCompetitorCreate request model."""
        request = ManagedCompetitorCreate(
            name="TestCompany",
            url="https://test.com",
            notes="Some notes",
        )

        assert request.name == "TestCompany"
        assert request.url == "https://test.com"
        assert request.notes == "Some notes"

    def test_managed_competitor_create_minimal(self):
        """Test ManagedCompetitorCreate with only name."""
        request = ManagedCompetitorCreate(name="TestCompany")

        assert request.name == "TestCompany"
        assert request.url is None
        assert request.notes is None

    def test_managed_competitor_update_request(self):
        """Test ManagedCompetitorUpdate request model."""
        request = ManagedCompetitorUpdate(
            url="https://updated.com",
            notes="Updated notes",
        )

        assert request.url == "https://updated.com"
        assert request.notes == "Updated notes"

    def test_managed_competitor_response_success(self):
        """Test ManagedCompetitorResponse with success."""
        now = datetime.now(UTC)
        competitor = ManagedCompetitor(
            name="TestCo",
            url="https://test.com",
            notes=None,
            added_at=now,
        )
        response = ManagedCompetitorResponse(
            success=True,
            competitor=competitor,
        )

        assert response.success is True
        assert response.competitor.name == "TestCo"
        assert response.error is None

    def test_managed_competitor_response_error(self):
        """Test ManagedCompetitorResponse with error."""
        response = ManagedCompetitorResponse(
            success=False,
            competitor=None,
            error="Competitor already exists",
        )

        assert response.success is False
        assert response.competitor is None
        assert response.error == "Competitor already exists"

    def test_managed_competitor_list_response(self):
        """Test ManagedCompetitorListResponse."""
        now = datetime.now(UTC)
        competitors = [
            ManagedCompetitor(name="Co1", url=None, notes=None, added_at=now),
            ManagedCompetitor(name="Co2", url="https://co2.com", notes="Great UX", added_at=now),
        ]
        response = ManagedCompetitorListResponse(
            success=True,
            competitors=competitors,
            count=2,
        )

        assert response.success is True
        assert len(response.competitors) == 2
        assert response.count == 2
        assert response.error is None

    def test_managed_competitor_list_response_empty(self):
        """Test ManagedCompetitorListResponse with no competitors."""
        response = ManagedCompetitorListResponse(
            success=True,
            competitors=[],
            count=0,
        )

        assert response.success is True
        assert response.competitors == []
        assert response.count == 0


class TestManagedCompetitorRepository:
    """Tests for managed competitor repository methods."""

    def test_get_managed_competitors_empty(self):
        """Test getting competitors when none exist."""
        from unittest.mock import patch

        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()

        with patch.object(repo, "get_context", return_value=None):
            result = repo.get_managed_competitors("user123")
            assert result == []

    def test_get_managed_competitors_with_data(self):
        """Test getting competitors when data exists."""
        from unittest.mock import patch

        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()

        mock_context = {
            "managed_competitors": [
                {
                    "name": "Notion",
                    "url": "https://notion.so",
                    "notes": None,
                    "added_at": "2025-01-01T00:00:00Z",
                },
                {
                    "name": "Airtable",
                    "url": None,
                    "notes": "Spreadsheet competitor",
                    "added_at": "2025-01-02T00:00:00Z",
                },
            ]
        }

        with patch.object(repo, "get_context", return_value=mock_context):
            result = repo.get_managed_competitors("user123")
            assert len(result) == 2
            assert result[0]["name"] == "Notion"
            assert result[1]["name"] == "Airtable"

    def test_add_managed_competitor_new(self):
        """Test adding a new competitor."""
        from unittest.mock import patch

        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()

        mock_context = {"managed_competitors": []}

        with patch.object(repo, "get_context", return_value=mock_context):
            with patch.object(repo, "save_context") as mock_save:
                result = repo.add_managed_competitor(
                    user_id="user123",
                    name="NewCompetitor",
                    url="https://new.com",
                    notes="New entry",
                )

                assert result is not None
                assert result["name"] == "NewCompetitor"
                assert result["url"] == "https://new.com"
                assert result["notes"] == "New entry"
                assert "added_at" in result

                # Verify save was called
                mock_save.assert_called_once()

    def test_add_managed_competitor_duplicate(self):
        """Test adding a duplicate competitor (case-insensitive)."""
        from unittest.mock import patch

        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()

        mock_context = {
            "managed_competitors": [
                {"name": "Notion", "url": None, "notes": None, "added_at": "2025-01-01T00:00:00Z"}
            ]
        }

        with patch.object(repo, "get_context", return_value=mock_context):
            with patch.object(repo, "save_context") as mock_save:
                # Same name, different case
                result = repo.add_managed_competitor(
                    user_id="user123",
                    name="NOTION",
                )

                assert result is None  # Duplicate
                mock_save.assert_not_called()

    def test_update_managed_competitor(self):
        """Test updating an existing competitor."""
        from unittest.mock import patch

        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()

        mock_context = {
            "managed_competitors": [
                {"name": "Notion", "url": None, "notes": None, "added_at": "2025-01-01T00:00:00Z"}
            ]
        }

        with patch.object(repo, "get_context", return_value=mock_context):
            with patch.object(repo, "save_context") as mock_save:
                result = repo.update_managed_competitor(
                    user_id="user123",
                    name="notion",  # Case-insensitive match
                    url="https://notion.so",
                    notes="Updated notes",
                )

                assert result is not None
                assert result["url"] == "https://notion.so"
                assert result["notes"] == "Updated notes"
                mock_save.assert_called_once()

    def test_update_managed_competitor_not_found(self):
        """Test updating a non-existent competitor."""
        from unittest.mock import patch

        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()

        mock_context = {"managed_competitors": []}

        with patch.object(repo, "get_context", return_value=mock_context):
            with patch.object(repo, "save_context") as mock_save:
                result = repo.update_managed_competitor(
                    user_id="user123",
                    name="NonExistent",
                    url="https://test.com",
                )

                assert result is None
                mock_save.assert_not_called()

    def test_remove_managed_competitor(self):
        """Test removing an existing competitor."""
        from unittest.mock import patch

        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()

        mock_context = {
            "managed_competitors": [
                {"name": "Notion", "url": None, "notes": None, "added_at": "2025-01-01T00:00:00Z"},
                {
                    "name": "Airtable",
                    "url": None,
                    "notes": None,
                    "added_at": "2025-01-02T00:00:00Z",
                },
            ]
        }

        with patch.object(repo, "get_context", return_value=mock_context):
            with patch.object(repo, "save_context") as mock_save:
                result = repo.remove_managed_competitor("user123", "NOTION")  # Case-insensitive

                assert result is True
                mock_save.assert_called_once()
                # Verify the saved context has only one competitor
                saved_context = mock_save.call_args[0][1]
                assert len(saved_context["managed_competitors"]) == 1
                assert saved_context["managed_competitors"][0]["name"] == "Airtable"

    def test_remove_managed_competitor_not_found(self):
        """Test removing a non-existent competitor."""
        from unittest.mock import patch

        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()

        mock_context = {"managed_competitors": []}

        with patch.object(repo, "get_context", return_value=mock_context):
            with patch.object(repo, "save_context") as mock_save:
                result = repo.remove_managed_competitor("user123", "NonExistent")

                assert result is False
                mock_save.assert_not_called()
