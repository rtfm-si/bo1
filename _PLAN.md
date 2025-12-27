# Plan: Commit Pending Changes + Verify Admin Endpoint Fixes

## Summary

- Commit all pending fair usage, SEO, and admin endpoint fixes to main
- Verify production deployment resolves `_TODO.md` issues (404s, 401s, 429s)
- No new code required—changes already implemented and tested

## Implementation Steps

1. **Review staged changes**
   - Fair usage: `backend/api/middleware/fair_usage.py`, `backend/services/fair_usage.py`, migration
   - SEO: Route ordering fix for `/assets` 404
   - Admin: Ratings/feedback 401 fix (require_admin_any)
   - Rate limits: Blog endpoints 429 fix

2. **Run full test suite**
   - `make test` or `pytest tests/`
   - Ensure all 51 fair usage + plan config tests pass
   - Verify no regressions in SEO/admin tests

3. **Commit with proper message**
   - Single atomic commit covering all pending changes
   - Message: "feat: fair usage caps + admin endpoint fixes"

4. **Deploy to production**
   - `ssh root@139.59.201.65`
   - Pull latest, run migrations, restart services

5. **Verify production fixes**
   - Test `/api/v1/seo/assets` returns 200 (not 404)
   - Test `/api/v1/admin/ratings/metrics` returns 200 (not 401)
   - Test `/api/admin/blog/posts` doesn't 429 cascade
   - Clear `_TODO.md` issues once verified

## Tests

- **Pre-commit:**
  - `pytest tests/services/test_fair_usage.py` (10 tests)
  - `pytest tests/billing/test_plan_config.py` (41 tests)
  - `make pre-commit` for lint/type checks

- **Post-deploy verification:**
  - Manual curl to production endpoints
  - Check Grafana for 4xx/5xx rate changes

## Dependencies & Risks

- **Dependencies:**
  - Migration `zm_add_fair_usage_tracking.py` must run on deploy

- **Risks:**
  - Low: All changes already tested locally
  - Low: Migration is additive (new columns/tables only)
