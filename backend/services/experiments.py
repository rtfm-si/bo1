"""A/B experiment management service.

Provides:
- Experiment CRUD and lifecycle management
- Deterministic variant assignment (reuses feature_flags hash function)
- Status transitions: draft -> running -> paused/concluded
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from bo1.state.database import db_session

logger = logging.getLogger(__name__)


@dataclass
class Variant:
    """Experiment variant."""

    name: str
    weight: int  # 0-100


@dataclass
class Experiment:
    """Experiment definition."""

    id: UUID
    name: str
    description: str | None
    status: str  # draft, running, paused, concluded
    variants: list[Variant]
    metrics: list[str]
    start_date: datetime | None
    end_date: datetime | None
    created_at: datetime
    updated_at: datetime


VALID_STATUSES = {"draft", "running", "paused", "concluded"}
VALID_TRANSITIONS = {
    "draft": {"running"},
    "running": {"paused", "concluded"},
    "paused": {"running", "concluded"},
    "concluded": set(),  # terminal state
}


def _hash_user_for_variant(experiment_name: str, user_id: str) -> int:
    """Generate deterministic hash for variant assignment (0-99).

    Uses same algorithm as feature_flags for consistency.
    """
    combined = f"exp:{experiment_name}:{user_id}"
    hash_bytes = hashlib.md5(combined.encode(), usedforsecurity=False).digest()
    return int.from_bytes(hash_bytes[:2], "big") % 100


def _parse_variants(data: Any) -> list[Variant]:
    """Parse variants from JSONB."""
    if isinstance(data, str):
        data = json.loads(data)
    return [Variant(name=v["name"], weight=v.get("weight", 50)) for v in (data or [])]


def _parse_metrics(data: Any) -> list[str]:
    """Parse metrics from JSONB."""
    if isinstance(data, str):
        data = json.loads(data)
    return data or []


def _row_to_experiment(row: dict) -> Experiment:
    """Convert database row to Experiment."""
    return Experiment(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        status=row["status"],
        variants=_parse_variants(row["variants"]),
        metrics=_parse_metrics(row["metrics"]),
        start_date=row["start_date"],
        end_date=row["end_date"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def get_experiment(experiment_id: UUID) -> Experiment | None:
    """Get an experiment by ID."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM experiments WHERE id = %s",
                (experiment_id,),
            )
            row = cur.fetchone()
            return _row_to_experiment(row) if row else None


def get_experiment_by_name(name: str) -> Experiment | None:
    """Get an experiment by name."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM experiments WHERE name = %s",
                (name,),
            )
            row = cur.fetchone()
            return _row_to_experiment(row) if row else None


def list_experiments(status: str | None = None) -> list[Experiment]:
    """List all experiments, optionally filtered by status."""
    with db_session() as conn:
        with conn.cursor() as cur:
            if status:
                cur.execute(
                    "SELECT * FROM experiments WHERE status = %s ORDER BY created_at DESC",
                    (status,),
                )
            else:
                cur.execute("SELECT * FROM experiments ORDER BY created_at DESC")
            return [_row_to_experiment(row) for row in cur.fetchall()]


def create_experiment(
    name: str,
    description: str | None = None,
    variants: list[dict[str, Any]] | None = None,
    metrics: list[str] | None = None,
) -> Experiment:
    """Create a new experiment in draft status.

    Args:
        name: Unique experiment name
        description: Optional description
        variants: List of {"name": str, "weight": int} (default: control/treatment 50/50)
        metrics: List of metric names to track

    Returns:
        Created experiment

    Raises:
        ValueError: If name already exists or variants invalid
    """
    # Validate variants
    if variants:
        total_weight = sum(v.get("weight", 50) for v in variants)
        if total_weight != 100:
            raise ValueError(f"Variant weights must sum to 100, got {total_weight}")
        if len(variants) < 2:
            raise ValueError("Must have at least 2 variants")
    else:
        variants = [{"name": "control", "weight": 50}, {"name": "treatment", "weight": 50}]

    now = datetime.now(UTC)

    with db_session() as conn:
        with conn.cursor() as cur:
            # Check for existing experiment
            cur.execute("SELECT id FROM experiments WHERE name = %s", (name,))
            if cur.fetchone():
                raise ValueError(f"Experiment '{name}' already exists")

            cur.execute(
                """
                INSERT INTO experiments (name, description, status, variants, metrics, created_at, updated_at)
                VALUES (%s, %s, 'draft', %s, %s, %s, %s)
                RETURNING *
                """,
                (name, description, json.dumps(variants), json.dumps(metrics or []), now, now),
            )
            row = cur.fetchone()
            conn.commit()
            return _row_to_experiment(row)


def update_experiment(
    experiment_id: UUID,
    description: str | None = None,
    variants: list[dict[str, Any]] | None = None,
    metrics: list[str] | None = None,
) -> Experiment | None:
    """Update an experiment. Only allowed in draft status.

    Args:
        experiment_id: Experiment UUID
        description: New description (None = no change)
        variants: New variants (None = no change)
        metrics: New metrics (None = no change)

    Returns:
        Updated experiment or None if not found

    Raises:
        ValueError: If experiment not in draft status or variants invalid
    """
    experiment = get_experiment(experiment_id)
    if not experiment:
        return None

    if experiment.status != "draft":
        raise ValueError(f"Cannot update experiment in '{experiment.status}' status")

    updates = []
    params: list[Any] = []
    now = datetime.now(UTC)

    if description is not None:
        updates.append("description = %s")
        params.append(description)

    if variants is not None:
        total_weight = sum(v.get("weight", 50) for v in variants)
        if total_weight != 100:
            raise ValueError(f"Variant weights must sum to 100, got {total_weight}")
        if len(variants) < 2:
            raise ValueError("Must have at least 2 variants")
        updates.append("variants = %s")
        params.append(json.dumps(variants))

    if metrics is not None:
        updates.append("metrics = %s")
        params.append(json.dumps(metrics))

    if not updates:
        return experiment

    updates.append("updated_at = %s")
    params.append(now)
    params.append(experiment_id)

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE experiments SET {', '.join(updates)} WHERE id = %s RETURNING *",
                params,
            )
            row = cur.fetchone()
            conn.commit()
            return _row_to_experiment(row) if row else None


def _transition_status(experiment_id: UUID, new_status: str) -> Experiment | None:
    """Internal helper for status transitions."""
    experiment = get_experiment(experiment_id)
    if not experiment:
        return None

    if new_status not in VALID_TRANSITIONS.get(experiment.status, set()):
        raise ValueError(f"Cannot transition from '{experiment.status}' to '{new_status}'")

    now = datetime.now(UTC)
    updates = ["status = %s", "updated_at = %s"]
    params: list[Any] = [new_status, now]

    # Set start_date when transitioning to running (first time)
    if new_status == "running" and experiment.start_date is None:
        updates.append("start_date = %s")
        params.append(now)

    # Set end_date when concluding
    if new_status == "concluded":
        updates.append("end_date = %s")
        params.append(now)

    params.append(experiment_id)

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE experiments SET {', '.join(updates)} WHERE id = %s RETURNING *",
                params,
            )
            row = cur.fetchone()
            conn.commit()
            return _row_to_experiment(row) if row else None


def start_experiment(experiment_id: UUID) -> Experiment | None:
    """Start an experiment (draft/paused -> running)."""
    return _transition_status(experiment_id, "running")


def pause_experiment(experiment_id: UUID) -> Experiment | None:
    """Pause a running experiment."""
    return _transition_status(experiment_id, "paused")


def conclude_experiment(experiment_id: UUID) -> Experiment | None:
    """Conclude an experiment (terminal state)."""
    return _transition_status(experiment_id, "concluded")


def delete_experiment(experiment_id: UUID) -> bool:
    """Delete an experiment. Only allowed in draft status.

    Returns:
        True if deleted, False if not found

    Raises:
        ValueError: If experiment not in draft status
    """
    experiment = get_experiment(experiment_id)
    if not experiment:
        return False

    if experiment.status != "draft":
        raise ValueError(f"Cannot delete experiment in '{experiment.status}' status")

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM experiments WHERE id = %s RETURNING id", (experiment_id,))
            row = cur.fetchone()
            conn.commit()
            return row is not None


def assign_user_to_variant(experiment_name: str, user_id: str) -> str | None:
    """Assign a user to a variant in a running experiment.

    Uses deterministic hashing for consistent assignment.

    Args:
        experiment_name: Experiment name
        user_id: User ID

    Returns:
        Variant name, or None if experiment not running
    """
    experiment = get_experiment_by_name(experiment_name)
    if not experiment or experiment.status != "running":
        return None

    bucket = _hash_user_for_variant(experiment_name, user_id)

    # Walk through variants by weight
    cumulative = 0
    for variant in experiment.variants:
        cumulative += variant.weight
        if bucket < cumulative:
            return variant.name

    # Fallback to last variant
    return experiment.variants[-1].name if experiment.variants else None


def get_user_variant(experiment_name: str, user_id: str) -> str | None:
    """Get the variant a user is assigned to.

    Alias for assign_user_to_variant for clarity in read contexts.
    """
    return assign_user_to_variant(experiment_name, user_id)
