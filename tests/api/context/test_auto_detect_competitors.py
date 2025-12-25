"""Tests for auto-detect competitors functionality."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.api.context.auto_detect import (
    AUTO_DETECT_COOLDOWN_HOURS,
    MIN_COMPETITORS_FOR_SKIP,
    _can_auto_detect,
    _record_auto_detect,
    get_auto_detect_status,
    run_auto_detect_competitors,
    should_trigger_auto_detect,
)


class TestShouldTriggerAutoDetect:
    """Tests for should_trigger_auto_detect function."""

    def test_triggers_with_company_name(self):
        """Should trigger when user has company_name and few competitors."""
        context = {
            "company_name": "Acme Inc",
            "managed_competitors": [],
        }
        with patch("backend.api.context.auto_detect._can_auto_detect", return_value=True):
            assert should_trigger_auto_detect("user123", context) is True

    def test_triggers_with_industry_and_product(self):
        """Should trigger when user has industry + product_description."""
        context = {
            "industry": "SaaS",
            "product_description": "A tool for teams",
            "managed_competitors": [],
        }
        with patch("backend.api.context.auto_detect._can_auto_detect", return_value=True):
            assert should_trigger_auto_detect("user123", context) is True

    def test_no_trigger_without_context(self):
        """Should not trigger without sufficient context."""
        context = {
            "managed_competitors": [],
        }
        assert should_trigger_auto_detect("user123", context) is False

    def test_no_trigger_with_only_industry(self):
        """Should not trigger with only industry (needs product too)."""
        context = {
            "industry": "SaaS",
            "managed_competitors": [],
        }
        assert should_trigger_auto_detect("user123", context) is False

    def test_no_trigger_when_has_enough_competitors(self):
        """Should not trigger when user already has 3+ competitors."""
        context = {
            "company_name": "Acme Inc",
            "managed_competitors": [
                {"name": "Competitor 1"},
                {"name": "Competitor 2"},
                {"name": "Competitor 3"},
            ],
        }
        assert should_trigger_auto_detect("user123", context) is False

    def test_no_trigger_when_rate_limited(self):
        """Should not trigger when rate limited."""
        context = {
            "company_name": "Acme Inc",
            "managed_competitors": [],
        }
        with patch("backend.api.context.auto_detect._can_auto_detect", return_value=False):
            assert should_trigger_auto_detect("user123", context) is False


class TestRateLimiting:
    """Tests for rate limiting functions."""

    def test_can_auto_detect_no_previous(self):
        """Should allow when no previous detection."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        with patch(
            "backend.api.dependencies.get_redis_manager",
            return_value=mock_redis,
        ):
            assert _can_auto_detect("user123") is True

    def test_can_auto_detect_after_cooldown(self):
        """Should allow after cooldown period."""
        mock_redis = MagicMock()
        # Set timestamp 25 hours ago
        old_time = datetime.now(UTC) - timedelta(hours=AUTO_DETECT_COOLDOWN_HOURS + 1)
        mock_redis.get.return_value = old_time.isoformat().encode()

        with patch(
            "backend.api.dependencies.get_redis_manager",
            return_value=mock_redis,
        ):
            assert _can_auto_detect("user123") is True

    def test_can_auto_detect_within_cooldown(self):
        """Should block within cooldown period."""
        mock_redis = MagicMock()
        # Set timestamp 1 hour ago
        recent_time = datetime.now(UTC) - timedelta(hours=1)
        mock_redis.get.return_value = recent_time.isoformat().encode()

        with patch(
            "backend.api.dependencies.get_redis_manager",
            return_value=mock_redis,
        ):
            assert _can_auto_detect("user123") is False

    def test_can_auto_detect_redis_error(self):
        """Should allow on Redis error (fail open)."""
        with patch(
            "backend.api.dependencies.get_redis_manager",
            side_effect=Exception("Redis down"),
        ):
            assert _can_auto_detect("user123") is True

    def test_record_auto_detect_sets_key(self):
        """Should set Redis key with timestamp."""
        mock_redis = MagicMock()

        with patch(
            "backend.api.dependencies.get_redis_manager",
            return_value=mock_redis,
        ):
            _record_auto_detect("user123")
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args[0]
            assert call_args[0] == "autodetect:competitor:user123"
            assert call_args[1] == 90000  # 25 hours in seconds


class TestGetAutoDetectStatus:
    """Tests for get_auto_detect_status function."""

    def test_returns_status_with_context(self):
        """Should return correct status when context exists."""
        mock_context = {
            "company_name": "Acme Inc",
            "managed_competitors": [{"name": "Comp1"}, {"name": "Comp2"}],
            "last_competitor_auto_detect": {
                "completed_at": "2025-01-01T12:00:00+00:00",
                "count": 3,
            },
        }

        with (
            patch(
                "backend.api.context.auto_detect.user_repository.get_context",
                return_value=mock_context,
            ),
            patch(
                "backend.api.context.auto_detect._can_auto_detect",
                return_value=True,
            ),
        ):
            status = get_auto_detect_status("user123")

            assert status["competitor_count"] == 2
            assert status["last_auto_detect_at"] == "2025-01-01T12:00:00+00:00"
            assert status["needs_competitor_refresh"] is True

    def test_returns_status_without_context(self):
        """Should return defaults when no context."""
        with patch(
            "backend.api.context.auto_detect.user_repository.get_context",
            return_value=None,
        ):
            status = get_auto_detect_status("user123")

            assert status["competitor_count"] == 0
            assert status["last_auto_detect_at"] is None
            assert status["needs_competitor_refresh"] is False


class TestRunAutoDetectCompetitors:
    """Tests for run_auto_detect_competitors function."""

    @pytest.mark.asyncio
    async def test_runs_detection_successfully(self):
        """Should run detection and save results."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.competitors = [MagicMock(name="Comp1"), MagicMock(name="Comp2")]

        with (
            patch(
                "backend.api.context.competitors.detect_competitors_for_user",
                new_callable=AsyncMock,
                return_value=mock_result,
            ) as mock_detect,
            patch.object(
                __import__("backend.api.context.auto_detect", fromlist=["_record_auto_detect"]),
                "_record_auto_detect",
            ) as mock_record,
            patch.object(
                __import__(
                    "backend.api.context.auto_detect", fromlist=["_mark_auto_detect_complete"]
                ),
                "_mark_auto_detect_complete",
            ) as mock_mark,
        ):
            await run_auto_detect_competitors("user123")

            mock_record.assert_called_once_with("user123")
            mock_detect.assert_called_once_with("user123")
            mock_mark.assert_called_once_with("user123", 2)

    @pytest.mark.asyncio
    async def test_handles_detection_failure(self):
        """Should handle detection failure gracefully."""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "API error"

        with (
            patch(
                "backend.api.context.competitors.detect_competitors_for_user",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
            patch.object(
                __import__("backend.api.context.auto_detect", fromlist=["_record_auto_detect"]),
                "_record_auto_detect",
            ),
            patch.object(
                __import__(
                    "backend.api.context.auto_detect", fromlist=["_mark_auto_detect_complete"]
                ),
                "_mark_auto_detect_complete",
            ) as mock_mark,
        ):
            # Should not raise
            await run_auto_detect_competitors("user123")

            # Should not mark complete on failure
            mock_mark.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        """Should handle exceptions without crashing."""
        with (
            patch(
                "backend.api.context.competitors.detect_competitors_for_user",
                new_callable=AsyncMock,
                side_effect=Exception("Network error"),
            ),
            patch.object(
                __import__("backend.api.context.auto_detect", fromlist=["_record_auto_detect"]),
                "_record_auto_detect",
            ),
        ):
            # Should not raise
            await run_auto_detect_competitors("user123")


class TestMinCompetitorsConstant:
    """Tests for configuration constants."""

    def test_min_competitors_for_skip(self):
        """MIN_COMPETITORS_FOR_SKIP should be 3."""
        assert MIN_COMPETITORS_FOR_SKIP == 3

    def test_cooldown_hours(self):
        """AUTO_DETECT_COOLDOWN_HOURS should be 24."""
        assert AUTO_DETECT_COOLDOWN_HOURS == 24
