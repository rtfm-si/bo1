"""Tests for managed competitors API endpoints."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from backend.api.context.models import (
    ManagedCompetitor,
    ManagedCompetitorCreate,
    ManagedCompetitorListResponse,
    ManagedCompetitorResponse,
    ManagedCompetitorUpdate,
)
from bo1.state.pool_degradation import PoolExhaustionError


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

        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()

        with patch.object(repo, "get_context", return_value=None):
            result = repo.get_managed_competitors("user123")
            assert result == []

    def test_get_managed_competitors_with_data(self):
        """Test getting competitors when data exists."""

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

        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()

        mock_context = {"managed_competitors": []}

        with patch.object(repo, "get_context", return_value=mock_context):
            with patch.object(repo, "save_context") as mock_save:
                result = repo.remove_managed_competitor("user123", "NonExistent")

                assert result is False
                mock_save.assert_not_called()


class TestManagedCompetitorsErrorHandling:
    """Tests for error handling in managed competitors endpoint."""

    @pytest.mark.asyncio
    async def test_pool_exhaustion_returns_503(self):
        """Test that pool exhaustion error returns 503 with Retry-After header."""
        from fastapi import HTTPException

        from backend.api.utils.errors import handle_api_errors

        @handle_api_errors("test operation")
        async def test_endpoint():
            raise PoolExhaustionError(
                message="Database pool exhausted",
                queue_depth=5,
                wait_estimate=10.0,
            )

        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint()

        assert exc_info.value.status_code == 503
        assert "service_unavailable" in exc_info.value.detail["error_code"]
        assert "Retry-After" in exc_info.value.headers

    @pytest.mark.asyncio
    async def test_handle_api_errors_preserves_http_exception(self):
        """Test that HTTPException passes through unchanged."""
        from fastapi import HTTPException

        from backend.api.utils.errors import handle_api_errors

        @handle_api_errors("test operation")
        async def test_endpoint():
            raise HTTPException(status_code=404, detail="Not found")

        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint()

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"

    @pytest.mark.asyncio
    async def test_handle_api_errors_value_error_returns_400(self):
        """Test that ValueError returns 400."""
        from fastapi import HTTPException

        from backend.api.utils.errors import handle_api_errors

        @handle_api_errors("test operation")
        async def test_endpoint():
            raise ValueError("Invalid input")

        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint()

        assert exc_info.value.status_code == 400
        assert "validation_error" in exc_info.value.detail["error_code"]

    @pytest.mark.asyncio
    async def test_handle_api_errors_generic_exception_returns_500(self):
        """Test that generic Exception returns 500."""
        from fastapi import HTTPException

        from backend.api.utils.errors import handle_api_errors

        @handle_api_errors("test operation")
        async def test_endpoint():
            raise RuntimeError("Something went wrong")

        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint()

        assert exc_info.value.status_code == 500
        assert "internal_error" in exc_info.value.detail["error_code"]


class TestManagedCompetitorAPI:
    """Integration tests for managed competitor API endpoints."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user dict as returned by get_current_user."""
        return {
            "user_id": "test-user-123",
            "email": "test@example.com",
            "auth_provider": "email",
            "subscription_tier": "free",
        }

    @pytest.mark.asyncio
    async def test_add_competitor_returns_success(self, mock_user):
        """Test POST /api/v1/context/managed-competitors returns 200 with valid request."""
        from backend.api.context.models import ManagedCompetitorCreate
        from backend.api.context.routes import add_managed_competitor

        request = ManagedCompetitorCreate(
            name="TestCompetitor",
            url="https://testcompetitor.com",
            notes="Test competitor for integration testing",
        )

        with (
            patch("backend.api.context.routes.user_repository.add_managed_competitor") as mock_add,
            patch("backend.api.context.routes.user_repository.get_context") as mock_context,
        ):
            mock_add.return_value = {
                "name": "TestCompetitor",
                "url": "https://testcompetitor.com",
                "notes": "Test competitor for integration testing",
                "added_at": "2025-01-01T00:00:00Z",
            }
            mock_context.return_value = None  # Skip skeptic check

            response = await add_managed_competitor(request=request, user=mock_user)

            assert response.success is True
            assert response.competitor is not None
            assert response.competitor.name == "TestCompetitor"
            assert response.competitor.url == "https://testcompetitor.com"
            assert response.competitor.notes == "Test competitor for integration testing"
            mock_add.assert_called_once_with(
                user_id="test-user-123",
                name="TestCompetitor",
                url="https://testcompetitor.com",
                notes="Test competitor for integration testing",
            )

    @pytest.mark.asyncio
    async def test_add_competitor_with_url_and_notes(self, mock_user):
        """Test all fields are persisted correctly."""
        from backend.api.context.models import ManagedCompetitorCreate
        from backend.api.context.routes import add_managed_competitor

        request = ManagedCompetitorCreate(
            name="FullDataCompetitor",
            url="https://full.example.com/path",
            notes="Detailed notes about this competitor including strategy insights",
        )

        with (
            patch("backend.api.context.routes.user_repository.add_managed_competitor") as mock_add,
            patch("backend.api.context.routes.user_repository.get_context") as mock_context,
        ):
            mock_add.return_value = {
                "name": "FullDataCompetitor",
                "url": "https://full.example.com/path",
                "notes": "Detailed notes about this competitor including strategy insights",
                "added_at": "2025-01-02T12:30:00Z",
            }
            mock_context.return_value = None

            response = await add_managed_competitor(request=request, user=mock_user)

            assert response.success is True
            assert response.competitor.url == "https://full.example.com/path"
            assert "strategy insights" in response.competitor.notes

    @pytest.mark.asyncio
    async def test_add_duplicate_competitor_returns_409(self, mock_user):
        """Test that adding a duplicate competitor (case-insensitive) returns 409."""
        from fastapi import HTTPException

        from backend.api.context.models import ManagedCompetitorCreate
        from backend.api.context.routes import add_managed_competitor

        request = ManagedCompetitorCreate(name="ExistingCompetitor")

        with patch("backend.api.context.routes.user_repository.add_managed_competitor") as mock_add:
            mock_add.return_value = None  # Indicates duplicate

            with pytest.raises(HTTPException) as exc_info:
                await add_managed_competitor(request=request, user=mock_user)

            assert exc_info.value.status_code == 409
            assert "already exists" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_add_competitor_skeptic_failure_still_succeeds(self, mock_user):
        """Test that skeptic check failure doesn't block competitor addition."""
        from backend.api.context.models import ManagedCompetitorCreate
        from backend.api.context.routes import add_managed_competitor

        request = ManagedCompetitorCreate(name="SkepticTestCompetitor")

        with (
            patch("backend.api.context.routes.user_repository.add_managed_competitor") as mock_add,
            patch("backend.api.context.routes.user_repository.get_context") as mock_context,
            patch("backend.api.context.routes.evaluate_competitor_relevance") as mock_skeptic,
        ):
            mock_add.return_value = {
                "name": "SkepticTestCompetitor",
                "url": None,
                "notes": None,
                "added_at": "2025-01-03T00:00:00Z",
            }
            mock_context.return_value = {"business_name": "Test Business"}
            # Skeptic check fails with exception
            mock_skeptic.side_effect = Exception("LLM API timeout")

            response = await add_managed_competitor(request=request, user=mock_user)

            # Competitor should still be added successfully
            assert response.success is True
            assert response.competitor is not None
            assert response.competitor.name == "SkepticTestCompetitor"
            # Relevance fields should be None since check failed
            assert response.relevance_score is None
            assert response.relevance_warning is None

    @pytest.mark.asyncio
    async def test_add_competitor_with_skeptic_warning(self, mock_user):
        """Test that relevance warning is returned when skeptic flags low relevance."""
        from unittest.mock import AsyncMock, MagicMock

        from backend.api.context.models import ManagedCompetitorCreate
        from backend.api.context.routes import add_managed_competitor

        request = ManagedCompetitorCreate(name="WeakCompetitor")

        with (
            patch("backend.api.context.routes.user_repository.add_managed_competitor") as mock_add,
            patch("backend.api.context.routes.user_repository.get_context") as mock_context,
            patch(
                "backend.api.context.routes.evaluate_competitor_relevance",
                new_callable=AsyncMock,
            ) as mock_skeptic,
        ):
            mock_add.return_value = {
                "name": "WeakCompetitor",
                "url": None,
                "notes": None,
                "added_at": "2025-01-03T00:00:00Z",
            }
            mock_context.return_value = {"business_name": "Test Business"}
            # Skeptic returns low relevance
            mock_result = MagicMock()
            mock_result.relevance_score = 0.25
            mock_result.relevance_warning = "Low relevance: different industry"
            mock_skeptic.return_value = mock_result

            response = await add_managed_competitor(request=request, user=mock_user)

            assert response.success is True
            assert response.relevance_score == 0.25
            assert response.relevance_warning == "Low relevance: different industry"
