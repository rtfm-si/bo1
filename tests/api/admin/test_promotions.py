"""Tests for admin promotions API endpoints.

Tests:
- POST /api/admin/promotions/apply - Apply promo to user
- DELETE /api/admin/promotions/user/{user_promotion_id} - Remove user promo
- GET /api/admin/promotions/users - List users with promotions
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.admin.promotions import router
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import limiter


def mock_admin_override():
    """Override admin auth to always succeed."""
    return "admin-user-id"


@pytest.fixture
def app():
    """Create test app with promotions router and admin auth override."""
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


class TestApplyPromoToUser:
    """Tests for POST /api/admin/promotions/apply."""

    def test_requires_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.post(
            "/api/admin/promotions/apply",
            json={"user_id": "user-123", "code": "TEST10"},
        )
        assert response.status_code == 403

    def test_apply_promo_successfully(self, client: TestClient):
        """Admin should be able to apply promo to user."""
        with patch("backend.api.admin.promotions.validate_and_apply_code") as mock_apply:
            mock_apply.return_value = {
                "id": "user-promo-123",
                "promotion": {"code": "TEST10"},
            }

            response = client.post(
                "/api/admin/promotions/apply",
                json={"user_id": "user-123", "code": "TEST10"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "applied"
            assert data["user_id"] == "user-123"
            assert data["user_promotion_id"] == "user-promo-123"
            assert data["promotion_code"] == "TEST10"

    def test_apply_promo_validation_error(self, client: TestClient):
        """Invalid promo code should return 400."""
        from backend.services.promotion_service import PromoValidationError

        with patch("backend.api.admin.promotions.validate_and_apply_code") as mock_apply:
            mock_apply.side_effect = PromoValidationError("Promo code not found", "not_found")

            response = client.post(
                "/api/admin/promotions/apply",
                json={"user_id": "user-123", "code": "INVALID"},
            )

            assert response.status_code == 400
            data = response.json()
            assert "not_found" in str(data["detail"])


class TestRemoveUserPromotion:
    """Tests for DELETE /api/admin/promotions/user/{user_promotion_id}."""

    def test_requires_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.delete("/api/admin/promotions/user/user-promo-123")
        assert response.status_code == 403

    def test_remove_promo_successfully(self, client: TestClient):
        """Admin should be able to remove user promo."""
        with patch("backend.api.admin.promotions.promotion_repository") as mock_repo:
            mock_repo.remove_user_promotion.return_value = True

            response = client.delete("/api/admin/promotions/user/user-promo-123")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "removed"
            assert data["user_promotion_id"] == "user-promo-123"

    def test_remove_promo_not_found(self, client: TestClient):
        """Removing non-existent promo should return 404."""
        with patch("backend.api.admin.promotions.promotion_repository") as mock_repo:
            mock_repo.remove_user_promotion.return_value = False

            response = client.delete("/api/admin/promotions/user/nonexistent-promo")

            assert response.status_code == 404


class TestListUsersWithPromotions:
    """Tests for GET /api/admin/promotions/users."""

    def test_requires_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.get("/api/admin/promotions/users")
        assert response.status_code == 403

    def test_list_users_empty(self, client: TestClient):
        """Should return empty list when no users have promos."""
        with patch("backend.api.admin.promotions.promotion_repository") as mock_repo:
            mock_repo.get_users_with_promotions.return_value = []

            response = client.get("/api/admin/promotions/users")

            assert response.status_code == 200
            data = response.json()
            assert data == []

    def test_list_users_with_promos(self, client: TestClient):
        """Should return users with their active promotions."""
        now = datetime.now(UTC)
        with patch("backend.api.admin.promotions.promotion_repository") as mock_repo:
            mock_repo.get_users_with_promotions.return_value = [
                {
                    "user_id": "user-123",
                    "email": "user@example.com",
                    "promotions": [
                        {
                            "id": "user-promo-1",
                            "promotion_id": "promo-1",
                            "promotion_code": "TEST10",
                            "promotion_type": "percentage_discount",
                            "promotion_value": 10.0,
                            "status": "active",
                            "applied_at": now.isoformat(),
                            "deliberations_remaining": None,
                            "discount_applied": 10.0,
                        }
                    ],
                }
            ]

            response = client.get("/api/admin/promotions/users")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["user_id"] == "user-123"
            assert data[0]["email"] == "user@example.com"
            assert len(data[0]["promotions"]) == 1
            assert data[0]["promotions"][0]["promotion_code"] == "TEST10"
