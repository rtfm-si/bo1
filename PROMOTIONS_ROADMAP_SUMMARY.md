# Promotions System - Roadmap Integration Summary

**Date**: 2025-01-18
**Added To**: Week 8-9 (Days 55-58)
**Timeline**: 4 days
**Tasks Added**: 28

---

## Schedule

### **Day 55**: Database + Models (1 day)
- Migration: `promotions` + `user_promotions` tables
- Pydantic models
- Seed common promotion templates

### **Day 56**: Backend Logic + API (1 day)
- Core logic: Deliberation allowance, discount application
- Admin API endpoints (add/remove promos)
- Integration with deliberation flow
- Integration with Stripe billing

### **Day 57**: Admin UI (1 day)
- User lookup page
- Add/remove promotion modals
- Promotion cards (active + history)

### **Day 58**: Integration Testing (1 day)
- E2E tests
- Manual testing scenarios
- Performance testing
- Documentation

---

## Key Features

### **Promo Types**:
1. `deliberations_bonus` - Extra deliberations
2. `percent_discount` - % off subscription
3. `amount_discount` - £ off subscription

### **Application Types**:
1. `one_time` - This billing period only
2. `recurring_periods` - Next N periods
3. `recurring_forever` - Until manually removed
4. `total_additional` - Bank of credits (draw down)

### **Discount Application Order**:
```python
# 1. £ off first (fixed amount)
final = base - amount_off
final = max(final, 0)

# 2. % off second (on remaining)
percent = min(total_percent, 100)
final = final - (final * percent / 100)

# Guardrails: Never negative, % capped at 100%
```

---

## Use Cases Covered

✅ **Goodwill gestures** (+5 deliberations)
✅ **Beta discounts** (50% off for 6 months)
✅ **Referral bonuses** (£50 credit)
✅ **Enterprise trials** (100% off first month)
✅ **Deliberation banks** (50 deliberations to draw down)

---

## Admin Workflow

**Example**: Give user +5 free deliberations

1. Visit `/admin/users/{email}/promotions`
2. Click "Add Promotion"
3. Select: "Goodwill +5 deliberations"
4. Reason: "Apology for outage"
5. Apply ✅

**Result**: User sees +5 to limit immediately

---

## Roadmap Impact

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Week 8-9 Tasks | 98 | 126 | +28 |
| Total Tasks | 1,671 | 1,699 | +28 |
| Timeline | No change | No change | 0 days |

**No timeline delay** - fits within existing Week 8-9 (9 days available)

---

## Files Created

### Design Docs:
- ✅ `zzz_project/detail/PROMOTIONS_SYSTEM_DESIGN.md` (893 lines)

### To Be Created (Days 55-58):
- `migrations/versions/XXX_add_promotions.py`
- `bo1/models/promotions.py`
- `backend/services/promotions.py`
- `backend/api/admin/promotions.py`
- `frontend/src/routes/(admin)/admin/users/[email]/promotions/+page.svelte`
- `frontend/src/lib/components/admin/AddPromotionModal.svelte`
- `tests/test_promotions.py`
- `tests/e2e/test_promotions_flow.py`
- `docs/ADMIN_GUIDE.md` (updated)
- `docs/PROMOTIONS_EXAMPLES.md`

---

## Cost

**Development**: 4 days
**Infrastructure**: $0 (uses existing DB)
**Ongoing**: $0 (no external services)

---

## Next Steps

1. Continue with Week 7 (OAuth + Actions)
2. Start Day 55 (Promotions backend)
3. Reference: `zzz_project/detail/PROMOTIONS_SYSTEM_DESIGN.md`
