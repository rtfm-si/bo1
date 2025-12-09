# Data Model Audit Report
**Date:** 2025-12-08

## Schema-to-Model Mapping

### Core Tables

| Table | Pydantic Model | Status |
|-------|----------------|--------|
| sessions | N/A (dict-based) | ⚠️ No model |
| contributions | ContributionMessage | ⚠️ Partial match |
| recommendations | Recommendation | ✅ Aligned |
| personas | PersonaProfile | ✅ Aligned |
| sub_problem_results | SubProblemResult | ✅ Aligned |

### Detailed Field Analysis

#### `contributions` Table vs `ContributionMessage` Model

| DB Column | Pydantic Field | Match |
|-----------|----------------|-------|
| id | N/A | ❌ Missing in model |
| session_id | N/A | ❌ Missing in model |
| persona_code | persona_code | ✅ |
| content | content | ✅ |
| round_number | round_number | ✅ |
| phase | contribution_type (Enum) | ⚠️ Type mismatch |
| cost | cost | ✅ |
| tokens | token_count | ⚠️ Name mismatch |
| model | N/A | ❌ Missing in model |
| embedding | N/A | ❌ Missing in model |
| created_at | timestamp | ✅ (different name) |

#### `sessions` Table
- No dedicated Pydantic model - uses dict throughout
- Repository returns `dict[str, Any]` for all session operations
- **Risk**: Type safety gaps, no validation on session data

## Drift Detection

### Schema Drift Issues

1. **ContributionMessage.contribution_type vs DB phase**
   - Model uses `ContributionType` enum (INITIAL, RESPONSE, MODERATOR, etc.)
   - DB stores string phase names (initial_round, deliberation, etc.)
   - **Risk**: Mismatch when deserializing from DB

2. **Missing `user_id` in ContributionMessage**
   - Added to DB via migration `074cc4d875b0_add_user_id_and_rls_contributions.py`
   - Not reflected in Pydantic model
   - Repository fetches it separately

3. **Missing `embedding` vector in model**
   - Added via migration `688378ba7cfa_add_embedding_column_contributions.py`
   - 1024-dimension vector for semantic dedup
   - Not in ContributionMessage model

## Nullable/Required Consistency

| Field | DB Nullable | Model Required | Consistent |
|-------|-------------|----------------|------------|
| session_id | NOT NULL | N/A | ⚠️ Not in model |
| persona_code | NOT NULL | Required | ✅ |
| content | NOT NULL | Required | ✅ |
| thinking | N/A (not in DB) | Optional | N/A |
| token_count | DEFAULT 0 | Optional | ✅ |
| cost | DEFAULT 0 | Optional | ✅ |
| embedding | NULL | N/A | N/A |

## Serialization Roundtrip Validation

### State Serialization Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `state_to_dict()` | bo1/graph/state.py | Checkpointing |
| `serialize_state_for_checkpoint()` | bo1/graph/state.py | Redis persistence |
| `deserialize_state_from_checkpoint()` | bo1/graph/state.py | Checkpoint restore |

### Serialization Issues

1. **Problem object can be dict or Pydantic model after restore**
   - `_get_problem_attr()` helper handles both cases
   - Added to routers.py as mitigation
   - **Risk**: Caller must always use helper, not direct access

2. **ContributionMessage datetime serialization**
   - `timestamp` field uses `datetime.now()` default
   - May serialize to ISO string, deserialize as string (not datetime)
   - Repository uses DB timestamp, not model timestamp

## Migration History Integrity

### Recent Migrations (Last 10)

| Revision | Description | Status |
|----------|-------------|--------|
| b3_user_id_fac_decisions | Add user_id to facilitator_decisions | ✅ |
| b2_add_actions_soft_delete | Soft delete for actions | ✅ |
| b1_add_final_rec | Add final_recommendation to sessions | ✅ |
| 9626a52fd9bf | Drop unused votes table | ✅ |
| a9_create_tags_table | Action tags | ✅ |

### Migration Concerns
- **47 migrations** since initial schema - consider squashing for new deployments
- Partition migrations (f3b5a664a3ff) for high-growth tables are in place

## Recommendations

### P0 - Critical
1. **Create Session Pydantic model** - Currently dict-based, no validation
2. **Align ContributionMessage with DB schema** - Add `id`, `session_id`, `model`, `embedding` fields

### P1 - High Value
3. **Fix contribution_type/phase mismatch** - Use consistent enum values
4. **Add user_id to ContributionMessage** - For RLS compliance

### P2 - Nice to Have
5. **Squash migrations** - Create consolidated baseline for new deployments
6. **Add model validation tests** - Ensure roundtrip serialization works
