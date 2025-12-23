# Plan: [FEAT][P2] Decision Delivery Templates

## Summary

- Add predefined meeting templates (launch, pricing changes, onboarding revamp, outreach sprint)
- Templates pre-populate problem statement, context hints, and suggested personas
- Admin can create/edit templates; users select from template gallery when starting a meeting
- Reduces cognitive load and ensures consistent decision quality for common scenarios

## Implementation Steps

1. **Database schema for templates**
   - File: `migrations/versions/z21_add_meeting_templates.py`
   - Create `meeting_templates` table: id, name, slug, description, category, problem_statement_template, context_hints (JSONB), suggested_persona_traits (JSONB), is_active, created_at, updated_at
   - Seed built-in templates (launch, pricing_changes, onboarding_revamp, outreach_sprint)

2. **Pydantic models**
   - File: `backend/api/models.py`
   - Add `MeetingTemplate`, `MeetingTemplateCreate`, `MeetingTemplateResponse` models
   - Add `TemplateListResponse` for gallery

3. **Backend API endpoints**
   - File: `backend/api/templates.py` (new)
   - GET `/api/v1/templates` - list active templates (public)
   - GET `/api/v1/templates/{slug}` - get template by slug (public)
   - POST `/api/admin/templates` - create template (admin)
   - PATCH `/api/admin/templates/{id}` - update template (admin)
   - DELETE `/api/admin/templates/{id}` - soft-delete/deactivate (admin)

4. **Repository layer**
   - File: `bo1/state/template_repository.py` (new)
   - CRUD operations with RLS-safe queries
   - Seed data initialization on first run

5. **Frontend API client**
   - File: `frontend/src/lib/api/templates.ts` (new)
   - `listTemplates()`, `getTemplate(slug)` methods

6. **Template selection UI**
   - File: `frontend/src/routes/(app)/meetings/new/+page.svelte`
   - Add template gallery grid before "Start from scratch" option
   - Show template cards with name, description, category badge
   - On select: pre-fill problem statement, show context hints, suggest personas

7. **Admin template management**
   - File: `frontend/src/routes/(app)/admin/templates/+page.svelte` (new)
   - List all templates with edit/delete actions
   - Create/edit form with live preview

8. **Wire template to session creation**
   - File: `backend/api/control.py`
   - Add optional `template_id` to session create request
   - Store `template_id` in session metadata for analytics

## Tests

- Unit tests:
  - `tests/api/test_templates.py` - API CRUD operations (8 tests)
  - `tests/state/test_template_repository.py` - repository layer (6 tests)

- Integration/flow tests:
  - `frontend/e2e/meeting-templates.spec.ts` - template selection flow (3 tests)

- Manual validation:
  - Create meeting via "Launch" template, verify pre-fill
  - Admin creates custom template, appears in gallery
  - Template deletion hides from gallery but preserves data

## Dependencies & Risks

- Dependencies:
  - Session creation endpoint already accepts `problem_statement`
  - Admin authorization patterns established

- Risks/edge cases:
  - Template versioning if we update built-ins (track version, don't overwrite user edits)
  - Long problem_statement_template may need textarea vs input
  - Category filtering UX (defer to v2 if >10 templates)
