# ADR 004: API Versioning Strategy

**Status:** Accepted
**Date:** 2025-12-18
**Authors:** Bo1 Team

## Context

Bo1 uses a `/api/v1/` prefix for all API endpoints. As the platform matures, we need clear guidelines for:
- When version bumps are required
- How to deprecate endpoints
- How to communicate changes to clients

## Decision

### Version Scheme

- **URL-based versioning**: `/api/v{major}/` prefix (current: v1)
- **Optional header override**: `Accept-Version` or `X-API-Version` for testing/migration
- **Response header**: `API-Version` on all responses

### Breaking Changes (Require Version Bump)

The following changes require incrementing the major version:

1. **Removing fields** from response bodies
2. **Removing endpoints** entirely
3. **Changing field types** (e.g., string to int, object to array)
4. **Changing required/optional semantics** for request fields
5. **Changing error response formats** or status codes for existing conditions
6. **Renaming fields** in request or response bodies
7. **Changing authentication/authorization requirements**

### Non-Breaking Changes (No Version Bump)

The following changes are backwards-compatible:

1. **Adding optional fields** to request bodies
2. **Adding new fields** to response bodies (clients should ignore unknown fields)
3. **Adding new endpoints**
4. **Adding new enum values** (clients must handle unknown values gracefully)
5. **Adding new optional query parameters**
6. **Relaxing validation** (e.g., accepting longer strings)
7. **Fixing bugs** that bring behavior in line with documentation

### Deprecation Policy

**Timeline:**
- Minimum deprecation notice: **90 days** before sunset
- Critical security fixes may have shortened timeline with direct notification

**Communication Channels:**
1. `Deprecation` header on deprecated endpoints (RFC 8594)
2. `Sunset` header with sunset date (RFC 8594)
3. `X-Deprecation-Notice` header with human-readable message
4. Changelog entry in release notes
5. Dashboard banner for affected users
6. Email notification 30 days before sunset

**Header Format:**
```http
Deprecation: true
Sunset: Sat, 01 Mar 2025 00:00:00 GMT
X-Deprecation-Notice: This endpoint is deprecated. Use /api/v2/sessions instead.
```

### Version Negotiation

Clients can request a specific API version:

```http
Accept-Version: 1.0
# or
X-API-Version: 1.0
```

If not specified, the latest stable version is used. Invalid versions return `400 Bad Request`.

### Analytics

All API requests log:
- Requested version (from header or URL)
- Whether deprecated endpoint was called
- Client identifier (for targeted migration outreach)

## Consequences

### Positive
- Clear contract for API consumers
- Predictable deprecation timeline
- Version analytics enable proactive client migration

### Negative
- Maintaining multiple versions increases complexity
- Header-based versioning adds middleware overhead

### Mitigations
- Keep version count low (target: max 2 active versions)
- Automate deprecation header injection via decorator
- Monitor version usage; sunset aggressively when adoption is low

## Implementation

- `backend/api/middleware/api_version.py` - Version header handling
- `backend/api/utils/deprecation.py` - `@deprecated()` decorator
- Prometheus metrics: `api_deprecated_calls_total{endpoint, version}`

## References

- [RFC 8594 - Sunset Header](https://datatracker.ietf.org/doc/html/rfc8594)
- [Stripe API Versioning](https://stripe.com/docs/api/versioning)
- [GitHub API Versioning](https://docs.github.com/en/rest/overview/api-versions)
