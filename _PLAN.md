# Plan: Centralize Plan Configuration

## Summary

- Create single `TierConfig` class in `bo1/constants.py` as source of truth for all tier limits
- Consolidate scattered tier definitions: competitors, insights, benchmarks, trends, features
- Update all call sites to use centralized config
- Add validation to ensure consistency across features

## Implementation Steps

1. **Create centralized TierConfig class in `bo1/constants.py`**
   - Define `TierConfig` dataclass with all limits per tier
   - Include: `max_competitors`, `competitor_data_depth`, `max_insights`, `benchmark_limit`, `trend_timeframes`, `feature_flags`
   - Create `TIER_CONFIGS: dict[str, TierConfig]` mapping tier name to config
   - Add `get_tier_config(tier: str) -> TierConfig` helper

2. **Migrate competitor limits from `backend/api/competitors.py`**
   - Remove local `TIER_LIMITS` dict (lines 41-45)
   - Import from `bo1.constants.TierConfig`
   - Update `get_competitors`, `create_competitor`, `enrich_competitor` to use centralized config

3. **Migrate competitor limits from `backend/api/constants.py`**
   - Remove duplicate `TIER_LIMITS` (lines 71-75)
   - This is a duplicate of competitors.py - consolidate

4. **Migrate insight limits from `backend/api/context/routes.py`**
   - Remove `COMPETITOR_INSIGHT_TIER_LIMITS` (lines 1369-1374)
   - Remove `_get_insight_limit_for_tier()` helper
   - Update `generate_competitor_insight` to use centralized config

5. **Migrate trend timeframes from `backend/services/trend_summary_generator.py`**
   - Remove `TREND_FORECAST_TIER_LIMITS` (lines 37-42)
   - Update `get_available_timeframes()` to use centralized config

6. **Migrate benchmark limits from `bo1/constants.py`**
   - Merge `IndustryBenchmarkLimits.TIER_LIMITS` into new `TierConfig`
   - Update `get_limit_for_tier()` to delegate to centralized config

7. **Merge TierFeatureFlags into TierConfig**
   - Combine `TierFeatureFlags.FEATURES` with new `TierConfig`
   - Update `is_feature_enabled()` and `get_features()` to use centralized config
   - Maintain backward compatibility with existing API

8. **Update tests**
   - `tests/api/context/test_competitor_insights.py` - update imports
   - `tests/services/test_trend_summary_generator.py` - update imports
   - `tests/api/test_industry_benchmarks.py` - update imports
   - Add new test file `tests/test_tier_config.py` for centralized config

## Tests

- Unit tests:
  - `tests/test_tier_config.py`: Test TierConfig class, all tier values, helper functions
  - Verify each tier (free/starter/pro/enterprise) has expected limits
- Integration tests:
  - Existing tests in `tests/api/context/`, `tests/services/` should pass with updated imports
- Manual validation:
  - `make test` - all existing tests pass
  - Grep for `TIER_LIMITS` - should only exist in `bo1/constants.py`

## Dependencies & Risks

- Dependencies:
  - None (refactor only, no new features)
- Risks/edge cases:
  - Import cycles if TierConfig references other modules
  - Must maintain backward compatibility for existing `TierFeatureFlags` API
  - May need to update OpenAPI spec if response models change

---

_Generated: 2025-12-26_
