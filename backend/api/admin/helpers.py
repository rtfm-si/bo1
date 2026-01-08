"""Shared helper functions and services for admin API endpoints.

This module contains:
- AdminQueryService: User queries with metrics
- AdminValidationService: Email validation utilities
- AdminApprovalService: Waitlist approval workflow

These services extract reusable logic from admin routers to reduce duplication.
"""

import re
from dataclasses import dataclass
from typing import Any

from backend.api.admin.models import (
    AdminStatsResponse,
    BetaWhitelistEntry,
    UserInfo,
    WaitlistEntry,
)
from backend.api.utils.db_helpers import count_rows, execute_query, exists, get_single_value
from backend.api.utils.errors import http_error
from bo1.logging import ErrorCode
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
        u.is_nonprofit,
        u.nonprofit_org_name,
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
             u.is_locked, u.locked_at, u.lock_reason, u.deleted_at, u.is_nonprofit,
             u.nonprofit_org_name, u.created_at, u.updated_at
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
        is_nonprofit=row.get("is_nonprofit", False),
        nonprofit_org_name=row.get("nonprofit_org_name"),
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
        # Get total users
        total_users = count_rows("users")

        # Get total meetings and cost from sessions
        session_stats = execute_query(
            """
            SELECT
                COUNT(*) as total_meetings,
                COALESCE(SUM(total_cost), 0) as total_cost
            FROM sessions
            """,
            fetch="one",
        )
        total_meetings = session_stats["total_meetings"] if session_stats else 0
        total_cost = float(session_stats["total_cost"]) if session_stats else 0.0

        # Get whitelist count (database-managed)
        whitelist_count = count_rows("beta_whitelist")

        # Get pending waitlist count
        waitlist_pending = count_rows("waitlist", where="status = 'pending'")

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
        # noqa: S608 - Safe: only uses controlled constants
        query = f"{USER_WITH_METRICS_SELECT} WHERE u.id = %s {USER_WITH_METRICS_GROUP_BY}"
        row = execute_query(query, (user_id,), fetch="one")

        if not row:
            raise http_error(ErrorCode.API_NOT_FOUND, f"User not found: {user_id}", status=404)

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
        # Build query with optional email filter
        params: list[Any] = []
        where_clause = ""

        if email_filter:
            where_clause = "WHERE LOWER(u.email) LIKE LOWER(%s)"
            params.append(f"%{email_filter}%")

        # Get total count
        total_count = get_single_value(
            f"SELECT COUNT(*) as count FROM users u {where_clause}",
            tuple(params),
            column="count",
            default=0,
        )

        # Get paginated users with metrics
        offset = (page - 1) * per_page
        # noqa: S608 - Safe: only uses controlled constants and where_clause
        data_query = f"""
            {USER_WITH_METRICS_SELECT}
            {where_clause}
            {USER_WITH_METRICS_GROUP_BY}
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """
        rows = execute_query(data_query, (*params, per_page, offset), fetch="all")
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
        return exists("users", where="id = %s", params=(user_id,))


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
            raise http_error(
                ErrorCode.VALIDATION_ERROR, f"Invalid email address: {email}", status=400
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
        valid_tiers = ["free", "starter", "pro", "enterprise"]
        if tier not in valid_tiers:
            raise http_error(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid subscription_tier. Must be one of: {', '.join(valid_tiers)}",
                status=400,
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

        # Check if email is on waitlist
        waitlist_row = execute_query(
            "SELECT id, status FROM waitlist WHERE email = %s",
            (email,),
            fetch="one",
        )

        if not waitlist_row:
            raise http_error(
                ErrorCode.VALIDATION_ERROR, f"Email not found on waitlist: {email}", status=400
            )

        if waitlist_row["status"] == "invited":
            raise http_error(
                ErrorCode.VALIDATION_ERROR, f"Email already approved: {email}", status=400
            )

        # Check if already on whitelist
        already_on_whitelist = exists("beta_whitelist", where="email = %s", params=(email,))
        if already_on_whitelist:
            logger.info(f"Email {email} already on whitelist, skipping add")
        else:
            # Add to whitelist
            execute_query(
                """
                INSERT INTO beta_whitelist (email, added_by, notes)
                VALUES (%s, %s, %s)
                """,
                (email, "admin", "Approved from waitlist"),
                fetch="none",
            )
            whitelist_added = True
            logger.info(f"Added {email} to beta whitelist")

        # Update waitlist status
        execute_query(
            """
            UPDATE waitlist
            SET status = 'invited', updated_at = NOW()
            WHERE email = %s
            """,
            (email,),
            fetch="none",
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
            message_parts.append(f"welcome email sent (id: {result.get('id', 'unknown')})")
        else:
            # Check if Resend is configured at all
            from bo1.config import get_settings

            settings = get_settings()
            if not settings.resend_api_key:
                message_parts.append("email not sent - RESEND_API_KEY not configured")
            else:
                message_parts.append("email failed - check API logs for Resend error details")

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
        return execute_query(
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
            fetch="one",
        )

    @staticmethod
    def unlock_user(user_id: str) -> dict[str, Any] | None:
        """Unlock a user account.

        Args:
            user_id: User to unlock

        Returns:
            Updated user row or None if not found
        """
        return execute_query(
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
            fetch="one",
        )

    @staticmethod
    def soft_delete_user(user_id: str, admin_id: str) -> bool:
        """Soft delete a user account.

        Args:
            user_id: User to delete
            admin_id: Admin performing the action

        Returns:
            True if user was deleted
        """
        result = execute_query(
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
            fetch="one",
        )
        return result is not None

    @staticmethod
    def hard_delete_user(user_id: str) -> bool:
        """Permanently delete a user and all associated data.

        Args:
            user_id: User to delete

        Returns:
            True if user was deleted
        """
        # Sessions have ON DELETE CASCADE, so they'll be deleted automatically
        result = execute_query(
            "DELETE FROM users WHERE id = %s RETURNING id",
            (user_id,),
            fetch="one",
        )
        return result is not None

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
        import json

        execute_query(
            """
            INSERT INTO audit_log (user_id, action, resource_type, resource_id, details, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                admin_id,
                action,
                resource_type,
                resource_id,
                json.dumps(details) if details else None,
                ip_address,
            ),
            fetch="none",
        )
