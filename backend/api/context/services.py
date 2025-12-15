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
from backend.api.utils.db_helpers import execute_query, get_single_value
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


async def auto_save_competitors(user_id: str, competitors: list[DetectedCompetitor]) -> None:
    """Auto-save detected competitors to competitor_profiles table.

    Respects tier limits and doesn't duplicate existing competitors.

    Args:
        user_id: User ID
        competitors: List of detected competitors
    """
    if not competitors:
        return

    try:
        # Get user tier and limits
        tier_limits = {
            "free": {"max_competitors": 3, "data_depth": "basic"},
            "starter": {"max_competitors": 5, "data_depth": "standard"},
            "pro": {"max_competitors": 8, "data_depth": "deep"},
        }

        # Get user's tier
        tier = get_single_value(
            "SELECT subscription_tier FROM users WHERE id = %s",
            (user_id,),
            column="subscription_tier",
            default="free",
        )
        tier_config = tier_limits.get(tier, tier_limits["free"])

        # Get current competitor count and names
        existing_rows = execute_query(
            "SELECT name FROM competitor_profiles WHERE user_id = %s",
            (user_id,),
            fetch="all",
        )
        existing = {row["name"].lower() for row in existing_rows}
        current_count = len(existing)

        # Calculate how many we can add
        available_slots = tier_config["max_competitors"] - current_count
        if available_slots <= 0:
            logger.info(
                f"User {user_id} at competitor limit ({current_count}/{tier_config['max_competitors']})"
            )
            return

        # Add new competitors (up to available slots)
        added = 0
        for comp in competitors:
            if added >= available_slots:
                break
            if comp.name.lower() in existing:
                continue

            # Use INSERT ... ON CONFLICT - check if inserted via RETURNING
            result = execute_query(
                """
                INSERT INTO competitor_profiles (user_id, name, website, tagline, data_depth)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id
                """,
                (
                    user_id,
                    comp.name,
                    comp.url,
                    comp.description,
                    tier_config["data_depth"],
                ),
                fetch="one",
            )
            if result:
                added += 1
                existing.add(comp.name.lower())

        logger.info(f"Auto-saved {added} competitors for user {user_id}")

    except Exception as e:
        # Don't fail the main request if auto-save fails
        logger.error(f"Failed to auto-save competitors: {e}")


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
