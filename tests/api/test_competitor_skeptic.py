"""Unit tests for competitor skeptic evaluation.

Tests the relevance scoring and warning generation for detected competitors.
"""

from backend.api.context.models import DetectedCompetitor, RelevanceFlags
from backend.api.context.skeptic import (
    _build_context_summary,
    _generate_warning,
    _parse_batch_response,
    _parse_skeptic_response,
)


class TestRelevanceFlags:
    """Tests for RelevanceFlags model."""

    def test_all_true(self):
        """Test with all checks passing."""
        flags = RelevanceFlags(similar_product=True, same_icp=True, same_market=True)
        assert flags.similar_product is True
        assert flags.same_icp is True
        assert flags.same_market is True

    def test_all_false(self):
        """Test with no checks passing."""
        flags = RelevanceFlags(similar_product=False, same_icp=False, same_market=False)
        assert flags.similar_product is False
        assert flags.same_icp is False
        assert flags.same_market is False

    def test_defaults_to_false(self):
        """Test that defaults are False."""
        flags = RelevanceFlags()
        assert flags.similar_product is False
        assert flags.same_icp is False
        assert flags.same_market is False

    def test_partial_checks(self):
        """Test with some checks passing."""
        flags = RelevanceFlags(similar_product=True, same_icp=False, same_market=True)
        assert flags.similar_product is True
        assert flags.same_icp is False
        assert flags.same_market is True


class TestDetectedCompetitorRelevance:
    """Tests for DetectedCompetitor with relevance fields."""

    def test_high_relevance_competitor(self):
        """Test competitor with high relevance (3/3 checks)."""
        competitor = DetectedCompetitor(
            name="Acme Corp",
            url="https://acme.com",
            description="Project management tool",
            relevance_score=1.0,
            relevance_flags=RelevanceFlags(similar_product=True, same_icp=True, same_market=True),
            relevance_warning=None,
        )
        assert competitor.relevance_score == 1.0
        assert competitor.relevance_warning is None
        assert competitor.relevance_flags.similar_product is True

    def test_medium_relevance_competitor(self):
        """Test competitor with medium relevance (2/3 checks)."""
        competitor = DetectedCompetitor(
            name="Beta Inc",
            url="https://beta.io",
            description="Similar tool",
            relevance_score=0.67,
            relevance_flags=RelevanceFlags(similar_product=True, same_icp=True, same_market=False),
            relevance_warning=None,
        )
        assert competitor.relevance_score == 0.67
        assert competitor.relevance_flags.same_market is False

    def test_low_relevance_competitor(self):
        """Test competitor with low relevance (1/3 checks)."""
        competitor = DetectedCompetitor(
            name="Gamma LLC",
            url="https://gamma.com",
            description="Different product",
            relevance_score=0.33,
            relevance_flags=RelevanceFlags(similar_product=False, same_icp=False, same_market=True),
            relevance_warning="Gamma LLC: different product focus, different target customers",
        )
        assert competitor.relevance_score == 0.33
        assert "different product" in competitor.relevance_warning

    def test_no_relevance_competitor(self):
        """Test competitor with no relevance (0/3 checks)."""
        competitor = DetectedCompetitor(
            name="Delta Corp",
            url="https://delta.com",
            description="Unrelated company",
            relevance_score=0.0,
            relevance_flags=RelevanceFlags(
                similar_product=False, same_icp=False, same_market=False
            ),
            relevance_warning="Delta Corp: different product focus, different target customers, different market segment",
        )
        assert competitor.relevance_score == 0.0
        assert "different market segment" in competitor.relevance_warning

    def test_null_relevance_fields(self):
        """Test competitor without relevance data (backward compat)."""
        competitor = DetectedCompetitor(
            name="Legacy Competitor",
            url=None,
            description=None,
            relevance_score=None,
            relevance_flags=None,
            relevance_warning=None,
        )
        assert competitor.relevance_score is None
        assert competitor.relevance_flags is None


class TestBuildContextSummary:
    """Tests for context summary builder."""

    def test_full_context(self):
        """Test with complete context."""
        context = {
            "company_name": "MyApp",
            "product_description": "AI-powered project management",
            "industry": "Software",
            "target_market": "Small businesses",
            "ideal_customer_profile": "SaaS companies with 10-50 employees",
            "target_geography": "North America",
            "business_model": "B2B SaaS",
        }
        summary = _build_context_summary(context)
        assert summary is not None
        assert "MyApp" in summary
        assert "AI-powered" in summary
        assert "Software" in summary

    def test_minimal_context(self):
        """Test with minimum required context (2 fields)."""
        context = {
            "company_name": "MyApp",
            "industry": "Software",
        }
        summary = _build_context_summary(context)
        assert summary is not None
        assert "MyApp" in summary

    def test_insufficient_context(self):
        """Test with insufficient context (<2 fields)."""
        context = {"company_name": "MyApp"}
        summary = _build_context_summary(context)
        assert summary is None

    def test_empty_context(self):
        """Test with empty context."""
        summary = _build_context_summary({})
        assert summary is None


class TestParseSkepticResponse:
    """Tests for skeptic response parsing."""

    def test_valid_json(self):
        """Test parsing valid JSON response."""
        response = (
            '{"similar_product": true, "same_icp": false, "same_market": true, "warning": null}'
        )
        result = _parse_skeptic_response(response)
        assert result is not None
        assert result["similar_product"] is True
        assert result["same_icp"] is False
        assert result["same_market"] is True

    def test_json_with_warning(self):
        """Test parsing JSON with warning message."""
        response = '{"similar_product": false, "same_icp": false, "same_market": true, "warning": "Different product focus"}'
        result = _parse_skeptic_response(response)
        assert result is not None
        assert result["warning"] == "Different product focus"

    def test_json_in_text(self):
        """Test extracting JSON from text response."""
        response = 'Here is the analysis: {"similar_product": true, "same_icp": true, "same_market": true, "warning": null}'
        result = _parse_skeptic_response(response)
        assert result is not None
        assert result["similar_product"] is True

    def test_invalid_response(self):
        """Test handling invalid response."""
        response = "This is not valid JSON at all"
        result = _parse_skeptic_response(response)
        assert result is None


class TestParseBatchResponse:
    """Tests for batch skeptic response parsing."""

    def test_valid_batch(self):
        """Test parsing valid batch response."""
        response = '[{"similar_product": true, "same_icp": true, "same_market": true, "warning": null}, {"similar_product": false, "same_icp": false, "same_market": false, "warning": "Not relevant"}]'
        result = _parse_batch_response(response)
        assert result is not None
        assert len(result) == 2
        assert result[0]["similar_product"] is True
        assert result[1]["warning"] == "Not relevant"

    def test_array_in_text(self):
        """Test extracting array from text response."""
        response = 'Analysis results: [{"similar_product": true, "same_icp": false, "same_market": true, "warning": null}]'
        result = _parse_batch_response(response)
        assert result is not None
        assert len(result) == 1

    def test_invalid_batch(self):
        """Test handling invalid batch response."""
        response = "Not a valid array"
        result = _parse_batch_response(response)
        assert result is None


class TestGenerateWarning:
    """Tests for warning message generation."""

    def test_no_checks_passing(self):
        """Test warning with 0 checks passing."""
        flags = RelevanceFlags(similar_product=False, same_icp=False, same_market=False)
        warning = _generate_warning(flags, "TestCorp")
        assert "TestCorp" in warning
        assert "different product focus" in warning
        assert "different target customers" in warning
        assert "different market segment" in warning

    def test_one_check_passing(self):
        """Test warning with 1 check passing."""
        flags = RelevanceFlags(similar_product=True, same_icp=False, same_market=False)
        warning = _generate_warning(flags, "TestCorp")
        assert "TestCorp" in warning
        assert "different product focus" not in warning
        assert "different target customers" in warning
        assert "different market segment" in warning

    def test_two_checks_passing(self):
        """Test warning with 2 checks passing (edge case - shouldn't normally generate)."""
        flags = RelevanceFlags(similar_product=True, same_icp=True, same_market=False)
        warning = _generate_warning(flags, "TestCorp")
        assert "TestCorp" in warning
        assert "different market segment" in warning
        assert "different product focus" not in warning


class TestRelevanceScoreCalculation:
    """Tests for relevance score calculation logic."""

    def test_score_three_checks(self):
        """Test score calculation for 3/3 checks."""
        # Score should be 1.0 (3/3 = 1.0)
        checks_passed = 3
        score = round(checks_passed / 3, 2)
        assert score == 1.0

    def test_score_two_checks(self):
        """Test score calculation for 2/3 checks."""
        # Score should be 0.67 (2/3 = 0.666...)
        checks_passed = 2
        score = round(checks_passed / 3, 2)
        assert score == 0.67

    def test_score_one_check(self):
        """Test score calculation for 1/3 checks."""
        # Score should be 0.33 (1/3 = 0.333...)
        checks_passed = 1
        score = round(checks_passed / 3, 2)
        assert score == 0.33

    def test_score_zero_checks(self):
        """Test score calculation for 0/3 checks."""
        # Score should be 0.0 (0/3 = 0.0)
        checks_passed = 0
        score = round(checks_passed / 3, 2)
        assert score == 0.0
