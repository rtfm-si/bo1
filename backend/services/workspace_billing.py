"""Workspace billing service.

Provides billing operations for team workspaces:
- Checkout session creation (with permission checks)
- Portal session creation
- Tier resolution and subscription management

Usage:
    from backend.services.workspace_billing import workspace_billing_service

    # Create checkout session for workspace
    result = await workspace_billing_service.create_checkout_session(
        workspace_id=workspace_id,
        user_id=user_id,
        price_id="price_xxx",
    )
"""

import logging
import uuid
from dataclasses import dataclass

from backend.api.workspaces.models import MemberRole
from backend.services.stripe_service import stripe_service
from backend.services.workspace_auth import check_role
from bo1.config import get_settings
from bo1.state.repositories.workspace_repository import workspace_repository

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceBillingInfo:
    """Billing information for a workspace."""

    workspace_id: uuid.UUID
    workspace_name: str
    tier: str
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    billing_email: str | None
    billing_owner_id: str | None
    owner_id: str
    is_billing_owner: bool  # Whether current user is billing owner


@dataclass
class WorkspaceCheckoutResult:
    """Result from workspace checkout session creation."""

    session_id: str
    url: str


class WorkspaceBillingError(Exception):
    """Error during workspace billing operation."""

    def __init__(self, message: str, code: str = "billing_error") -> None:
        """Initialize workspace billing error."""
        self.message = message
        self.code = code
        super().__init__(message)


class WorkspaceBillingService:
    """Service for workspace-level billing operations."""

    async def create_checkout_session(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
        price_id: str,
    ) -> WorkspaceCheckoutResult:
        """Create a Stripe checkout session for workspace subscription.

        Args:
            workspace_id: Workspace UUID
            user_id: User requesting checkout (must be owner/admin)
            price_id: Stripe price ID for the plan

        Returns:
            WorkspaceCheckoutResult with session URL

        Raises:
            WorkspaceBillingError: If permission denied or workspace not found
        """
        # Verify permission (owner or admin required)
        if not check_role(workspace_id, user_id, MemberRole.ADMIN):
            raise WorkspaceBillingError(
                "Only workspace owners and admins can manage billing",
                code="permission_denied",
            )

        # Get workspace info
        billing_info = workspace_repository.get_billing_info(workspace_id)
        if not billing_info:
            raise WorkspaceBillingError(
                "Workspace not found",
                code="not_found",
            )

        # Get or create Stripe customer for workspace
        billing_email = billing_info["billing_email"]
        existing_customer_id = billing_info["stripe_customer_id"]

        # Use workspace owner's email as billing email if not set
        if not billing_email:
            from bo1.state.repositories.user_repository import user_repository

            owner_id = billing_info["owner_id"]
            owner = user_repository.get_user_by_id(owner_id)
            billing_email = owner.get("email") if owner else None

        customer = await stripe_service.get_or_create_customer(
            user_id=f"workspace_{workspace_id}",  # Prefix to distinguish from user customers
            email=billing_email or f"billing@workspace-{workspace_id}",
            existing_customer_id=existing_customer_id,
        )

        # Save customer ID if newly created
        if not existing_customer_id:
            workspace_repository.set_stripe_customer(
                workspace_id,
                customer.id,
                billing_email,
            )

        # Set billing owner if not set
        if not billing_info["billing_owner_id"]:
            workspace_repository.set_billing_owner(workspace_id, user_id)

        # Build success/cancel URLs
        settings = get_settings()
        base_url = settings.frontend_url.rstrip("/")
        success_url = (
            f"{base_url}/settings/workspace/billing?success=true&session_id={{CHECKOUT_SESSION_ID}}"
        )
        cancel_url = f"{base_url}/settings/workspace/billing?cancelled=true"

        # Create checkout session with workspace metadata
        result = await stripe_service.create_checkout_session(
            customer_id=customer.id,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        logger.info(
            f"Created workspace checkout session {result.session_id} "
            f"for workspace {workspace_id} by user {user_id}"
        )

        return WorkspaceCheckoutResult(
            session_id=result.session_id,
            url=result.url,
        )

    async def create_portal_session(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
    ) -> str:
        """Create a Stripe billing portal session for workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User requesting portal (must be billing owner or admin)

        Returns:
            Portal URL

        Raises:
            WorkspaceBillingError: If permission denied or no billing account
        """
        # Get billing info
        billing_info = workspace_repository.get_billing_info(workspace_id)
        if not billing_info:
            raise WorkspaceBillingError(
                "Workspace not found",
                code="not_found",
            )

        # Check permission: billing owner, owner, or admin
        billing_owner_id = billing_info["billing_owner_id"]
        is_billing_owner = billing_owner_id == user_id
        is_owner = billing_info["owner_id"] == user_id
        is_admin = check_role(workspace_id, user_id, MemberRole.ADMIN)

        if not (is_billing_owner or is_owner or is_admin):
            raise WorkspaceBillingError(
                "Only billing owner, workspace owner, or admins can access billing portal",
                code="permission_denied",
            )

        # Check for Stripe customer
        customer_id = billing_info["stripe_customer_id"]
        if not customer_id:
            raise WorkspaceBillingError(
                "No billing account found. Subscribe to a plan first.",
                code="no_billing_account",
            )

        # Build return URL
        settings = get_settings()
        return_url = f"{settings.frontend_url.rstrip('/')}/settings/workspace/billing"

        # Create portal session
        result = await stripe_service.create_portal_session(
            customer_id=customer_id,
            return_url=return_url,
        )

        logger.info(
            f"Created workspace billing portal for workspace {workspace_id} by user {user_id}"
        )

        return result.url

    def get_billing_info(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
    ) -> WorkspaceBillingInfo:
        """Get billing information for a workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: Current user (for billing owner flag)

        Returns:
            WorkspaceBillingInfo

        Raises:
            WorkspaceBillingError: If workspace not found
        """
        billing_info = workspace_repository.get_billing_info(workspace_id)
        if not billing_info:
            raise WorkspaceBillingError(
                "Workspace not found",
                code="not_found",
            )

        billing_owner_id = billing_info["billing_owner_id"]
        is_billing_owner = billing_owner_id == user_id or (
            billing_owner_id is None and billing_info["owner_id"] == user_id
        )

        return WorkspaceBillingInfo(
            workspace_id=billing_info["workspace_id"],
            workspace_name=billing_info["name"],
            tier=billing_info["tier"],
            stripe_customer_id=billing_info["stripe_customer_id"],
            stripe_subscription_id=billing_info["stripe_subscription_id"],
            billing_email=billing_info["billing_email"],
            billing_owner_id=billing_info["billing_owner_id"],
            owner_id=billing_info["owner_id"],
            is_billing_owner=is_billing_owner,
        )

    def get_workspace_tier(self, workspace_id: uuid.UUID) -> str:
        """Get subscription tier for a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Tier string (free, starter, pro, enterprise)
        """
        return workspace_repository.get_workspace_tier(workspace_id)

    async def sync_subscription_status(self, workspace_id: uuid.UUID) -> str | None:
        """Sync subscription status from Stripe.

        Refreshes the workspace tier based on current Stripe subscription state.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Current tier after sync, or None if no subscription
        """
        billing_info = workspace_repository.get_billing_info(workspace_id)
        if not billing_info:
            return None

        subscription_id = billing_info["stripe_subscription_id"]
        if not subscription_id:
            return billing_info["tier"]

        # Get subscription from Stripe
        subscription = await stripe_service.get_subscription(subscription_id)
        if not subscription:
            # Subscription not found - clear it
            workspace_repository.clear_subscription(workspace_id)
            logger.warning(
                f"Subscription {subscription_id} not found for workspace {workspace_id}, "
                "cleared subscription"
            )
            return "free"

        # Check subscription status
        if subscription.status in ("active", "trialing"):
            # Update tier based on current price
            if subscription.items.data:
                price_id = subscription.items.data[0].price.id
                tier = stripe_service.get_tier_for_price(price_id) or "starter"
                workspace_repository.set_subscription(workspace_id, subscription_id, tier)
                return tier
        elif subscription.status in ("canceled", "unpaid", "past_due"):
            # Downgrade to free
            workspace_repository.clear_subscription(workspace_id)
            logger.info(
                f"Workspace {workspace_id} subscription {subscription.status}, downgraded to free"
            )
            return "free"

        return billing_info["tier"]


# Singleton instance
workspace_billing_service = WorkspaceBillingService()
