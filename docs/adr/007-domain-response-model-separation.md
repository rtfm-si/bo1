# ADR 007: Domain vs Response Model Separation

**Status:** Accepted
**Date:** 2026-02-03
**Authors:** Bo1 Team

## Context

The codebase has two types of Session models:
- **Domain model** (`bo1/models/session.py:Session`): Full database entity with ~30 fields
- **Response model** (`backend/api/models.py:SessionResponse`): User-facing API subset with ~14 fields

This pattern appears duplicative but serves distinct purposes.

## Decision

Maintain separate domain and response models with clear boundaries:

| Layer | Location | Purpose |
|-------|----------|---------|
| Domain | `bo1/models/` | Full DB entity, internal tracking, checkpoint state |
| API Response | `backend/api/models.py` | User-facing subset, billing credits, warnings |
| Admin Response | `backend/api/admin/models.py` | Raw introspection for support/debugging |

### Fields Excluded from User-Facing Response

| Field | Reason |
|-------|--------|
| `recovery_needed`, `has_untracked_costs` | Internal recovery state |
| `last_completed_sp_index`, `sp_checkpoint_at`, `total_sub_problems` | Checkpoint implementation detail |
| `persona_count_variant` | A/B experiment tracking |
| `billable_portion` | Internal billing calculation |
| `termination_type`, `termination_reason`, `terminated_at` | Admin-level detail |
| `template_id`, `workspace_id`, `dataset_id` | Available via separate endpoints |

## Consequences

### Positive
- Clear security/privacy boundary: internal state never leaks to API
- Response models can evolve independently (add `stale_insights` warning without touching domain)
- Domain model remains 1:1 with database schema

### Negative
- Minor field duplication between models
- Developers must know which model to use where

### Mitigations
- Docstrings cross-reference related models
- This ADR documents the rationale

## References

- `bo1/models/session.py` - domain model
- `backend/api/models.py:SessionResponse` - user API
- `backend/api/admin/models.py:FullSessionResponse` - admin introspection
