# Plan: Workspace Authorization Layer [TEAMS][P3]

## Summary

- Create workspace authorization service with role-based permissions
- Add `require_workspace_access()` and `require_workspace_role()` dependencies
- Integrate authorization checks into sessions and datasets endpoints
- Add API routes for workspace CRUD and member management

## Implementation Steps

1. **Create authorization service** `backend/services/workspace_auth.py`
   - Permission enum: VIEW, EDIT, MANAGE_MEMBERS, DELETE
   - Role-to-permissions mapping (OWNER > ADMIN > MEMBER)
   - `check_permission(workspace_id, user_id, permission) -> bool`
   - `get_accessible_workspaces(user_id) -> list[UUID]`

2. **Create FastAPI dependencies** `backend/api/middleware/workspace_auth.py`
   - `require_workspace_access(workspace_id, user_id)` - 403 if not member
   - `require_workspace_role(workspace_id, user_id, min_role)` - 403 if insufficient
   - `get_workspace_context()` - inject workspace from path param or header

3. **Create workspaces API routes** `backend/api/workspaces/routes.py`
   - POST /api/v1/workspaces - create workspace
   - GET /api/v1/workspaces - list user's workspaces
   - GET /api/v1/workspaces/{id} - get workspace details
   - PATCH /api/v1/workspaces/{id} - update (admin+)
   - DELETE /api/v1/workspaces/{id} - delete (owner only)
   - GET /api/v1/workspaces/{id}/members - list members
   - POST /api/v1/workspaces/{id}/members - add member (admin+)
   - PATCH /api/v1/workspaces/{id}/members/{user_id} - update role (admin+)
   - DELETE /api/v1/workspaces/{id}/members/{user_id} - remove (admin+)

4. **Integrate with sessions endpoint** `backend/api/sessions.py`
   - Add workspace_id filter to GET /sessions
   - Add workspace_id to session creation
   - Add workspace access check for session retrieval

5. **Integrate with datasets endpoint** `backend/api/datasets.py`
   - Add workspace_id filter to GET /datasets
   - Add workspace_id to dataset upload
   - Add workspace access check for dataset retrieval

6. **Register routes** `backend/api/main.py`
   - Include workspaces router at /api/v1/workspaces

## Tests

- Unit tests:
  - `tests/api/test_workspace_auth.py`: permission checks, role hierarchy
  - Test non-member access denied (403)
  - Test role upgrade/downgrade permissions
  - Test owner-only delete

- Integration tests:
  - `tests/api/test_workspaces_api.py`: full CRUD + member ops
  - Test session/dataset workspace filtering
  - Test cross-workspace isolation

- Manual validation:
  - Create workspace → invite member → verify access
  - Try accessing other user's workspace (expect 403)

## Dependencies & Risks

- Dependencies:
  - workspace_repository (exists)
  - MemberRole enum (exists)

- Risks/edge cases:
  - Users without workspace can still access personal content (null workspace_id)
  - Concurrent role changes during request (last-write-wins acceptable)
  - Owner leaves workspace (prevent, require transfer ownership first)
