"""Shared helper functions and services for admin API endpoints.

This module contains:
- AdminQueryService: User queries with metrics
- AdminValidationService: Email validation utilities
- AdminApprovalService: Waitlist approval workflow

These services extract reusable logic from admin routers to reduce duplication.
"""

import os
import re
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from backend.api.admin.models import (
    AdminStatsResponse,
    BetaWhitelistEntry,
    UserInfo,
    WaitlistEntry,
)
from bo1.state.postgres_manager import db_session
from bo1.utils.logging import get_logger

logger = get_logger(__name__)


def _to_iso(value: Any) -> str:
    """Convert datetime to ISO format string, empty string if None."""
    return value.isoformat() if value else ""


def _to_iso_or_none(value: Any) -> str | None:
    """Convert datetime to ISO format string, None if None."""
    return value.isoformat() if value else None


# SQL query for user with metrics (reused in get_user, update_user, list_users)
USER_WITH_METRICS_SELECT = """
    SELECT
        u.id,
        u.email,
        u.auth_provider,
        u.subscription_tier,
        u.is_admin,
        u.is_locked,
        u.locked_at,
        u.lock_reason,
        u.deleted_at,
        u.created_at,
        u.updated_at,
        COUNT(s.id) as total_meetings,
        SUM(s.total_cost) as total_cost,
        MAX(s.created_at) as last_meeting_at,
        (SELECT id FROM sessions WHERE user_id = u.id ORDER BY created_at DESC LIMIT 1) as last_meeting_id
    FROM users u
    LEFT JOIN sessions s ON u.id = s.user_id
"""

USER_WITH_METRICS_GROUP_BY = """
    GROUP BY u.id, u.email, u.auth_provider, u.subscription_tier, u.is_admin,
             u.is_locked, u.locked_at, u.lock_reason, u.deleted_at, u.created_at, u.updated_at
"""


def _row_to_user_info(row: dict[str, Any]) -> UserInfo:
    """Convert database row to UserInfo model."""
    return UserInfo(
        user_id=row["id"],
        email=row["email"],
        auth_provider=row["auth_provider"],
        subscription_tier=row["subscription_tier"],
        is_admin=row["is_admin"],
        is_locked=row.get("is_locked", False),
        locked_at=_to_iso_or_none(row.get("locked_at")),
        lock_reason=row.get("lock_reason"),
        deleted_at=_to_iso_or_none(row.get("deleted_at")),
        created_at=_to_iso(row["created_at"]),
        updated_at=_to_iso(row["updated_at"]),
        total_meetings=row["total_meetings"] or 0,
        total_cost=float(row["total_cost"]) if row["total_cost"] else None,
        last_meeting_at=_to_iso_or_none(row["last_meeting_at"]),
        last_meeting_id=row["last_meeting_id"],
    )


def _row_to_whitelist_entry(row: dict[str, Any]) -> BetaWhitelistEntry:
    """Convert database row to BetaWhitelistEntry model."""
    return BetaWhitelistEntry(
        id=str(row["id"]),
        email=row["email"],
        added_by=row["added_by"],
        notes=row["notes"],
        created_at=_to_iso(row["created_at"]),
    )


def _row_to_waitlist_entry(row: dict[str, Any]) -> WaitlistEntry:
    """Convert database row to WaitlistEntry model."""
    return WaitlistEntry(
        id=str(row["id"]),
        email=row["email"],
        status=row["status"],
        source=row["source"],
        notes=row["notes"],
        created_at=_to_iso(row["created_at"]),
    )


class AdminQueryService:
    """Service for admin user queries with metrics."""

    @staticmethod
    def get_stats() -> AdminStatsResponse:
        """Get admin dashboard statistics.

        Returns:
            AdminStatsResponse with aggregated stats
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Get total users
                cur.execute("SELECT COUNT(*) as count FROM users")
                total_users = cur.fetchone()["count"]

                # Get total meetings and cost from sessions
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total_meetings,
                        COALESCE(SUM(total_cost), 0) as total_cost
                    FROM sessions
                    """
                )
                session_stats = cur.fetchone()
                total_meetings = session_stats["total_meetings"]
                total_cost = float(session_stats["total_cost"])

                # Get whitelist count (db + env)
                cur.execute("SELECT COUNT(*) as count FROM beta_whitelist")
                db_whitelist_count = cur.fetchone()["count"]

                env_whitelist = os.getenv("BETA_WHITELIST", "")
                env_emails = [e.strip().lower() for e in env_whitelist.split(",") if e.strip()]
                whitelist_count = db_whitelist_count + len(env_emails)

                # Get pending waitlist count
                cur.execute("SELECT COUNT(*) as count FROM waitlist WHERE status = 'pending'")
                waitlist_pending = cur.fetchone()["count"]

        return AdminStatsResponse(
            total_users=total_users,
            total_meetings=total_meetings,
            total_cost=total_cost,
            whitelist_count=whitelist_count,
            waitlist_pending=waitlist_pending,
        )

    @staticmethod
    def get_user(user_id: str) -> UserInfo:
        """Get single user with metrics.

        Args:
            user_id: User identifier

        Returns:
            UserInfo with user details and metrics

        Raises:
            HTTPException: If user not found
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                query = f"""
                    {USER_WITH_METRICS_SELECT}
                    WHERE u.id = %s
                    {USER_WITH_METRICS_GROUP_BY}
                """  # noqa: S608 - Safe: only uses controlled constants
                cur.execute(query, (user_id,))
                row = cur.fetchone()

                if not row:
                    raise HTTPException(
                        status_code=404,
                        detail=f"User not found: {user_id}",
                    )

                return _row_to_user_info(row)

    @staticmethod
    def list_users(
        page: int = 1,
        per_page: int = 10,
        email_filter: str | None = None,
    ) -> tuple[int, list[UserInfo]]:
        """List users with metrics and pagination.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            email_filter: Optional email search filter (case-insensitive partial match)

        Returns:
            Tuple of (total_count, users)
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Build query with optional email filter
                params: list[Any] = []
                where_clause = ""

                if email_filter:
                    where_clause = "WHERE LOWER(u.email) LIKE LOWER(%s)"
                    params.append(f"%{email_filter}%")

                # Get total count
                count_query = f"SELECT COUNT(*) as count FROM users u {where_clause}"
                cur.execute(count_query, params)
                total_count = cur.fetchone()["count"]

                # Get paginated users with metrics
                offset = (page - 1) * per_page
                data_query = f"""
                    {USER_WITH_METRICS_SELECT}
                    {where_clause}
                    {USER_WITH_METRICS_GROUP_BY}
                    ORDER BY u.created_at DESC
                    LIMIT %s OFFSET %s
                """  # noqa: S608 - Safe: only uses controlled constants and where_clause
                cur.execute(data_query, [*params, per_page, offset])
                rows = cur.fetchall()

                users = [_row_to_user_info(row) for row in rows]

        return total_count, users

    @staticmethod
    def user_exists(user_id: str) -> bool:
        """Check if user exists.

        Args:
            user_id: User identifier

        Returns:
            True if user exists
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                return cur.fetchone() is not None


class AdminValidationService:
    """Service for admin input validation."""

    # Simple email regex for basic validation
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    @staticmethod
    def validate_email(email: str) -> str:
        """Validate and normalize email address.

        Args:
            email: Email to validate

        Returns:
            Normalized (lowercase, stripped) email

        Raises:
            HTTPException: If email is invalid
        """
        normalized = email.strip().lower()

        # Basic validation - must have @ and domain with .
        if "@" not in normalized or "." not in normalized.split("@")[1]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid email address: {email}",
            )

        return normalized

    @staticmethod
    def validate_subscription_tier(tier: str) -> str:
        """Validate subscription tier.

        Args:
            tier: Subscription tier to validate

        Returns:
            Validated tier

        Raises:
            HTTPException: If tier is invalid
        """
        valid_tiers = ["free", "pro", "enterprise"]
        if tier not in valid_tiers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid subscription_tier. Must be one of: {', '.join(valid_tiers)}",
            )
        return tier


@dataclass
class ApprovalResult:
    """Result of waitlist approval operation."""

    email: str
    whitelist_added: bool
    email_sent: bool
    message: str


class AdminApprovalService:
    """Service for waitlist approval workflow."""

    @staticmethod
    def approve_waitlist_entry(email: str) -> ApprovalResult:
        """Approve a waitlist entry.

        This method:
        1. Checks if email is on the waitlist with pending status
        2. Adds email to beta_whitelist table (if not already there)
        3. Updates waitlist status to 'invited'
        4. Sends welcome email via Resend

        Args:
            email: Email address to approve

        Returns:
            ApprovalResult with operation details

        Raises:
            HTTPException: If email not found or already approved
        """
        from backend.api.email import send_beta_welcome_email

        email = email.strip().lower()
        whitelist_added = False
        email_sent = False

        with db_session() as conn:
            with conn.cursor() as cur:
                # Check if email is on waitlist
                cur.execute(
                    "SELECT id, status FROM waitlist WHERE email = %s",
                    (email,),
                )
                waitlist_row = cur.fetchone()

                if not waitlist_row:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Email not found on waitlist: {email}",
                    )

                if waitlist_row["status"] == "invited":
                    raise HTTPException(
                        status_code=400,
                        detail=f"Email already approved: {email}",
                    )

                # Check if already on whitelist
                cur.execute(
                    "SELECT id FROM beta_whitelist WHERE email = %s",
                    (email,),
                )
                if cur.fetchone():
                    logger.info(f"Email {email} already on whitelist, skipping add")
                else:
                    # Add to whitelist
                    cur.execute(
                        """
                        INSERT INTO beta_whitelist (email, added_by, notes)
                        VALUES (%s, %s, %s)
                        """,
                        (email, "admin", "Approved from waitlist"),
                    )
                    whitelist_added = True
                    logger.info(f"Added {email} to beta whitelist")

                # Update waitlist status
                cur.execute(
                    """
                    UPDATE waitlist
                    SET status = 'invited', updated_at = NOW()
                    WHERE email = %s
                    """,
                    (email,),
                )

        # Send welcome email (outside transaction)
        result = send_beta_welcome_email(email)
        email_sent = result is not None

        message_parts = []
        if whitelist_added:
            message_parts.append("added to whitelist")
        else:
            message_parts.append("already on whitelist")
        if email_sent:
            message_parts.append("welcome email sent")
        else:
            message_parts.append("email not sent (check RESEND_API_KEY)")

        message = f"Approved {email}: {', '.join(message_parts)}"

        return ApprovalResult(
            email=email,
            whitelist_added=whitelist_added,
            email_sent=email_sent,
            message=message,
        )


@dataclass
class LockResult:
    """Result of lock/unlock operation."""

    user_id: str
    is_locked: bool
    locked_at: str | None
    lock_reason: str | None
    sessions_revoked: int
    message: str


@dataclass
class DeleteResult:
    """Result of delete operation."""

    user_id: str
    deleted: bool
    hard_delete: bool
    sessions_revoked: int
    message: str


class AdminUserService:
    """Service for admin user management operations (lock/unlock/delete)."""

    @staticmethod
    async def revoke_user_sessions(user_id: str) -> int:
        """Revoke all SuperTokens sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            Number of sessions revoked
        """
        try:
            from supertokens_python.recipe.session.asyncio import revoke_all_sessions_for_user

            revoked = await revoke_all_sessions_for_user(user_id)
            count = len(revoked) if revoked else 0
            logger.info(f"Revoked {count} sessions for user {user_id}")
            return count
        except Exception as e:
            logger.warning(f"Failed to revoke sessions for {user_id}: {e}")
            return 0

    @staticmethod
    def lock_user(user_id: str, admin_id: str, reason: str | None = None) -> dict[str, Any] | None:
        """Lock a user account.

        Args:
            user_id: User to lock
            admin_id: Admin performing the action
            reason: Optional reason for locking

        Returns:
            Updated user row or None if not found
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET is_locked = true,
                        locked_at = NOW(),
                        locked_by = %s,
                        lock_reason = %s,
                        updated_at = NOW()
                    WHERE id = %s AND deleted_at IS NULL
                    RETURNING id, is_locked, locked_at, lock_reason
                    """,
                    (admin_id, reason, user_id),
                )
                return cur.fetchone()

    @staticmethod
    def unlock_user(user_id: str) -> dict[str, Any] | None:
        """Unlock a user account.

        Args:
            user_id: User to unlock

        Returns:
            Updated user row or None if not found
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET is_locked = false,
                        locked_at = NULL,
                        locked_by = NULL,
                        lock_reason = NULL,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, is_locked
                    """,
                    (user_id,),
                )
                return cur.fetchone()

    @staticmethod
    def soft_delete_user(user_id: str, admin_id: str) -> bool:
        """Soft delete a user account.

        Args:
            user_id: User to delete
            admin_id: Admin performing the action

        Returns:
            True if user was deleted
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET deleted_at = NOW(),
                        deleted_by = %s,
                        is_locked = true,
                        updated_at = NOW()
                    WHERE id = %s AND deleted_at IS NULL
                    RETURNING id
                    """,
                    (admin_id, user_id),
                )
                return cur.fetchone() is not None

    @staticmethod
    def hard_delete_user(user_id: str) -> bool:
        """Permanently delete a user and all associated data.

        Args:
            user_id: User to delete

        Returns:
            True if user was deleted
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Sessions have ON DELETE CASCADE, so they'll be deleted automatically
                cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
                return cur.fetchone() is not None

    @staticmethod
    def log_admin_action(
        admin_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Log admin action to audit trail.

        Args:
            admin_id: Admin performing the action
            action: Action type (user_locked, user_unlocked, user_deleted)
            resource_type: Resource type (user)
            resource_id: Resource identifier
            details: Optional additional details
            ip_address: Optional IP address
        """
        from psycopg.types.json import Json

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_log (user_id, action, resource_type, resource_id, details, ip_address)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        admin_id,
                        action,
                        resource_type,
                        resource_id,
                        Json(details) if details else None,
                        ip_address,
                    ),
                )
