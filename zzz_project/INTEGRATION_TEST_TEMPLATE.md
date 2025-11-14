# Integration Test & Input Validation Requirements Template

This template should be applied to ALL incomplete days in the MVP roadmap.

## Standard Integration Test Requirements

For EVERY day that is incomplete, add the following section before the "Validation" section:

### Integration Tests (REQUIRED)
```bash
pytest tests/integration/test_[feature_name]_integration.py -v
```

**Required Test Coverage**:
- [ ] **Input validation**: All user inputs validated (Pydantic models)
- [ ] **Malicious input handling**: XSS attempts, SQL injection, script tags, path traversal
- [ ] **Boundary conditions**: Empty strings, max length (10,000 chars), special characters
- [ ] **Error recovery**: Network failures, API timeouts, database unavailable
- [ ] **State consistency**: Verify state remains consistent after errors
- [ ] **Authentication bypass attempts**: Verify all protected endpoints require auth
- [ ] **Authorization bypass attempts**: Verify users can't access others' data
- [ ] **Rate limiting**: Verify rate limits enforced, headers present

## User Input Locations to Validate

### Frontend (SvelteKit)
- [ ] Form inputs: Min/max length, type validation, sanitization
- [ ] URL parameters: Type validation, no script injection
- [ ] Query strings: Type validation, no SQL injection attempts
- [ ] File uploads: Extension validation, size limits, virus scanning (future)
- [ ] Cookies: Signature validation, expiration checks

### Backend (FastAPI)
- [ ] Request bodies: Pydantic validation, reject unknown fields
- [ ] Path parameters: Type validation (UUID, int, etc.)
- [ ] Query parameters: Type validation, default values
- [ ] Headers: Whitelist allowed headers, reject malicious values
- [ ] Webhooks: Signature validation (Stripe, Supabase)

### Database
- [ ] Parameterized queries: NEVER string interpolation
- [ ] Row-level security (RLS): Enabled on all user-facing tables
- [ ] Input sanitization: Before database writes

### Redis
- [ ] Key validation: No control characters, max length 512 bytes
- [ ] Value sanitization: No script injection via stored values

## Security Checklist (Apply to ALL Days)

- [ ] **Never trust user input**: Validate, sanitize, escape
- [ ] **Fail securely**: Default deny, explicit allow
- [ ] **Least privilege**: Users only access own data
- [ ] **Defense in depth**: Multiple layers (Pydantic, RLS, rate limiting)
- [ ] **Audit logging**: Log all security-relevant events

## Example Integration Test (Template)

```python
import pytest
from fastapi.testclient import TestClient

class TestFeatureIntegration:
    """Integration tests for [Feature Name]."""

    def test_valid_input_accepted(self, client: TestClient):
        """Test that valid input is accepted."""
        response = client.post("/api/v1/resource", json={
            "field": "valid value"
        })
        assert response.status_code == 200

    def test_invalid_input_rejected(self, client: TestClient):
        """Test that invalid input is rejected."""
        response = client.post("/api/v1/resource", json={
            "field": "x" * 10001  # Exceeds max length
        })
        assert response.status_code == 422  # Validation error

    def test_xss_attempt_sanitized(self, client: TestClient):
        """Test that XSS attempts are sanitized."""
        response = client.post("/api/v1/resource", json={
            "field": "<script>alert('XSS')</script>"
        })
        assert response.status_code == 200
        # Verify script tag not stored/returned
        data = response.json()
        assert "<script>" not in data["field"]

    def test_sql_injection_blocked(self, client: TestClient):
        """Test that SQL injection is blocked."""
        response = client.post("/api/v1/resource", json={
            "field": "'; DROP TABLE users; --"
        })
        assert response.status_code == 200
        # Verify no SQL injection occurred
        # (parameterized queries prevent this)

    def test_unauthorized_access_blocked(self, client: TestClient):
        """Test that unauthorized users are blocked."""
        response = client.get("/api/v1/protected-resource")
        assert response.status_code == 401  # Unauthorized

    def test_authorization_enforced(self, client: TestClient, user_token: str, other_user_session_id: str):
        """Test that users can't access others' data."""
        response = client.get(
            f"/api/v1/sessions/{other_user_session_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403  # Forbidden (RLS)

    def test_rate_limit_enforced(self, client: TestClient, user_token: str):
        """Test that rate limits are enforced."""
        # Exceed rate limit
        for _ in range(15):
            response = client.post(
                "/api/v1/sessions",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"problem_statement": "test"}
            )

        # 11th request should be rate limited (free tier: 10/min)
        assert response.status_code == 429
        assert "Retry-After" in response.headers
```

## Days Requiring Immediate Updates

ALL days from Day 28 onward need these requirements added.
