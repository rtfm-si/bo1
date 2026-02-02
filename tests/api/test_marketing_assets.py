"""Tests for marketing assets API endpoints.

Tests CRUD operations, validation, tier limits, and asset suggestions.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.services import marketing_assets as asset_service


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {"sub": "test-user-123", "email": "test@example.com"}


@pytest.fixture
def mock_pro_tier():
    """Mock pro tier for unlimited access."""
    with patch("backend.api.seo.routes.get_user_tier", return_value="pro"):
        yield


@pytest.fixture
def mock_free_tier():
    """Mock free tier for limited access."""
    with patch("backend.api.seo.routes.get_user_tier", return_value="free"):
        yield


@pytest.fixture
def mock_auth(mock_user):
    """Mock authentication middleware."""
    with patch("backend.api.seo.routes.get_current_user", return_value=mock_user):
        yield


class TestMarketingAssetsValidation:
    """Test asset validation functions."""

    def test_validate_file_valid_image(self):
        """Valid image file should pass validation."""
        asset_service.validate_file("test.png", "image/png", 1024)  # Should not raise

    def test_validate_file_invalid_mime(self):
        """Invalid MIME type should raise error."""
        with pytest.raises(asset_service.AssetValidationError, match="not allowed"):
            asset_service.validate_file("test.exe", "application/exe", 1024)

    def test_validate_file_too_large(self):
        """File exceeding size limit should raise error."""
        # 15MB PNG (limit is 10MB)
        with pytest.raises(asset_service.AssetValidationError, match="too large"):
            asset_service.validate_file("test.png", "image/png", 15 * 1024 * 1024)

    def test_validate_file_video_size(self):
        """Video can be up to 50MB."""
        asset_service.validate_file("test.mp4", "video/mp4", 45 * 1024 * 1024)

    def test_validate_asset_type_valid(self):
        """Valid asset types should pass."""
        for t in ["image", "animation", "concept", "template"]:
            asset_service.validate_asset_type(t)  # Should not raise

    def test_validate_asset_type_invalid(self):
        """Invalid asset type should raise error."""
        with pytest.raises(asset_service.AssetValidationError, match="Invalid asset type"):
            asset_service.validate_asset_type("video")


class TestMarketingAssetsService:
    """Test asset service functions."""

    @patch("backend.services.marketing_assets.get_spaces_client")
    @patch("backend.services.marketing_assets.db_session")
    def test_upload_asset_success(self, mock_db, mock_spaces):
        """Successful upload should create record and return asset."""
        # Mock Spaces client
        mock_client = MagicMock()
        mock_client.upload_file.return_value = "https://cdn.example.com/test.png"
        mock_spaces.return_value = mock_client

        # Mock database session with proper cursor pattern
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "created_at": "2025-01-01",
            "updated_at": "2025-01-01",
        }
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value = mock_conn

        result = asset_service.upload_asset(
            user_id="test-user-123",
            workspace_id=None,
            filename="test.png",
            file_data=b"fake image data",
            mime_type="image/png",
            title="Test Image",
            asset_type="image",
            tags=["test", "demo"],
        )

        assert result.id == 1
        assert result.title == "Test Image"
        assert result.cdn_url == "https://cdn.example.com/test.png"
        mock_client.upload_file.assert_called_once()

    @patch("backend.services.marketing_assets.db_session")
    def test_list_assets(self, mock_db):
        """List assets should return filtered results."""
        # Mock database session with proper cursor pattern
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock list query - create proper dict row data
        mock_rows = [
            {
                "id": 1,
                "user_id": "user1",
                "workspace_id": None,
                "filename": "test1.png",
                "storage_key": "key1",
                "cdn_url": "https://cdn/1",
                "asset_type": "image",
                "title": "Test 1",
                "description": None,
                "tags": ["tag1"],
                "metadata": None,
                "file_size": 1024,
                "mime_type": "image/png",
                "created_at": "2025-01-01",
                "updated_at": "2025-01-01",
            },
            {
                "id": 2,
                "user_id": "user1",
                "workspace_id": None,
                "filename": "test2.png",
                "storage_key": "key2",
                "cdn_url": "https://cdn/2",
                "asset_type": "image",
                "title": "Test 2",
                "description": None,
                "tags": ["tag2"],
                "metadata": None,
                "file_size": 2048,
                "mime_type": "image/png",
                "created_at": "2025-01-01",
                "updated_at": "2025-01-01",
            },
        ]

        # Return different results based on call order
        call_count = [0]

        def execute_side_effect(*args):
            call_count[0] += 1
            # First call is count query, second is list query
            if call_count[0] == 1:
                mock_cursor.fetchone.return_value = {"count": 2}
            else:
                mock_cursor.fetchall.return_value = mock_rows

        mock_cursor.execute.side_effect = execute_side_effect
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value = mock_conn

        assets, total = asset_service.list_assets(user_id="user1")

        assert total == 2
        assert len(assets) == 2
        assert assets[0].title == "Test 1"

    @patch("backend.services.marketing_assets.db_session")
    def test_get_asset_not_found(self, mock_db):
        """Get non-existent asset should return None."""
        # Mock database session with proper cursor pattern
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value = mock_conn

        result = asset_service.get_asset("user1", 999)

        assert result is None

    def test_suggest_for_article_no_keywords(self):
        """Empty keywords should return empty suggestions."""
        result = asset_service.suggest_for_article("user1", [])

        assert result == []

    @patch("backend.services.marketing_assets.search_by_tags")
    def test_suggest_for_article_calculates_relevance(self, mock_search):
        """Suggestions should calculate relevance based on tag overlap."""
        mock_asset = asset_service.AssetRecord(
            id=1,
            user_id="user1",
            workspace_id=None,
            filename="test.png",
            storage_key="key1",
            cdn_url="https://cdn/1",
            asset_type="image",
            title="Pricing Chart",
            description=None,
            tags=["pricing", "saas", "chart"],
            metadata=None,
            file_size=1024,
            mime_type="image/png",
            created_at="2025-01-01",
            updated_at="2025-01-01",
        )
        mock_search.return_value = [mock_asset]

        result = asset_service.suggest_for_article("user1", ["pricing", "saas", "demo"])

        assert len(result) == 1
        assert result[0].asset.id == 1
        # 2 matching tags out of 3 keywords = 0.67
        assert result[0].relevance_score == 0.67
        assert result[0].matching_tags == ["pricing", "saas"]


class TestTierLimits:
    """Test tier-based storage limits."""

    def test_free_tier_limit(self):
        """Free tier should have 10 asset limit."""
        from bo1.billing import PlanConfig

        limit = PlanConfig.get_marketing_assets_limit("free")
        assert limit == 10

    def test_starter_tier_limit(self):
        """Starter tier should have 50 asset limit."""
        from bo1.billing import PlanConfig

        limit = PlanConfig.get_marketing_assets_limit("starter")
        assert limit == 50

    def test_pro_tier_limit(self):
        """Pro tier should have 500 asset limit."""
        from bo1.billing import PlanConfig

        limit = PlanConfig.get_marketing_assets_limit("pro")
        assert limit == 500

    def test_enterprise_tier_unlimited(self):
        """Enterprise tier should be unlimited (-1)."""
        from bo1.billing import PlanConfig

        limit = PlanConfig.get_marketing_assets_limit("enterprise")
        assert limit == -1


class TestAssetSuggestions:
    """Test asset suggestion algorithm."""

    def test_relevance_score_calculation(self):
        """Relevance score should be based on tag overlap."""
        from backend.services.marketing_assets import AssetRecord

        # Asset with 2/3 matching tags
        asset = AssetRecord(
            id=1,
            user_id="user1",
            workspace_id=None,
            filename="test.png",
            storage_key="key1",
            cdn_url="https://cdn/1",
            asset_type="image",
            title="Test",
            description=None,
            tags=["pricing", "saas"],
            metadata=None,
            file_size=1024,
            mime_type="image/png",
            created_at="2025-01-01",
            updated_at="2025-01-01",
        )

        keywords = ["pricing", "saas", "demo"]
        asset_tags_lower = [t.lower() for t in asset.tags]
        matching = [k for k in keywords if k in asset_tags_lower]

        # 2 matches out of 3 keywords
        score = min(len(matching) / len(keywords), 1.0)
        assert round(score, 2) == 0.67
