"""Context management API endpoints.

Provides:
- GET /api/v1/context - Get user's saved business context
- PUT /api/v1/context - Update user's business context
- DELETE /api/v1/context - Delete user's saved context
- POST /api/v1/sessions/{session_id}/clarify - Submit clarification answer
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from bo1.state.postgres_manager import (
    delete_user_context,
    load_user_context,
    save_user_context,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["context"])


class BusinessContext(BaseModel):
    """Business context data model.

    Attributes:
        business_model: Business model description
        target_market: Target market description
        product_description: Product/service description
        revenue: Monthly/annual revenue (optional)
        customers: Number of customers (optional)
        growth_rate: Growth rate percentage (optional)
        competitors: List of competitors (optional)
        website: Website URL (optional)
    """

    business_model: str | None = Field(
        None,
        description="Business model (e.g., B2B SaaS, marketplace)",
        examples=["B2B SaaS"],
    )
    target_market: str | None = Field(
        None,
        description="Target market description",
        examples=["Small businesses in North America"],
    )
    product_description: str | None = Field(
        None,
        description="Product/service description",
        examples=["AI-powered project management tool"],
    )
    revenue: float | None = Field(
        None,
        description="Monthly/annual revenue in USD",
        examples=[50000.0],
    )
    customers: int | None = Field(
        None,
        description="Number of active customers",
        examples=[150],
    )
    growth_rate: float | None = Field(
        None,
        description="Growth rate percentage",
        examples=[15.5],
    )
    competitors: list[str] | None = Field(
        None,
        description="List of competitors",
        examples=[["Asana", "Monday.com", "Jira"]],
    )
    website: str | None = Field(
        None,
        description="Website URL",
        examples=["https://example.com"],
    )


class ContextResponse(BaseModel):
    """Response model for context retrieval.

    Attributes:
        exists: Whether user has saved context
        context: Business context data (if exists)
        updated_at: Last update timestamp (if exists)
    """

    exists: bool = Field(..., description="Whether user has saved context")
    context: BusinessContext | None = Field(None, description="Business context data")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "exists": True,
                    "context": {
                        "business_model": "B2B SaaS",
                        "target_market": "Small businesses in North America",
                        "product_description": "AI-powered project management tool",
                        "revenue": 50000.0,
                        "customers": 150,
                        "growth_rate": 15.5,
                        "competitors": ["Asana", "Monday.com", "Jira"],
                        "website": "https://example.com",
                    },
                    "updated_at": "2025-01-15T12:00:00",
                },
                {
                    "exists": False,
                    "context": None,
                    "updated_at": None,
                },
            ]
        }
    }


class ClarificationRequest(BaseModel):
    """Request model for clarification answer.

    Attributes:
        answer: User's answer to the clarification question
    """

    answer: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Answer to clarification question",
    )


def _get_user_id_from_header() -> str:
    """Get user ID from request header.

    For MVP, we'll use a hardcoded user ID. In production (Week 7+),
    this will extract user ID from JWT token.

    Returns:
        User ID string
    """
    # TODO(Week 7): Extract from JWT token
    # For now, use a test user ID
    return "test_user_1"


@router.get(
    "/v1/context",
    response_model=ContextResponse,
    summary="Get user's saved business context",
    description="""
    Retrieve the authenticated user's saved business context.

    Business context is persistent across sessions and helps the AI personas
    provide more relevant recommendations. Context includes:
    - Business model and target market
    - Product/service description
    - Revenue and growth metrics
    - Competitor information

    **Use Cases:**
    - Check if user has saved context before starting deliberation
    - Display saved context in user profile
    - Pre-fill forms with existing context
    """,
    responses={
        200: {
            "description": "Context retrieved successfully (exists=true if saved, false if not)",
            "content": {
                "application/json": {
                    "examples": {
                        "with_context": {
                            "summary": "User has saved context",
                            "value": {
                                "exists": True,
                                "context": {
                                    "business_model": "B2B SaaS",
                                    "target_market": "Small businesses in North America",
                                    "product_description": "AI-powered project management tool",
                                    "revenue": 50000.0,
                                    "customers": 150,
                                    "growth_rate": 15.5,
                                    "competitors": ["Asana", "Monday.com", "Jira"],
                                    "website": "https://example.com",
                                },
                                "updated_at": "2025-01-15T12:00:00",
                            },
                        },
                        "no_context": {
                            "summary": "User has no saved context",
                            "value": {
                                "exists": False,
                                "context": None,
                                "updated_at": None,
                            },
                        },
                    }
                }
            },
        },
        500: {"description": "Database error"},
    },
)
async def get_context() -> ContextResponse:
    """Get user's saved business context.

    Returns:
        ContextResponse with context data if exists

    Raises:
        HTTPException: If database error occurs
    """
    try:
        user_id = _get_user_id_from_header()

        # Load context from database
        context_data = load_user_context(user_id)

        if not context_data:
            return ContextResponse(exists=False, context=None, updated_at=None)

        # Parse into BusinessContext
        context = BusinessContext(
            business_model=context_data.get("business_model"),
            target_market=context_data.get("target_market"),
            product_description=context_data.get("product_description"),
            revenue=context_data.get("revenue"),
            customers=context_data.get("customers"),
            growth_rate=context_data.get("growth_rate"),
            competitors=context_data.get("competitors"),
            website=context_data.get("website"),
        )

        return ContextResponse(
            exists=True,
            context=context,
            updated_at=context_data.get("updated_at"),
        )

    except Exception as e:
        logger.error(f"Failed to get context: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get context: {str(e)}",
        ) from e


@router.put(
    "/v1/context",
    response_model=dict[str, str],
    summary="Update user's business context",
    description="""
    Create or update the authenticated user's business context.

    Business context is saved to PostgreSQL and persists across sessions.
    This context is used during deliberations to provide more relevant
    recommendations from AI personas.

    **Use Cases:**
    - Save business context during onboarding
    - Update context when business metrics change
    - Pre-populate context for faster deliberation setup

    **Note:** All fields are optional. Only provided fields will be saved.
    """,
    responses={
        200: {
            "description": "Context updated successfully",
            "content": {"application/json": {"example": {"status": "updated"}}},
        },
        500: {"description": "Database error"},
    },
)
async def update_context(context: BusinessContext) -> dict[str, str]:
    """Update user's business context.

    Args:
        context: Business context to save

    Returns:
        Status message

    Raises:
        HTTPException: If database error occurs
    """
    try:
        user_id = _get_user_id_from_header()

        # Convert to dict for save function
        context_dict = {
            "business_model": context.business_model,
            "target_market": context.target_market,
            "product_description": context.product_description,
            "revenue": context.revenue,
            "customers": context.customers,
            "growth_rate": context.growth_rate,
            "competitors": context.competitors,
            "website": context.website,
        }

        # Save to database
        save_user_context(user_id, context_dict)

        logger.info(f"Updated context for user {user_id}")

        return {"status": "updated"}

    except Exception as e:
        logger.error(f"Failed to update context: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update context: {str(e)}",
        ) from e


@router.delete(
    "/v1/context",
    response_model=dict[str, str],
    status_code=200,
    summary="Delete user's saved context",
    description="""
    Delete the authenticated user's saved business context.

    This permanently removes all saved business context from the database.
    Future deliberations will not have access to this context unless
    it is re-entered.

    **Use Cases:**
    - User wants to start fresh
    - User wants to remove outdated business information
    - Privacy: Remove all stored business data

    **Warning:** This action cannot be undone.
    """,
    responses={
        200: {
            "description": "Context deleted successfully",
            "content": {"application/json": {"example": {"status": "deleted"}}},
        },
        404: {"description": "No context found to delete"},
        500: {"description": "Database error"},
    },
)
async def delete_context() -> dict[str, str]:
    """Delete user's saved business context.

    Returns:
        Status message

    Raises:
        HTTPException: If database error occurs
    """
    try:
        user_id = _get_user_id_from_header()

        # Delete from database
        deleted = delete_user_context(user_id)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="No context found to delete",
            )

        logger.info(f"Deleted context for user {user_id}")

        return {"status": "deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete context: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete context: {str(e)}",
        ) from e


# Clarify endpoint moved to control.py (Day 39)
