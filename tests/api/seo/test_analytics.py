"""Tests for SEO article analytics Pydantic models.

Validates:
- ArticleEventCreate model validation
- ArticleAnalytics model with CTR/signup rate calculations
- ArticleAnalyticsListResponse aggregation
"""

import pytest

from backend.api.seo.routes import (
    ArticleAnalytics,
    ArticleAnalyticsListResponse,
    ArticleEventCreate,
)


@pytest.mark.unit
class TestArticleEventCreate:
    """Test ArticleEventCreate Pydantic model."""

    def test_valid_view_event(self):
        """Valid view event should pass validation."""
        event = ArticleEventCreate(
            event_type="view",
            referrer="https://google.com/search?q=test",
            utm_source="google",
            utm_medium="organic",
            utm_campaign=None,
            session_id="abc123",
        )
        assert event.event_type == "view"
        assert event.referrer == "https://google.com/search?q=test"
        assert event.utm_source == "google"
        assert event.session_id == "abc123"

    def test_valid_click_event(self):
        """Valid click event should pass validation."""
        event = ArticleEventCreate(
            event_type="click",
            referrer=None,
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            session_id="xyz789",
        )
        assert event.event_type == "click"
        assert event.referrer is None

    def test_valid_signup_event(self):
        """Valid signup event should pass validation."""
        event = ArticleEventCreate(
            event_type="signup",
            referrer="https://blog.example.com/article",
            utm_source="facebook",
            utm_medium="social",
            utm_campaign="launch2024",
            session_id="sess_001",
        )
        assert event.event_type == "signup"
        assert event.utm_campaign == "launch2024"

    def test_minimal_event(self):
        """Event with only required fields is valid."""
        event = ArticleEventCreate(event_type="view")
        assert event.event_type == "view"
        assert event.referrer is None
        assert event.utm_source is None
        assert event.session_id is None

    def test_all_utm_parameters(self):
        """Event with all UTM parameters is valid."""
        event = ArticleEventCreate(
            event_type="click",
            utm_source="newsletter",
            utm_medium="email",
            utm_campaign="weekly_digest",
        )
        assert event.utm_source == "newsletter"
        assert event.utm_medium == "email"
        assert event.utm_campaign == "weekly_digest"

    def test_long_referrer_truncated_at_boundary(self):
        """Referrer at max length is valid."""
        long_referrer = "https://example.com/" + "a" * 980
        event = ArticleEventCreate(
            event_type="view",
            referrer=long_referrer,
        )
        assert len(event.referrer) == 1000

    def test_referrer_exceeds_max_length(self):
        """Referrer exceeding max length should fail validation."""
        too_long_referrer = "https://example.com/" + "a" * 1000
        with pytest.raises(ValueError):
            ArticleEventCreate(
                event_type="view",
                referrer=too_long_referrer,
            )

    def test_session_id_max_length(self):
        """Session ID at max length is valid."""
        session_id = "s" * 255
        event = ArticleEventCreate(
            event_type="view",
            session_id=session_id,
        )
        assert len(event.session_id) == 255

    def test_session_id_exceeds_max_length(self):
        """Session ID exceeding max length should fail validation."""
        too_long_session = "s" * 256
        with pytest.raises(ValueError):
            ArticleEventCreate(
                event_type="view",
                session_id=too_long_session,
            )


@pytest.mark.unit
class TestArticleAnalytics:
    """Test ArticleAnalytics Pydantic model."""

    def test_valid_analytics(self):
        """Valid analytics should pass validation."""
        analytics = ArticleAnalytics(
            article_id=1,
            title="Test Article",
            views=100,
            clicks=10,
            signups=2,
            ctr=0.1,
            signup_rate=0.02,
        )
        assert analytics.article_id == 1
        assert analytics.views == 100
        assert analytics.clicks == 10
        assert analytics.signups == 2
        assert analytics.ctr == 0.1
        assert analytics.signup_rate == 0.02

    def test_zero_metrics(self):
        """Analytics with zero metrics is valid."""
        analytics = ArticleAnalytics(
            article_id=1,
            title="New Article",
            views=0,
            clicks=0,
            signups=0,
            ctr=0.0,
            signup_rate=0.0,
        )
        assert analytics.views == 0
        assert analytics.ctr == 0.0
        assert analytics.signup_rate == 0.0

    def test_ctr_at_max(self):
        """CTR at 1.0 (100%) is valid."""
        analytics = ArticleAnalytics(
            article_id=1,
            title="High CTR Article",
            views=10,
            clicks=10,
            signups=5,
            ctr=1.0,
            signup_rate=0.5,
        )
        assert analytics.ctr == 1.0

    def test_ctr_exceeds_max(self):
        """CTR > 1.0 should fail validation."""
        with pytest.raises(ValueError):
            ArticleAnalytics(
                article_id=1,
                title="Invalid CTR",
                views=10,
                clicks=15,
                signups=0,
                ctr=1.5,
                signup_rate=0.0,
            )

    def test_negative_views_invalid(self):
        """Negative views should fail validation."""
        with pytest.raises(ValueError):
            ArticleAnalytics(
                article_id=1,
                title="Negative Views",
                views=-5,
                clicks=0,
                signups=0,
                ctr=0.0,
                signup_rate=0.0,
            )

    def test_negative_ctr_invalid(self):
        """Negative CTR should fail validation."""
        with pytest.raises(ValueError):
            ArticleAnalytics(
                article_id=1,
                title="Negative CTR",
                views=10,
                clicks=0,
                signups=0,
                ctr=-0.1,
                signup_rate=0.0,
            )


@pytest.mark.unit
class TestArticleAnalyticsListResponse:
    """Test ArticleAnalyticsListResponse Pydantic model."""

    def test_valid_list_response(self):
        """Valid list response should pass validation."""
        response = ArticleAnalyticsListResponse(
            articles=[
                ArticleAnalytics(
                    article_id=1,
                    title="Article 1",
                    views=100,
                    clicks=10,
                    signups=2,
                    ctr=0.1,
                    signup_rate=0.02,
                ),
                ArticleAnalytics(
                    article_id=2,
                    title="Article 2",
                    views=50,
                    clicks=5,
                    signups=1,
                    ctr=0.1,
                    signup_rate=0.02,
                ),
            ],
            total_views=150,
            total_clicks=15,
            total_signups=3,
            overall_ctr=0.1,
            overall_signup_rate=0.02,
        )
        assert len(response.articles) == 2
        assert response.total_views == 150
        assert response.total_clicks == 15
        assert response.overall_ctr == 0.1

    def test_empty_list_response(self):
        """Empty list response is valid."""
        response = ArticleAnalyticsListResponse(
            articles=[],
            total_views=0,
            total_clicks=0,
            total_signups=0,
            overall_ctr=0.0,
            overall_signup_rate=0.0,
        )
        assert len(response.articles) == 0
        assert response.total_views == 0
        assert response.overall_ctr == 0.0

    def test_default_values(self):
        """Default values should be applied."""
        response = ArticleAnalyticsListResponse()
        assert response.articles == []
        assert response.total_views == 0
        assert response.total_clicks == 0
        assert response.total_signups == 0
        assert response.overall_ctr == 0.0
        assert response.overall_signup_rate == 0.0

    def test_overall_ctr_at_max(self):
        """Overall CTR at 1.0 is valid."""
        response = ArticleAnalyticsListResponse(
            articles=[],
            total_views=10,
            total_clicks=10,
            total_signups=0,
            overall_ctr=1.0,
            overall_signup_rate=0.0,
        )
        assert response.overall_ctr == 1.0

    def test_overall_ctr_exceeds_max(self):
        """Overall CTR > 1.0 should fail validation."""
        with pytest.raises(ValueError):
            ArticleAnalyticsListResponse(
                articles=[],
                total_views=10,
                total_clicks=15,
                total_signups=0,
                overall_ctr=1.5,
                overall_signup_rate=0.0,
            )
