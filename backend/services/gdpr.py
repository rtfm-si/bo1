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

logger = logging.getLogger(__name__)


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
                data["business_context"] = dict(row) if row else None

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

                # Datasets
                cur.execute(
                    """
                    SELECT id, name, source_type, file_path, row_count,
                           column_count, file_size_bytes, summary,
                           created_at, updated_at
                    FROM datasets WHERE user_id = %s AND deleted_at IS NULL
                    ORDER BY created_at DESC
                    """,
                    (user_id,),
                )
                data["datasets"] = [dict(r) for r in cur.fetchall()]

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
        "errors": [],
    }

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


def _serialize_for_json(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(v) for v in obj]
    return obj
