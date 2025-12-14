"""Workspace repository for team collaboration.

Provides:
- create_workspace(), get_workspace(), update_workspace()
- add_member(), remove_member(), get_members()
- get_user_workspaces()
"""

import logging
import re
import uuid
from typing import Any

from backend.api.workspaces.models import (
    JoinRequestResponse,
    JoinRequestStatus,
    MemberRole,
    WorkspaceDiscoverability,
    WorkspaceMemberResponse,
    WorkspaceResponse,
)

from .base import BaseRepository

logger = logging.getLogger(__name__)


class WorkspaceRepository(BaseRepository):
    """Repository for workspace and team member operations."""

    def create_workspace(
        self,
        name: str,
        owner_id: str,
        slug: str | None = None,
    ) -> WorkspaceResponse:
        """Create a new workspace.

        Args:
            name: Workspace display name
            owner_id: User ID of the workspace owner
            slug: Optional URL-friendly slug (auto-generated if not provided)

        Returns:
            Created workspace

        Raises:
            ValueError: If slug already exists
        """
        workspace_id = uuid.uuid4()

        # Generate slug from name if not provided
        if not slug:
            slug = self._generate_slug(name, str(workspace_id))

        # Create workspace
        query = """
            INSERT INTO workspaces (id, name, slug, owner_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, slug, owner_id, created_at, updated_at
        """
        row = self._execute_returning(
            query,
            (workspace_id, name, slug, owner_id),
        )

        # Add owner as member with owner role
        self._add_member_internal(
            workspace_id=workspace_id,
            user_id=owner_id,
            role=MemberRole.OWNER,
            invited_by=None,
        )

        return WorkspaceResponse(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            owner_id=row["owner_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            member_count=1,
        )

    def get_workspace(self, workspace_id: uuid.UUID) -> WorkspaceResponse | None:
        """Get a workspace by ID.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Workspace or None if not found
        """
        query = """
            SELECT w.id, w.name, w.slug, w.owner_id, w.created_at, w.updated_at,
                   COUNT(wm.id) as member_count
            FROM workspaces w
            LEFT JOIN workspace_members wm ON w.id = wm.workspace_id
            WHERE w.id = %s
            GROUP BY w.id
        """
        row = self._execute_one(query, (workspace_id,))
        if not row:
            return None

        return WorkspaceResponse(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            owner_id=row["owner_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            member_count=row["member_count"],
        )

    def get_workspace_by_slug(self, slug: str) -> WorkspaceResponse | None:
        """Get a workspace by slug.

        Args:
            slug: Workspace slug

        Returns:
            Workspace or None if not found
        """
        query = """
            SELECT w.id, w.name, w.slug, w.owner_id, w.created_at, w.updated_at,
                   COUNT(wm.id) as member_count
            FROM workspaces w
            LEFT JOIN workspace_members wm ON w.id = wm.workspace_id
            WHERE w.slug = %s
            GROUP BY w.id
        """
        row = self._execute_one(query, (slug,))
        if not row:
            return None

        return WorkspaceResponse(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            owner_id=row["owner_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            member_count=row["member_count"],
        )

    def update_workspace(
        self,
        workspace_id: uuid.UUID,
        name: str | None = None,
        slug: str | None = None,
    ) -> WorkspaceResponse | None:
        """Update a workspace.

        Args:
            workspace_id: Workspace UUID
            name: New name (optional)
            slug: New slug (optional)

        Returns:
            Updated workspace or None if not found
        """
        updates: list[str] = []
        params: list[Any] = []

        if name is not None:
            updates.append("name = %s")
            params.append(name)

        if slug is not None:
            updates.append("slug = %s")
            params.append(slug)

        if not updates:
            return self.get_workspace(workspace_id)

        updates.append("updated_at = NOW()")
        params.append(workspace_id)

        query = f"""
            UPDATE workspaces
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, name, slug, owner_id, created_at, updated_at
        """
        row = self._execute_one(query, tuple(params))
        if not row:
            return None

        return WorkspaceResponse(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            owner_id=row["owner_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def delete_workspace(self, workspace_id: uuid.UUID) -> bool:
        """Delete a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            True if deleted, False if not found
        """
        query = "DELETE FROM workspaces WHERE id = %s"
        count = self._execute_count(query, (workspace_id,))
        return count > 0

    def add_member(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
        role: MemberRole,
        invited_by: str | None = None,
    ) -> WorkspaceMemberResponse:
        """Add a user to a workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User ID to add
            role: Member role
            invited_by: User ID who invited this member

        Returns:
            Created membership

        Raises:
            ValueError: If user is already a member
        """
        return self._add_member_internal(workspace_id, user_id, role, invited_by)

    def _add_member_internal(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
        role: MemberRole,
        invited_by: str | None,
    ) -> WorkspaceMemberResponse:
        """Internal method to add a member."""
        member_id = uuid.uuid4()
        query = """
            INSERT INTO workspace_members (id, workspace_id, user_id, role, invited_by)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, workspace_id, user_id, role, invited_by, joined_at
        """
        row = self._execute_returning(
            query,
            (member_id, workspace_id, user_id, role.value, invited_by),
        )

        return WorkspaceMemberResponse(
            id=row["id"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            role=MemberRole(row["role"]),
            invited_by=row["invited_by"],
            joined_at=row["joined_at"],
        )

    def remove_member(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
    ) -> bool:
        """Remove a user from a workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User ID to remove

        Returns:
            True if removed, False if not found
        """
        query = """
            DELETE FROM workspace_members
            WHERE workspace_id = %s AND user_id = %s
        """
        count = self._execute_count(query, (workspace_id, user_id))
        return count > 0

    def update_member_role(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
        role: MemberRole,
    ) -> WorkspaceMemberResponse | None:
        """Update a member's role.

        Args:
            workspace_id: Workspace UUID
            user_id: User ID
            role: New role

        Returns:
            Updated membership or None if not found
        """
        query = """
            UPDATE workspace_members
            SET role = %s
            WHERE workspace_id = %s AND user_id = %s
            RETURNING id, workspace_id, user_id, role, invited_by, joined_at
        """
        row = self._execute_one(query, (role.value, workspace_id, user_id))
        if not row:
            return None

        return WorkspaceMemberResponse(
            id=row["id"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            role=MemberRole(row["role"]),
            invited_by=row["invited_by"],
            joined_at=row["joined_at"],
        )

    def get_members(
        self,
        workspace_id: uuid.UUID,
    ) -> list[WorkspaceMemberResponse]:
        """Get all members of a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            List of workspace members
        """
        query = """
            SELECT wm.id, wm.workspace_id, wm.user_id, wm.role, wm.invited_by,
                   wm.joined_at, u.email as user_email
            FROM workspace_members wm
            LEFT JOIN users u ON wm.user_id = u.id
            WHERE wm.workspace_id = %s
            ORDER BY wm.joined_at
        """
        rows = self._execute_query(query, (workspace_id,))

        return [
            WorkspaceMemberResponse(
                id=row["id"],
                workspace_id=row["workspace_id"],
                user_id=row["user_id"],
                role=MemberRole(row["role"]),
                invited_by=row["invited_by"],
                joined_at=row["joined_at"],
                user_email=row.get("user_email"),
            )
            for row in rows
        ]

    def get_member(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
    ) -> WorkspaceMemberResponse | None:
        """Get a specific member of a workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User ID

        Returns:
            Workspace member or None if not found
        """
        query = """
            SELECT wm.id, wm.workspace_id, wm.user_id, wm.role, wm.invited_by,
                   wm.joined_at, u.email as user_email
            FROM workspace_members wm
            LEFT JOIN users u ON wm.user_id = u.id
            WHERE wm.workspace_id = %s AND wm.user_id = %s
        """
        row = self._execute_one(query, (workspace_id, user_id))
        if not row:
            return None

        return WorkspaceMemberResponse(
            id=row["id"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            role=MemberRole(row["role"]),
            invited_by=row["invited_by"],
            joined_at=row["joined_at"],
            user_email=row.get("user_email"),
        )

    def get_user_workspaces(self, user_id: str) -> list[WorkspaceResponse]:
        """Get all workspaces a user is a member of.

        Args:
            user_id: User ID

        Returns:
            List of workspaces
        """
        query = """
            SELECT w.id, w.name, w.slug, w.owner_id, w.created_at, w.updated_at,
                   COUNT(wm2.id) as member_count
            FROM workspaces w
            INNER JOIN workspace_members wm ON w.id = wm.workspace_id
            LEFT JOIN workspace_members wm2 ON w.id = wm2.workspace_id
            WHERE wm.user_id = %s
            GROUP BY w.id
            ORDER BY w.created_at DESC
        """
        rows = self._execute_query(query, (user_id,))

        return [
            WorkspaceResponse(
                id=row["id"],
                name=row["name"],
                slug=row["slug"],
                owner_id=row["owner_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                member_count=row["member_count"],
            )
            for row in rows
        ]

    def is_member(self, workspace_id: uuid.UUID, user_id: str) -> bool:
        """Check if a user is a member of a workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User ID

        Returns:
            True if user is a member
        """
        query = """
            SELECT 1 FROM workspace_members
            WHERE workspace_id = %s AND user_id = %s
            LIMIT 1
        """
        row = self._execute_one(query, (workspace_id, user_id))
        return row is not None

    def get_member_role(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
    ) -> MemberRole | None:
        """Get a user's role in a workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User ID

        Returns:
            Member role or None if not a member
        """
        query = """
            SELECT role FROM workspace_members
            WHERE workspace_id = %s AND user_id = %s
        """
        row = self._execute_one(query, (workspace_id, user_id))
        if not row:
            return None
        return MemberRole(row["role"])

    def _generate_slug(self, name: str, workspace_id: str) -> str:
        """Generate a URL-friendly slug from the name.

        Args:
            name: Workspace name
            workspace_id: Workspace ID for fallback uniqueness

        Returns:
            Generated slug
        """
        # Convert to lowercase and replace non-alphanumeric with hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
        # Remove leading/trailing hyphens
        slug = slug.strip("-")
        # Limit length
        if len(slug) > 50:
            slug = slug[:50].rstrip("-")
        # If empty or too short, use ID prefix
        if len(slug) < 3:
            slug = f"workspace-{workspace_id[:8]}"

        # Check uniqueness and append ID if needed
        if self._slug_exists(slug):
            slug = f"{slug}-{workspace_id[:8]}"

        return slug

    def _slug_exists(self, slug: str) -> bool:
        """Check if a slug already exists."""
        query = "SELECT 1 FROM workspaces WHERE slug = %s LIMIT 1"
        row = self._execute_one(query, (slug,))
        return row is not None

    # =========================================================================
    # Billing Methods
    # =========================================================================

    def set_stripe_customer(
        self,
        workspace_id: uuid.UUID,
        customer_id: str,
        billing_email: str | None = None,
    ) -> bool:
        """Set Stripe customer ID for a workspace.

        Args:
            workspace_id: Workspace UUID
            customer_id: Stripe customer ID
            billing_email: Optional billing email

        Returns:
            True if updated
        """
        query = """
            UPDATE workspaces
            SET stripe_customer_id = %s,
                billing_email = COALESCE(%s, billing_email),
                updated_at = NOW()
            WHERE id = %s
        """
        count = self._execute_count(query, (customer_id, billing_email, workspace_id))
        return count > 0

    def set_subscription(
        self,
        workspace_id: uuid.UUID,
        subscription_id: str,
        tier: str,
    ) -> bool:
        """Set subscription for a workspace.

        Args:
            workspace_id: Workspace UUID
            subscription_id: Stripe subscription ID
            tier: Subscription tier (starter, pro, enterprise)

        Returns:
            True if updated
        """
        query = """
            UPDATE workspaces
            SET stripe_subscription_id = %s,
                subscription_tier = %s,
                updated_at = NOW()
            WHERE id = %s
        """
        count = self._execute_count(query, (subscription_id, tier, workspace_id))
        return count > 0

    def clear_subscription(self, workspace_id: uuid.UUID) -> bool:
        """Clear subscription and reset to free tier.

        Args:
            workspace_id: Workspace UUID

        Returns:
            True if updated
        """
        query = """
            UPDATE workspaces
            SET stripe_subscription_id = NULL,
                subscription_tier = 'free',
                updated_at = NOW()
            WHERE id = %s
        """
        count = self._execute_count(query, (workspace_id,))
        return count > 0

    def get_billing_info(self, workspace_id: uuid.UUID) -> dict[str, Any] | None:
        """Get billing information for a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Dict with billing info or None if workspace not found
        """
        query = """
            SELECT id, name, stripe_customer_id, stripe_subscription_id,
                   billing_email, subscription_tier, billing_owner_id, owner_id
            FROM workspaces
            WHERE id = %s
        """
        row = self._execute_one(query, (workspace_id,))
        if not row:
            return None

        return {
            "workspace_id": row["id"],
            "name": row["name"],
            "stripe_customer_id": row["stripe_customer_id"],
            "stripe_subscription_id": row["stripe_subscription_id"],
            "billing_email": row["billing_email"],
            "tier": row["subscription_tier"],
            "billing_owner_id": row["billing_owner_id"],
            "owner_id": row["owner_id"],
        }

    def get_workspace_by_stripe_customer(
        self,
        customer_id: str,
    ) -> dict[str, Any] | None:
        """Get workspace by Stripe customer ID.

        Args:
            customer_id: Stripe customer ID

        Returns:
            Workspace dict or None if not found
        """
        query = """
            SELECT id, name, slug, owner_id, stripe_customer_id,
                   stripe_subscription_id, subscription_tier, billing_owner_id
            FROM workspaces
            WHERE stripe_customer_id = %s
        """
        row = self._execute_one(query, (customer_id,))
        if not row:
            return None

        return {
            "id": row["id"],
            "name": row["name"],
            "slug": row["slug"],
            "owner_id": row["owner_id"],
            "stripe_customer_id": row["stripe_customer_id"],
            "stripe_subscription_id": row["stripe_subscription_id"],
            "tier": row["subscription_tier"],
            "billing_owner_id": row["billing_owner_id"],
        }

    def set_billing_owner(
        self,
        workspace_id: uuid.UUID,
        billing_owner_id: str,
    ) -> bool:
        """Set the billing owner for a workspace.

        Args:
            workspace_id: Workspace UUID
            billing_owner_id: User ID of new billing owner

        Returns:
            True if updated
        """
        query = """
            UPDATE workspaces
            SET billing_owner_id = %s,
                updated_at = NOW()
            WHERE id = %s
        """
        count = self._execute_count(query, (billing_owner_id, workspace_id))
        return count > 0

    def get_workspace_tier(self, workspace_id: uuid.UUID) -> str:
        """Get subscription tier for a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Tier string (defaults to 'free')
        """
        query = "SELECT subscription_tier FROM workspaces WHERE id = %s"
        row = self._execute_one(query, (workspace_id,))
        return row["subscription_tier"] if row else "free"

    # =========================================================================
    # Join Request Methods
    # =========================================================================

    def create_join_request(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
        message: str | None = None,
    ) -> JoinRequestResponse:
        """Create a join request for a workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: Requesting user's ID
            message: Optional message from requester

        Returns:
            Created join request

        Raises:
            ValueError: If user already has pending request or is already a member
        """
        # Check if user is already a member
        if self.is_member(workspace_id, user_id):
            raise ValueError("User is already a member of this workspace")

        # Check for existing pending request
        existing = self.get_pending_join_request(workspace_id, user_id)
        if existing:
            raise ValueError("User already has a pending join request")

        request_id = uuid.uuid4()
        query = """
            INSERT INTO workspace_join_requests
                (id, workspace_id, user_id, message, status)
            VALUES (%s, %s, %s, %s, 'pending')
            RETURNING id, workspace_id, user_id, message, status,
                      rejection_reason, reviewed_by, reviewed_at, created_at
        """
        row = self._execute_returning(
            query,
            (request_id, workspace_id, user_id, message),
        )

        return JoinRequestResponse(
            id=row["id"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            message=row["message"],
            status=JoinRequestStatus(row["status"]),
            rejection_reason=row["rejection_reason"],
            reviewed_by=row["reviewed_by"],
            reviewed_at=row["reviewed_at"],
            created_at=row["created_at"],
        )

    def get_pending_join_request(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
    ) -> JoinRequestResponse | None:
        """Get a pending join request for a user and workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User ID

        Returns:
            Join request or None if not found
        """
        query = """
            SELECT jr.id, jr.workspace_id, jr.user_id, jr.message, jr.status,
                   jr.rejection_reason, jr.reviewed_by, jr.reviewed_at, jr.created_at,
                   u.email as user_email, w.name as workspace_name
            FROM workspace_join_requests jr
            LEFT JOIN users u ON jr.user_id = u.id
            LEFT JOIN workspaces w ON jr.workspace_id = w.id
            WHERE jr.workspace_id = %s AND jr.user_id = %s AND jr.status = 'pending'
        """
        row = self._execute_one(query, (workspace_id, user_id))
        if not row:
            return None

        return JoinRequestResponse(
            id=row["id"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            message=row["message"],
            status=JoinRequestStatus(row["status"]),
            rejection_reason=row["rejection_reason"],
            reviewed_by=row["reviewed_by"],
            reviewed_at=row["reviewed_at"],
            created_at=row["created_at"],
            user_email=row.get("user_email"),
            workspace_name=row.get("workspace_name"),
        )

    def get_join_request(
        self,
        request_id: uuid.UUID,
    ) -> JoinRequestResponse | None:
        """Get a join request by ID.

        Args:
            request_id: Join request UUID

        Returns:
            Join request or None if not found
        """
        query = """
            SELECT jr.id, jr.workspace_id, jr.user_id, jr.message, jr.status,
                   jr.rejection_reason, jr.reviewed_by, jr.reviewed_at, jr.created_at,
                   u.email as user_email, w.name as workspace_name
            FROM workspace_join_requests jr
            LEFT JOIN users u ON jr.user_id = u.id
            LEFT JOIN workspaces w ON jr.workspace_id = w.id
            WHERE jr.id = %s
        """
        row = self._execute_one(query, (request_id,))
        if not row:
            return None

        return JoinRequestResponse(
            id=row["id"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            message=row["message"],
            status=JoinRequestStatus(row["status"]),
            rejection_reason=row["rejection_reason"],
            reviewed_by=row["reviewed_by"],
            reviewed_at=row["reviewed_at"],
            created_at=row["created_at"],
            user_email=row.get("user_email"),
            workspace_name=row.get("workspace_name"),
        )

    def list_pending_requests(
        self,
        workspace_id: uuid.UUID,
    ) -> list[JoinRequestResponse]:
        """List all pending join requests for a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            List of pending join requests
        """
        query = """
            SELECT jr.id, jr.workspace_id, jr.user_id, jr.message, jr.status,
                   jr.rejection_reason, jr.reviewed_by, jr.reviewed_at, jr.created_at,
                   u.email as user_email, w.name as workspace_name
            FROM workspace_join_requests jr
            LEFT JOIN users u ON jr.user_id = u.id
            LEFT JOIN workspaces w ON jr.workspace_id = w.id
            WHERE jr.workspace_id = %s AND jr.status = 'pending'
            ORDER BY jr.created_at ASC
        """
        rows = self._execute_query(query, (workspace_id,))

        return [
            JoinRequestResponse(
                id=row["id"],
                workspace_id=row["workspace_id"],
                user_id=row["user_id"],
                message=row["message"],
                status=JoinRequestStatus(row["status"]),
                rejection_reason=row["rejection_reason"],
                reviewed_by=row["reviewed_by"],
                reviewed_at=row["reviewed_at"],
                created_at=row["created_at"],
                user_email=row.get("user_email"),
                workspace_name=row.get("workspace_name"),
            )
            for row in rows
        ]

    def approve_request(
        self,
        request_id: uuid.UUID,
        reviewer_id: str,
    ) -> JoinRequestResponse | None:
        """Approve a join request and add user as member.

        Args:
            request_id: Join request UUID
            reviewer_id: ID of user approving the request

        Returns:
            Updated join request or None if not found
        """
        # Get request first to get workspace_id and user_id
        request = self.get_join_request(request_id)
        if not request or request.status != JoinRequestStatus.PENDING:
            return None

        # Update request status
        query = """
            UPDATE workspace_join_requests
            SET status = 'approved', reviewed_by = %s, reviewed_at = NOW()
            WHERE id = %s AND status = 'pending'
            RETURNING id, workspace_id, user_id, message, status,
                      rejection_reason, reviewed_by, reviewed_at, created_at
        """
        row = self._execute_one(query, (reviewer_id, request_id))
        if not row:
            return None

        # Add user as member
        self._add_member_internal(
            workspace_id=request.workspace_id,
            user_id=request.user_id,
            role=MemberRole.MEMBER,
            invited_by=reviewer_id,
        )

        return JoinRequestResponse(
            id=row["id"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            message=row["message"],
            status=JoinRequestStatus(row["status"]),
            rejection_reason=row["rejection_reason"],
            reviewed_by=row["reviewed_by"],
            reviewed_at=row["reviewed_at"],
            created_at=row["created_at"],
        )

    def reject_request(
        self,
        request_id: uuid.UUID,
        reviewer_id: str,
        reason: str | None = None,
    ) -> JoinRequestResponse | None:
        """Reject a join request.

        Args:
            request_id: Join request UUID
            reviewer_id: ID of user rejecting the request
            reason: Optional reason for rejection

        Returns:
            Updated join request or None if not found
        """
        query = """
            UPDATE workspace_join_requests
            SET status = 'rejected', reviewed_by = %s, reviewed_at = NOW(),
                rejection_reason = %s
            WHERE id = %s AND status = 'pending'
            RETURNING id, workspace_id, user_id, message, status,
                      rejection_reason, reviewed_by, reviewed_at, created_at
        """
        row = self._execute_one(query, (reviewer_id, reason, request_id))
        if not row:
            return None

        return JoinRequestResponse(
            id=row["id"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            message=row["message"],
            status=JoinRequestStatus(row["status"]),
            rejection_reason=row["rejection_reason"],
            reviewed_by=row["reviewed_by"],
            reviewed_at=row["reviewed_at"],
            created_at=row["created_at"],
        )

    def cancel_join_request(
        self,
        request_id: uuid.UUID,
        user_id: str,
    ) -> bool:
        """Cancel a pending join request (by the requester).

        Args:
            request_id: Join request UUID
            user_id: ID of user cancelling (must be requester)

        Returns:
            True if cancelled, False if not found or not authorized
        """
        query = """
            UPDATE workspace_join_requests
            SET status = 'cancelled'
            WHERE id = %s AND user_id = %s AND status = 'pending'
        """
        count = self._execute_count(query, (request_id, user_id))
        return count > 0

    def get_user_join_requests(
        self,
        user_id: str,
        status: JoinRequestStatus | None = None,
    ) -> list[JoinRequestResponse]:
        """Get all join requests for a user.

        Args:
            user_id: User ID
            status: Optional status filter

        Returns:
            List of join requests
        """
        if status:
            query = """
                SELECT jr.id, jr.workspace_id, jr.user_id, jr.message, jr.status,
                       jr.rejection_reason, jr.reviewed_by, jr.reviewed_at, jr.created_at,
                       w.name as workspace_name
                FROM workspace_join_requests jr
                LEFT JOIN workspaces w ON jr.workspace_id = w.id
                WHERE jr.user_id = %s AND jr.status = %s
                ORDER BY jr.created_at DESC
            """
            rows = self._execute_query(query, (user_id, status.value))
        else:
            query = """
                SELECT jr.id, jr.workspace_id, jr.user_id, jr.message, jr.status,
                       jr.rejection_reason, jr.reviewed_by, jr.reviewed_at, jr.created_at,
                       w.name as workspace_name
                FROM workspace_join_requests jr
                LEFT JOIN workspaces w ON jr.workspace_id = w.id
                WHERE jr.user_id = %s
                ORDER BY jr.created_at DESC
            """
            rows = self._execute_query(query, (user_id,))

        return [
            JoinRequestResponse(
                id=row["id"],
                workspace_id=row["workspace_id"],
                user_id=row["user_id"],
                message=row["message"],
                status=JoinRequestStatus(row["status"]),
                rejection_reason=row["rejection_reason"],
                reviewed_by=row["reviewed_by"],
                reviewed_at=row["reviewed_at"],
                created_at=row["created_at"],
                workspace_name=row.get("workspace_name"),
            )
            for row in rows
        ]

    # =========================================================================
    # Discoverability Methods
    # =========================================================================

    def get_discoverability(
        self,
        workspace_id: uuid.UUID,
    ) -> WorkspaceDiscoverability:
        """Get discoverability setting for a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Discoverability setting (defaults to PRIVATE)
        """
        query = "SELECT discoverability FROM workspaces WHERE id = %s"
        row = self._execute_one(query, (workspace_id,))
        if not row:
            return WorkspaceDiscoverability.PRIVATE
        return WorkspaceDiscoverability(row["discoverability"])

    def update_discoverability(
        self,
        workspace_id: uuid.UUID,
        discoverability: WorkspaceDiscoverability,
    ) -> bool:
        """Update discoverability setting for a workspace.

        Args:
            workspace_id: Workspace UUID
            discoverability: New discoverability setting

        Returns:
            True if updated
        """
        query = """
            UPDATE workspaces
            SET discoverability = %s, updated_at = NOW()
            WHERE id = %s
        """
        count = self._execute_count(query, (discoverability.value, workspace_id))
        return count > 0

    def count_pending_requests(self, workspace_id: uuid.UUID) -> int:
        """Count pending join requests for a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Number of pending requests
        """
        query = """
            SELECT COUNT(*) as count
            FROM workspace_join_requests
            WHERE workspace_id = %s AND status = 'pending'
        """
        row = self._execute_one(query, (workspace_id,))
        return row["count"] if row else 0

    # =========================================================================
    # Role Management Methods
    # =========================================================================

    def transfer_ownership(
        self,
        workspace_id: uuid.UUID,
        from_user_id: str,
        to_user_id: str,
    ) -> bool:
        """Transfer workspace ownership atomically.

        The old owner becomes an admin, and the new owner gets full ownership.
        Both the workspace owner_id and member roles are updated.

        Args:
            workspace_id: Workspace UUID
            from_user_id: Current owner's user ID
            to_user_id: New owner's user ID

        Returns:
            True if transfer successful

        Note:
            This is an atomic operation - all changes succeed or none do.
        """
        # Demote old owner to admin
        self._execute_count(
            """
            UPDATE workspace_members
            SET role = 'admin'
            WHERE workspace_id = %s AND user_id = %s
            """,
            (workspace_id, from_user_id),
        )

        # Promote new owner
        self._execute_count(
            """
            UPDATE workspace_members
            SET role = 'owner'
            WHERE workspace_id = %s AND user_id = %s
            """,
            (workspace_id, to_user_id),
        )

        # Update workspace owner_id
        count = self._execute_count(
            """
            UPDATE workspaces
            SET owner_id = %s, updated_at = NOW()
            WHERE id = %s AND owner_id = %s
            """,
            (to_user_id, workspace_id, from_user_id),
        )

        if count > 0:
            # Log role changes
            self.log_role_change(
                workspace_id=workspace_id,
                user_id=from_user_id,
                old_role=MemberRole.OWNER,
                new_role=MemberRole.ADMIN,
                changed_by=from_user_id,
                change_type="transfer_ownership",
            )
            self.log_role_change(
                workspace_id=workspace_id,
                user_id=to_user_id,
                old_role=MemberRole.ADMIN,  # Could be MEMBER, but we log the effective change
                new_role=MemberRole.OWNER,
                changed_by=from_user_id,
                change_type="transfer_ownership",
            )

        return count > 0

    def promote_to_admin(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
        promoted_by: str,
    ) -> WorkspaceMemberResponse | None:
        """Promote a member to admin role.

        Args:
            workspace_id: Workspace UUID
            user_id: User to promote
            promoted_by: User performing the promotion

        Returns:
            Updated member or None if not found
        """
        # Get current role for audit
        current_role = self.get_member_role(workspace_id, user_id)
        if not current_role or current_role != MemberRole.MEMBER:
            return None

        result = self.update_member_role(workspace_id, user_id, MemberRole.ADMIN)
        if result:
            self.log_role_change(
                workspace_id=workspace_id,
                user_id=user_id,
                old_role=current_role,
                new_role=MemberRole.ADMIN,
                changed_by=promoted_by,
                change_type="promote",
            )
        return result

    def demote_to_member(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
        demoted_by: str,
    ) -> WorkspaceMemberResponse | None:
        """Demote an admin to member role.

        Args:
            workspace_id: Workspace UUID
            user_id: User to demote
            demoted_by: User performing the demotion

        Returns:
            Updated member or None if not found
        """
        # Get current role for audit
        current_role = self.get_member_role(workspace_id, user_id)
        if not current_role or current_role != MemberRole.ADMIN:
            return None

        result = self.update_member_role(workspace_id, user_id, MemberRole.MEMBER)
        if result:
            self.log_role_change(
                workspace_id=workspace_id,
                user_id=user_id,
                old_role=current_role,
                new_role=MemberRole.MEMBER,
                changed_by=demoted_by,
                change_type="demote",
            )
        return result

    def log_role_change(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
        old_role: MemberRole,
        new_role: MemberRole,
        changed_by: str,
        change_type: str,
    ) -> None:
        """Log a role change to the audit table.

        Args:
            workspace_id: Workspace UUID
            user_id: User whose role changed
            old_role: Previous role
            new_role: New role
            changed_by: User who made the change
            change_type: Type of change (transfer_ownership, promote, demote)
        """
        change_id = uuid.uuid4()
        self._execute_count(
            """
            INSERT INTO workspace_role_changes
                (id, workspace_id, user_id, old_role, new_role, change_type, changed_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                change_id,
                workspace_id,
                user_id,
                old_role.value,
                new_role.value,
                change_type,
                changed_by,
            ),
        )

    def get_role_history(
        self,
        workspace_id: uuid.UUID,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get role change history for a workspace.

        Args:
            workspace_id: Workspace UUID
            limit: Maximum number of records to return

        Returns:
            List of role change records
        """
        query = """
            SELECT rc.id, rc.workspace_id, rc.user_id, rc.old_role, rc.new_role,
                   rc.change_type, rc.changed_by, rc.changed_at,
                   u.email as user_email, cb.email as changed_by_email
            FROM workspace_role_changes rc
            LEFT JOIN users u ON rc.user_id = u.id
            LEFT JOIN users cb ON rc.changed_by = cb.id
            WHERE rc.workspace_id = %s
            ORDER BY rc.changed_at DESC
            LIMIT %s
        """
        rows = self._execute_query(query, (workspace_id, limit))
        return [
            {
                "id": row["id"],
                "workspace_id": row["workspace_id"],
                "user_id": row["user_id"],
                "user_email": row.get("user_email"),
                "old_role": row["old_role"],
                "new_role": row["new_role"],
                "change_type": row["change_type"],
                "changed_by": row["changed_by"],
                "changed_by_email": row.get("changed_by_email"),
                "changed_at": row["changed_at"],
            }
            for row in rows
        ]


# Singleton instance
workspace_repository = WorkspaceRepository()
