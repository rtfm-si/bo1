"""GDPR data export and deletion service.

Provides:
- collect_user_data: Aggregate all user data for export (Art. 15)
- delete_user_data: Anonymize/delete user data (Art. 17)
"""

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from bo1.state.database import db_session
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# Redis key prefixes (from conversation_repo.py)
CONV_PREFIX = "dataset_conv"
CONV_INDEX_PREFIX = "dataset_convs"


class GDPRError(Exception):
    """Error during GDPR operation."""

    pass


def _hash_text(text: str) -> str:
    """Hash text for anonymization."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def collect_user_data(user_id: str) -> dict[str, Any]:
    """Collect all user data for GDPR export (Art. 15).

    Aggregates data from all tables where the user has data.

    Args:
        user_id: User identifier

    Returns:
        Dictionary with all user data organized by category

    Raises:
        GDPRError: If data collection fails
    """
    try:
        data: dict[str, Any] = {
            "export_date": datetime.now(UTC).isoformat(),
            "user_id": user_id,
        }

        with db_session() as conn:
            with conn.cursor() as cur:
                # User profile
                cur.execute(
                    """
                    SELECT id, email, auth_provider, subscription_tier,
                           is_admin, gdpr_consent_at, email_preferences,
                           created_at, updated_at
                    FROM users WHERE id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                data["profile"] = dict(row) if row else None

                # User context (business settings)
                cur.execute(
                    """
                    SELECT * FROM user_context WHERE user_id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                context_data = dict(row) if row else None
                data["business_context"] = context_data

                # Extract and structure insights (clarifications) separately for clarity
                if context_data and context_data.get("clarifications"):
                    clarifications = context_data.get("clarifications", {})
                    data["insights"] = {
                        "clarifications": [
                            {
                                "question": question,
                                "answer": item.get("answer") if isinstance(item, dict) else item,
                                "answered_at": item.get("answered_at")
                                if isinstance(item, dict)
                                else None,
                                "updated_at": item.get("updated_at")
                                if isinstance(item, dict)
                                else None,
                                "session_id": item.get("session_id")
                                if isinstance(item, dict)
                                else None,
                                "source": item.get("source", "meeting")
                                if isinstance(item, dict)
                                else "meeting",
                            }
                            for question, item in clarifications.items()
                        ]
                    }

                # Sessions (meetings)
                cur.execute(
                    """
                    SELECT id, problem_statement, problem_context, status,
                           phase, total_cost, round_number, synthesis,
                           created_at, updated_at
                    FROM sessions WHERE user_id = %s
                    ORDER BY created_at DESC
                    """,
                    (user_id,),
                )
                data["sessions"] = [dict(r) for r in cur.fetchall()]

                # Actions
                cur.execute(
                    """
                    SELECT id, title, description, status, priority,
                           estimated_start_date, estimated_end_date,
                           target_start_date, target_end_date,
                           actual_start_date, actual_end_date,
                           source_session_id, created_at, updated_at
                    FROM actions WHERE user_id = %s
                    ORDER BY created_at DESC
                    """,
                    (user_id,),
                )
                data["actions"] = [dict(r) for r in cur.fetchall()]

                # Datasets (including clarifications)
                cur.execute(
                    """
                    SELECT id, name, source_type, file_path, row_count,
                           column_count, file_size_bytes, summary, clarifications,
                           created_at, updated_at
                    FROM datasets WHERE user_id = %s AND deleted_at IS NULL
                    ORDER BY created_at DESC
                    """,
                    (user_id,),
                )
                datasets = [dict(r) for r in cur.fetchall()]
                data["datasets"] = datasets

                # Extract clarifications for easy access
                data["dataset_clarifications"] = [
                    {
                        "dataset_id": ds["id"],
                        "dataset_name": ds["name"],
                        "clarifications": ds.get("clarifications") or [],
                    }
                    for ds in datasets
                    if ds.get("clarifications")
                ]

                # Projects
                cur.execute(
                    """
                    SELECT id, name, description, status, color,
                           created_at, updated_at
                    FROM projects WHERE user_id = %s
                    ORDER BY created_at DESC
                    """,
                    (user_id,),
                )
                data["projects"] = [dict(r) for r in cur.fetchall()]

                # GDPR audit log (user's own audit trail)
                cur.execute(
                    """
                    SELECT id, action, details, ip_address, created_at
                    FROM gdpr_audit_log WHERE user_id = %s
                    ORDER BY created_at DESC
                    """,
                    (user_id,),
                )
                data["gdpr_audit_log"] = [dict(r) for r in cur.fetchall()]

        # Collect dataset conversations from PostgreSQL (source of truth)
        data["dataset_conversations"] = _collect_dataset_conversations(user_id)

        # Collect mentor conversations from PostgreSQL
        data["mentor_conversations"] = _collect_mentor_conversations(user_id)

        # Convert datetime objects to ISO strings for JSON serialization
        data = _serialize_for_json(data)

        logger.info(f"Collected GDPR export data for user {user_id}")
        return data

    except Exception as e:
        logger.error(f"Failed to collect user data for {user_id}: {e}")
        raise GDPRError(f"Data collection failed: {e}") from e


def delete_user_data(user_id: str) -> dict[str, Any]:
    """Delete/anonymize user data for GDPR erasure (Art. 17).

    Anonymization strategy:
    - Sessions: Keep structure, null user_id, hash problem_statement
    - Actions: Keep structure, null user_id, anonymize titles
    - Datasets: Delete files from storage, remove DB records
    - User profile: Delete completely
    - User context: Delete completely

    Args:
        user_id: User identifier

    Returns:
        Summary of deleted/anonymized records

    Raises:
        GDPRError: If deletion fails
    """
    from backend.services.spaces import SpacesClient, SpacesError

    summary: dict[str, Any] = {
        "user_id": user_id,
        "deleted_at": datetime.now(UTC).isoformat(),
        "sessions_anonymized": 0,
        "actions_anonymized": 0,
        "datasets_deleted": 0,
        "files_deleted": 0,
        "dataset_conversations_deleted": 0,
        "mentor_conversations_deleted": 0,
        "errors": [],
    }

    # Delete dataset conversations from PostgreSQL + Redis cache
    summary["dataset_conversations_deleted"] = _delete_dataset_conversations(user_id)

    # Delete mentor conversations from PostgreSQL (via CASCADE, but explicit is safer)
    summary["mentor_conversations_deleted"] = _delete_mentor_conversations(user_id)

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # 1. Get dataset files to delete from storage
                cur.execute(
                    """
                    SELECT id, file_path FROM datasets
                    WHERE user_id = %s AND deleted_at IS NULL
                    """,
                    (user_id,),
                )
                datasets = cur.fetchall()

                # Delete files from DO Spaces
                if datasets:
                    try:
                        spaces = SpacesClient()
                        for ds in datasets:
                            file_path = ds.get("file_path")
                            if file_path:
                                try:
                                    spaces.delete(file_path)
                                    summary["files_deleted"] += 1
                                except SpacesError as e:
                                    summary["errors"].append(f"File delete failed: {e}")
                    except Exception as e:
                        summary["errors"].append(f"Spaces client error: {e}")

                # 2. Delete datasets (hard delete since files are gone)
                cur.execute(
                    """
                    DELETE FROM datasets WHERE user_id = %s
                    """,
                    (user_id,),
                )
                summary["datasets_deleted"] = cur.rowcount

                # 3. Delete dataset analyses
                cur.execute(
                    """
                    DELETE FROM dataset_analyses
                    WHERE dataset_id IN (
                        SELECT id FROM datasets WHERE user_id = %s
                    )
                    """,
                    (user_id,),
                )

                # 4. Anonymize actions (keep for reporting, remove PII)
                cur.execute(
                    """
                    UPDATE actions
                    SET user_id = NULL,
                        title = 'Deleted Action',
                        description = NULL,
                        updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                summary["actions_anonymized"] = cur.rowcount

                # 5. Anonymize sessions (keep for aggregate stats)
                cur.execute(
                    """
                    UPDATE sessions
                    SET user_id = NULL,
                        problem_statement = %s,
                        problem_context = NULL,
                        synthesis = NULL,
                        updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (f"[DELETED:{_hash_text(user_id)}]", user_id),
                )
                summary["sessions_anonymized"] = cur.rowcount

                # 6. Delete user context
                cur.execute(
                    """
                    DELETE FROM user_context WHERE user_id = %s
                    """,
                    (user_id,),
                )

                # 7. Delete projects
                cur.execute(
                    """
                    DELETE FROM projects WHERE user_id = %s
                    """,
                    (user_id,),
                )

                # 8. Delete user record last (FK constraints)
                cur.execute(
                    """
                    DELETE FROM users WHERE id = %s
                    """,
                    (user_id,),
                )

        logger.info(f"Completed GDPR deletion for user {user_id}: {summary}")
        return summary

    except Exception as e:
        logger.error(f"GDPR deletion failed for {user_id}: {e}")
        raise GDPRError(f"Deletion failed: {e}") from e


def _collect_dataset_conversations(user_id: str) -> list[dict[str, Any]]:
    """Collect dataset Q&A conversations from PostgreSQL for GDPR export.

    Args:
        user_id: User identifier

    Returns:
        List of dataset conversation dicts with full messages
    """
    try:
        from backend.services.dataset_conversation_pg_repo import (
            get_dataset_conversation_pg_repo,
        )

        pg_repo = get_dataset_conversation_pg_repo()
        conversations = pg_repo.get_all_for_export(user_id)
        logger.info(f"Collected {len(conversations)} dataset conversations for user {user_id}")
        return conversations
    except Exception as e:
        logger.warning(f"Failed to collect dataset conversations for {user_id}: {e}")
        return []


def _delete_dataset_conversations(user_id: str) -> int:
    """Delete all dataset conversations for a user from PostgreSQL + Redis.

    Args:
        user_id: User identifier

    Returns:
        Number of conversations deleted
    """
    deleted = 0

    # Delete from PostgreSQL (source of truth)
    try:
        from backend.services.dataset_conversation_pg_repo import (
            get_dataset_conversation_pg_repo,
        )

        pg_repo = get_dataset_conversation_pg_repo()
        deleted = pg_repo.delete_all_for_user(user_id)
        logger.info(f"Deleted {deleted} dataset conversations from PostgreSQL for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to delete dataset conversations from PostgreSQL for {user_id}: {e}")

    # Also clean up Redis cache
    _delete_user_conversations_redis(user_id)

    return deleted


def _delete_user_conversations_redis(user_id: str) -> int:
    """Clean up Redis cache for user's dataset conversations.

    Args:
        user_id: User identifier

    Returns:
        Number of cached conversations deleted
    """
    deleted_count = 0
    try:
        redis = RedisManager()
        client = redis.client

        # Scan for all conversation index keys for this user
        index_pattern = f"{CONV_INDEX_PREFIX}:{user_id}:*"
        cursor = 0
        keys_to_delete: list[str] = []
        conv_ids: set[str] = set()

        while True:
            cursor, keys = client.scan(cursor, match=index_pattern, count=100)
            for key in keys:
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                keys_to_delete.append(key_str)
                members = client.zrange(key_str, 0, -1)
                for member in members:
                    member_str = member.decode("utf-8") if isinstance(member, bytes) else member
                    conv_ids.add(member_str)
            if cursor == 0:
                break

        # Delete conversation data
        for conv_id in conv_ids:
            conv_key = f"{CONV_PREFIX}:{conv_id}"
            if client.delete(conv_key):
                deleted_count += 1

        # Delete index keys
        for key in keys_to_delete:
            client.delete(key)

        logger.info(f"Cleaned up {deleted_count} cached conversations for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to clean up Redis cache for {user_id}: {e}")

    return deleted_count


def _collect_mentor_conversations(user_id: str) -> list[dict[str, Any]]:
    """Collect mentor chat conversations from PostgreSQL for GDPR export.

    Args:
        user_id: User identifier

    Returns:
        List of mentor conversation dicts with full messages
    """
    try:
        from backend.services.mentor_conversation_pg_repo import (
            get_mentor_conversation_pg_repo,
        )

        pg_repo = get_mentor_conversation_pg_repo()
        conversations = pg_repo.get_all_for_export(user_id)
        logger.info(f"Collected {len(conversations)} mentor conversations for user {user_id}")
        return conversations
    except Exception as e:
        logger.warning(f"Failed to collect mentor conversations for {user_id}: {e}")
        return []


def _delete_mentor_conversations(user_id: str) -> int:
    """Delete all mentor conversations for a user.

    Args:
        user_id: User identifier

    Returns:
        Number of conversations deleted
    """
    try:
        from backend.services.mentor_conversation_pg_repo import (
            get_mentor_conversation_pg_repo,
        )

        pg_repo = get_mentor_conversation_pg_repo()
        deleted = pg_repo.delete_all_for_user(user_id)
        logger.info(f"Deleted {deleted} mentor conversations for user {user_id}")
        return deleted
    except Exception as e:
        logger.warning(f"Failed to delete mentor conversations for {user_id}: {e}")
        return 0


def _serialize_for_json(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(v) for v in obj]
    return obj
