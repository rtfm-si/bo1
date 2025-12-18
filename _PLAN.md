# Plan: [API][P3] Define API versioning strategy for breaking changes

## Summary

- Document API versioning conventions already in use (v1 prefix)
- Define criteria for when a version bump is required
- Establish deprecation timeline and sunset policy
- Create ADR (Architecture Decision Record) for versioning strategy

## Implementation Steps

1. **Create ADR document** (`docs/adr/004-api-versioning.md`)
   - Document current v1 prefix convention
   - Define what constitutes a breaking change:
     - Removing fields/endpoints
     - Changing field types
     - Changing required/optional semantics
     - Changing error response formats
   - Define what does NOT require a version bump:
     - Adding optional fields
     - Adding new endpoints
     - Adding new enum values (if client handles unknowns)

2. **Define deprecation policy**
   - Minimum deprecation notice: 90 days
   - Deprecation headers: `Deprecation`, `Sunset` (RFC 8594)
   - Announce via: changelog, dashboard banner, email to affected users

3. **Add version header support** (`backend/api/middleware/versioning.py`)
   - Read `Accept-Version` or `X-API-Version` header
   - Default to latest if not specified
   - Log version usage for analytics

4. **Create deprecation decorator** (`backend/api/utils/deprecation.py`)
   - `@deprecated(sunset_date="2025-06-01", message="Use /v2/... instead")`
   - Adds `Deprecation` and `Sunset` headers to response
   - Logs usage of deprecated endpoints

5. **Update CLAUDE.md**
   - Add brief versioning rule reference
   - Link to ADR

## Tests

- Unit tests:
  - `tests/api/test_versioning_middleware.py`: header parsing, default behavior
  - `tests/api/test_deprecation_decorator.py`: header injection, logging
- Manual validation:
  - Call deprecated endpoint, verify headers present
  - Check logs for deprecation tracking

## Dependencies & Risks

- Dependencies:
  - None (documentation + lightweight middleware)
- Risks:
  - Over-engineering: keep middleware simple, don't add full router versioning yet
  - Clients may ignore deprecation headers: supplement with email/dashboard notices
