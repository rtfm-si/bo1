# Plan: [ADMIN][P3] User promotion management (add/remove/view)

## Summary

- Add admin endpoints to apply/remove promotions from user accounts
- Add endpoint to list users with active promotions
- Add UI controls on Admin > Users and Admin > Promotions pages

## Implementation Steps

1. **Add repository methods** (`bo1/state/repositories/promotion_repository.py`)
   - `remove_user_promotion(user_promotion_id, user_id)` - hard delete user_promotion row
   - `get_users_with_promotions()` - list users with active promos (join users/user_promotions/promotions)

2. **Add admin API endpoints** (`backend/api/admin/promotions.py`)
   - `POST /api/admin/promotions/apply` - apply promo code to user by user_id
   - `DELETE /api/admin/promotions/user/{user_promotion_id}` - remove promo from user
   - `GET /api/admin/promotions/users` - list users with promotions applied

3. **Add Pydantic models** (`backend/api/models.py`)
   - `ApplyPromoToUserRequest(user_id: str, code: str)`
   - `UserWithPromotionsResponse(user_id, email, promotions: list)`

4. **Update Admin > Users page** (`frontend/src/routes/(app)/admin/users/+page.svelte`)
   - Add "Apply Promo" button per user row (opens modal with code input)
   - Show active promo badges in user row (if any)

5. **Update Admin > Promotions page** (`frontend/src/routes/(app)/admin/promotions/+page.svelte`)
   - Add "Users" tab showing accounts with promotions
   - Add "Remove" button per user-promotion row

6. **Add frontend API functions** (`frontend/src/lib/api/admin.ts`)
   - `applyPromoToUser(userId, code)`
   - `removeUserPromotion(userPromotionId)`
   - `getUsersWithPromotions()`

## Tests

- Unit tests:
  - `tests/api/admin/test_promotion_user_management.py`: apply, remove, list endpoints
- Manual validation:
  - [ ] Apply promo to user from Admin > Users
  - [ ] Remove promo from user via Admin > Promotions
  - [ ] List users with promotions shows correct data

## Dependencies & Risks

- Dependencies: Existing promotion_repository, promotion_service
- Risks:
  - Removing promo mid-cycle may confuse users (acceptable for admin action)
  - Should not remove promo that's already been partially consumed (warn in UI)
