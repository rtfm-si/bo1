"""Competitor Watch API endpoints.

Provides:
- GET /api/v1/competitors - Get user's tracked competitors
- POST /api/v1/competitors - Add a competitor to watch
- PUT /api/v1/competitors/{id} - Update a competitor
- DELETE /api/v1/competitors/{id} - Remove a competitor
- POST /api/v1/competitors/{id}/enrich - Enrich competitor with Tavily
- POST /api/v1/competitors/enrich-all - Enrich all competitors (monthly refresh)
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from psycopg2 import DatabaseError, OperationalError
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.db_helpers import (
    count_rows,
    execute_query,
    exists,
    get_user_tier,
)
from backend.api.utils.errors import handle_api_errors
from bo1.config import get_settings
from bo1.logging.errors import ErrorCode, log_error

logger = logging.getLogger(__name__)

router = APIRouter(tags=["competitors"])

# Tier limits
TIER_LIMITS = {
    "free": {"max_competitors": 3, "data_depth": "basic"},
    "starter": {"max_competitors": 5, "data_depth": "standard"},
    "pro": {"max_competitors": 8, "data_depth": "deep"},
}


# =============================================================================
# Models
# =============================================================================


class CompetitorProfile(BaseModel):
    """A tracked competitor profile."""

    id: UUID | None = None
    name: str = Field(..., min_length=1, max_length=200)
    website: str | None = None
    tagline: str | None = None
    industry: str | None = None
    # Standard tier
    product_description: str | None = None
    pricing_model: str | None = None
    target_market: str | None = None
    business_model: str | None = None
    # Deep tier
    value_proposition: str | None = None
    tech_stack: list[str] | None = None
    recent_news: list[dict[str, str]] | None = None
    funding_info: str | None = None
    employee_count: str | None = None
    # Metadata
    display_order: int = 0
    is_primary: bool = False
    data_depth: str = "basic"
    last_enriched_at: datetime | None = None
    changes_detected: list[str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CompetitorListResponse(BaseModel):
    """Response for competitor list."""

    competitors: list[CompetitorProfile]
    tier: str
    max_allowed: int
    data_depth: str


class CompetitorCreateRequest(BaseModel):
    """Request to create a competitor."""

    name: str = Field(..., min_length=1, max_length=200)
    website: str | None = None
    is_primary: bool = False


class EnrichResponse(BaseModel):
    """Response from enrichment."""

    success: bool
    competitor: CompetitorProfile | None = None
    changes: list[str] | None = None
    error: str | None = None


class BulkEnrichResponse(BaseModel):
    """Response from bulk enrichment."""

    success: bool
    enriched_count: int
    competitors: list[CompetitorProfile]
    errors: list[str] | None = None


# =============================================================================
# Helper Functions
# =============================================================================


def get_competitor_count(user_id: str) -> int:
    """Get count of user's tracked competitors."""
    return count_rows("competitor_profiles", where="user_id = %s", params=(user_id,))


def row_to_profile(row: dict[str, Any]) -> CompetitorProfile:
    """Convert database row to CompetitorProfile."""
    return CompetitorProfile(
        id=row["id"],
        name=row["name"],
        website=row.get("website"),
        tagline=row.get("tagline"),
        industry=row.get("industry"),
        product_description=row.get("product_description"),
        pricing_model=row.get("pricing_model"),
        target_market=row.get("target_market"),
        business_model=row.get("business_model"),
        value_proposition=row.get("value_proposition"),
        tech_stack=row.get("tech_stack"),
        recent_news=row.get("recent_news"),
        funding_info=row.get("funding_info"),
        employee_count=row.get("employee_count"),
        display_order=row.get("display_order", 0),
        is_primary=row.get("is_primary", False),
        data_depth=row.get("data_depth", "basic"),
        last_enriched_at=row.get("last_enriched_at"),
        changes_detected=row.get("changes_detected"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


async def enrich_competitor_with_tavily(
    name: str, website: str | None, data_depth: str
) -> dict[str, Any]:
    """Enrich competitor data using Tavily Search API."""
    settings = get_settings()
    if not settings.tavily_api_key:
        raise ValueError("Tavily API not configured")

    # Build search query
    search_query = f'"{name}" company'
    if website:
        search_query += (
            f" site:{website.replace('https://', '').replace('http://', '').split('/')[0]}"
        )

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.tavily_api_key,
                "query": search_query,
                "search_depth": "advanced" if data_depth in ("standard", "deep") else "basic",
                "include_domains": [
                    "g2.com",
                    "capterra.com",
                    "crunchbase.com",
                    "linkedin.com",
                    "techcrunch.com",
                ]
                if data_depth == "deep"
                else ["g2.com", "capterra.com"],
                "max_results": 5 if data_depth == "deep" else 3,
            },
        )
        response.raise_for_status()
        data = response.json()

    # Extract data from results
    results = data.get("results", [])
    enriched: dict[str, Any] = {}

    for result in results:
        content = result.get("content", "")
        title = result.get("title", "")
        url = result.get("url", "")

        # Extract tagline from G2/Capterra
        if "g2.com" in url or "capterra.com" in url:
            if not enriched.get("tagline") and len(content) < 200:
                enriched["tagline"] = content[:200]
            if not enriched.get("product_description") and len(content) > 50:
                enriched["product_description"] = content[:500]

        # Extract funding/employee info from Crunchbase
        if "crunchbase.com" in url and data_depth == "deep":
            if "funding" in content.lower() or "raised" in content.lower():
                enriched["funding_info"] = content[:300]
            if "employees" in content.lower():
                # Try to extract employee count
                import re

                match = re.search(r"(\d+[\-\+]?\d*)\s*employees", content, re.IGNORECASE)
                if match:
                    enriched["employee_count"] = match.group(1)

        # Extract news from TechCrunch
        if "techcrunch.com" in url and data_depth == "deep":
            if not enriched.get("recent_news"):
                enriched["recent_news"] = []
            enriched["recent_news"].append(
                {
                    "title": title,
                    "url": url,
                    "date": datetime.now(UTC).isoformat(),
                }
            )

    return enriched


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/v1/competitors",
    response_model=CompetitorListResponse,
    summary="Get tracked competitors",
)
@handle_api_errors("get competitors")
async def get_competitors(
    user: dict[str, Any] = Depends(get_current_user),
) -> CompetitorListResponse:
    """Get user's tracked competitors."""
    user_id = extract_user_id(user)
    tier = get_user_tier(user_id)
    tier_config = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    rows = execute_query(
        """
        SELECT * FROM competitor_profiles
        WHERE user_id = %s
        ORDER BY is_primary DESC, display_order, created_at
        """,
        (user_id,),
        fetch="all",
    )

    competitors = [row_to_profile(row) for row in rows]

    return CompetitorListResponse(
        competitors=competitors,
        tier=tier,
        max_allowed=tier_config["max_competitors"],
        data_depth=tier_config["data_depth"],
    )


@router.post(
    "/v1/competitors",
    response_model=CompetitorProfile,
    summary="Add a competitor to watch",
)
@handle_api_errors("create competitor")
async def create_competitor(
    request: CompetitorCreateRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> CompetitorProfile:
    """Add a new competitor to track."""
    user_id = extract_user_id(user)
    tier = get_user_tier(user_id)
    tier_config = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    # Check limit
    current_count = get_competitor_count(user_id)
    if current_count >= tier_config["max_competitors"]:
        raise HTTPException(
            status_code=403,
            detail=f"Competitor limit reached ({tier_config['max_competitors']}). Upgrade your plan to track more.",
        )

    row = execute_query(
        """
        INSERT INTO competitor_profiles (user_id, name, website, is_primary, data_depth)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            user_id,
            request.name,
            request.website,
            request.is_primary,
            tier_config["data_depth"],
        ),
        fetch="one",
    )

    return row_to_profile(row)


@router.put(
    "/v1/competitors/{competitor_id}",
    response_model=CompetitorProfile,
    summary="Update a competitor",
)
@handle_api_errors("update competitor")
async def update_competitor(
    competitor_id: UUID,
    request: CompetitorProfile,
    user: dict[str, Any] = Depends(get_current_user),
) -> CompetitorProfile:
    """Update a tracked competitor."""
    user_id = extract_user_id(user)

    # Verify ownership
    if not exists(
        "competitor_profiles",
        where="id = %s AND user_id = %s",
        params=(str(competitor_id), user_id),
    ):
        raise HTTPException(status_code=404, detail="Competitor not found")

    row = execute_query(
        """
        UPDATE competitor_profiles SET
            name = %s,
            website = %s,
            is_primary = %s,
            display_order = %s,
            updated_at = NOW()
        WHERE id = %s AND user_id = %s
        RETURNING *
        """,
        (
            request.name,
            request.website,
            request.is_primary,
            request.display_order,
            str(competitor_id),
            user_id,
        ),
        fetch="one",
    )

    return row_to_profile(row)


@router.delete(
    "/v1/competitors/{competitor_id}",
    response_model=dict[str, str],
    summary="Remove a competitor",
)
@handle_api_errors("delete competitor")
async def delete_competitor(
    competitor_id: UUID,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Remove a competitor from tracking."""
    user_id = extract_user_id(user)

    # Verify ownership before delete
    if not exists(
        "competitor_profiles",
        where="id = %s AND user_id = %s",
        params=(str(competitor_id), user_id),
    ):
        raise HTTPException(status_code=404, detail="Competitor not found")

    execute_query(
        "DELETE FROM competitor_profiles WHERE id = %s AND user_id = %s",
        (str(competitor_id), user_id),
        fetch="none",
    )

    return {"status": "deleted"}


@router.post(
    "/v1/competitors/{competitor_id}/enrich",
    response_model=EnrichResponse,
    summary="Enrich a competitor with latest data",
)
@handle_api_errors("enrich competitor")
async def enrich_competitor(
    competitor_id: UUID,
    user: dict[str, Any] = Depends(get_current_user),
) -> EnrichResponse:
    """Enrich a single competitor with Tavily data."""
    user_id = extract_user_id(user)
    tier = get_user_tier(user_id)
    tier_config = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    # Get competitor
    row = execute_query(
        "SELECT * FROM competitor_profiles WHERE id = %s AND user_id = %s",
        (str(competitor_id), user_id),
        fetch="one",
    )
    if not row:
        raise HTTPException(status_code=404, detail="Competitor not found")

    try:
        # Enrich with Tavily
        enriched = await enrich_competitor_with_tavily(
            row["name"],
            row["website"],
            tier_config["data_depth"],
        )

        # Detect changes
        changes = []
        for key, value in enriched.items():
            if value and row.get(key) != value:
                changes.append(key)

        # Store previous snapshot for change detection
        previous_snapshot = {
            "tagline": row.get("tagline"),
            "product_description": row.get("product_description"),
            "pricing_model": row.get("pricing_model"),
        }

        # Update record
        updated_row = execute_query(
            """
            UPDATE competitor_profiles SET
                tagline = COALESCE(%s, tagline),
                product_description = COALESCE(%s, product_description),
                pricing_model = COALESCE(%s, pricing_model),
                target_market = COALESCE(%s, target_market),
                value_proposition = COALESCE(%s, value_proposition),
                funding_info = COALESCE(%s, funding_info),
                employee_count = COALESCE(%s, employee_count),
                recent_news = COALESCE(%s, recent_news),
                last_enriched_at = NOW(),
                previous_snapshot = %s,
                changes_detected = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING *
            """,
            (
                enriched.get("tagline"),
                enriched.get("product_description"),
                enriched.get("pricing_model"),
                enriched.get("target_market"),
                enriched.get("value_proposition"),
                enriched.get("funding_info"),
                enriched.get("employee_count"),
                enriched.get("recent_news"),
                json.dumps(previous_snapshot),
                json.dumps(changes) if changes else None,
                str(competitor_id),
            ),
            fetch="one",
        )

        return EnrichResponse(
            success=True,
            competitor=row_to_profile(updated_row),
            changes=changes if changes else None,
        )

    except httpx.HTTPError as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"HTTP error during enrichment: {e}",
            competitor_id=str(competitor_id),
            competitor_name=row["name"],
        )
        return EnrichResponse(
            success=False,
            error=f"Failed to connect to enrichment service: {e}",
        )
    except (DatabaseError, OperationalError) as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Database error during enrichment: {e}",
            competitor_id=str(competitor_id),
            competitor_name=row["name"],
        )
        return EnrichResponse(
            success=False,
            error="Database error during enrichment",
        )
    except asyncio.CancelledError:
        # Always re-raise CancelledError
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Unexpected error during enrichment: {e}",
            exc_info=True,
            competitor_id=str(competitor_id),
            competitor_name=row["name"],
        )
        return EnrichResponse(
            success=False,
            error=str(e),
        )


@router.post(
    "/v1/competitors/enrich-all",
    response_model=BulkEnrichResponse,
    summary="Refresh all competitors (monthly)",
)
@handle_api_errors("enrich all competitors")
async def enrich_all_competitors(
    user: dict[str, Any] = Depends(get_current_user),
) -> BulkEnrichResponse:
    """Enrich all tracked competitors. Use sparingly (monthly refresh)."""
    user_id = extract_user_id(user)
    tier = get_user_tier(user_id)
    tier_config = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    rows = execute_query(
        "SELECT * FROM competitor_profiles WHERE user_id = %s",
        (user_id,),
        fetch="all",
    )

    if not rows:
        return BulkEnrichResponse(
            success=True,
            enriched_count=0,
            competitors=[],
        )

    enriched_competitors = []
    errors = []

    for row in rows:
        try:
            enriched = await enrich_competitor_with_tavily(
                row["name"],
                row["website"],
                tier_config["data_depth"],
            )

            updated_row = execute_query(
                """
                UPDATE competitor_profiles SET
                    tagline = COALESCE(%s, tagline),
                    product_description = COALESCE(%s, product_description),
                    last_enriched_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                RETURNING *
                """,
                (
                    enriched.get("tagline"),
                    enriched.get("product_description"),
                    str(row["id"]),
                ),
                fetch="one",
            )
            enriched_competitors.append(row_to_profile(updated_row))

        except httpx.HTTPError as e:
            errors.append(f"{row['name']}: HTTP error - {e}")
            enriched_competitors.append(row_to_profile(row))
        except (DatabaseError, OperationalError):
            errors.append(f"{row['name']}: Database error")
            enriched_competitors.append(row_to_profile(row))
        except asyncio.CancelledError:
            # Always re-raise CancelledError
            raise
        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"Unexpected error enriching {row['name']}: {e}",
                exc_info=True,
                competitor_id=str(row["id"]),
                competitor_name=row["name"],
            )
            errors.append(f"{row['name']}: {str(e)}")
            enriched_competitors.append(row_to_profile(row))

    return BulkEnrichResponse(
        success=len(errors) == 0,
        enriched_count=len(rows) - len(errors),
        competitors=enriched_competitors,
        errors=errors if errors else None,
    )
