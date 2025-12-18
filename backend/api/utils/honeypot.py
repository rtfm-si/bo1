"""Honeypot detection for automated bot/attack filtering.

Provides:
- Hidden form field validation for bot detection
- Prometheus metrics for honeypot triggers
- Zero-cost first-pass filter before LLM-based detection

Usage:
    from backend.api.utils.honeypot import validate_honeypot_fields

    @router.post("/endpoint")
    async def create_item(body: MyRequestWithHoneypot):
        validate_honeypot_fields(body, "create_item")  # Raises 400 if honeypot filled
        ...
"""

import logging
from typing import Any

from fastapi import HTTPException
from prometheus_client import Counter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Prometheus metric for tracking honeypot triggers
honeypot_triggered = Counter(
    "bo1_honeypot_triggered_total",
    "Total honeypot field triggers (bot detection)",
    ["endpoint", "field_name"],
)


class HoneypotMixin(BaseModel):
    """Mixin for Pydantic models that include honeypot fields.

    Add this as a parent class to request models that should have honeypot protection.
    Frontend forms should include invisible fields with these names that humans won't fill.

    Fields use _hp_ prefix to avoid collision with real fields and password managers.
    """

    hp_email: str | None = Field(
        None,
        alias="_hp_email",
        description="Hidden honeypot field - should always be empty",
        json_schema_extra={"hidden": True},
    )
    hp_url: str | None = Field(
        None,
        alias="_hp_url",
        description="Hidden honeypot field - should always be empty",
        json_schema_extra={"hidden": True},
    )
    hp_phone: str | None = Field(
        None,
        alias="_hp_phone",
        description="Hidden honeypot field - should always be empty",
        json_schema_extra={"hidden": True},
    )


def validate_honeypot_field(value: str | None) -> bool:
    """Check if a honeypot field is clean (empty or None).

    Args:
        value: The honeypot field value to check

    Returns:
        True if clean (empty/None/whitespace-only), False if triggered
    """
    if value is None:
        return True
    return value.strip() == ""


def validate_honeypot_fields(body: Any, endpoint: str) -> None:
    """Validate all honeypot fields on a request body.

    Should be called early in endpoint handlers as a cheap first-pass filter.
    Logs and increments metrics when honeypot is triggered.

    Args:
        body: Pydantic model instance (should have HoneypotMixin fields)
        endpoint: Name of the endpoint for metrics labels

    Raises:
        HTTPException: 400 if any honeypot field is filled
    """
    honeypot_fields = [
        ("_hp_email", "hp_email"),
        ("_hp_url", "hp_url"),
        ("_hp_phone", "hp_phone"),
    ]

    for field_name, attr_name in honeypot_fields:
        value = getattr(body, attr_name, None)
        if not validate_honeypot_field(value):
            # Log for security audit
            logger.warning(
                f"Honeypot triggered: endpoint={endpoint} field={field_name}",
                extra={"endpoint": endpoint, "field": field_name},
            )
            # Increment Prometheus metric
            honeypot_triggered.labels(endpoint=endpoint, field_name=field_name).inc()
            # Return generic error to avoid revealing detection method
            raise HTTPException(
                status_code=400,
                detail="Invalid request",
            )
