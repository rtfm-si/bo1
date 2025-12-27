"""Research sharing consent service.

Manages user opt-in/opt-out for cross-user research sharing.
Privacy-first: no PII in shared research, explicit consent required.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from bo1.state.database import db_session
from bo1.state.repositories import cache_repository

logger = logging.getLogger(__name__)


@dataclass
class ResearchSharingConsentStatus:
    """User's research sharing consent status."""

    consented: bool
    consented_at: datetime | None = None
    revoked_at: datetime | None = None


def get_consent_status(user_id: str) -> ResearchSharingConsentStatus:
    """Get user's current research sharing consent status.

    Args:
        user_id: User identifier

    Returns:
        ResearchSharingConsentStatus with current state
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT consented_at, revoked_at
                FROM research_sharing_consent
                WHERE user_id = %s
                """,
                (user_id,),
            )
            result = cur.fetchone()

            if not result:
                return ResearchSharingConsentStatus(consented=False)

            consented_at = result["consented_at"]
            revoked_at = result["revoked_at"]
            # User is consented if they have a consent timestamp and haven't revoked
            is_consented = consented_at is not None and revoked_at is None

            return ResearchSharingConsentStatus(
                consented=is_consented,
                consented_at=consented_at,
                revoked_at=revoked_at,
            )


def give_consent(user_id: str) -> ResearchSharingConsentStatus:
    """Opt-in user to research sharing.

    When consent is given, existing research from this user becomes shareable.

    Args:
        user_id: User identifier

    Returns:
        Updated ResearchSharingConsentStatus
    """
    now = datetime.now(UTC)

    with db_session() as conn:
        with conn.cursor() as cur:
            # Upsert: insert or update existing record
            cur.execute(
                """
                INSERT INTO research_sharing_consent (user_id, consented_at, revoked_at)
                VALUES (%s, %s, NULL)
                ON CONFLICT (user_id)
                DO UPDATE SET consented_at = EXCLUDED.consented_at, revoked_at = NULL
                """,
                (user_id, now),
            )

    # Mark existing research as shareable
    updated = cache_repository.mark_user_research_shareable(user_id)
    logger.info(
        "research_sharing_consent_given",
        extra={"user_id": user_id, "entries_made_shareable": updated},
    )

    return ResearchSharingConsentStatus(consented=True, consented_at=now)


def revoke_consent(user_id: str) -> ResearchSharingConsentStatus:
    """Opt-out user from research sharing.

    Immediate effect: user's research marked as non-shareable.

    Args:
        user_id: User identifier

    Returns:
        Updated ResearchSharingConsentStatus
    """
    now = datetime.now(UTC)
    consented_at = None

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE research_sharing_consent
                SET revoked_at = %s
                WHERE user_id = %s
                RETURNING consented_at
                """,
                (now, user_id),
            )
            result = cur.fetchone()
            if result:
                consented_at = result["consented_at"]

    # Mark user's research as non-shareable
    updated = cache_repository.mark_user_research_non_shareable(user_id)
    logger.info(
        "research_sharing_consent_revoked",
        extra={"user_id": user_id, "entries_made_non_shareable": updated},
    )

    if consented_at:
        return ResearchSharingConsentStatus(
            consented=False,
            consented_at=consented_at,
            revoked_at=now,
        )

    return ResearchSharingConsentStatus(consented=False)


def is_consented(user_id: str) -> bool:
    """Quick check if user has consented to research sharing.

    Args:
        user_id: User identifier

    Returns:
        True if user has active consent
    """
    return get_consent_status(user_id).consented
