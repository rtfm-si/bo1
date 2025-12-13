"""Unit tests for promotions Pydantic models and service.

Tests validation logic for:
- Promotion response model
- UserPromotion response model
- AddPromotionRequest (admin)
- ApplyPromoCodeRequest (user)
- PromotionService functions
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.api.models import (
    AddPromotionRequest,
    ApplyPromoCodeRequest,
    Promotion,
    PromotionType,
    UserPromotion,
    UserPromotionStatus,
)


class TestPromotionType:
    """Tests for PromotionType constants."""

    def test_valid_types(self):
        """Verify all valid promotion types."""
        assert PromotionType.GOODWILL_CREDITS == "goodwill_credits"
        assert PromotionType.PERCENTAGE_DISCOUNT == "percentage_discount"
        assert PromotionType.FLAT_DISCOUNT == "flat_discount"
        assert PromotionType.EXTRA_DELIBERATIONS == "extra_deliberations"


class TestUserPromotionStatus:
    """Tests for UserPromotionStatus constants."""

    def test_valid_statuses(self):
        """Verify all valid statuses."""
        assert UserPromotionStatus.ACTIVE == "active"
        assert UserPromotionStatus.EXHAUSTED == "exhausted"
        assert UserPromotionStatus.EXPIRED == "expired"


class TestPromotion:
    """Tests for Promotion response model."""

    @pytest.fixture
    def valid_promotion_data(self):
        """Valid promotion data."""
        return {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "code": "WELCOME10",
            "type": "percentage_discount",
            "value": 10.0,
            "max_uses": 1000,
            "uses_count": 42,
            "expires_at": None,
            "created_at": datetime.now(UTC),
            "is_active": True,
        }

    def test_valid_promotion(self, valid_promotion_data):
        """Valid promotion data should pass validation."""
        promo = Promotion(**valid_promotion_data)
        assert promo.code == "WELCOME10"
        assert promo.type == "percentage_discount"
        assert promo.value == 10.0

    def test_all_valid_types(self, valid_promotion_data):
        """All valid promotion types should pass."""
        for promo_type in [
            "goodwill_credits",
            "percentage_discount",
            "flat_discount",
            "extra_deliberations",
        ]:
            data = {**valid_promotion_data, "type": promo_type}
            promo = Promotion(**data)
            assert promo.type == promo_type

    def test_invalid_type_rejected(self, valid_promotion_data):
        """Invalid promotion type should be rejected."""
        data = {**valid_promotion_data, "type": "invalid_type"}
        with pytest.raises(ValidationError) as exc_info:
            Promotion(**data)
        assert "Invalid promotion type" in str(exc_info.value)

    def test_code_min_length(self, valid_promotion_data):
        """Code must be at least 3 characters."""
        data = {**valid_promotion_data, "code": "AB"}
        with pytest.raises(ValidationError) as exc_info:
            Promotion(**data)
        assert "String should have at least 3 characters" in str(exc_info.value)

    def test_code_max_length(self, valid_promotion_data):
        """Code must be at most 50 characters."""
        data = {**valid_promotion_data, "code": "A" * 51}
        with pytest.raises(ValidationError) as exc_info:
            Promotion(**data)
        assert "String should have at most 50 characters" in str(exc_info.value)

    def test_value_must_be_positive(self, valid_promotion_data):
        """Value must be greater than 0."""
        data = {**valid_promotion_data, "value": 0}
        with pytest.raises(ValidationError) as exc_info:
            Promotion(**data)
        assert "greater than 0" in str(exc_info.value)

        data = {**valid_promotion_data, "value": -5}
        with pytest.raises(ValidationError) as exc_info:
            Promotion(**data)
        assert "greater than 0" in str(exc_info.value)

    def test_uses_count_must_be_non_negative(self, valid_promotion_data):
        """Uses count cannot be negative."""
        data = {**valid_promotion_data, "uses_count": -1}
        with pytest.raises(ValidationError) as exc_info:
            Promotion(**data)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_nullable_fields(self, valid_promotion_data):
        """max_uses and expires_at can be None."""
        data = {**valid_promotion_data, "max_uses": None, "expires_at": None}
        promo = Promotion(**data)
        assert promo.max_uses is None
        assert promo.expires_at is None


class TestUserPromotion:
    """Tests for UserPromotion response model."""

    @pytest.fixture
    def valid_user_promo_data(self):
        """Valid user promotion data."""
        return {
            "id": "660e8400-e29b-41d4-a716-446655440001",
            "promotion": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "code": "GOODWILL5",
                "type": "extra_deliberations",
                "value": 5.0,
                "max_uses": None,
                "uses_count": 100,
                "expires_at": None,
                "created_at": datetime.now(UTC),
                "is_active": True,
            },
            "applied_at": datetime.now(UTC),
            "deliberations_remaining": 3,
            "discount_applied": None,
            "status": "active",
        }

    def test_valid_user_promotion(self, valid_user_promo_data):
        """Valid user promotion data should pass validation."""
        user_promo = UserPromotion(**valid_user_promo_data)
        assert user_promo.status == "active"
        assert user_promo.deliberations_remaining == 3
        assert user_promo.promotion.code == "GOODWILL5"

    def test_all_valid_statuses(self, valid_user_promo_data):
        """All valid statuses should pass."""
        for status in ["active", "exhausted", "expired"]:
            data = {**valid_user_promo_data, "status": status}
            user_promo = UserPromotion(**data)
            assert user_promo.status == status

    def test_invalid_status_rejected(self, valid_user_promo_data):
        """Invalid status should be rejected."""
        data = {**valid_user_promo_data, "status": "cancelled"}
        with pytest.raises(ValidationError) as exc_info:
            UserPromotion(**data)
        assert "Invalid status" in str(exc_info.value)

    def test_nullable_fields(self, valid_user_promo_data):
        """deliberations_remaining and discount_applied can be None."""
        data = {
            **valid_user_promo_data,
            "deliberations_remaining": None,
            "discount_applied": None,
        }
        user_promo = UserPromotion(**data)
        assert user_promo.deliberations_remaining is None
        assert user_promo.discount_applied is None


class TestAddPromotionRequest:
    """Tests for AddPromotionRequest (admin)."""

    @pytest.fixture
    def valid_add_promo_data(self):
        """Valid add promotion request data."""
        return {
            "code": "SUMMER2025",
            "type": "percentage_discount",
            "value": 20.0,
            "max_uses": 500,
            "expires_at": datetime(2025, 8, 31, 23, 59, 59, tzinfo=UTC),
        }

    def test_valid_request(self, valid_add_promo_data):
        """Valid request should pass validation."""
        req = AddPromotionRequest(**valid_add_promo_data)
        assert req.code == "SUMMER2025"
        assert req.type == "percentage_discount"
        assert req.value == 20.0

    def test_code_pattern_uppercase_alphanumeric(self, valid_add_promo_data):
        """Code must be uppercase alphanumeric + underscore."""
        # Valid patterns
        for code in ["ABC123", "TEST_CODE", "PROMO_2025"]:
            data = {**valid_add_promo_data, "code": code}
            req = AddPromotionRequest(**data)
            assert req.code == code

    def test_code_pattern_rejects_lowercase(self, valid_add_promo_data):
        """Lowercase codes should be rejected."""
        data = {**valid_add_promo_data, "code": "lowercase"}
        with pytest.raises(ValidationError) as exc_info:
            AddPromotionRequest(**data)
        assert "String should match pattern" in str(exc_info.value)

    def test_code_pattern_rejects_special_chars(self, valid_add_promo_data):
        """Special characters (except underscore) should be rejected."""
        for code in ["PROMO-2025", "PROMO.CODE", "PROMO@TEST"]:
            data = {**valid_add_promo_data, "code": code}
            with pytest.raises(ValidationError) as exc_info:
                AddPromotionRequest(**data)
            assert "String should match pattern" in str(exc_info.value)

    def test_invalid_type_rejected(self, valid_add_promo_data):
        """Invalid promotion type should be rejected."""
        data = {**valid_add_promo_data, "type": "free_stuff"}
        with pytest.raises(ValidationError) as exc_info:
            AddPromotionRequest(**data)
        assert "Invalid promotion type" in str(exc_info.value)

    def test_value_must_be_positive(self, valid_add_promo_data):
        """Value must be greater than 0."""
        data = {**valid_add_promo_data, "value": 0}
        with pytest.raises(ValidationError) as exc_info:
            AddPromotionRequest(**data)
        assert "greater than 0" in str(exc_info.value)

    def test_max_uses_must_be_positive_if_set(self, valid_add_promo_data):
        """max_uses must be positive if provided."""
        data = {**valid_add_promo_data, "max_uses": 0}
        with pytest.raises(ValidationError) as exc_info:
            AddPromotionRequest(**data)
        assert "greater than 0" in str(exc_info.value)

    def test_nullable_optional_fields(self, valid_add_promo_data):
        """max_uses and expires_at are optional."""
        data = {
            "code": "BASIC",
            "type": "percentage_discount",
            "value": 10.0,
        }
        req = AddPromotionRequest(**data)
        assert req.max_uses is None
        assert req.expires_at is None


class TestApplyPromoCodeRequest:
    """Tests for ApplyPromoCodeRequest (user)."""

    def test_valid_request(self):
        """Valid request should pass validation."""
        req = ApplyPromoCodeRequest(code="WELCOME10")
        assert req.code == "WELCOME10"

    def test_code_normalized_to_uppercase(self):
        """Code should be normalized to uppercase."""
        req = ApplyPromoCodeRequest(code="welcome10")
        assert req.code == "WELCOME10"

    def test_code_whitespace_trimmed(self):
        """Whitespace should be trimmed."""
        req = ApplyPromoCodeRequest(code="  PROMO123  ")
        assert req.code == "PROMO123"

    def test_code_min_length(self):
        """Code must be at least 3 characters."""
        with pytest.raises(ValidationError) as exc_info:
            ApplyPromoCodeRequest(code="AB")
        assert "String should have at least 3 characters" in str(exc_info.value)

    def test_code_max_length(self):
        """Code must be at most 50 characters."""
        with pytest.raises(ValidationError) as exc_info:
            ApplyPromoCodeRequest(code="A" * 51)
        assert "String should have at most 50 characters" in str(exc_info.value)

    def test_empty_code_rejected(self):
        """Empty code (after trim) should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ApplyPromoCodeRequest(code="   ")
        # Either min_length or custom validator catches this
        assert "cannot be empty" in str(exc_info.value) or "at least 3" in str(exc_info.value)

    def test_special_chars_rejected(self):
        """Special characters should be rejected."""
        for code in ["PROMO-123", "PROMO.CODE", "PROMO@TEST", "PROMO CODE"]:
            with pytest.raises(ValidationError) as exc_info:
                ApplyPromoCodeRequest(code=code)
            assert "alphanumeric" in str(exc_info.value)

    def test_underscore_allowed(self):
        """Underscore should be allowed."""
        req = ApplyPromoCodeRequest(code="PROMO_CODE_123")
        assert req.code == "PROMO_CODE_123"


class TestAllowanceResult:
    """Tests for AllowanceResult dataclass."""

    def test_allowance_result_with_credits(self):
        """AllowanceResult should reflect credits correctly."""
        from backend.services.promotion_service import AllowanceResult

        result = AllowanceResult(
            total_remaining=10,
            active_promos=["promo-1", "promo-2"],
            has_credits=True,
        )
        assert result.total_remaining == 10
        assert len(result.active_promos) == 2
        assert result.has_credits is True

    def test_allowance_result_no_credits(self):
        """AllowanceResult should handle zero credits."""
        from backend.services.promotion_service import AllowanceResult

        result = AllowanceResult(
            total_remaining=0,
            active_promos=[],
            has_credits=False,
        )
        assert result.total_remaining == 0
        assert result.has_credits is False


class TestInvoiceResult:
    """Tests for InvoiceResult dataclass."""

    def test_invoice_result_with_discount(self):
        """InvoiceResult should calculate discount correctly."""
        from backend.services.promotion_service import InvoiceResult

        result = InvoiceResult(
            base_amount=100.0,
            final_amount=75.0,
            total_discount=25.0,
            applied_promotions=[("promo-1", 25.0)],
        )
        assert result.base_amount == 100.0
        assert result.final_amount == 75.0
        assert result.total_discount == 25.0
        assert len(result.applied_promotions) == 1

    def test_invoice_result_no_discount(self):
        """InvoiceResult should handle no discounts."""
        from backend.services.promotion_service import InvoiceResult

        result = InvoiceResult(
            base_amount=100.0,
            final_amount=100.0,
            total_discount=0.0,
            applied_promotions=[],
        )
        assert result.final_amount == result.base_amount
        assert result.total_discount == 0.0


class TestPromoValidationError:
    """Tests for PromoValidationError exception."""

    def test_error_with_code(self):
        """Error should include code and message."""
        from backend.services.promotion_service import PromoValidationError

        error = PromoValidationError("Promo not found", "not_found")
        assert error.message == "Promo not found"
        assert error.code == "not_found"
        assert str(error) == "Promo not found"

    def test_error_default_code(self):
        """Error should have default code."""
        from backend.services.promotion_service import PromoValidationError

        error = PromoValidationError("Generic error")
        assert error.code == "validation_error"
