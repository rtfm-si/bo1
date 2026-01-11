"""Unit tests for metric calculation endpoints.

Tests:
- Calculation formulas (MRR, churn, etc.)
- Insight storage with source_type="calculation"
- Validation of answer inputs
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.api.context.metric_questions import (
    calculate_metric,
    get_available_metrics,
    get_metric_questions,
)

# =============================================================================
# Unit Tests for metric_questions.py
# =============================================================================


class TestGetAvailableMetrics:
    """Tests for get_available_metrics()."""

    def test_returns_list_of_metric_keys(self):
        """Should return list of all supported metric keys."""
        metrics = get_available_metrics()
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        assert "mrr" in metrics
        assert "churn" in metrics
        assert "cac" in metrics
        assert "ltv" in metrics

    def test_all_returned_metrics_have_questions(self):
        """All returned metrics should have question definitions."""
        metrics = get_available_metrics()
        for metric_key in metrics:
            formula = get_metric_questions(metric_key)
            assert formula is not None
            assert "questions" in formula
            assert len(formula["questions"]) > 0


class TestGetMetricQuestions:
    """Tests for get_metric_questions()."""

    def test_returns_none_for_unknown_metric(self):
        """Should return None for unknown metric key."""
        result = get_metric_questions("unknown_metric_xyz")
        assert result is None

    def test_mrr_has_single_question(self):
        """MRR should have a single question for monthly subscription revenue."""
        formula = get_metric_questions("mrr")
        assert formula is not None
        assert len(formula["questions"]) == 1
        assert formula["questions"][0]["id"] == "monthly_subscription_revenue"
        assert formula["result_unit"] == "$"

    def test_churn_has_two_questions(self):
        """Churn rate should have two questions."""
        formula = get_metric_questions("churn")
        assert formula is not None
        assert len(formula["questions"]) == 2
        question_ids = {q["id"] for q in formula["questions"]}
        assert "customers_lost" in question_ids
        assert "customers_start" in question_ids
        assert formula["result_unit"] == "%"

    def test_nps_has_three_questions(self):
        """NPS should have three questions for promoters, passives, detractors."""
        formula = get_metric_questions("nps")
        assert formula is not None
        assert len(formula["questions"]) == 3
        question_ids = {q["id"] for q in formula["questions"]}
        assert "promoters" in question_ids
        assert "passives" in question_ids
        assert "detractors" in question_ids

    def test_question_has_required_fields(self):
        """Each question should have required fields."""
        formula = get_metric_questions("cac")
        assert formula is not None
        for question in formula["questions"]:
            assert "id" in question
            assert "question" in question
            assert "input_type" in question
            assert "placeholder" in question


class TestCalculateMetric:
    """Tests for calculate_metric()."""

    def test_unknown_metric_raises_error(self):
        """Should raise ValueError for unknown metric."""
        with pytest.raises(ValueError, match="Unknown metric"):
            calculate_metric("unknown_metric", {})

    def test_missing_answers_raises_error(self):
        """Should raise ValueError when required answers are missing."""
        with pytest.raises(ValueError, match="Missing answers"):
            calculate_metric("churn", {"customers_lost": 5})  # Missing customers_start

    def test_mrr_calculation(self):
        """MRR should return the subscription revenue directly."""
        value, formula = calculate_metric("mrr", {"monthly_subscription_revenue": 5000})
        assert value == 5000.0
        assert formula == "monthly_subscription_revenue"

    def test_arr_calculation(self):
        """ARR should be MRR * 12."""
        value, formula = calculate_metric("arr", {"monthly_recurring_revenue": 5000})
        assert value == 60000.0
        assert "* 12" in formula

    def test_churn_calculation(self):
        """Churn rate = (customers_lost / customers_start) * 100."""
        value, formula = calculate_metric("churn", {"customers_lost": 5, "customers_start": 100})
        assert value == 5.0  # 5%

    def test_churn_with_zero_start_customers(self):
        """Should handle division by zero gracefully."""
        value, formula = calculate_metric("churn", {"customers_lost": 5, "customers_start": 0})
        assert value == 0.0

    def test_burn_rate_calculation(self):
        """Burn rate = expenses - revenue."""
        value, formula = calculate_metric(
            "burn_rate", {"monthly_expenses": 25000, "monthly_revenue": 15000}
        )
        assert value == 10000.0

    def test_runway_calculation(self):
        """Runway = cash_balance / monthly_burn."""
        value, formula = calculate_metric("runway", {"cash_balance": 150000, "monthly_burn": 10000})
        assert value == 15.0  # 15 months

    def test_runway_with_zero_burn(self):
        """Should handle zero burn rate."""
        value, formula = calculate_metric("runway", {"cash_balance": 150000, "monthly_burn": 0})
        assert value == 0.0

    def test_gross_margin_calculation(self):
        """Gross margin = (revenue - cogs) / revenue * 100."""
        value, formula = calculate_metric("gross_margin", {"revenue": 50000, "cogs": 15000})
        assert value == 70.0  # 70%

    def test_nps_calculation(self):
        """NPS = (promoters - detractors) / total * 100."""
        value, formula = calculate_metric(
            "nps", {"promoters": 50, "passives": 30, "detractors": 20}
        )
        # (50 - 20) / 100 * 100 = 30
        assert value == 30.0

    def test_cac_calculation(self):
        """CAC = marketing_spend / new_customers."""
        value, formula = calculate_metric("cac", {"marketing_spend": 10000, "new_customers": 25})
        assert value == 400.0

    def test_ltv_calculation(self):
        """LTV = ARPU * average_customer_lifetime."""
        value, formula = calculate_metric("ltv", {"arpu": 50, "avg_customer_lifetime": 24})
        assert value == 1200.0

    def test_ltv_cac_ratio_calculation(self):
        """LTV:CAC ratio = LTV / CAC."""
        value, formula = calculate_metric("ltv_cac_ratio", {"ltv": 1200, "cac": 400})
        assert value == 3.0

    def test_aov_calculation(self):
        """AOV = total_revenue / total_orders."""
        value, formula = calculate_metric("aov", {"total_revenue": 50000, "total_orders": 500})
        assert value == 100.0

    def test_conversion_rate_calculation(self):
        """Conversion rate = (conversions / visitors) * 100."""
        value, formula = calculate_metric("conversion_rate", {"conversions": 100, "visitors": 5000})
        assert value == 2.0

    def test_return_rate_calculation(self):
        """Return rate = (returns / total_orders) * 100."""
        value, formula = calculate_metric("return_rate", {"returns": 25, "total_orders": 500})
        assert value == 5.0


# =============================================================================
# Integration Tests for Route Functions
# =============================================================================


class TestGetCalculableMetricsRoute:
    """Tests for get_calculable_metrics route function."""

    @pytest.mark.asyncio
    async def test_returns_available_metrics(self):
        """Should return list of calculable metrics."""
        from backend.api.context.routes import get_calculable_metrics

        response = await get_calculable_metrics()

        assert isinstance(response.metrics, list)
        assert "mrr" in response.metrics
        assert "churn" in response.metrics


class TestGetMetricQuestionsRoute:
    """Tests for get_metric_questions route function."""

    @pytest.mark.asyncio
    async def test_returns_questions_for_valid_metric(self):
        """Should return questions for a valid metric."""
        from backend.api.context.routes import get_metric_questions

        response = await get_metric_questions("churn")

        assert response.metric_key == "churn"
        assert len(response.questions) == 2
        assert response.result_unit == "%"

    @pytest.mark.asyncio
    async def test_raises_404_for_unknown_metric(self):
        """Should raise HTTPException for unknown metric."""
        from fastapi import HTTPException

        from backend.api.context.routes import get_metric_questions

        with pytest.raises(HTTPException) as exc_info:
            await get_metric_questions("unknown_xyz")

        assert exc_info.value.status_code == 404


class TestCalculateMetricRoute:
    """Tests for calculate_metric route function."""

    @pytest.fixture
    def mock_user_repository(self):
        """Create mock user repository."""
        repo = MagicMock()
        return repo

    @pytest.mark.asyncio
    async def test_calculates_metric_successfully(self, mock_user_repository):
        """Should calculate metric and return result."""
        from backend.api.context.models import MetricCalculationAnswer, MetricCalculationRequest
        from backend.api.context.routes import calculate_metric

        mock_user_repository.get_context.return_value = {}

        request = MetricCalculationRequest(
            answers=[
                MetricCalculationAnswer(question_id="customers_lost", value=5),
                MetricCalculationAnswer(question_id="customers_start", value=100),
            ],
            save_insight=True,
        )

        mock_user = {"user_id": "user-123"}

        with patch("backend.api.context.routes.user_repository", mock_user_repository):
            response = await calculate_metric("churn", request, user=mock_user)

        assert response.success is True
        assert response.calculated_value == 5.0
        assert response.result_unit == "%"
        assert response.confidence == 1.0

    @pytest.mark.asyncio
    async def test_raises_400_for_missing_answers(self, mock_user_repository):
        """Should raise HTTPException when required answers are missing."""
        from fastapi import HTTPException

        from backend.api.context.models import MetricCalculationAnswer, MetricCalculationRequest
        from backend.api.context.routes import calculate_metric

        request = MetricCalculationRequest(
            answers=[
                MetricCalculationAnswer(question_id="customers_lost", value=5),
                # Missing customers_start
            ],
        )

        mock_user = {"user_id": "user-123"}

        with pytest.raises(HTTPException) as exc_info:
            with patch("backend.api.context.routes.user_repository", mock_user_repository):
                await calculate_metric("churn", request, user=mock_user)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_raises_404_for_unknown_metric(self, mock_user_repository):
        """Should raise HTTPException for unknown metric."""
        from fastapi import HTTPException

        from backend.api.context.models import MetricCalculationAnswer, MetricCalculationRequest
        from backend.api.context.routes import calculate_metric

        # Need at least one answer per validation
        request = MetricCalculationRequest(
            answers=[MetricCalculationAnswer(question_id="dummy", value=1)]
        )

        mock_user = {"user_id": "user-123"}

        with pytest.raises(HTTPException) as exc_info:
            with patch("backend.api.context.routes.user_repository", mock_user_repository):
                await calculate_metric("unknown_xyz", request, user=mock_user)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_saves_insight_when_requested(self, mock_user_repository):
        """Should save calculation as insight when save_insight=True."""
        from backend.api.context.models import MetricCalculationAnswer, MetricCalculationRequest
        from backend.api.context.routes import calculate_metric

        mock_user_repository.get_context.return_value = {}

        request = MetricCalculationRequest(
            answers=[
                MetricCalculationAnswer(question_id="monthly_subscription_revenue", value=5000),
            ],
            save_insight=True,
        )

        mock_user = {"user_id": "user-123"}

        with patch("backend.api.context.routes.user_repository", mock_user_repository):
            response = await calculate_metric("mrr", request, user=mock_user)

        assert response.success is True
        assert response.insight_saved is True

        # Verify save was called
        mock_user_repository.save_context.assert_called_once()
        call_args = mock_user_repository.save_context.call_args
        saved_data = call_args[0][1]  # Second positional arg is context_data
        assert "clarifications" in saved_data
        assert "[Calculation] MRR" in saved_data["clarifications"]

        # Verify clarification entry structure
        entry = saved_data["clarifications"]["[Calculation] MRR"]
        assert entry["source"] == "calculation"
        assert entry["metric_key"] == "mrr"
        assert entry["metric"]["value"] == 5000.0
        assert entry["metric"]["unit"] == "$"

    @pytest.mark.asyncio
    async def test_skips_insight_save_when_not_requested(self, mock_user_repository):
        """Should not save insight when save_insight=False."""
        from backend.api.context.models import MetricCalculationAnswer, MetricCalculationRequest
        from backend.api.context.routes import calculate_metric

        mock_user_repository.get_context.return_value = {}

        request = MetricCalculationRequest(
            answers=[
                MetricCalculationAnswer(question_id="monthly_subscription_revenue", value=5000),
            ],
            save_insight=False,
        )

        mock_user = {"user_id": "user-123"}

        with patch("backend.api.context.routes.user_repository", mock_user_repository):
            response = await calculate_metric("mrr", request, user=mock_user)

        assert response.success is True
        assert response.insight_saved is False
        mock_user_repository.save_context.assert_not_called()
