"""Billing API endpoints (stub implementation).

Phase 5 of ACCOUNT_CONTEXT_PLAN - Billing Integration.

This module provides stub endpoints for billing functionality.
Full Stripe integration to be implemented later.

Provides:
- GET /api/v1/billing/usage - Get usage statistics
- GET /api/v1/billing/plan - Get current plan details
- POST /api/v1/billing/portal - Create Stripe billing portal session (stub)
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])


# =============================================================================
# Models
# =============================================================================


class PlanDetails(BaseModel):
    """Current subscription plan details."""

    tier: str = Field(..., description="Subscription tier: free, starter, pro, enterprise")
    name: str = Field(..., description="Display name of the plan")
    price_monthly: int = Field(..., description="Monthly price in cents (0 for free)")
    meetings_limit: int | None = Field(
        None, description="Max meetings per month (null = unlimited)"
    )
    features: list[str] = Field(default_factory=list, description="List of included features")
    billing_cycle_start: datetime | None = Field(None, description="Start of current billing cycle")
    billing_cycle_end: datetime | None = Field(None, description="End of current billing cycle")


class UsageStats(BaseModel):
    """Usage statistics for current billing period."""

    meetings_used: int = Field(0, description="Meetings created this period")
    meetings_limit: int | None = Field(None, description="Max meetings (null = unlimited)")
    meetings_remaining: int | None = Field(
        None, description="Remaining meetings (null = unlimited)"
    )
    api_calls_used: int = Field(0, description="API calls this period")
    total_cost_cents: int = Field(0, description="Total cost incurred in cents")
    period_start: datetime | None = Field(None, description="Start of usage period")
    period_end: datetime | None = Field(None, description="End of usage period")


class BillingPortalResponse(BaseModel):
    """Response from billing portal creation."""

    url: str | None = Field(None, description="Stripe billing portal URL")
    message: str = Field(..., description="Status message")
    available: bool = Field(False, description="Whether billing portal is available")


# =============================================================================
# Plan Configuration
# =============================================================================

PLAN_CONFIG = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "meetings_limit": 3,
        "features": [
            "3 meetings per month",
            "Basic expert panel",
            "Community support",
        ],
    },
    "starter": {
        "name": "Starter",
        "price_monthly": 2900,  # $29.00
        "meetings_limit": 20,
        "features": [
            "20 meetings per month",
            "All expert personas",
            "Email support",
            "Priority processing",
        ],
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 9900,  # $99.00
        "meetings_limit": None,  # Unlimited
        "features": [
            "Unlimited meetings",
            "All expert personas",
            "Priority support",
            "API access",
            "Custom expert personas",
        ],
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 0,  # Custom pricing
        "meetings_limit": None,
        "features": [
            "Everything in Pro",
            "Dedicated support",
            "SLA guarantee",
            "Custom integrations",
            "On-premise option",
        ],
    },
}


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/v1/billing/plan",
    response_model=PlanDetails,
    summary="Get current plan details",
    description="Returns details about the user's current subscription plan.",
)
async def get_plan(user: dict[str, Any] = Depends(get_current_user)) -> PlanDetails:
    """Get user's current plan details."""
    try:
        user_id = extract_user_id(user)

        # Get user's subscription tier from database
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT subscription_tier FROM users WHERE id = %s",
                    (user_id,),
                )
                row = cur.fetchone()

        tier = row["subscription_tier"] if row else "free"
        config = PLAN_CONFIG.get(tier, PLAN_CONFIG["free"])

        return PlanDetails(
            tier=tier,
            name=config["name"],
            price_monthly=config["price_monthly"],
            meetings_limit=config["meetings_limit"],
            features=config["features"],
            billing_cycle_start=None,  # TODO: Get from Stripe
            billing_cycle_end=None,
        )

    except Exception as e:
        logger.error(f"Failed to get plan: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get plan: {str(e)}",
        ) from e


@router.get(
    "/v1/billing/usage",
    response_model=UsageStats,
    summary="Get usage statistics",
    description="Returns usage statistics for the current billing period.",
)
async def get_usage(user: dict[str, Any] = Depends(get_current_user)) -> UsageStats:
    """Get user's usage statistics."""
    try:
        user_id = extract_user_id(user)

        # Get meeting count for current month
        with db_session() as conn:
            with conn.cursor() as cur:
                # Count meetings this month
                cur.execute(
                    """
                    SELECT COUNT(*) as meeting_count
                    FROM sessions
                    WHERE user_id = %s
                    AND created_at >= date_trunc('month', CURRENT_DATE)
                    """,
                    (user_id,),
                )
                meeting_row = cur.fetchone()
                meetings_used = meeting_row["meeting_count"] if meeting_row else 0

                # Get user's tier for limit
                cur.execute(
                    "SELECT subscription_tier FROM users WHERE id = %s",
                    (user_id,),
                )
                user_row = cur.fetchone()
                tier = user_row["subscription_tier"] if user_row else "free"

                # Get total cost this month (from api_costs if available)
                cur.execute(
                    """
                    SELECT COALESCE(SUM(total_cost), 0) as total_cost
                    FROM api_costs
                    WHERE user_id = %s
                    AND created_at >= date_trunc('month', CURRENT_DATE)
                    """,
                    (user_id,),
                )
                cost_row = cur.fetchone()
                total_cost = float(cost_row["total_cost"]) if cost_row else 0.0

        config = PLAN_CONFIG.get(tier, PLAN_CONFIG["free"])
        meetings_limit = config["meetings_limit"]

        return UsageStats(
            meetings_used=meetings_used,
            meetings_limit=meetings_limit,
            meetings_remaining=(meetings_limit - meetings_used) if meetings_limit else None,
            api_calls_used=0,  # TODO: Track API calls
            total_cost_cents=int(total_cost * 100),  # Convert to cents
            period_start=None,  # TODO: Get from billing cycle
            period_end=None,
        )

    except Exception as e:
        logger.error(f"Failed to get usage: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get usage: {str(e)}",
        ) from e


@router.post(
    "/v1/billing/portal",
    response_model=BillingPortalResponse,
    summary="Create billing portal session",
    description="""
    Creates a Stripe billing portal session for the user to manage their subscription.

    **Note:** This is currently a stub. Full Stripe integration coming soon.
    """,
)
async def create_portal_session(
    user: dict[str, Any] = Depends(get_current_user),
) -> BillingPortalResponse:
    """Create Stripe billing portal session (stub)."""
    try:
        user_id = extract_user_id(user)
        logger.info(f"Billing portal requested by user {user_id}")

        # TODO: Implement Stripe billing portal
        # 1. Get or create Stripe customer ID for user
        # 2. Create billing portal session
        # 3. Return portal URL

        return BillingPortalResponse(
            url=None,
            message="Billing portal coming soon. Contact support@boardof.one for plan changes.",
            available=False,
        )

    except Exception as e:
        logger.error(f"Failed to create portal session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create portal session: {str(e)}",
        ) from e
