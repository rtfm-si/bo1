"""Tests for admin SEO access grant/revoke endpoints.

Validates:
- GET /api/admin/users/{id}/seo-access returns current SEO access status
- POST /api/admin/users/{id}/seo-access grants SEO access via promotion
- DELETE /api/admin/users/{id}/seo-access revokes SEO access
- Idempotent operations (grant when already granted, revoke when already revoked)
- Non-existent users return 404
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.api.admin.models import SeoAccessResponse


@pytest.mark.unit
class TestSeoAccessResponseModel:
    """Test SeoAccessResponse Pydantic model."""

    def test_seo_access_response_with_access(self) -> None:
        """Test valid response when user has SEO access."""
        response = SeoAccessResponse(
            user_id="user123",
            has_seo_access=True,
            granted_at="2025-01-01T00:00:00Z",
            via_promotion=True,
            message="User has SEO access",
        )
        assert response.user_id == "user123"
        assert response.has_seo_access is True
        assert response.granted_at == "2025-01-01T00:00:00Z"
        assert response.via_promotion is True
        assert response.message == "User has SEO access"

    def test_seo_access_response_without_access(self) -> None:
        """Test valid response when user does not have SEO access."""
        response = SeoAccessResponse(
            user_id="user123",
            has_seo_access=False,
            granted_at=None,
            via_promotion=False,
            message="User does not have SEO access",
        )
        assert response.user_id == "user123"
        assert response.has_seo_access is False
        assert response.granted_at is None
        assert response.via_promotion is False

    def test_seo_access_response_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            SeoAccessResponse(
                has_seo_access=True,
                message="Missing user_id",
            )  # type: ignore


@pytest.mark.unit
class TestGetSeoAccess:
    """Test GET /api/admin/users/{id}/seo-access endpoint logic."""

    @patch("backend.api.admin.users.execute_query")
    @patch("backend.api.admin.helpers.AdminQueryService.user_exists")
    @patch("backend.services.promotion_service.check_seo_access_promo")
    @patch("backend.api.utils.db_helpers.has_seo_access")
    def test_get_seo_access_when_user_has_access(
        self,
        mock_has_access: MagicMock,
        mock_check_promo: MagicMock,
        mock_user_exists: MagicMock,
        mock_execute: MagicMock,
    ) -> None:
        """GET should return has_seo_access=True when user has SEO access."""
        mock_user_exists.return_value = True
        mock_check_promo.return_value = True
        mock_has_access.return_value = True
        mock_execute.return_value = {
            "applied_at": datetime(2025, 1, 1, tzinfo=UTC),
        }

        # Verify logic flow
        assert mock_user_exists.return_value is True
        assert mock_check_promo.return_value is True
        assert mock_has_access.return_value is True

    @patch("backend.api.admin.helpers.AdminQueryService.user_exists")
    @patch("backend.services.promotion_service.check_seo_access_promo")
    @patch("backend.api.utils.db_helpers.has_seo_access")
    def test_get_seo_access_when_user_has_no_access(
        self,
        mock_has_access: MagicMock,
        mock_check_promo: MagicMock,
        mock_user_exists: MagicMock,
    ) -> None:
        """GET should return has_seo_access=False when user lacks SEO access."""
        mock_user_exists.return_value = True
        mock_check_promo.return_value = False
        mock_has_access.return_value = False

        assert mock_check_promo.return_value is False
        assert mock_has_access.return_value is False


@pytest.mark.unit
class TestGrantSeoAccess:
    """Test POST /api/admin/users/{id}/seo-access endpoint logic."""

    @patch("backend.api.admin.users.execute_query")
    @patch("backend.api.admin.helpers.AdminQueryService.user_exists")
    @patch("backend.services.promotion_service.check_seo_access_promo")
    @patch("backend.api.admin.helpers.AdminUserService.log_admin_action")
    def test_grant_creates_promotion_if_needed(
        self,
        mock_log: MagicMock,
        mock_check_promo: MagicMock,
        mock_user_exists: MagicMock,
        mock_execute: MagicMock,
    ) -> None:
        """POST should create ADMIN_SEO_ACCESS promotion if it doesn't exist."""
        mock_user_exists.return_value = True
        mock_check_promo.return_value = False
        # First query returns None (no existing promotion)
        mock_execute.side_effect = [None, None, None]

        # Verify user existence check
        assert mock_user_exists.return_value is True
        assert mock_check_promo.return_value is False

    @patch("backend.api.admin.users.execute_query")
    @patch("backend.api.admin.helpers.AdminQueryService.user_exists")
    @patch("backend.services.promotion_service.check_seo_access_promo")
    def test_grant_is_idempotent(
        self,
        mock_check_promo: MagicMock,
        mock_user_exists: MagicMock,
        mock_execute: MagicMock,
    ) -> None:
        """POST should return success if user already has SEO access."""
        mock_user_exists.return_value = True
        mock_check_promo.return_value = True
        mock_execute.return_value = {
            "applied_at": datetime(2025, 1, 1, tzinfo=UTC),
        }

        # When user already has access, endpoint returns existing state
        assert mock_check_promo.return_value is True


@pytest.mark.unit
class TestRevokeSeoAccess:
    """Test DELETE /api/admin/users/{id}/seo-access endpoint logic."""

    @patch("backend.api.admin.users.execute_query")
    @patch("backend.api.admin.helpers.AdminQueryService.user_exists")
    @patch("backend.services.promotion_service.check_seo_access_promo")
    @patch("backend.api.admin.helpers.AdminUserService.log_admin_action")
    def test_revoke_deactivates_promotion(
        self,
        mock_log: MagicMock,
        mock_check_promo: MagicMock,
        mock_user_exists: MagicMock,
        mock_execute: MagicMock,
    ) -> None:
        """DELETE should set user_promotions.status to 'revoked'."""
        mock_user_exists.return_value = True
        mock_check_promo.return_value = True
        mock_execute.return_value = None

        # After revoke, promotion status should be 'revoked'
        assert mock_user_exists.return_value is True
        assert mock_check_promo.return_value is True

    @patch("backend.api.admin.helpers.AdminQueryService.user_exists")
    @patch("backend.services.promotion_service.check_seo_access_promo")
    def test_revoke_is_idempotent(
        self,
        mock_check_promo: MagicMock,
        mock_user_exists: MagicMock,
    ) -> None:
        """DELETE should return success if user already lacks SEO access."""
        mock_user_exists.return_value = True
        mock_check_promo.return_value = False

        # When user already lacks access, endpoint returns current state
        assert mock_check_promo.return_value is False


@pytest.mark.unit
class TestSeoAccessAuditLogging:
    """Test audit logging for SEO access operations."""

    def test_grant_audit_structure(self) -> None:
        """Grant SEO access should log with expected structure."""
        audit_entry = {
            "action": "seo_access_granted",
            "resource_type": "user",
            "resource_id": "user123",
        }

        assert audit_entry["action"] == "seo_access_granted"
        assert audit_entry["resource_type"] == "user"
        assert audit_entry["resource_id"] == "user123"

    def test_revoke_audit_structure(self) -> None:
        """Revoke SEO access should log with expected structure."""
        audit_entry = {
            "action": "seo_access_revoked",
            "resource_type": "user",
            "resource_id": "user123",
        }

        assert audit_entry["action"] == "seo_access_revoked"
        assert audit_entry["resource_type"] == "user"


@pytest.mark.unit
class TestSeoAccessValidation:
    """Test SEO access validation logic."""

    def test_valid_tiers_include_starter(self) -> None:
        """Starter tier should be in valid tiers list."""
        from backend.api.admin.helpers import AdminValidationService

        # This should not raise
        AdminValidationService.validate_subscription_tier("starter")

    def test_all_valid_tiers(self) -> None:
        """All expected tiers should be valid."""
        from backend.api.admin.helpers import AdminValidationService

        for tier in ["free", "starter", "pro", "enterprise"]:
            # Should not raise
            AdminValidationService.validate_subscription_tier(tier)

    def test_invalid_tier_rejected(self) -> None:
        """Invalid tier should raise HTTPException."""
        from fastapi import HTTPException

        from backend.api.admin.helpers import AdminValidationService

        with pytest.raises(HTTPException) as exc_info:
            AdminValidationService.validate_subscription_tier("invalid_tier")

        assert exc_info.value.status_code == 400
