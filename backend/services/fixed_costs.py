"""Fixed costs service for infrastructure cost tracking.

Provides CRUD operations for fixed infrastructure costs:
- DigitalOcean Droplet, Spaces
- Managed Redis, PostgreSQL
- Resend email
- Other recurring costs

These are manually configured values that don't come from API usage.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from bo1.state.database import db_session

logger = logging.getLogger(__name__)


@dataclass
class FixedCost:
    """Fixed infrastructure cost entry."""

    id: int
    provider: str
    description: str
    monthly_amount_usd: Decimal
    category: str
    active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


def _row_to_fixed_cost(row: dict[str, Any]) -> FixedCost:
    """Convert database row to FixedCost dataclass."""
    return FixedCost(
        id=row["id"],
        provider=row["provider"],
        description=row["description"],
        monthly_amount_usd=row["monthly_amount_usd"],
        category=row["category"],
        active=row["active"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_fixed_costs(active_only: bool = True) -> list[FixedCost]:
    """List all fixed costs.

    Args:
        active_only: If True, only return active costs

    Returns:
        List of FixedCost entries
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            if active_only:
                cur.execute(
                    """
                    SELECT * FROM fixed_costs
                    WHERE active = TRUE
                    ORDER BY provider, description
                    """
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM fixed_costs
                    ORDER BY provider, description
                    """
                )
            rows = cur.fetchall()
            return [_row_to_fixed_cost(row) for row in rows]


def get_fixed_cost(cost_id: int) -> FixedCost | None:
    """Get a fixed cost by ID.

    Args:
        cost_id: Fixed cost ID

    Returns:
        FixedCost if found, None otherwise
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM fixed_costs WHERE id = %s", (cost_id,))
            row = cur.fetchone()
            return _row_to_fixed_cost(row) if row else None


def create_fixed_cost(
    provider: str,
    description: str,
    monthly_amount_usd: Decimal,
    category: str = "compute",
    notes: str | None = None,
) -> FixedCost:
    """Create a new fixed cost entry.

    Args:
        provider: Provider name (e.g., digitalocean, redis_labs)
        description: Cost description (e.g., "Droplet s-2vcpu-4gb")
        monthly_amount_usd: Monthly cost in USD
        category: Category (compute, storage, database, email, monitoring)
        notes: Optional notes

    Returns:
        Created FixedCost
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fixed_costs (provider, description, monthly_amount_usd, category, notes)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (provider, description, monthly_amount_usd, category, notes),
            )
            row = cur.fetchone()
            logger.info(f"Created fixed cost: {provider}/{description} ${monthly_amount_usd}")
            return _row_to_fixed_cost(row)


def update_fixed_cost(
    cost_id: int,
    monthly_amount_usd: Decimal | None = None,
    active: bool | None = None,
    notes: str | None = None,
) -> FixedCost | None:
    """Update a fixed cost entry.

    Args:
        cost_id: Fixed cost ID
        monthly_amount_usd: New monthly amount (optional)
        active: New active status (optional)
        notes: New notes (optional)

    Returns:
        Updated FixedCost if found, None otherwise
    """
    updates = []
    params = []

    if monthly_amount_usd is not None:
        updates.append("monthly_amount_usd = %s")
        params.append(monthly_amount_usd)

    if active is not None:
        updates.append("active = %s")
        params.append(active)

    if notes is not None:
        updates.append("notes = %s")
        params.append(notes)

    if not updates:
        return get_fixed_cost(cost_id)

    updates.append("updated_at = NOW()")
    params.append(cost_id)

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE fixed_costs
                SET {", ".join(updates)}
                WHERE id = %s
                RETURNING *
                """,
                params,
            )
            row = cur.fetchone()
            if row:
                logger.info(f"Updated fixed cost {cost_id}")
                return _row_to_fixed_cost(row)
            return None


def delete_fixed_cost(cost_id: int) -> bool:
    """Delete a fixed cost entry (soft delete via active=false).

    Args:
        cost_id: Fixed cost ID

    Returns:
        True if deleted, False if not found
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE fixed_costs
                SET active = FALSE, updated_at = NOW()
                WHERE id = %s AND active = TRUE
                RETURNING id
                """,
                (cost_id,),
            )
            result = cur.fetchone()
            if result:
                logger.info(f"Deleted fixed cost {cost_id}")
                return True
            return False


def get_monthly_fixed_total() -> Decimal:
    """Get total monthly fixed costs.

    Returns:
        Total monthly fixed costs in USD
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(monthly_amount_usd), 0) as total
                FROM fixed_costs
                WHERE active = TRUE
                """
            )
            row = cur.fetchone()
            return Decimal(row["total"]) if row else Decimal(0)


def get_fixed_costs_by_category() -> dict[str, Decimal]:
    """Get fixed costs grouped by category.

    Returns:
        Dict mapping category to total monthly cost
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT category, SUM(monthly_amount_usd) as total
                FROM fixed_costs
                WHERE active = TRUE
                GROUP BY category
                ORDER BY total DESC
                """
            )
            rows = cur.fetchall()
            return {row["category"]: Decimal(row["total"]) for row in rows}


def get_fixed_costs_by_provider() -> dict[str, Decimal]:
    """Get fixed costs grouped by provider.

    Returns:
        Dict mapping provider to total monthly cost
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT provider, SUM(monthly_amount_usd) as total
                FROM fixed_costs
                WHERE active = TRUE
                GROUP BY provider
                ORDER BY total DESC
                """
            )
            rows = cur.fetchall()
            return {row["provider"]: Decimal(row["total"]) for row in rows}


def seed_default_fixed_costs() -> list[FixedCost]:
    """Seed default fixed costs if table is empty.

    Default entries based on typical Bo1 infrastructure:
    - DigitalOcean Droplet (s-2vcpu-4gb-intel): $28/mo
    - DigitalOcean Spaces (250GB): $5/mo
    - Managed Redis (2GB): $15/mo (estimate)
    - Neon PostgreSQL (free tier): $0/mo

    Returns:
        List of created FixedCost entries
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM fixed_costs")
            row = cur.fetchone()
            if row["count"] > 0:
                logger.info("Fixed costs already seeded, skipping")
                return []

    # Default infrastructure costs
    defaults = [
        ("digitalocean", "Droplet s-2vcpu-4gb-intel", Decimal("28.00"), "compute"),
        ("digitalocean", "Spaces 250GB", Decimal("5.00"), "storage"),
        ("digitalocean", "Managed Redis 2GB", Decimal("15.00"), "database"),
        ("neon", "PostgreSQL Pro", Decimal("0.00"), "database"),
        ("resend", "Email (Pro tier)", Decimal("20.00"), "email"),
    ]

    created = []
    for provider, desc, amount, category in defaults:
        cost = create_fixed_cost(provider, desc, amount, category)
        created.append(cost)

    logger.info(f"Seeded {len(created)} default fixed costs")
    return created
