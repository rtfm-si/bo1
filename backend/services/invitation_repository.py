"""Invitation repository for workspace invitations.

Provides:
- create_invitation(), get_invitation_by_token()
- list_pending_invitations(), get_user_pending_invitations()
- accept_invitation(), decline_invitation(), revoke_invitation()
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from backend.api.workspaces.models import (
    InvitationResponse,
    InvitationStatus,
    MemberRole,
)
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

# Default invitation expiry: 7 days
INVITATION_EXPIRY_DAYS = 7


class InvitationRepository(BaseRepository):
    """Repository for workspace invitation operations."""

    def create_invitation(
        self,
        workspace_id: uuid.UUID,
        email: str,
        role: MemberRole,
        invited_by: str,
        expiry_days: int = INVITATION_EXPIRY_DAYS,
    ) -> InvitationResponse:
        """Create a new workspace invitation.

        Args:
            workspace_id: Target workspace UUID
            email: Email address to invite
            role: Role to assign on acceptance
            invited_by: User ID of the inviter
            expiry_days: Days until invitation expires

        Returns:
            Created invitation

        Raises:
            ValueError: If duplicate pending invitation exists
        """
        invitation_id = uuid.uuid4()
        token = uuid.uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=expiry_days)

        query = """
            INSERT INTO workspace_invitations
                (id, workspace_id, email, role, token, status, expires_at, invited_by)
            VALUES (%s, %s, %s, %s, %s, 'pending', %s, %s)
            RETURNING id, workspace_id, email, role, token, status,
                      expires_at, invited_by, created_at, accepted_at
        """
        row = self._execute_returning(
            query,
            (
                invitation_id,
                workspace_id,
                email.lower(),
                role.value,
                token,
                expires_at,
                invited_by,
            ),
        )

        return InvitationResponse(
            id=row["id"],
            workspace_id=row["workspace_id"],
            email=row["email"],
            role=MemberRole(row["role"]),
            status=InvitationStatus(row["status"]),
            expires_at=row["expires_at"],
            created_at=row["created_at"],
            invited_by=row["invited_by"],
            accepted_at=row["accepted_at"],
        )

    def get_invitation_by_token(self, token: str) -> InvitationResponse | None:
        """Get an invitation by its token.

        Args:
            token: Invitation token UUID string

        Returns:
            Invitation or None if not found
        """
        try:
            token_uuid = uuid.UUID(token)
        except ValueError:
            return None

        query = """
            SELECT i.id, i.workspace_id, i.email, i.role, i.status,
                   i.expires_at, i.invited_by, i.created_at, i.accepted_at,
                   w.name as workspace_name,
                   u.email as inviter_email
            FROM workspace_invitations i
            JOIN workspaces w ON i.workspace_id = w.id
            LEFT JOIN users u ON i.invited_by = u.id
            WHERE i.token = %s
        """
        row = self._execute_one(query, (token_uuid,))
        if not row:
            return None

        return InvitationResponse(
            id=row["id"],
            workspace_id=row["workspace_id"],
            email=row["email"],
            role=MemberRole(row["role"]),
            status=InvitationStatus(row["status"]),
            expires_at=row["expires_at"],
            created_at=row["created_at"],
            invited_by=row["invited_by"],
            accepted_at=row["accepted_at"],
            workspace_name=row["workspace_name"],
            inviter_name=row.get("inviter_email"),
        )

    def get_invitation_by_id(self, invitation_id: uuid.UUID) -> InvitationResponse | None:
        """Get an invitation by its ID.

        Args:
            invitation_id: Invitation UUID

        Returns:
            Invitation or None if not found
        """
        query = """
            SELECT i.id, i.workspace_id, i.email, i.role, i.status,
                   i.expires_at, i.invited_by, i.created_at, i.accepted_at,
                   w.name as workspace_name
            FROM workspace_invitations i
            JOIN workspaces w ON i.workspace_id = w.id
            WHERE i.id = %s
        """
        row = self._execute_one(query, (invitation_id,))
        if not row:
            return None

        return InvitationResponse(
            id=row["id"],
            workspace_id=row["workspace_id"],
            email=row["email"],
            role=MemberRole(row["role"]),
            status=InvitationStatus(row["status"]),
            expires_at=row["expires_at"],
            created_at=row["created_at"],
            invited_by=row["invited_by"],
            accepted_at=row["accepted_at"],
            workspace_name=row["workspace_name"],
        )

    def list_pending_invitations(self, workspace_id: uuid.UUID) -> list[InvitationResponse]:
        """List all pending invitations for a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            List of pending invitations
        """
        query = """
            SELECT i.id, i.workspace_id, i.email, i.role, i.status,
                   i.expires_at, i.invited_by, i.created_at, i.accepted_at,
                   u.email as inviter_email
            FROM workspace_invitations i
            LEFT JOIN users u ON i.invited_by = u.id
            WHERE i.workspace_id = %s AND i.status = 'pending'
            ORDER BY i.created_at DESC
        """
        rows = self._execute_query(query, (workspace_id,))
        return [
            InvitationResponse(
                id=row["id"],
                workspace_id=row["workspace_id"],
                email=row["email"],
                role=MemberRole(row["role"]),
                status=InvitationStatus(row["status"]),
                expires_at=row["expires_at"],
                created_at=row["created_at"],
                invited_by=row["invited_by"],
                accepted_at=row["accepted_at"],
                inviter_name=row.get("inviter_email"),
            )
            for row in rows
        ]

    def get_user_pending_invitations(self, email: str) -> list[InvitationResponse]:
        """Get all pending invitations for a user by email.

        Args:
            email: User's email address

        Returns:
            List of pending invitations for this email
        """
        query = """
            SELECT i.id, i.workspace_id, i.email, i.role, i.status,
                   i.expires_at, i.invited_by, i.created_at, i.accepted_at,
                   w.name as workspace_name,
                   u.email as inviter_email
            FROM workspace_invitations i
            JOIN workspaces w ON i.workspace_id = w.id
            LEFT JOIN users u ON i.invited_by = u.id
            WHERE i.email = %s
              AND i.status = 'pending'
              AND i.expires_at > NOW()
            ORDER BY i.created_at DESC
        """
        rows = self._execute_query(query, (email.lower(),))
        return [
            InvitationResponse(
                id=row["id"],
                workspace_id=row["workspace_id"],
                email=row["email"],
                role=MemberRole(row["role"]),
                status=InvitationStatus(row["status"]),
                expires_at=row["expires_at"],
                created_at=row["created_at"],
                invited_by=row["invited_by"],
                accepted_at=row["accepted_at"],
                workspace_name=row["workspace_name"],
                inviter_name=row.get("inviter_email"),
            )
            for row in rows
        ]

    def has_pending_invitation(self, workspace_id: uuid.UUID, email: str) -> bool:
        """Check if a pending invitation already exists.

        Args:
            workspace_id: Workspace UUID
            email: Email address

        Returns:
            True if pending invitation exists
        """
        query = """
            SELECT 1 FROM workspace_invitations
            WHERE workspace_id = %s
              AND email = %s
              AND status = 'pending'
              AND expires_at > NOW()
            LIMIT 1
        """
        row = self._execute_one(query, (workspace_id, email.lower()))
        return row is not None

    def accept_invitation(self, token: str, user_id: str) -> bool:
        """Mark an invitation as accepted.

        Args:
            token: Invitation token
            user_id: User accepting the invitation

        Returns:
            True if successful, False if invitation not found/invalid
        """
        try:
            token_uuid = uuid.UUID(token)
        except ValueError:
            return False

        query = """
            UPDATE workspace_invitations
            SET status = 'accepted', accepted_at = NOW()
            WHERE token = %s
              AND status = 'pending'
              AND expires_at > NOW()
            RETURNING id
        """
        row = self._execute_returning(query, (token_uuid,))
        return row is not None

    def decline_invitation(self, token: str) -> bool:
        """Mark an invitation as declined.

        Args:
            token: Invitation token

        Returns:
            True if successful, False if not found
        """
        try:
            token_uuid = uuid.UUID(token)
        except ValueError:
            return False

        query = """
            UPDATE workspace_invitations
            SET status = 'declined'
            WHERE token = %s AND status = 'pending'
            RETURNING id
        """
        row = self._execute_returning(query, (token_uuid,))
        return row is not None

    def revoke_invitation(self, invitation_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
        """Revoke a pending invitation.

        Args:
            invitation_id: Invitation UUID
            workspace_id: Workspace UUID (for authorization)

        Returns:
            True if successful, False if not found
        """
        query = """
            UPDATE workspace_invitations
            SET status = 'revoked'
            WHERE id = %s AND workspace_id = %s AND status = 'pending'
            RETURNING id
        """
        row = self._execute_returning(query, (invitation_id, workspace_id))
        return row is not None

    def expire_old_invitations(self) -> int:
        """Mark expired invitations as expired.

        Returns:
            Number of invitations expired
        """
        query = """
            UPDATE workspace_invitations
            SET status = 'expired'
            WHERE status = 'pending' AND expires_at < NOW()
            RETURNING id
        """
        rows = self._execute_query(query, ())
        return len(rows)

    def get_invitation_token(self, invitation_id: uuid.UUID) -> str | None:
        """Get the token for an invitation (for email links).

        Args:
            invitation_id: Invitation UUID

        Returns:
            Token string or None
        """
        query = "SELECT token FROM workspace_invitations WHERE id = %s"
        row = self._execute_one(query, (invitation_id,))
        return str(row["token"]) if row else None


# Singleton instance
invitation_repository = InvitationRepository()
