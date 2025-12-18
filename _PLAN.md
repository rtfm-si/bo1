# Plan: [DATA][P3] Update CLAUDE.md state serialization references

## Summary

- Replace outdated `state_to_v1()` / `v1_to_state()` references with actual function names
- Update 3 files: root CLAUDE.md, bo1/CLAUDE.md, data_model manifest
- Actual functions: `serialize_state_for_checkpoint()` / `deserialize_state_from_checkpoint()`

## Implementation Steps

1. **Update root CLAUDE.md** (line 49)
   - Change: `state_to_v1() / v1_to_state()` → `serialize_state_for_checkpoint() / deserialize_state_from_checkpoint()`

2. **Update bo1/CLAUDE.md** (line 6)
   - Change: `state_to_v1() / v1_to_state()` → `serialize_state_for_checkpoint() / deserialize_state_from_checkpoint()`

3. **Update audits/manifests/data_model.manifest.xml** (line 13)
   - Change: `state_to_v1/v1_to_state` → `serialize_state_for_checkpoint/deserialize_state_from_checkpoint`

## Tests

- Unit tests:
  - None needed; documentation-only change
- Integration tests:
  - N/A
- Manual validation:
  - Grep confirms no remaining references to old function names
  - New function names match actual code in `bo1/graph/state.py:428,516`

## Dependencies & Risks

- Dependencies:
  - None
- Risks:
  - None; purely documentation update
