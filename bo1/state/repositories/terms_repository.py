"""Terms & Conditions repository for T&C versioning and consent tracking.

Handles:
- T&C version management (get active version, get by ID)
- Consent recording and lookup
"""

import logging
from typing import Any
from uuid import UUID

from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class TermsRepository(BaseRepository):
    """Repository for T&C versions and user consents."""

    # =========================================================================
    # T&C Version Operations
    # =========================================================================

    def get_active_version(self) -> dict[str, Any] | None:
        """Get the currently active T&C version.

        Returns:
            Active T&C version dict or None if no active version.
        """
        query = """
            SELECT id, version, content, published_at, is_active, created_at
            FROM terms_versions
            WHERE is_active = true
            LIMIT 1
        """
        return self._execute_one(query)

    def get_version_by_id(self, version_id: UUID | str) -> dict[str, Any] | None:
        """Get a specific T&C version by ID.

        Args:
            version_id: UUID of the T&C version.

        Returns:
            T&C version dict or None.
        """
        query = """
            SELECT id, version, content, published_at, is_active, created_at
            FROM terms_versions
            WHERE id = %s
        """
        return self._execute_one(query, (str(version_id),))

    def get_all_versions(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        """Get all T&C versions with pagination.

        Args:
            limit: Max records to return.
            offset: Records to skip.

        Returns:
            Tuple of (version records, total count).
        """
        count_query = "SELECT COUNT(*) as count FROM terms_versions"
        count_result = self._execute_one(count_query)
        total = count_result["count"] if count_result else 0

        query = """
            SELECT id, version, content, published_at, is_active, created_at
            FROM terms_versions
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        records = self._execute_query(query, (limit, offset))
        return records, total

    def create_version(self, version: str, content: str, is_active: bool = False) -> dict[str, Any]:
        """Create a new T&C version (draft by default).

        Args:
            version: Version string (e.g., "1.1").
            content: T&C content (markdown).
            is_active: Whether to activate immediately (default False).

        Returns:
            Created version record.
        """
        query = """
            INSERT INTO terms_versions (version, content, is_active, published_at)
            VALUES (%s, %s, %s, CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END)
            RETURNING id, version, content, published_at, is_active, created_at
        """
        return self._execute_returning(query, (version, content, is_active, is_active))

    def update_version(self, version_id: UUID | str, content: str) -> dict[str, Any] | None:
        """Update a draft T&C version's content.

        Only updates if version is not active (draft).

        Args:
            version_id: UUID of the version to update.
            content: New content.

        Returns:
            Updated version record or None if not found/active.
        """
        query = """
            UPDATE terms_versions
            SET content = %s
            WHERE id = %s AND is_active = false
            RETURNING id, version, content, published_at, is_active, created_at
        """
        return self._execute_returning(query, (content, str(version_id)))

    def publish_version(self, version_id: UUID | str) -> dict[str, Any] | None:
        """Publish a T&C version (atomically deactivate others).

        Args:
            version_id: UUID of the version to publish.

        Returns:
            Published version record or None if not found.
        """
        # Atomic: deactivate all, then activate the target
        query = """
            WITH deactivate AS (
                UPDATE terms_versions SET is_active = false WHERE is_active = true
            )
            UPDATE terms_versions
            SET is_active = true, published_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, version, content, published_at, is_active, created_at
        """
        return self._execute_returning(query, (str(version_id),))

    # =========================================================================
    # Consent Operations
    # =========================================================================

    def create_consent(
        self,
        user_id: str,
        version_id: UUID | str,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        """Record a user's consent to a T&C version.

        Args:
            user_id: User ID.
            version_id: T&C version ID.
            ip_address: User's IP address (optional).

        Returns:
            Created consent record.
        """
        query = """
            INSERT INTO terms_consents (user_id, terms_version_id, ip_address)
            VALUES (%s, %s, %s)
            RETURNING id, user_id, terms_version_id, consented_at, ip_address
        """
        return self._execute_returning(
            query,
            (user_id, str(version_id), ip_address),
            user_id=user_id,
        )

    def get_user_latest_consent(self, user_id: str) -> dict[str, Any] | None:
        """Get a user's most recent consent record.

        Args:
            user_id: User ID.

        Returns:
            Latest consent dict with version info, or None.
        """
        query = """
            SELECT tc.id, tc.user_id, tc.terms_version_id, tc.consented_at, tc.ip_address,
                   tv.version as terms_version, tv.published_at as terms_published_at
            FROM terms_consents tc
            JOIN terms_versions tv ON tc.terms_version_id = tv.id
            WHERE tc.user_id = %s
            ORDER BY tc.consented_at DESC
            LIMIT 1
        """
        return self._execute_one(query, (user_id,), user_id=user_id)

    def has_user_consented_to_current(self, user_id: str) -> bool:
        """Check if user has consented to the current active T&C version.

        Args:
            user_id: User ID.

        Returns:
            True if user has consented to current active version, False otherwise.
        """
        query = """
            SELECT EXISTS(
                SELECT 1 FROM terms_consents tc
                JOIN terms_versions tv ON tc.terms_version_id = tv.id
                WHERE tc.user_id = %s AND tv.is_active = true
            ) as has_consented
        """
        result = self._execute_one(query, (user_id,), user_id=user_id)
        return bool(result and result.get("has_consented"))

    def get_user_consents(self, user_id: str) -> list[dict[str, Any]]:
        """Get all consent records for a user.

        Args:
            user_id: User ID.

        Returns:
            List of consent records with version info.
        """
        query = """
            SELECT tc.id, tc.user_id, tc.terms_version_id, tc.consented_at, tc.ip_address,
                   tv.version as terms_version, tv.published_at as terms_published_at
            FROM terms_consents tc
            JOIN terms_versions tv ON tc.terms_version_id = tv.id
            WHERE tc.user_id = %s
            ORDER BY tc.consented_at DESC
        """
        return self._execute_query(query, (user_id,), user_id=user_id)

    def get_all_consents(
        self,
        limit: int = 50,
        offset: int = 0,
        time_filter_sql: str = "TRUE",
    ) -> tuple[list[dict[str, Any]], int]:
        """Get all consent records with pagination and time filtering.

        Args:
            limit: Max records to return.
            offset: Records to skip.
            time_filter_sql: SQL WHERE clause for time filtering (e.g. "consented_at >= ...").

        Returns:
            Tuple of (consent records with user email, total count).
        """
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as count
            FROM terms_consents tc
            WHERE {time_filter_sql}
        """
        count_result = self._execute_one(count_query)
        total = count_result["count"] if count_result else 0

        # Get paginated records with user email
        query = f"""
            SELECT tc.id, tc.user_id, tc.terms_version_id, tc.consented_at, tc.ip_address,
                   tv.version as terms_version, u.email
            FROM terms_consents tc
            JOIN terms_versions tv ON tc.terms_version_id = tv.id
            LEFT JOIN users u ON tc.user_id = u.id
            WHERE {time_filter_sql}
            ORDER BY tc.consented_at DESC
            LIMIT %s OFFSET %s
        """
        records = self._execute_query(query, (limit, offset))
        return records, total


# Singleton instance
terms_repository = TermsRepository()
