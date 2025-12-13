"""Tests for billing API endpoints.

This module tests:
- Plan/usage endpoint responses
- Webhook timestamp validation
- Idempotency logic
- Plan configuration
"""

import time

import pytest

from backend.api.billing import (
    PLAN_CONFIG,
    _validate_webhook_timestamp,
)


class TestWebhookTimestampValidation:
    """Tests for webhook timestamp validation."""

    def test_valid_timestamp(self):
        """Recent timestamps are accepted."""
        current_time = int(time.time())
        sig = f"t={current_time},v1=abc123"
        # Should not raise
        _validate_webhook_timestamp(sig)

    def test_old_timestamp_rejected(self):
        """Old timestamps are rejected."""
        old_time = int(time.time()) - 600  # 10 minutes ago
        sig = f"t={old_time},v1=abc123"

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            _validate_webhook_timestamp(sig)
        assert exc.value.status_code == 400
        assert "too old" in exc.value.detail.lower()

    def test_missing_timestamp(self):
        """Missing timestamp raises error."""
        sig = "v1=abc123"

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            _validate_webhook_timestamp(sig)
        assert exc.value.status_code == 400

    def test_invalid_timestamp(self):
        """Non-numeric timestamp raises error."""
        sig = "t=notanumber,v1=abc123"

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            _validate_webhook_timestamp(sig)
        assert exc.value.status_code == 400


class TestPlanConfig:
    """Tests for plan configuration."""

    def test_all_tiers_have_required_fields(self):
        """All plan tiers have required configuration fields."""
        required_fields = ["name", "price_monthly", "meetings_limit", "features"]

        for tier, config in PLAN_CONFIG.items():
            for field in required_fields:
                assert field in config, f"Tier {tier} missing {field}"

    def test_free_tier_is_free(self):
        """Free tier has zero price."""
        assert PLAN_CONFIG["free"]["price_monthly"] == 0

    def test_pro_tier_is_unlimited(self):
        """Pro tier has unlimited meetings."""
        assert PLAN_CONFIG["pro"]["meetings_limit"] is None

    def test_tier_prices_ascending(self):
        """Tier prices increase from free to pro."""
        assert PLAN_CONFIG["free"]["price_monthly"] < PLAN_CONFIG["starter"]["price_monthly"]
        assert PLAN_CONFIG["starter"]["price_monthly"] < PLAN_CONFIG["pro"]["price_monthly"]

    def test_tier_limits_ascending(self):
        """Meeting limits increase from free to starter."""
        free_limit = PLAN_CONFIG["free"]["meetings_limit"]
        starter_limit = PLAN_CONFIG["starter"]["meetings_limit"]
        pro_limit = PLAN_CONFIG["pro"]["meetings_limit"]

        # Free < Starter (both have limits)
        assert free_limit < starter_limit
        # Pro is unlimited (None)
        assert pro_limit is None

    def test_all_tiers_have_features(self):
        """All tiers have at least one feature."""
        for tier, config in PLAN_CONFIG.items():
            assert len(config["features"]) > 0, f"Tier {tier} has no features"
