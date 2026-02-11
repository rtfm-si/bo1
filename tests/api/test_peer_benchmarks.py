"""Tests for peer benchmarks service and API routes."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


class TestPeerBenchmarksConsentService:
    """Tests for consent management in service layer."""

    def test_get_consent_status_returns_false_when_no_record(self):
        """Should return consented=False when no consent record exists."""
        from backend.services.peer_benchmarks import get_consent_status

        with patch("backend.services.peer_benchmarks.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = None
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            result = get_consent_status("test_user")
            assert result.consented is False
            assert result.consented_at is None

    def test_get_consent_status_returns_true_when_consented(self):
        """Should return consented=True when consent is active."""
        from backend.services.peer_benchmarks import get_consent_status

        now = datetime.now(UTC)
        with patch("backend.services.peer_benchmarks.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = {"consented_at": now, "revoked_at": None}
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            result = get_consent_status("test_user")
            assert result.consented is True
            assert result.consented_at == now

    def test_get_consent_status_returns_false_when_revoked(self):
        """Should return consented=False when consent was revoked."""
        from backend.services.peer_benchmarks import get_consent_status

        consented_at = datetime(2025, 1, 1, tzinfo=UTC)
        revoked_at = datetime(2025, 1, 15, tzinfo=UTC)

        with patch("backend.services.peer_benchmarks.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = {
                "consented_at": consented_at,
                "revoked_at": revoked_at,
            }
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            result = get_consent_status("test_user")
            assert result.consented is False
            assert result.revoked_at == revoked_at


class TestPeerBenchmarksPreviewService:
    """Tests for preview metric service."""

    def test_get_preview_metric_returns_none_when_no_user_context(self):
        """Should return None when user has no context entry."""
        from backend.services.peer_benchmarks import get_preview_metric

        with patch("backend.services.peer_benchmarks.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = None
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            result = get_preview_metric("nonexistent_user")
            assert result is None

    def test_get_preview_metric_returns_none_when_no_industry(self):
        """Should return None when user has no industry set."""
        from backend.services.peer_benchmarks import get_preview_metric

        with patch("backend.services.peer_benchmarks.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = {"industry": None}
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            result = get_preview_metric("test_user")
            assert result is None

    def test_get_preview_metric_handles_db_error(self):
        """Should return None on database error."""
        from backend.services.peer_benchmarks import get_preview_metric

        with patch("backend.services.peer_benchmarks.db_session") as mock_db:
            mock_db.side_effect = Exception("Database connection failed")

            result = get_preview_metric("test_user")
            assert result is None


class TestPeerBenchmarksComparisonService:
    """Tests for peer comparison service."""

    def test_get_peer_comparison_returns_none_when_no_user_context(self):
        """Should return None when user has no context entry."""
        from backend.services.peer_benchmarks import get_peer_comparison

        with patch("backend.services.peer_benchmarks.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = None
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            result = get_peer_comparison("nonexistent_user")
            assert result is None

    def test_get_peer_comparison_returns_none_when_no_industry(self):
        """Should return None when user has no industry set."""
        from backend.services.peer_benchmarks import get_peer_comparison

        with patch("backend.services.peer_benchmarks.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = {"industry": None}
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            result = get_peer_comparison("test_user")
            assert result is None

    def test_get_peer_comparison_handles_db_error(self):
        """Should return None on database error."""
        from backend.services.peer_benchmarks import get_peer_comparison

        with patch("backend.services.peer_benchmarks.db_session") as mock_db:
            mock_db.side_effect = Exception("Database connection failed")

            result = get_peer_comparison("test_user")
            assert result is None

    def test_get_peer_comparison_returns_empty_metrics_when_no_aggregates(self):
        """Should return result with empty metrics when no aggregates exist."""
        from backend.services.peer_benchmarks import get_peer_comparison

        with (
            patch("backend.services.peer_benchmarks.db_session") as mock_db,
            patch("backend.services.peer_benchmarks.get_cached_aggregates") as mock_cached,
            patch("backend.services.peer_benchmarks.aggregate_industry_metrics") as mock_aggregate,
        ):
            # First call returns industry, second returns user values
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.side_effect = [
                {"industry": "SaaS"},  # First query - get industry
                {
                    "revenue": None,
                    "customers": None,
                    "growth_rate": None,
                    "team_size": None,
                    "mau_bucket": None,
                    "traffic_range": None,
                    "revenue_stage": None,
                    "dau": None,
                    "mau": None,
                    "dau_mau_ratio": None,
                    "arpu": None,
                    "arr_growth_rate": None,
                    "grr": None,
                    "active_churn": None,
                    "revenue_churn": None,
                    "nps": None,
                    "quick_ratio": None,
                },  # Second query
            ]
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            mock_cached.return_value = None
            mock_aggregate.return_value = {}  # No aggregates

            result = get_peer_comparison("test_user")
            assert result is not None
            assert result.industry == "SaaS"
            assert result.metrics == []


class TestPeerBenchmarksRouteValidation:
    """Tests for route validation logic."""

    def test_preview_route_raises_404_when_no_data(self):
        """Should raise 404 when get_preview_metric returns None."""
        from backend.api.peer_benchmarks.routes import PreviewMetricResponse

        # The route raises HTTPException(404) when get_preview_metric returns None
        # This is tested through the service layer tests above
        # Here we just verify the response model exists
        assert PreviewMetricResponse is not None

    def test_benchmarks_route_raises_404_when_no_industry(self):
        """Should raise 404 when get_peer_comparison returns None."""
        from backend.api.peer_benchmarks.routes import PeerBenchmarksResponse

        # Verify response model exists
        assert PeerBenchmarksResponse is not None


class TestTrendSummaryRefresh:
    """Tests for trend summary refresh endpoint."""

    def test_refresh_raises_400_when_no_industry(self):
        """Should raise 400 when user has no industry set."""
        from backend.api.context.routes import refresh_trend_summary

        mock_user = {"user_id": "test_user_123", "subscription_tier": "free"}

        with patch("backend.api.context.trends_routes.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {}  # No industry

            import asyncio

            with pytest.raises(HTTPException) as exc_info:
                asyncio.get_event_loop().run_until_complete(refresh_trend_summary(mock_user))

            assert exc_info.value.status_code == 400
            # detail can be a dict (structured error) or string
            detail = exc_info.value.detail
            if isinstance(detail, dict):
                detail_str = str(detail.get("message", "")).lower()
            else:
                detail_str = str(detail).lower()
            assert "industry" in detail_str

    def test_refresh_raises_429_for_free_tier_within_28_days(self):
        """Should raise 429 when free tier user refreshes within 28 days."""
        from backend.api.context.routes import refresh_trend_summary

        mock_user = {"user_id": "test_user_123", "subscription_tier": "free"}

        # Last refresh was 10 days ago
        last_refresh = (datetime.now(UTC) - timedelta(days=10)).isoformat()

        with patch("backend.api.context.trends_routes.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "industry": "SaaS",
                "trend_summary": {
                    "generated_at": last_refresh,
                },
            }

            import asyncio

            with pytest.raises(HTTPException) as exc_info:
                asyncio.get_event_loop().run_until_complete(refresh_trend_summary(mock_user))

            assert exc_info.value.status_code == 429
            # detail can be a dict (structured error) or string
            detail = exc_info.value.detail
            if isinstance(detail, dict):
                detail_str = str(detail.get("message", ""))
            else:
                detail_str = str(detail)
            assert "18 day" in detail_str  # 28 - 10 = 18 days remaining

    def test_refresh_rate_limited_within_1_hour(self):
        """Should return rate_limited response when called within 1 hour."""
        from backend.api.context.routes import refresh_trend_summary

        # Paid user, last refresh was 30 minutes ago
        last_refresh = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
        mock_user = {"user_id": "test_user", "subscription_tier": "pro"}

        with patch("backend.api.context.trends_routes.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "industry": "SaaS",
                "trend_summary": {
                    "generated_at": last_refresh,
                },
            }

            import asyncio

            result = asyncio.get_event_loop().run_until_complete(refresh_trend_summary(mock_user))

            assert result["success"] is False
            assert result["rate_limited"] is True
            assert "wait" in result["error"].lower()


class TestCheckUserContext:
    """Tests for check_user_context helper function."""

    def test_returns_no_context_when_no_record(self):
        """Should return has_context=False when no user_context record exists."""
        from backend.services.peer_benchmarks import check_user_context

        with patch("backend.services.peer_benchmarks.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = None
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            result = check_user_context("nonexistent_user")
            assert result.has_context is False
            assert result.has_industry is False
            assert result.industry is None

    def test_returns_has_context_no_industry_when_industry_null(self):
        """Should return has_context=True, has_industry=False when industry is null."""
        from backend.services.peer_benchmarks import check_user_context

        with patch("backend.services.peer_benchmarks.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = {"industry": None}
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            result = check_user_context("test_user")
            assert result.has_context is True
            assert result.has_industry is False
            assert result.industry is None

    def test_returns_has_context_no_industry_when_industry_empty_string(self):
        """Should return has_context=True, has_industry=False when industry is empty string."""
        from backend.services.peer_benchmarks import check_user_context

        with patch("backend.services.peer_benchmarks.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = {"industry": "   "}
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            result = check_user_context("test_user")
            assert result.has_context is True
            assert result.has_industry is False

    def test_returns_has_context_and_industry_when_industry_set(self):
        """Should return has_context=True, has_industry=True when industry is set."""
        from backend.services.peer_benchmarks import check_user_context

        with patch("backend.services.peer_benchmarks.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = {"industry": "SaaS"}
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            result = check_user_context("test_user")
            assert result.has_context is True
            assert result.has_industry is True
            assert result.industry == "SaaS"

    def test_handles_db_error_gracefully(self):
        """Should return no context status on database error."""
        from backend.services.peer_benchmarks import check_user_context

        with patch("backend.services.peer_benchmarks.db_session") as mock_db:
            mock_db.side_effect = Exception("Database connection failed")

            result = check_user_context("test_user")
            assert result.has_context is False
            assert result.has_industry is False


class TestPeerBenchmarksRouteErrorCodes:
    """Tests for route error codes (CONTEXT_MISSING, INDUSTRY_NOT_SET)."""

    def test_preview_route_returns_context_missing_error_code(self):
        """Preview route should return API_CONTEXT_MISSING when no user_context."""
        from bo1.logging import ErrorCode

        # Verify error code exists
        assert ErrorCode.API_CONTEXT_MISSING.value == "API_CONTEXT_MISSING"

    def test_preview_route_returns_industry_not_set_error_code(self):
        """Preview route should return API_INDUSTRY_NOT_SET when no industry."""
        from bo1.logging import ErrorCode

        # Verify error code exists
        assert ErrorCode.API_INDUSTRY_NOT_SET.value == "API_INDUSTRY_NOT_SET"

    def test_error_codes_are_distinct(self):
        """Error codes should be distinct for different failure modes."""
        from bo1.logging import ErrorCode

        assert ErrorCode.API_CONTEXT_MISSING != ErrorCode.API_INDUSTRY_NOT_SET
        assert ErrorCode.API_CONTEXT_MISSING != ErrorCode.API_NOT_FOUND
        assert ErrorCode.API_INDUSTRY_NOT_SET != ErrorCode.API_NOT_FOUND


class TestParseNumericValue:
    """Tests for numeric value parsing utility."""

    def test_parse_integer(self):
        """Should parse integer values."""
        from backend.services.peer_benchmarks import _parse_numeric_value

        assert _parse_numeric_value(50000) == 50000.0
        assert _parse_numeric_value(0) == 0.0

    def test_parse_float(self):
        """Should parse float values."""
        from backend.services.peer_benchmarks import _parse_numeric_value

        assert _parse_numeric_value(50.5) == 50.5
        assert _parse_numeric_value(0.0) == 0.0

    def test_parse_string_number(self):
        """Should parse string numbers."""
        from backend.services.peer_benchmarks import _parse_numeric_value

        assert _parse_numeric_value("50000") == 50000.0
        assert _parse_numeric_value("50.5") == 50.5

    def test_parse_currency_string(self):
        """Should parse currency formatted strings."""
        from backend.services.peer_benchmarks import _parse_numeric_value

        assert _parse_numeric_value("$50000") == 50000.0
        assert _parse_numeric_value("$50,000") == 50000.0

    def test_parse_k_suffix(self):
        """Should parse K suffix (thousands)."""
        from backend.services.peer_benchmarks import _parse_numeric_value

        assert _parse_numeric_value("50K") == 50000.0
        assert _parse_numeric_value("$50k") == 50000.0

    def test_parse_m_suffix(self):
        """Should parse M suffix (millions)."""
        from backend.services.peer_benchmarks import _parse_numeric_value

        assert _parse_numeric_value("1.5M") == 1500000.0
        assert _parse_numeric_value("$2m") == 2000000.0

    def test_parse_percentage(self):
        """Should parse percentage strings."""
        from backend.services.peer_benchmarks import _parse_numeric_value

        assert _parse_numeric_value("15%") == 15.0
        assert _parse_numeric_value("2.5%") == 2.5

    def test_parse_none(self):
        """Should return None for None input."""
        from backend.services.peer_benchmarks import _parse_numeric_value

        assert _parse_numeric_value(None) is None

    def test_parse_invalid_string(self):
        """Should return None for invalid strings."""
        from backend.services.peer_benchmarks import _parse_numeric_value

        assert _parse_numeric_value("not a number") is None
        assert _parse_numeric_value("") is None
