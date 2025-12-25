"""Business logic services for context management.

Contains helper functions for context operations like enrichment,
context conversion, and data merging.
"""

import logging
from typing import Any

from backend.api.context.models import (
    BusinessContext,
    ClarificationsStorage,
    ClarificationStorageEntry,
    DetectedCompetitor,
    EnrichmentSource,
)
from backend.api.utils.db_helpers import get_single_value
from bo1.logging.errors import ErrorCode, log_error
from bo1.security import sanitize_for_prompt

logger = logging.getLogger(__name__)


# Fields that contain user-provided text and need sanitization before LLM use
_TEXT_FIELDS_TO_SANITIZE = frozenset(
    {
        "business_model",
        "target_market",
        "product_description",
        "competitors",
        "company_name",
        "industry",
        "pricing_model",
        "brand_positioning",
        "brand_tone",
        "brand_maturity",
        "ideal_customer_profile",
        "main_value_proposition",
        "budget_constraints",
        "time_constraints",
        "regulatory_constraints",
        "north_star_goal",
    }
)


def sanitize_context_values(context_dict: dict[str, Any]) -> dict[str, Any]:
    """Sanitize user-provided text values in context dict to prevent prompt injection.

    Applies XML escape characters to string fields that may be interpolated into
    LLM prompts. Handles nested lists (e.g., product_categories, tech_stack).

    Args:
        context_dict: Context dict from context_model_to_dict()

    Returns:
        Sanitized context dict safe for LLM prompt interpolation
    """
    sanitized = context_dict.copy()

    for key, value in sanitized.items():
        if value is None:
            continue

        if key in _TEXT_FIELDS_TO_SANITIZE and isinstance(value, str):
            sanitized[key] = sanitize_for_prompt(value)
        elif isinstance(value, list):
            # Handle list fields like product_categories, tech_stack, keywords
            sanitized[key] = [
                sanitize_for_prompt(item) if isinstance(item, str) else item for item in value
            ]

    return sanitized


def context_data_to_model(context_data: dict[str, Any]) -> BusinessContext:
    """Convert raw context data dict to BusinessContext model.

    Args:
        context_data: Raw context data from database

    Returns:
        BusinessContext model instance
    """
    return BusinessContext(
        # Original fields
        business_model=context_data.get("business_model"),
        target_market=context_data.get("target_market"),
        product_description=context_data.get("product_description"),
        revenue=context_data.get("revenue"),
        customers=context_data.get("customers"),
        growth_rate=context_data.get("growth_rate"),
        competitors=context_data.get("competitors"),
        website=context_data.get("website"),
        # Extended fields (Tier 3)
        company_name=context_data.get("company_name"),
        business_stage=context_data.get("business_stage"),
        primary_objective=context_data.get("primary_objective"),
        industry=context_data.get("industry"),
        product_categories=context_data.get("product_categories"),
        pricing_model=context_data.get("pricing_model"),
        brand_positioning=context_data.get("brand_positioning"),
        brand_tone=context_data.get("brand_tone"),
        brand_maturity=context_data.get("brand_maturity"),
        tech_stack=context_data.get("tech_stack"),
        seo_structure=context_data.get("seo_structure"),
        detected_competitors=context_data.get("detected_competitors"),
        ideal_customer_profile=context_data.get("ideal_customer_profile"),
        keywords=context_data.get("keywords"),
        target_geography=context_data.get("target_geography"),
        traffic_range=context_data.get("traffic_range"),
        mau_bucket=context_data.get("mau_bucket"),
        revenue_stage=context_data.get("revenue_stage"),
        main_value_proposition=context_data.get("main_value_proposition"),
        team_size=context_data.get("team_size"),
        budget_constraints=context_data.get("budget_constraints"),
        time_constraints=context_data.get("time_constraints"),
        regulatory_constraints=context_data.get("regulatory_constraints"),
        enrichment_source=context_data.get("enrichment_source"),
        enrichment_date=context_data.get("enrichment_date"),
        north_star_goal=context_data.get("north_star_goal"),
        strategic_objectives=context_data.get("strategic_objectives"),
        benchmark_timestamps=context_data.get("benchmark_timestamps"),
    )


def context_model_to_dict(context: BusinessContext) -> dict[str, Any]:
    """Convert BusinessContext model to dict for database storage.

    Args:
        context: BusinessContext model instance

    Returns:
        Dict suitable for database storage
    """
    return {
        # Original fields
        "business_model": context.business_model,
        "target_market": context.target_market,
        "product_description": context.product_description,
        "revenue": context.revenue,
        "customers": context.customers,
        "growth_rate": context.growth_rate,
        "competitors": context.competitors,
        "website": context.website,
        # Extended fields (Tier 3)
        "company_name": context.company_name,
        "business_stage": context.business_stage.value if context.business_stage else None,
        "primary_objective": context.primary_objective.value if context.primary_objective else None,
        "industry": context.industry,
        "product_categories": context.product_categories,
        "pricing_model": context.pricing_model,
        "brand_positioning": context.brand_positioning,
        "brand_tone": context.brand_tone,
        "brand_maturity": context.brand_maturity,
        "tech_stack": context.tech_stack,
        "seo_structure": context.seo_structure,
        "detected_competitors": context.detected_competitors,
        "ideal_customer_profile": context.ideal_customer_profile,
        "keywords": context.keywords,
        "target_geography": context.target_geography,
        "traffic_range": context.traffic_range,
        "mau_bucket": context.mau_bucket,
        "revenue_stage": context.revenue_stage,
        "main_value_proposition": context.main_value_proposition,
        "team_size": context.team_size,
        "budget_constraints": context.budget_constraints,
        "time_constraints": context.time_constraints,
        "regulatory_constraints": context.regulatory_constraints,
        "enrichment_source": context.enrichment_source.value if context.enrichment_source else None,
        "enrichment_date": context.enrichment_date,
        "north_star_goal": context.north_star_goal,
        "strategic_objectives": context.strategic_objectives,
        "benchmark_timestamps": context.benchmark_timestamps,
    }


def enriched_data_to_dict(enriched: Any) -> dict[str, Any]:
    """Convert enrichment service result to dict.

    Args:
        enriched: EnrichedContext from EnrichmentService

    Returns:
        Dict suitable for merging with existing context
    """
    return {
        "company_name": enriched.company_name,
        "website": enriched.website,
        "industry": enriched.industry,
        "business_model": enriched.business_model,
        "pricing_model": enriched.pricing_model,
        "target_market": enriched.target_market,
        "product_description": enriched.product_description,
        "product_categories": enriched.product_categories,
        "main_value_proposition": enriched.main_value_proposition,
        "brand_positioning": enriched.brand_positioning,
        "brand_tone": enriched.brand_tone,
        "brand_maturity": enriched.brand_maturity,
        "tech_stack": enriched.tech_stack,
        "seo_structure": enriched.seo_structure,
        "keywords": enriched.keywords,
        "detected_competitors": enriched.detected_competitors,
        "ideal_customer_profile": enriched.ideal_customer_profile,
        "enrichment_source": enriched.enrichment_source,
        "enrichment_date": enriched.enrichment_date.isoformat()
        if enriched.enrichment_date
        else None,
    }


def enriched_to_context_model(enriched: Any) -> BusinessContext:
    """Convert enrichment service result to BusinessContext model.

    Args:
        enriched: EnrichedContext from EnrichmentService

    Returns:
        BusinessContext model instance
    """
    return BusinessContext(
        company_name=enriched.company_name,
        website=enriched.website,
        industry=enriched.industry,
        business_model=enriched.business_model,
        pricing_model=enriched.pricing_model,
        target_market=enriched.target_market,
        product_description=enriched.product_description,
        product_categories=enriched.product_categories,
        main_value_proposition=enriched.main_value_proposition,
        brand_positioning=enriched.brand_positioning,
        brand_tone=enriched.brand_tone,
        brand_maturity=enriched.brand_maturity,
        tech_stack=enriched.tech_stack,
        seo_structure=enriched.seo_structure,
        keywords=enriched.keywords,
        detected_competitors=enriched.detected_competitors,
        ideal_customer_profile=enriched.ideal_customer_profile,
        enrichment_source=EnrichmentSource(enriched.enrichment_source),
        enrichment_date=enriched.enrichment_date,
    )


def merge_context(
    existing: dict[str, Any],
    enriched: dict[str, Any],
    preserve_existing: bool = True,
) -> dict[str, Any]:
    """Merge enriched data with existing context.

    Args:
        existing: Existing context data
        enriched: New enriched data
        preserve_existing: If True, only update fields that are empty

    Returns:
        Merged context dict
    """
    merged = existing.copy()

    for key, value in enriched.items():
        if value is not None:
            if preserve_existing and existing.get(key):
                # Keep existing value
                continue
            merged[key] = value

    return merged


async def auto_save_competitors(
    user_id: str,
    competitors: list[DetectedCompetitor],
    source: str = "auto_detected",
) -> int:
    """Auto-save detected competitors to managed_competitors in user context.

    Respects tier limits and doesn't duplicate existing competitors (case-insensitive).

    Args:
        user_id: User ID
        competitors: List of detected competitors
        source: Source of competitors ("auto_detected" or "manual")

    Returns:
        Number of competitors added
    """
    from datetime import UTC, datetime

    from bo1.state.repositories import user_repository

    if not competitors:
        return 0

    try:
        # Get user tier and limits
        tier_limits = {
            "free": 3,
            "starter": 5,
            "pro": 8,
        }

        # Get user's tier
        tier = get_single_value(
            "SELECT subscription_tier FROM users WHERE id = %s",
            (user_id,),
            column="subscription_tier",
            default="free",
        )
        max_competitors = tier_limits.get(tier, 3)

        # Get current managed competitors
        context = user_repository.get_context(user_id) or {}
        managed = context.get("managed_competitors", [])
        if not isinstance(managed, list):
            managed = []

        # Build set of existing names (case-insensitive)
        existing_names = {c.get("name", "").lower().strip() for c in managed}
        current_count = len(managed)

        # Calculate how many we can add
        available_slots = max_competitors - current_count
        if available_slots <= 0:
            logger.info(f"User {user_id} at competitor limit ({current_count}/{max_competitors})")
            return 0

        # Add new competitors (up to available slots)
        added = 0
        now = datetime.now(UTC).isoformat()

        for comp in competitors:
            if added >= available_slots:
                break

            name_lower = comp.name.lower().strip()
            if name_lower in existing_names:
                continue

            # Add to managed competitors with source tracking
            managed.append(
                {
                    "name": comp.name.strip(),
                    "url": comp.url.strip() if comp.url else None,
                    "notes": comp.description.strip() if comp.description else None,
                    "added_at": now,
                    "source": source,
                }
            )
            existing_names.add(name_lower)
            added += 1

        # Save updated context
        if added > 0:
            context["managed_competitors"] = managed
            user_repository.save_context(user_id, context)
            logger.info(f"Auto-saved {added} competitors for user {user_id} (source={source})")

        return added

    except Exception as e:
        # Don't fail the main request if auto-save fails
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to auto-save competitors: {e}",
            user_id=user_id,
        )
        return 0


# =============================================================================
# Clarification Validation Helpers
# =============================================================================


def validate_clarification_entry(question: str, data: dict[str, Any]) -> ClarificationStorageEntry:
    """Validate a single clarification entry before storage.

    Converts legacy string format to dict format if needed.

    Args:
        question: The clarification question text (for error messages)
        data: Raw entry dict (or string for legacy format)

    Returns:
        Validated ClarificationStorageEntry

    Raises:
        ValidationError: If data doesn't match expected schema
    """
    # Handle legacy string format: convert to dict with answer field
    if isinstance(data, str):
        data = {"answer": data, "source": "migration"}

    # Validate using Pydantic model
    return ClarificationStorageEntry.model_validate(data)


def validate_clarifications_storage(raw: dict[str, Any]) -> ClarificationsStorage:
    """Validate the entire clarifications JSONB structure.

    Handles legacy string values by converting them to proper dict format.

    Args:
        raw: Raw clarifications dict from database

    Returns:
        Validated ClarificationsStorage model

    Raises:
        ValidationError: If any entry doesn't match schema
    """
    if not raw:
        return ClarificationsStorage.model_validate({})

    # Convert legacy string entries to dict format
    normalized: dict[str, dict[str, Any]] = {}
    for question, entry in raw.items():
        if isinstance(entry, str):
            normalized[question] = {"answer": entry, "source": "migration"}
        elif isinstance(entry, dict):
            normalized[question] = entry
        else:
            raise ValueError(
                f"Clarification '{question}': expected dict or str, got {type(entry).__name__}"
            )

    return ClarificationsStorage.model_validate(normalized)


def normalize_clarification_for_storage(entry: dict[str, Any]) -> dict[str, Any]:
    """Normalize and validate a clarification entry, returning serializable dict.

    Use this before saving to ensure the entry is valid and properly formatted.

    Args:
        entry: Raw entry dict to normalize

    Returns:
        Validated dict ready for JSON storage

    Raises:
        ValidationError: If entry is invalid
    """
    validated = ClarificationStorageEntry.model_validate(entry)
    return validated.model_dump(mode="json", exclude_none=True)


# =============================================================================
# Benchmark Timestamp Tracking
# =============================================================================

# Fields that are considered "benchmark metrics" for timestamp tracking
BENCHMARK_METRIC_FIELDS = frozenset(
    {
        "revenue",
        "customers",
        "growth_rate",
        "team_size",
        "mau_bucket",
        "revenue_stage",
        "traffic_range",
    }
)


def update_benchmark_timestamps(
    new_context: dict[str, Any],
    existing_context: dict[str, Any] | None,
) -> dict[str, str]:
    """Update timestamps for benchmark metrics that have changed.

    Only updates timestamp if:
    - The field is a benchmark metric (in BENCHMARK_METRIC_FIELDS)
    - The new value is non-empty
    - The value has actually changed from existing

    Args:
        new_context: New context data being saved
        existing_context: Existing context data from database (or None)

    Returns:
        Updated benchmark_timestamps dict with ISO format strings
    """
    from datetime import UTC, datetime

    # Get existing timestamps or start fresh
    if existing_context and existing_context.get("benchmark_timestamps"):
        timestamps = dict(existing_context["benchmark_timestamps"])
    else:
        timestamps = {}

    now = datetime.now(UTC).isoformat()

    for field in BENCHMARK_METRIC_FIELDS:
        new_value = new_context.get(field)
        old_value = existing_context.get(field) if existing_context else None

        # Only update timestamp if:
        # 1. New value exists and is non-empty
        # 2. Value is different from old value
        if new_value is not None and new_value != "":
            if old_value != new_value:
                timestamps[field] = now

    return timestamps


# Maximum historical entries per metric
MAX_BENCHMARK_HISTORY_ENTRIES = 6


def append_benchmark_history(
    new_context: dict[str, Any],
    existing_context: dict[str, Any] | None,
) -> dict[str, list[dict[str, Any]]]:
    """Append changed benchmark values to history, keeping max 6 per metric.

    Records historical values when benchmark metrics change, enabling
    trend visualization and monthly check-in tracking.

    Args:
        new_context: New context data being saved
        existing_context: Existing context data from database (or None)

    Returns:
        Updated benchmark_history dict: {metric_key: [{value, date}, ...]}
    """
    from datetime import UTC, datetime

    # Get existing history or start fresh
    if existing_context and existing_context.get("benchmark_history"):
        history = {k: list(v) for k, v in existing_context["benchmark_history"].items()}
    else:
        history = {}

    today = datetime.now(UTC).strftime("%Y-%m-%d")

    for field in BENCHMARK_METRIC_FIELDS:
        new_value = new_context.get(field)
        old_value = existing_context.get(field) if existing_context else None

        # Only record if value changed and is non-empty
        if new_value is not None and new_value != "" and old_value != new_value:
            if field not in history:
                history[field] = []

            # Don't duplicate if already recorded today
            if history[field] and history[field][0].get("date") == today:
                # Update today's entry instead
                history[field][0]["value"] = new_value
            else:
                # Prepend new entry
                history[field].insert(0, {"value": new_value, "date": today})

            # Trim to max entries
            history[field] = history[field][:MAX_BENCHMARK_HISTORY_ENTRIES]

    return history
