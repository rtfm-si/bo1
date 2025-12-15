"""Promotion repository for managing promo codes and user redemptions.

Provides:
- Lookup promotions by code
- Track user-applied promotions
- Increment usage counts with race-condition protection
- Query user's active promotions
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class PromotionRepository(BaseRepository):
    """Repository for promotions and user_promotions tables."""

    def get_promotion_by_code(self, code: str) -> dict[str, Any] | None:
        """Get a promotion by its code.

        Args:
            code: The promo code (case-insensitive)

        Returns:
            Promotion dict or None if not found
        """
        code = code.strip().upper()
        query = """
            SELECT id, code, type, value, max_uses, uses_count,
                   expires_at, created_at, deleted_at
            FROM promotions
            WHERE UPPER(code) = %s
        """
        return self._execute_one(query, (code,))

    def get_promotion_by_id(self, promotion_id: str) -> dict[str, Any] | None:
        """Get a promotion by its ID.

        Args:
            promotion_id: The promotion UUID

        Returns:
            Promotion dict or None if not found
        """
        self._validate_id(promotion_id, "promotion_id")
        query = """
            SELECT id, code, type, value, max_uses, uses_count,
                   expires_at, created_at, deleted_at
            FROM promotions
            WHERE id = %s
        """
        return self._execute_one(query, (promotion_id,))

    def get_active_promotions(self) -> list[dict[str, Any]]:
        """Get all active promotions.

        Returns:
            List of active promotion dicts
        """
        query = """
            SELECT id, code, type, value, max_uses, uses_count,
                   expires_at, created_at, deleted_at
            FROM promotions
            WHERE deleted_at IS NULL
              AND (expires_at IS NULL OR expires_at > NOW())
              AND (max_uses IS NULL OR uses_count < max_uses)
            ORDER BY created_at DESC
        """
        return self._execute_query(query)

    def get_all_promotions(self) -> list[dict[str, Any]]:
        """Get all promotions (admin).

        Returns:
            List of all promotion dicts
        """
        query = """
            SELECT id, code, type, value, max_uses, uses_count,
                   expires_at, created_at, deleted_at
            FROM promotions
            ORDER BY created_at DESC
        """
        return self._execute_query(query)

    def create_promotion(
        self,
        code: str,
        promo_type: str,
        value: float,
        max_uses: int | None = None,
        expires_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Create a new promotion.

        Args:
            code: Unique promo code
            promo_type: Type of promotion
            value: Promotion value
            max_uses: Maximum uses (None = unlimited)
            expires_at: Expiration timestamp (None = never)

        Returns:
            Created promotion dict

        Raises:
            ValueError: If code already exists
        """
        code = code.strip().upper()
        promotion_id = str(uuid4())

        query = """
            INSERT INTO promotions (id, code, type, value, max_uses, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, code, type, value, max_uses, uses_count,
                      expires_at, created_at, deleted_at
        """
        return self._execute_returning(
            query,
            (promotion_id, code, promo_type, value, max_uses, expires_at),
        )

    def deactivate_promotion(self, promotion_id: str) -> bool:
        """Deactivate (soft-delete) a promotion.

        Args:
            promotion_id: The promotion UUID

        Returns:
            True if promotion was deactivated, False if not found
        """
        self._validate_id(promotion_id, "promotion_id")
        query = """
            UPDATE promotions
            SET deleted_at = NOW()
            WHERE id = %s AND deleted_at IS NULL
        """
        count = self._execute_count(query, (promotion_id,))
        return count > 0

    def restore_promotion(self, promotion_id: str) -> bool:
        """Restore a soft-deleted promotion.

        Args:
            promotion_id: The promotion UUID

        Returns:
            True if promotion was restored, False if not found/not deleted
        """
        self._validate_id(promotion_id, "promotion_id")
        query = """
            UPDATE promotions
            SET deleted_at = NULL
            WHERE id = %s AND deleted_at IS NOT NULL
        """
        count = self._execute_count(query, (promotion_id,))
        return count > 0

    def increment_promotion_uses(self, promotion_id: str) -> bool:
        """Increment uses_count with race-condition protection.

        Only increments if:
        - max_uses is NULL (unlimited), OR
        - uses_count < max_uses

        Args:
            promotion_id: The promotion UUID

        Returns:
            True if increment succeeded, False if at max uses
        """
        self._validate_id(promotion_id, "promotion_id")
        query = """
            UPDATE promotions
            SET uses_count = uses_count + 1
            WHERE id = %s
              AND (max_uses IS NULL OR uses_count < max_uses)
        """
        count = self._execute_count(query, (promotion_id,))
        return count > 0

    def get_user_promotions(self, user_id: str) -> list[dict[str, Any]]:
        """Get all promotions applied by a user.

        Args:
            user_id: The user ID

        Returns:
            List of user_promotion dicts with nested promotion data
        """
        self._validate_id(user_id, "user_id")
        query = """
            SELECT
                up.id,
                up.user_id,
                up.promotion_id,
                up.applied_at,
                up.deliberations_remaining,
                up.discount_applied,
                up.status,
                p.code AS promotion_code,
                p.type AS promotion_type,
                p.value AS promotion_value,
                p.max_uses AS promotion_max_uses,
                p.uses_count AS promotion_uses_count,
                p.expires_at AS promotion_expires_at,
                p.created_at AS promotion_created_at,
                p.deleted_at AS promotion_deleted_at
            FROM user_promotions up
            JOIN promotions p ON up.promotion_id = p.id
            WHERE up.user_id = %s
            ORDER BY up.applied_at DESC
        """
        rows = self._execute_query(query, (user_id,), user_id=user_id)
        return [self._format_user_promotion(row) for row in rows]

    def get_user_active_promotions(self, user_id: str) -> list[dict[str, Any]]:
        """Get user's active promotions only.

        Args:
            user_id: The user ID

        Returns:
            List of active user_promotion dicts
        """
        self._validate_id(user_id, "user_id")
        query = """
            SELECT
                up.id,
                up.user_id,
                up.promotion_id,
                up.applied_at,
                up.deliberations_remaining,
                up.discount_applied,
                up.status,
                p.code AS promotion_code,
                p.type AS promotion_type,
                p.value AS promotion_value,
                p.max_uses AS promotion_max_uses,
                p.uses_count AS promotion_uses_count,
                p.expires_at AS promotion_expires_at,
                p.created_at AS promotion_created_at,
                p.deleted_at AS promotion_deleted_at
            FROM user_promotions up
            JOIN promotions p ON up.promotion_id = p.id
            WHERE up.user_id = %s
              AND up.status = 'active'
            ORDER BY up.applied_at DESC
        """
        rows = self._execute_query(query, (user_id,), user_id=user_id)
        return [self._format_user_promotion(row) for row in rows]

    def get_user_promotion(self, user_id: str, promotion_id: str) -> dict[str, Any] | None:
        """Check if user has already applied a specific promotion.

        Args:
            user_id: The user ID
            promotion_id: The promotion UUID

        Returns:
            User_promotion dict or None if not applied
        """
        self._validate_id(user_id, "user_id")
        self._validate_id(promotion_id, "promotion_id")
        query = """
            SELECT
                up.id,
                up.user_id,
                up.promotion_id,
                up.applied_at,
                up.deliberations_remaining,
                up.discount_applied,
                up.status,
                p.code AS promotion_code,
                p.type AS promotion_type,
                p.value AS promotion_value,
                p.max_uses AS promotion_max_uses,
                p.uses_count AS promotion_uses_count,
                p.expires_at AS promotion_expires_at,
                p.created_at AS promotion_created_at,
                p.deleted_at AS promotion_deleted_at
            FROM user_promotions up
            JOIN promotions p ON up.promotion_id = p.id
            WHERE up.user_id = %s AND up.promotion_id = %s
        """
        row = self._execute_one(query, (user_id, promotion_id), user_id=user_id)
        return self._format_user_promotion(row) if row else None

    def apply_promotion(
        self,
        user_id: str,
        promotion_id: str,
        deliberations_remaining: int | None = None,
        discount_applied: float | None = None,
    ) -> dict[str, Any]:
        """Apply a promotion to a user.

        Args:
            user_id: The user ID
            promotion_id: The promotion UUID
            deliberations_remaining: Initial credit balance (for credit promos)
            discount_applied: Discount amount (for discount promos)

        Returns:
            Created user_promotion dict

        Raises:
            ValueError: If user already has this promotion
        """
        self._validate_id(user_id, "user_id")
        self._validate_id(promotion_id, "promotion_id")

        user_promo_id = str(uuid4())
        query = """
            INSERT INTO user_promotions
                (id, user_id, promotion_id, deliberations_remaining, discount_applied, status)
            VALUES (%s, %s, %s, %s, %s, 'active')
            RETURNING id, user_id, promotion_id, applied_at,
                      deliberations_remaining, discount_applied, status
        """
        return self._execute_returning(
            query,
            (user_promo_id, user_id, promotion_id, deliberations_remaining, discount_applied),
            user_id=user_id,
        )

    def update_user_promotion_status(
        self,
        user_promotion_id: str,
        status: str,
        user_id: str | None = None,
    ) -> bool:
        """Update user_promotion status.

        Args:
            user_promotion_id: The user_promotion UUID
            status: New status (active, exhausted, expired)
            user_id: Optional user_id for RLS

        Returns:
            True if updated, False if not found
        """
        self._validate_id(user_promotion_id, "user_promotion_id")
        query = """
            UPDATE user_promotions
            SET status = %s
            WHERE id = %s
        """
        count = self._execute_count(query, (status, user_promotion_id), user_id=user_id)
        return count > 0

    def decrement_deliberations(self, user_promotion_id: str, user_id: str) -> int | None:
        """Decrement deliberations_remaining and return new value.

        Marks as exhausted if reaches 0.

        Args:
            user_promotion_id: The user_promotion UUID
            user_id: The user ID for RLS

        Returns:
            New deliberations_remaining value, or None if not found/already 0
        """
        self._validate_id(user_promotion_id, "user_promotion_id")
        self._validate_id(user_id, "user_id")

        query = """
            UPDATE user_promotions
            SET deliberations_remaining = GREATEST(0, deliberations_remaining - 1),
                status = CASE
                    WHEN deliberations_remaining <= 1 THEN 'exhausted'
                    ELSE status
                END
            WHERE id = %s
              AND status = 'active'
              AND deliberations_remaining > 0
            RETURNING deliberations_remaining
        """
        row = self._execute_one(query, (user_promotion_id,), user_id=user_id)
        return row["deliberations_remaining"] if row else None

    def expire_promotions(self) -> int:
        """Expire all promotions past their expires_at date.

        Also updates user_promotions status to 'expired'.

        Returns:
            Number of user_promotions marked expired
        """
        now = datetime.now(UTC)

        # Update user_promotions for expired promotions
        query = """
            UPDATE user_promotions up
            SET status = 'expired'
            FROM promotions p
            WHERE up.promotion_id = p.id
              AND up.status = 'active'
              AND p.expires_at IS NOT NULL
              AND p.expires_at < %s
        """
        return self._execute_count(query, (now,))

    def get_applicable_invoice_promos(self, user_id: str) -> list[dict[str, Any]]:
        """Get user's active discount promotions applicable to invoices.

        Returns promotions with type percentage_discount or flat_discount
        that are still active.

        Args:
            user_id: The user ID

        Returns:
            List of user_promotion dicts with nested promotion data,
            ordered by type (percentage first) then applied_at
        """
        self._validate_id(user_id, "user_id")
        query = """
            SELECT
                up.id,
                up.user_id,
                up.promotion_id,
                up.applied_at,
                up.deliberations_remaining,
                up.discount_applied,
                up.status,
                p.code AS promotion_code,
                p.type AS promotion_type,
                p.value AS promotion_value,
                p.max_uses AS promotion_max_uses,
                p.uses_count AS promotion_uses_count,
                p.expires_at AS promotion_expires_at,
                p.created_at AS promotion_created_at,
                p.deleted_at AS promotion_deleted_at
            FROM user_promotions up
            JOIN promotions p ON up.promotion_id = p.id
            WHERE up.user_id = %s
              AND up.status = 'active'
              AND p.type IN ('percentage_discount', 'flat_discount')
              AND p.deleted_at IS NULL
            ORDER BY
                CASE p.type
                    WHEN 'percentage_discount' THEN 1
                    WHEN 'flat_discount' THEN 2
                END,
                up.applied_at ASC
        """
        rows = self._execute_query(query, (user_id,), user_id=user_id)
        return [self._format_user_promotion(row) for row in rows]

    def record_promo_invoice_application(
        self,
        user_promotion_id: str,
        stripe_invoice_id: str,
        stripe_invoice_item_id: str,
        discount_amount_cents: int,
    ) -> dict[str, Any]:
        """Record a promo discount application to a Stripe invoice.

        Args:
            user_promotion_id: The user_promotion UUID
            stripe_invoice_id: Stripe invoice ID
            stripe_invoice_item_id: Stripe invoice item ID
            discount_amount_cents: Discount amount in cents (positive)

        Returns:
            Created promo_invoice_application dict
        """
        self._validate_id(user_promotion_id, "user_promotion_id")

        app_id = str(uuid4())
        query = """
            INSERT INTO promo_invoice_applications
                (id, user_promotion_id, stripe_invoice_id, stripe_invoice_item_id, discount_amount_cents)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, user_promotion_id, stripe_invoice_id, stripe_invoice_item_id,
                      discount_amount_cents, applied_at
        """
        return self._execute_returning(
            query,
            (
                app_id,
                user_promotion_id,
                stripe_invoice_id,
                stripe_invoice_item_id,
                discount_amount_cents,
            ),
        )

    def has_promo_applied_to_invoice(self, stripe_invoice_id: str) -> bool:
        """Check if any promos have been applied to a Stripe invoice.

        Used for idempotency check.

        Args:
            stripe_invoice_id: Stripe invoice ID

        Returns:
            True if promos already applied
        """
        query = """
            SELECT 1 FROM promo_invoice_applications
            WHERE stripe_invoice_id = %s
            LIMIT 1
        """
        row = self._execute_one(query, (stripe_invoice_id,))
        return row is not None

    def mark_discount_promo_exhausted(self, user_promotion_id: str, user_id: str) -> bool:
        """Mark a discount promo as exhausted after invoice application.

        Args:
            user_promotion_id: The user_promotion UUID
            user_id: The user ID for RLS

        Returns:
            True if updated, False if not found
        """
        self._validate_id(user_promotion_id, "user_promotion_id")
        self._validate_id(user_id, "user_id")

        query = """
            UPDATE user_promotions
            SET status = 'exhausted'
            WHERE id = %s
              AND status = 'active'
        """
        count = self._execute_count(query, (user_promotion_id,), user_id=user_id)
        return count > 0

    @staticmethod
    def _format_user_promotion(row: dict[str, Any]) -> dict[str, Any]:
        """Format raw row into nested user_promotion structure.

        Args:
            row: Raw database row

        Returns:
            Formatted dict with nested promotion object
        """
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "promotion_id": row["promotion_id"],
            "applied_at": row["applied_at"],
            "deliberations_remaining": row["deliberations_remaining"],
            "discount_applied": row["discount_applied"],
            "status": row["status"],
            "promotion": {
                "id": row["promotion_id"],
                "code": row["promotion_code"],
                "type": row["promotion_type"],
                "value": float(row["promotion_value"]),
                "max_uses": row["promotion_max_uses"],
                "uses_count": row["promotion_uses_count"],
                "expires_at": row["promotion_expires_at"],
                "created_at": row["promotion_created_at"],
                "deleted_at": row["promotion_deleted_at"],
            },
        }


# Singleton instance
promotion_repository = PromotionRepository()
