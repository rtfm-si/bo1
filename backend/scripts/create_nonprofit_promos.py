#!/usr/bin/env python3
"""Create nonprofit/charity promotional codes.

Creates two permanent promo codes for verified nonprofits:
- NONPROFIT80: 80% discount for nonprofits that can afford partial cost
- NONPROFIT100: 100% discount (free) for qualifying nonprofits

Usage:
    cd /Users/si/projects/bo1
    docker-compose exec bo1 uv run python -m backend.scripts.create_nonprofit_promos
"""

import sys
from datetime import UTC, datetime

from bo1.state.database import db_session
from bo1.utils.logging import get_logger

logger = get_logger(__name__)


def create_nonprofit_promos() -> None:
    """Create nonprofit promotional codes if they don't exist."""
    promos = [
        {
            "code": "NONPROFIT80",
            "type": "percentage_discount",
            "value": 80,
            "description": "80% nonprofit discount - for verified charities/nonprofits",
        },
        {
            "code": "NONPROFIT100",
            "type": "percentage_discount",
            "value": 100,
            "description": "100% nonprofit discount (free tier) - for verified charities/nonprofits",
        },
    ]

    with db_session() as conn:
        with conn.cursor() as cur:
            for promo in promos:
                # Check if already exists
                cur.execute(
                    "SELECT id FROM promotions WHERE code = %s",
                    (promo["code"],),
                )
                existing = cur.fetchone()

                if existing:
                    logger.info(f"Promo {promo['code']} already exists, skipping")
                    continue

                # Create the promo
                cur.execute(
                    """
                    INSERT INTO promotions (code, type, value, max_uses, expires_at, created_at)
                    VALUES (%s, %s, %s, NULL, NULL, %s)
                    RETURNING id
                    """,
                    (
                        promo["code"],
                        promo["type"],
                        promo["value"],
                        datetime.now(UTC),
                    ),
                )
                result = cur.fetchone()
                promo_id = result["id"] if result else None
                logger.info(
                    f"Created promo {promo['code']} (id={promo_id}): {promo['description']}"
                )

    print("Nonprofit promo codes created successfully:")  # noqa: T201
    print("  - NONPROFIT80: 80% discount (no expiry, unlimited uses)")  # noqa: T201
    print("  - NONPROFIT100: 100% discount/free (no expiry, unlimited uses)")  # noqa: T201
    print("\nApply to users via: Admin > Users > [user] > Promo button")  # noqa: T201


if __name__ == "__main__":
    try:
        create_nonprofit_promos()
    except Exception as e:
        logger.error(f"Failed to create nonprofit promos: {e}")
        sys.exit(1)
