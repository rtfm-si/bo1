"""Tests for Field(max_length=) validation on request models.

Validates that text fields reject oversized input with 422 errors.
"""

import pytest
from pydantic import ValidationError

from backend.api.context.models import BusinessContext
from backend.api.control import ClarificationRequest
from backend.api.models import ActionCreate, ActionUpdate


class TestActionCreateMaxLength:
    """Tests for ActionCreate max_length validation."""

    def test_title_at_boundary_accepted(self) -> None:
        """Title at exactly 500 chars should be accepted."""
        action = ActionCreate(
            title="x" * 500,
            description="Valid description",
        )
        assert len(action.title) == 500

    def test_title_over_limit_rejected(self) -> None:
        """Title over 500 chars should be rejected with 422."""
        with pytest.raises(ValidationError) as exc_info:
            ActionCreate(
                title="x" * 501,
                description="Valid description",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("title",)
        assert "at most 500" in errors[0]["msg"].lower()

    def test_description_at_boundary_accepted(self) -> None:
        """Description at exactly 10000 chars should be accepted."""
        action = ActionCreate(
            title="Valid title",
            description="x" * 10000,
        )
        assert len(action.description) == 10000

    def test_description_over_limit_rejected(self) -> None:
        """Description over 10000 chars should be rejected with 422."""
        with pytest.raises(ValidationError) as exc_info:
            ActionCreate(
                title="Valid title",
                description="x" * 10001,
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("description",)
        assert "at most 10000" in errors[0]["msg"].lower()


class TestActionUpdateMaxLength:
    """Tests for ActionUpdate max_length validation."""

    def test_title_over_limit_rejected(self) -> None:
        """Title over 500 chars should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ActionUpdate(title="x" * 501)
        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("title",)

    def test_description_over_limit_rejected(self) -> None:
        """Description over 10000 chars should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ActionUpdate(description="x" * 10001)
        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("description",)


class TestClarificationRequestMaxLength:
    """Tests for ClarificationRequest max_length validation."""

    def test_answer_at_boundary_accepted(self) -> None:
        """Answer at exactly 5000 chars should be accepted."""
        req = ClarificationRequest(answer="x" * 5000)
        assert len(req.answer) == 5000

    def test_answer_over_limit_rejected(self) -> None:
        """Answer over 5000 chars should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ClarificationRequest(answer="x" * 5001)
        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("answer",)

    def test_answers_dict_value_at_boundary_accepted(self) -> None:
        """Answer dict value at exactly 5000 chars should be accepted."""
        req = ClarificationRequest(answers={"Question?": "x" * 5000})
        assert len(req.answers["Question?"]) == 5000

    def test_answers_dict_value_over_limit_rejected(self) -> None:
        """Answer dict value over 5000 chars should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ClarificationRequest(answers={"Question?": "x" * 5001})
        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("answers",)
        assert "exceeds 5000 characters" in str(exc_info.value)

    def test_answers_multiple_values_all_validated(self) -> None:
        """All answer values in dict should be validated."""
        # First valid, second invalid
        with pytest.raises(ValidationError) as exc_info:
            ClarificationRequest(
                answers={
                    "First question?": "Short answer",
                    "Second question?": "x" * 5001,
                }
            )
        assert "exceeds 5000 characters" in str(exc_info.value)


class TestBusinessContextMaxLength:
    """Tests for BusinessContext max_length validation."""

    def test_business_model_over_limit_rejected(self) -> None:
        """business_model over 500 chars should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BusinessContext(business_model="x" * 501)
        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("business_model",)

    def test_target_market_over_limit_rejected(self) -> None:
        """target_market over 1000 chars should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BusinessContext(target_market="x" * 1001)
        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("target_market",)

    def test_product_description_over_limit_rejected(self) -> None:
        """product_description over 2000 chars should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BusinessContext(product_description="x" * 2001)
        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("product_description",)

    def test_revenue_over_limit_rejected(self) -> None:
        """revenue over 200 chars should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BusinessContext(revenue="x" * 201)
        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("revenue",)

    def test_ideal_customer_profile_over_limit_rejected(self) -> None:
        """ideal_customer_profile over 2000 chars should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BusinessContext(ideal_customer_profile="x" * 2001)
        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("ideal_customer_profile",)

    def test_all_fields_at_limits_accepted(self) -> None:
        """All fields at their exact limits should be accepted."""
        ctx = BusinessContext(
            business_model="x" * 500,
            target_market="x" * 1000,
            product_description="x" * 2000,
            revenue="x" * 200,
            customers="x" * 200,
            growth_rate="x" * 200,
            competitors="x" * 2000,
            website="x" * 500,
            company_name="x" * 200,
            industry="x" * 200,
            pricing_model="x" * 200,
            brand_positioning="x" * 1000,
            brand_tone="x" * 200,
            brand_maturity="x" * 100,
            ideal_customer_profile="x" * 2000,
            target_geography="x" * 500,
            traffic_range="x" * 50,
            mau_bucket="x" * 50,
            revenue_stage="x" * 50,
            main_value_proposition="x" * 1000,
            team_size="x" * 100,
            budget_constraints="x" * 500,
            time_constraints="x" * 500,
            regulatory_constraints="x" * 1000,
        )
        assert ctx.business_model is not None
        assert len(ctx.business_model) == 500
