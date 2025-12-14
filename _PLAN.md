# Plan: [UX][P2] Add projected meeting cost calculator

## Summary

- Add meeting cost calculator widget to dashboard
- Estimate traditional meeting cost based on: participant count × salary × duration + research time
- Compare against Bo1 meeting cost (from tier/usage)
- Show potential savings to reinforce value proposition

## Implementation Steps

1. **Create cost calculator component**
   - File: `frontend/src/lib/components/dashboard/MeetingCostCalculator.svelte`
   - Inputs: participants (1-20), avg hourly rate ($), meeting duration (mins), prep time (mins)
   - Calculate traditional cost: `(participants × hourly_rate × (duration + prep_time) / 60)`
   - Show Bo1 cost comparison (from tier data or fixed estimates)

2. **Add user defaults storage**
   - Migration: `migrations/versions/ax1_add_cost_calculator_defaults.py`
   - Add `cost_calculator_defaults JSONB` column to users table
   - Store: `avg_hourly_rate`, `typical_participants`, `typical_duration_mins`, `typical_prep_mins`

3. **Create API endpoint for defaults**
   - File: `backend/api/user.py`
   - `GET /api/v1/user/cost-calculator-defaults` - retrieve saved defaults
   - `PATCH /api/v1/user/cost-calculator-defaults` - save defaults

4. **Add repository methods**
   - File: `bo1/state/repositories/user_repository.py`
   - `get_cost_calculator_defaults(user_id)` - return JSONB or defaults
   - `update_cost_calculator_defaults(user_id, defaults)` - save JSONB

5. **Create frontend API client methods**
   - File: `frontend/src/lib/api/client.ts`
   - `getCostCalculatorDefaults()` → GET defaults
   - `updateCostCalculatorDefaults(defaults)` → PATCH defaults

6. **Create types**
   - File: `frontend/src/lib/api/types.ts`
   - `CostCalculatorDefaults { avg_hourly_rate: number, typical_participants: number, typical_duration_mins: number, typical_prep_mins: number }`
   - File: `backend/api/models.py`
   - `CostCalculatorDefaults` Pydantic model

7. **Integrate into dashboard**
   - File: `frontend/src/routes/(app)/dashboard/+page.svelte`
   - Add calculator widget below completion trends
   - Collapsible/expandable to minimize visual footprint

## Tests

- Unit tests:
  - `tests/api/test_cost_calculator.py` - GET/PATCH defaults endpoints, validation
  - Repository method tests in existing `test_user_repository.py`

- Manual validation:
  - Adjust slider inputs and verify real-time cost updates
  - Save defaults and reload page to verify persistence
  - Verify sensible default values on first load

## Dependencies & Risks

- Dependencies:
  - User authentication (already in place)
  - Dashboard page (already exists)

- Risks/edge cases:
  - Large values could show unrealistic numbers - add reasonable caps
  - Currency formatting - use user locale or default USD
  - Mobile responsiveness - ensure calculator works on small screens
