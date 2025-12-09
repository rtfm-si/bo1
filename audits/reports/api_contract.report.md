# API Contract Audit Report
**Date:** 2025-12-08

## Endpoint Inventory

### Session Management (`/api/v1/sessions`)

| Method | Path | Auth | Rate Limit | Response Model |
|--------|------|------|------------|----------------|
| POST | `/api/v1/sessions` | ✅ get_current_user | SESSION_RATE_LIMIT | SessionResponse |
| GET | `/api/v1/sessions` | ✅ get_current_user | - | SessionListResponse |
| GET | `/api/v1/sessions/{session_id}` | ✅ get_current_user | - | SessionDetailResponse |

### Streaming (`/api`)

| Method | Path | Auth | Rate Limit | Response Type |
|--------|------|------|------------|---------------|
| GET | `/api/{session_id}/stream` | ✅ get_current_user | - | SSE EventStream |
| GET | `/api/{session_id}/events` | ✅ get_current_user | - | JSON (event history) |

### Control (`/api`)

| Method | Path | Auth | Rate Limit | Response Model |
|--------|------|------|------------|----------------|
| POST | `/api/{session_id}/start` | ✅ get_current_user | - | SessionResponse |
| POST | `/api/{session_id}/pause` | ✅ get_current_user | - | SessionResponse |
| POST | `/api/{session_id}/resume` | ✅ get_current_user | - | SessionResponse |
| POST | `/api/{session_id}/kill` | ✅ get_current_user | - | SessionResponse |
| POST | `/api/{session_id}/clarify` | ✅ get_current_user | - | SessionResponse |

### Admin (`/api/admin`)

| Method | Path | Auth | Rate Limit | Response Type |
|--------|------|------|------------|---------------|
| GET | `/api/admin/sessions` | ✅ require_admin | - | JSON |
| POST | `/api/admin/sessions/{id}/kill` | ✅ require_admin | - | JSON |
| GET | `/admin/docs` | ✅ require_admin | - | HTML (Swagger) |
| GET | `/admin/openapi.json` | ✅ require_admin | - | OpenAPI spec |

### Other Routers

| Router | Prefix | Auth Required |
|--------|--------|---------------|
| health | /api | ❌ No auth |
| waitlist | /api | ❌ No auth (public signup) |
| auth | /api/auth | Mixed (SuperTokens) |
| context | /api | ✅ Required |
| actions | /api | ✅ Required |
| projects | /api | ✅ Required |
| tags | /api | ✅ Required |
| billing | /api | ✅ Required |
| onboarding | /api | ✅ Required |

## Schema Validation Coverage

### Request Models ✅

| Model | Validation | Pydantic |
|-------|------------|----------|
| CreateSessionRequest | ✅ | ✅ BaseModel |
| TaskStatusUpdate | ✅ | ✅ BaseModel |
| ClarificationRequest | ✅ | ✅ BaseModel |

### Response Models ✅

| Model | Used By | Fields Documented |
|-------|---------|-------------------|
| SessionResponse | create/start/pause | ✅ |
| SessionListResponse | list sessions | ✅ |
| SessionDetailResponse | get session | ✅ |
| ErrorResponse | all error handlers | ✅ |

### Validation Gaps ⚠️

1. **Problem statement validation**
   - `check_for_injection()` called but not documented in OpenAPI
   - Max length not enforced in Pydantic model

2. **Session ID format**
   - `validate_session_id()` helper exists
   - Not enforced as Pydantic validator (runtime only)

## Breaking Change Risk Assessment

### High Risk ❌
1. **Session ID format change** - Frontend hardcodes `bo1_` prefix
2. **SSE event type changes** - Frontend switch statements on event types
3. **Response field removal** - Frontend destructures specific fields

### Medium Risk ⚠️
4. **New required fields** - Would break existing clients
5. **Error response format** - Frontend error handlers expect `{error, message, type}`

### Low Risk ✅
6. **Adding optional response fields** - Backward compatible
7. **New endpoints** - No breaking change
8. **New optional request fields** - Backward compatible

## Error Response Consistency

### Consistent Pattern ✅

```json
{
  "error": "Human-readable error type",
  "message": "Detailed error message",
  "type": "ErrorClassName"
}
```

### HTTP Status Codes Used

| Code | Usage | Consistent |
|------|-------|------------|
| 200 | Success | ✅ |
| 201 | Created | ✅ |
| 400 | Bad Request | ✅ |
| 401 | Unauthorized | ✅ |
| 403 | Forbidden | ✅ |
| 404 | Not Found | ✅ |
| 429 | Rate Limit | ✅ |
| 500 | Internal Error | ✅ |

### Error Handling Decorators
- `@handle_api_errors(context)` - Consistent error wrapping
- `raise_api_error()` - Standardized error raising

## SSE Event Contract

### Core Events

| Event Type | Payload Keys | Tab Filter |
|------------|--------------|------------|
| decomposition_complete | sub_problems, total | ❌ |
| persona_selected | persona, rationale, order | sub_problem_index |
| contribution | persona_code, content, summary, round | sub_problem_index |
| convergence | should_stop, metrics | sub_problem_index |
| voting_complete | recommendations | sub_problem_index |
| synthesis_complete | synthesis, expert_summaries | sub_problem_index |
| meta_synthesis_complete | meta_synthesis | ❌ |
| complete | session_id, status | ❌ |
| error | error, error_type | sub_problem_index |

### SSE Contract Issues

1. **No versioning** - Event format changes could break clients
2. **Inconsistent sub_problem_index** - Some events don't include it
3. **No retry/reconnect guidance** - Client must implement own backoff

## Recommendations

### P0 - Critical
1. **Document injection check in OpenAPI** - Security feature not visible in docs
2. **Add SSE event versioning** - Include `event_version: 1` in payloads

### P1 - High Value
3. **Enforce problem_statement max length** - Add Pydantic Field(max_length=10000)
4. **Add session_id regex validation** - Pydantic validator for `bo1_[uuid]` format
5. **Document all SSE event types** - Create SSE event schema documentation

### P2 - Nice to Have
6. **Add OpenAPI spec versioning** - `/api/v1/` prefix already used, formalize
7. **Add deprecation headers** - For future API changes
8. **Create SDK types package** - TypeScript types for frontend consumption
