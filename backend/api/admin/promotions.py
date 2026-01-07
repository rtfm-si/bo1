"""Admin API endpoints for promotions management.

Provides:
- GET /api/admin/promotions - List all promotions with stats
- POST /api/admin/promotions - Create new promotion
- DELETE /api/admin/promotions/{id} - Deactivate promotion (soft delete)
- POST /api/admin/promotions/apply - Apply promo code to user
- DELETE /api/admin/promotions/user/{user_promotion_id} - Remove promo from user
- GET /api/admin/promotions/users - List users with active promotions
"""

from fastapi import APIRouter, Depends, Request

from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.models import (
    AddPromotionRequest,
    ApplyPromoToUserRequest,
    ErrorResponse,
    Promotion,
    UserPromotionBrief,
    UserWithPromotionsResponse,
)
from backend.api.utils.errors import handle_api_errors, http_error
from backend.services.promotion_service import PromoValidationError, validate_and_apply_code
from bo1.logging import ErrorCode
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
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("list promotions")
async def list_promotions(
    request: Request,
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
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("create promotion")
async def create_promotion(
    request: Request,
    body: AddPromotionRequest,
    _admin: str = Depends(require_admin_any),
) -> Promotion:
    """Create a new promotion."""
    # Check if code already exists
    existing = promotion_repository.get_promotion_by_code(body.code)
    if existing:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            f"Promotion code '{body.code}' already exists",
            status=400,
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
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("deactivate promotion")
async def deactivate_promotion(
    request: Request,
    promotion_id: str,
    _admin: str = Depends(require_admin_any),
) -> dict:
    """Deactivate a promotion (soft delete)."""
    # Verify exists
    promo = promotion_repository.get_promotion_by_id(promotion_id)
    if not promo:
        raise http_error(ErrorCode.API_NOT_FOUND, "Promotion not found", status=404)

    result = promotion_repository.deactivate_promotion(promotion_id)
    if not result:
        raise http_error(
            ErrorCode.API_NOT_FOUND, "Promotion not found or already deactivated", status=404
        )

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
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("restore promotion")
async def restore_promotion(
    request: Request,
    promotion_id: str,
    _admin: str = Depends(require_admin_any),
) -> dict:
    """Restore a soft-deleted promotion."""
    result = promotion_repository.restore_promotion(promotion_id)
    if not result:
        raise http_error(ErrorCode.API_NOT_FOUND, "Promotion not found or not deleted", status=404)

    logger.info(f"Admin: Restored promotion {promotion_id}")
    return {"status": "restored", "promotion_id": promotion_id}


@router.post(
    "/apply",
    summary="Apply promotion to user",
    description="Apply a promo code to a specific user account.",
    responses={
        200: {"description": "Promotion applied successfully"},
        400: {"description": "Invalid code or already applied", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("apply promotion to user")
async def apply_promotion_to_user(
    request: Request,
    body: ApplyPromoToUserRequest,
    _admin: str = Depends(require_admin_any),
) -> dict:
    """Apply a promo code to a user account."""
    try:
        user_promo = validate_and_apply_code(body.user_id, body.code)
        logger.info(f"Admin: Applied promo {body.code} to user {body.user_id}")
        return {
            "status": "applied",
            "user_id": body.user_id,
            "user_promotion_id": user_promo["id"],
            "promotion_code": body.code,
        }
    except PromoValidationError as e:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            e.message,
            status=400,
            promo_error_code=e.code,
        ) from None


@router.delete(
    "/user/{user_promotion_id}",
    summary="Remove promotion from user",
    description="Remove a promotion from a user account (hard delete).",
    responses={
        200: {"description": "Promotion removed successfully"},
        404: {"description": "User promotion not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("remove user promotion")
async def remove_user_promotion(
    request: Request,
    user_promotion_id: str,
    _admin: str = Depends(require_admin_any),
) -> dict:
    """Remove a promotion from a user account."""
    result = promotion_repository.remove_user_promotion(user_promotion_id)
    if not result:
        raise http_error(ErrorCode.API_NOT_FOUND, "User promotion not found", status=404)

    logger.info(f"Admin: Removed user promotion {user_promotion_id}")
    return {"status": "removed", "user_promotion_id": user_promotion_id}


@router.get(
    "/users",
    response_model=list[UserWithPromotionsResponse],
    summary="List users with promotions",
    description="List all users who have active promotions applied.",
    responses={
        200: {"description": "Users retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("list users with promotions")
async def list_users_with_promotions(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> list[UserWithPromotionsResponse]:
    """List all users with active promotions."""
    rows = promotion_repository.get_users_with_promotions()
    logger.info(f"Admin: Listed {len(rows)} users with promotions")

    result = []
    for row in rows:
        promos = row.get("promotions") or []
        result.append(
            UserWithPromotionsResponse(
                user_id=row["user_id"],
                email=row.get("email"),
                promotions=[
                    UserPromotionBrief(
                        id=p["id"],
                        promotion_id=p["promotion_id"],
                        promotion_code=p["promotion_code"],
                        promotion_type=p["promotion_type"],
                        promotion_value=float(p["promotion_value"]),
                        status=p["status"],
                        applied_at=p["applied_at"],
                        deliberations_remaining=p.get("deliberations_remaining"),
                        discount_applied=(
                            float(p["discount_applied"]) if p.get("discount_applied") else None
                        ),
                    )
                    for p in promos
                ],
            )
        )
    return result
