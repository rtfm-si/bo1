"""Tests for context insight enrichment with market benchmarks.

Tests:
- InsightEnrichmentService unit tests
- Manual enrichment endpoint
- Enrichment triggered after metric calculation
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from backend.api.context.models import (
    ClarificationInsightMarketContext,
    ClarificationStorageEntry,
    InsightMetricResponse,
    MarketContext,
)
from backend.services.industry_benchmark_researcher import (
    BenchmarkMetric,
    IndustryBenchmarkResult,
)
from backend.services.insight_enrichment import (
    InsightEnrichmentService,
    MarketContextResult,
    dict_to_market_context,
    market_context_to_dict,
)


class TestMarketContextModels:
    """Test MarketContext Pydantic models."""

    def test_market_context_model_valid(self):
        """Test valid MarketContext model."""
        mc = MarketContext(
            benchmark_value=50.0,
            benchmark_percentile="p50",
            percentile_position=45,
            comparison_text="Your CAC ($50) is in the 45th percentile for SaaS",
            source_url="https://example.com/benchmarks",
            enriched_at=datetime.now(UTC),
            confidence=0.8,
        )
        assert mc.percentile_position == 45
        assert mc.confidence == 0.8

    def test_market_context_percentile_bounds(self):
        """Test percentile_position bounds validation."""
        # Valid bounds
        mc = MarketContext(percentile_position=0)
        assert mc.percentile_position == 0

        mc = MarketContext(percentile_position=100)
        assert mc.percentile_position == 100

        # Invalid bounds should raise
        with pytest.raises(ValueError):
            MarketContext(percentile_position=-1)

        with pytest.raises(ValueError):
            MarketContext(percentile_position=101)

    def test_clarification_insight_market_context(self):
        """Test ClarificationInsightMarketContext response model."""
        mc = ClarificationInsightMarketContext(
            percentile_position=75,
            comparison_text="Excellent performance",
            source_url="https://example.com",
            enriched_at=datetime.now(UTC),
        )
        assert mc.percentile_position == 75

    def test_clarification_storage_entry_with_market_context(self):
        """Test ClarificationStorageEntry includes market_context field."""
        entry = ClarificationStorageEntry(
            answer="Our CAC is $50",
            source="calculation",
            metric_key="cac",
            metric=InsightMetricResponse(
                value=50.0,
                unit="USD",
                metric_type="cac",
            ),
            market_context=MarketContext(
                percentile_position=45,
                comparison_text="Below average",
            ),
        )
        assert entry.market_context is not None
        assert entry.market_context.percentile_position == 45


class TestMarketContextSerialization:
    """Test market context dict serialization."""

    def test_market_context_to_dict(self):
        """Test converting MarketContextResult to dict."""
        result = MarketContextResult(
            benchmark_value=100.0,
            benchmark_percentile="p75",
            percentile_position=80,
            comparison_text="Top performer",
            source_url="https://example.com",
            enriched_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
            confidence=0.9,
        )
        d = market_context_to_dict(result)

        assert d["benchmark_value"] == 100.0
        assert d["percentile_position"] == 80
        assert d["confidence"] == 0.9
        assert "2025-01-15" in d["enriched_at"]

    def test_market_context_to_dict_none(self):
        """Test None input returns None."""
        assert market_context_to_dict(None) is None

    def test_dict_to_market_context(self):
        """Test converting dict back to MarketContextResult."""
        d = {
            "benchmark_value": 50.0,
            "percentile_position": 60,
            "comparison_text": "Above average",
            "enriched_at": "2025-01-15T12:00:00+00:00",
            "confidence": 0.7,
        }
        result = dict_to_market_context(d)

        assert result.benchmark_value == 50.0
        assert result.percentile_position == 60
        assert result.enriched_at.year == 2025

    def test_dict_to_market_context_none(self):
        """Test None input returns None."""
        assert dict_to_market_context(None) is None


class TestInsightEnrichmentService:
    """Test InsightEnrichmentService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return InsightEnrichmentService()

    @pytest.fixture
    def mock_benchmark_result(self):
        """Create mock benchmark result."""
        return IndustryBenchmarkResult(
            industry="SaaS",
            metrics=[
                BenchmarkMetric(
                    metric="cac",
                    display_name="Customer Acquisition Cost",
                    p25=30.0,
                    p50=50.0,
                    p75=80.0,
                    source_url="https://example.com/saas-benchmarks",
                    confidence=0.8,
                ),
                BenchmarkMetric(
                    metric="churn",
                    display_name="Monthly Churn Rate",
                    p25=2.0,
                    p50=5.0,
                    p75=8.0,
                    confidence=0.7,
                ),
            ],
            sources=["https://example.com"],
            confidence=0.8,
            generated_at=datetime.now(UTC),
            source_type="cache",
        )

    @pytest.mark.asyncio
    async def test_enrich_insight_no_industry(self, service):
        """Test enrichment fails gracefully without industry."""
        result = await service.enrich_insight(
            metric_key="cac",
            metric_value=50.0,
            industry="",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_enrich_insight_no_benchmarks(self, service):
        """Test enrichment fails gracefully with no benchmarks."""
        with patch.object(
            service.researcher,
            "get_or_research_benchmarks",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await service.enrich_insight(
                metric_key="cac",
                metric_value=50.0,
                industry="SaaS",
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_enrich_insight_no_matching_metric(self, service, mock_benchmark_result):
        """Test enrichment fails when no matching metric found."""
        with patch.object(
            service.researcher,
            "get_or_research_benchmarks",
            new_callable=AsyncMock,
            return_value=mock_benchmark_result,
        ):
            result = await service.enrich_insight(
                metric_key="unknown_metric",
                metric_value=50.0,
                industry="SaaS",
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_enrich_insight_success(self, service, mock_benchmark_result):
        """Test successful enrichment with matching benchmark."""
        with patch.object(
            service.researcher,
            "get_or_research_benchmarks",
            new_callable=AsyncMock,
            return_value=mock_benchmark_result,
        ):
            result = await service.enrich_insight(
                metric_key="cac",
                metric_value=50.0,
                industry="SaaS",
            )

            assert result is not None
            assert result.percentile_position is not None
            assert result.comparison_text is not None
            assert "CAC" in result.comparison_text
            assert "SaaS" in result.comparison_text

    @pytest.mark.asyncio
    async def test_enrich_insight_lower_is_better(self, service, mock_benchmark_result):
        """Test percentile calculation for metrics where lower is better (CAC, churn)."""
        with patch.object(
            service.researcher,
            "get_or_research_benchmarks",
            new_callable=AsyncMock,
            return_value=mock_benchmark_result,
        ):
            # CAC at p25 (low cost = good = high percentile)
            result = await service.enrich_insight(
                metric_key="cac",
                metric_value=30.0,
                industry="SaaS",
            )
            assert result is not None
            assert result.percentile_position >= 70  # Should be high percentile

            # CAC at p75 (high cost = bad = low percentile)
            result = await service.enrich_insight(
                metric_key="cac",
                metric_value=80.0,
                industry="SaaS",
            )
            assert result is not None
            assert result.percentile_position <= 30  # Should be low percentile

    @pytest.mark.asyncio
    async def test_enrich_insight_churn(self, service, mock_benchmark_result):
        """Test enrichment for churn rate."""
        with patch.object(
            service.researcher,
            "get_or_research_benchmarks",
            new_callable=AsyncMock,
            return_value=mock_benchmark_result,
        ):
            result = await service.enrich_insight(
                metric_key="churn",
                metric_value=5.0,  # At median
                industry="SaaS",
            )

            assert result is not None
            # At median = ~50th percentile
            assert 40 <= result.percentile_position <= 60


class TestFindMatchingBenchmark:
    """Test _find_matching_benchmark helper."""

    def test_find_by_metric_key(self):
        """Test finding benchmark by metric key."""
        service = InsightEnrichmentService()
        metrics = [
            BenchmarkMetric(metric="cac", display_name="CAC", p50=50.0),
            BenchmarkMetric(metric="ltv", display_name="LTV", p50=500.0),
        ]

        result = service._find_matching_benchmark("cac", metrics)
        assert result is not None
        assert result.metric == "cac"

    def test_find_by_alternate_name(self):
        """Test finding benchmark by alternate metric name."""
        service = InsightEnrichmentService()
        metrics = [
            BenchmarkMetric(metric="customer_acquisition_cost", display_name="CAC", p50=50.0),
        ]

        result = service._find_matching_benchmark("cac", metrics)
        assert result is not None
        assert result.metric == "customer_acquisition_cost"

    def test_find_no_match(self):
        """Test returns None when no match."""
        service = InsightEnrichmentService()
        metrics = [
            BenchmarkMetric(metric="revenue", display_name="Revenue", p50=100000.0),
        ]

        result = service._find_matching_benchmark("cac", metrics)
        assert result is None


class TestGenerateComparisonText:
    """Test _generate_comparison_text helper."""

    def test_comparison_text_formats_correctly(self):
        """Test comparison text includes all expected parts."""
        service = InsightEnrichmentService()

        text = service._generate_comparison_text(
            metric_key="cac",
            user_value=50.0,
            percentile_position=45,
            industry="SaaS",
        )

        assert "CAC" in text
        assert "$50" in text
        assert "45th percentile" in text
        assert "SaaS" in text
        assert "below average" in text

    def test_comparison_text_excellent(self):
        """Test comparison text for excellent performance."""
        service = InsightEnrichmentService()

        text = service._generate_comparison_text(
            metric_key="gross_margin",
            user_value=75.0,
            percentile_position=85,
            industry="Software",
        )

        assert "excellent" in text.lower()

    def test_comparison_text_needs_improvement(self):
        """Test comparison text for poor performance."""
        service = InsightEnrichmentService()

        text = service._generate_comparison_text(
            metric_key="churn",
            user_value=10.0,
            percentile_position=15,
            industry="SaaS",
        )

        assert "needs improvement" in text.lower()


class TestFormatMetricValue:
    """Test _format_metric_value helper."""

    def test_format_currency_large(self):
        """Test formatting large currency values."""
        service = InsightEnrichmentService()

        assert service._format_metric_value("cac", 1500.0) == "$1,500"
        assert service._format_metric_value("arr", 1500000.0) == "$1,500,000"

    def test_format_currency_small(self):
        """Test formatting small currency values."""
        service = InsightEnrichmentService()

        assert service._format_metric_value("cac", 25.50) == "$25.50"

    def test_format_percentage(self):
        """Test formatting percentage values."""
        service = InsightEnrichmentService()

        assert service._format_metric_value("churn", 5.5) == "5.5%"
        assert service._format_metric_value("conversion_rate", 12.0) == "12.0%"

    def test_format_ratio(self):
        """Test formatting ratio values."""
        service = InsightEnrichmentService()

        assert service._format_metric_value("ltv_cac_ratio", 3.5) == "3.5x"

    def test_format_runway(self):
        """Test formatting runway values."""
        service = InsightEnrichmentService()

        assert service._format_metric_value("runway", 18.0) == "18 months"

    def test_format_nps(self):
        """Test formatting NPS values."""
        service = InsightEnrichmentService()

        assert service._format_metric_value("nps", 45.0) == "+45"
        assert service._format_metric_value("nps", -10.0) == "-10"


class TestEnrichmentEndpoint:
    """Integration tests for the enrichment endpoint.

    Note: Full endpoint tests require authenticated client setup.
    These tests verify the data models and service integration.
    """

    @pytest.fixture
    def mock_user_context(self):
        """Create mock user context with insights."""
        return {
            "industry": "SaaS",
            "clarifications": {
                "[Calculation] CAC": {
                    "answer": "CAC is $50",
                    "source": "calculation",
                    "metric_key": "cac",
                    "metric": {
                        "value": 50.0,
                        "unit": "USD",
                        "metric_type": "cac",
                    },
                }
            },
        }

    def test_enrich_response_model_success(self):
        """Test InsightEnrichResponse model for success case."""
        from backend.api.context.routes import InsightEnrichResponse

        response = InsightEnrichResponse(
            success=True,
            enriched=True,
            percentile_position=45,
            comparison_text="Below average",
            error=None,
        )
        assert response.success is True
        assert response.enriched is True
        assert response.percentile_position == 45

    def test_enrich_response_model_no_benchmarks(self):
        """Test InsightEnrichResponse model when no benchmarks found."""
        from backend.api.context.routes import InsightEnrichResponse

        response = InsightEnrichResponse(
            success=True,
            enriched=False,
            percentile_position=None,
            comparison_text=None,
            error="No benchmark data available for cac in SaaS",
        )
        assert response.success is True
        assert response.enriched is False
        assert response.error is not None

    def test_enrich_response_model_no_industry(self):
        """Test InsightEnrichResponse model when no industry set."""
        from backend.api.context.routes import InsightEnrichResponse

        response = InsightEnrichResponse(
            success=False,
            enriched=False,
            percentile_position=None,
            comparison_text=None,
            error="No industry set in context. Set your industry first.",
        )
        assert response.success is False
        assert "industry" in response.error.lower()
