"""Admin API endpoints for promotions management.

Provides:
- GET /api/admin/promotions - List all promotions with stats
- POST /api/admin/promotions - Create new promotion
- DELETE /api/admin/promotions/{id} - Deactivate promotion (soft delete)
"""

from fastapi import APIRouter, Depends, HTTPException

from backend.api.middleware.admin import require_admin_any
from backend.api.models import AddPromotionRequest, ErrorResponse, Promotion
from backend.api.utils.errors import handle_api_errors
from bo1.state.repositories.promotion_repository import promotion_repository
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/promotions", tags=["Admin - Promotions"])


@router.get(
    "",
    response_model=list[Promotion],
    summary="List all promotions",
    description="List all promotions with usage statistics.",
    responses={
        200: {"description": "Promotions retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@handle_api_errors("list promotions")
async def list_promotions(
    _admin: str = Depends(require_admin_any),
) -> list[Promotion]:
    """List all promotions (admin view)."""
    promos = promotion_repository.get_all_promotions()
    logger.info(f"Admin: Listed {len(promos)} promotions")
    return [Promotion(**p) for p in promos]


@router.post(
    "",
    response_model=Promotion,
    summary="Create promotion",
    description="Create a new promotion code.",
    responses={
        200: {"description": "Promotion created successfully"},
        400: {"description": "Invalid request or code already exists", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@handle_api_errors("create promotion")
async def create_promotion(
    body: AddPromotionRequest,
    _admin: str = Depends(require_admin_any),
) -> Promotion:
    """Create a new promotion."""
    # Check if code already exists
    existing = promotion_repository.get_promotion_by_code(body.code)
    if existing:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Code already exists",
                "message": f"Promotion code '{body.code}' already exists",
            },
        )

    promo = promotion_repository.create_promotion(
        code=body.code,
        promo_type=body.type,
        value=body.value,
        max_uses=body.max_uses,
        expires_at=body.expires_at,
    )

    logger.info(f"Admin: Created promotion {body.code} type={body.type} value={body.value}")
    return Promotion(**promo)


@router.delete(
    "/{promotion_id}",
    summary="Deactivate promotion",
    description="Soft-delete a promotion by setting deleted_at timestamp.",
    responses={
        200: {"description": "Promotion deactivated successfully"},
        404: {"description": "Promotion not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@handle_api_errors("deactivate promotion")
async def deactivate_promotion(
    promotion_id: str,
    _admin: str = Depends(require_admin_any),
) -> dict:
    """Deactivate a promotion (soft delete)."""
    # Verify exists
    promo = promotion_repository.get_promotion_by_id(promotion_id)
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")

    result = promotion_repository.deactivate_promotion(promotion_id)
    if not result:
        raise HTTPException(status_code=404, detail="Promotion not found or already deactivated")

    logger.info(f"Admin: Deactivated promotion {promotion_id} ({promo['code']})")
    return {"status": "deactivated", "promotion_id": promotion_id}


@router.post(
    "/{promotion_id}/restore",
    summary="Restore promotion",
    description="Restore a soft-deleted promotion by clearing deleted_at.",
    responses={
        200: {"description": "Promotion restored successfully"},
        404: {"description": "Promotion not found or not deleted", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@handle_api_errors("restore promotion")
async def restore_promotion(
    promotion_id: str,
    _admin: str = Depends(require_admin_any),
) -> dict:
    """Restore a soft-deleted promotion."""
    result = promotion_repository.restore_promotion(promotion_id)
    if not result:
        raise HTTPException(status_code=404, detail="Promotion not found or not deleted")

    logger.info(f"Admin: Restored promotion {promotion_id}")
    return {"status": "restored", "promotion_id": promotion_id}
