# Board of One - Authentication & Authorization Implementation Summary

**Date**: November 17, 2025
**Status**: MVP (v1.0) - Hardcoded auth, v2.0+ planned with full Supabase integration
**Use Case**: Closed beta with ~10 users

---

## Executive Summary

Board of One currently implements a **minimal MVP authentication** system suitable for closed beta testing:

- **Current**: Hardcoded user ID (`test_user_1`) for all API calls - no actual authentication required
- **Admin Access**: API key-based authentication via `X-Admin-Key` header
- **Database**: Full schema prepared with user management, RLS policies, and audit logging
- **Path to Production**: Feature flag (`ENABLE_SUPABASE_AUTH`) to enable Supabase OAuth when ready

---

## Table of Contents

1. [Current Implementation (MVP)](#1-current-implementation-mvp)
2. [User Database Schema](#2-user-database-schema)
3. [API Authentication](#3-api-authentication)
4. [Authorization & Access Control](#4-authorization--access-control)
5. [Environment Configuration](#5-environment-configuration)
6. [For Closed Beta (~10 Users)](#6-for-closed-beta-10-users)
7. [Production Readiness Roadmap](#7-production-readiness-roadmap)

---

## 1. Current Implementation (MVP)

### 1.1 Auth Middleware Location

**File**: `/Users/si/projects/bo1/backend/api/middleware/auth.py`

```python
# Feature flag for Supabase auth (disabled for MVP)
ENABLE_SUPABASE_AUTH = os.getenv("ENABLE_SUPABASE_AUTH", "false").lower() == "true"

# MVP: Hardcoded user ID for development
DEFAULT_USER_ID = "test_user_1"
```

### 1.2 How It Works (MVP Mode)

When `ENABLE_SUPABASE_AUTH=false` (current default):

1. All API endpoints skip authentication
2. Returns hardcoded user object:
   ```python
   {
       "user_id": "test_user_1",
       "email": "test_user_1@test.com",
       "role": "authenticated",
       "subscription_tier": "free",
   }
   ```
3. No JWT token validation
4. No permission checks on API calls

**Key Functions** in `auth.py`:

- `verify_jwt(authorization: str)` - Validates JWT or returns hardcoded user
- `get_current_user(authorization: str)` - Alias for `verify_jwt()`
- `require_auth(user: dict)` - Dependency to ensure user exists

### 1.3 Admin Authentication

**File**: `/Users/si/projects/bo1/backend/api/middleware/admin.py`

Uses environment variable `ADMIN_API_KEY` with header-based verification:

```python
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

def require_admin(x_admin_key: str = Header(...)) -> str:
    """Validate X-Admin-Key header against environment variable."""
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin API key")
    return x_admin_key
```

**Usage Example**:
```bash
curl -X GET http://localhost:8000/api/admin/sessions/active \
  -H "X-Admin-Key: your_admin_api_key_here"
```

---

## 2. User Database Schema

### 2.1 Users Table

**File**: `/Users/si/projects/bo1/migrations/versions/ced8f3f148bb_initial_schema.py`

```sql
CREATE TABLE users (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    auth_provider VARCHAR(50) NOT NULL,  -- 'supabase', 'google', 'linkedin', 'github'
    subscription_tier VARCHAR(50) DEFAULT 'free',  -- 'free', 'pro', 'enterprise'
    gdpr_consent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

### 2.2 Related Tables with User References

**Sessions Table** (owned by user):
```sql
CREATE TABLE sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) FOREIGN KEY REFERENCES users.id,
    problem_statement TEXT,
    problem_context JSON,
    status VARCHAR(50) DEFAULT 'active',
    phase VARCHAR(50) DEFAULT 'problem_decomposition',
    total_cost NUMERIC(10,4) DEFAULT 0.0,
    total_tokens INTEGER DEFAULT 0,
    round_number INTEGER DEFAULT 0,
    max_rounds INTEGER DEFAULT 10,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    completed_at TIMESTAMP,
    killed_at TIMESTAMP,
    killed_by VARCHAR(255),  -- user_id or 'admin'
    kill_reason VARCHAR(500)
);
```

**Contributions Table** (from personas in sessions):
```sql
CREATE TABLE contributions (
    id INTEGER PRIMARY KEY,
    session_id VARCHAR(255) FOREIGN KEY,
    persona_code VARCHAR(50) FOREIGN KEY,
    content TEXT,
    round_number INTEGER,
    phase VARCHAR(50),
    cost NUMERIC(10,4),
    tokens INTEGER,
    model VARCHAR(100),
    created_at TIMESTAMP DEFAULT now()
);
```

**Audit Log Table** (tracks all user actions):
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    user_id VARCHAR(255) FOREIGN KEY REFERENCES users.id,
    action VARCHAR(100),  -- 'session_created', 'session_killed', 'user_login'
    resource_type VARCHAR(50),  -- 'session', 'user', 'persona'
    resource_id VARCHAR(255),
    details JSON,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    timestamp TIMESTAMP DEFAULT now()
);
```

### 2.3 Row-Level Security (RLS) Policies

**File**: `/Users/si/projects/bo1/migrations/versions/396e8f26d0a5_create_rls_policies.py`

```sql
-- Sessions: Users can only access their own sessions
CREATE POLICY sessions_user_isolation ON sessions
FOR ALL
USING (user_id = current_setting('app.current_user_id', TRUE)::text);

-- Contributions: Users can only see contributions from their own sessions
CREATE POLICY contributions_user_isolation ON contributions
FOR ALL
USING (
    session_id IN (
        SELECT id FROM sessions
        WHERE user_id = current_setting('app.current_user_id', TRUE)::text
    )
);

-- Votes: Users can only see votes from their own sessions
CREATE POLICY votes_user_isolation ON votes
FOR ALL
USING (
    session_id IN (
        SELECT id FROM sessions
        WHERE user_id = current_setting('app.current_user_id', TRUE)::text
    )
);

-- Audit Log: Users can only see their own audit logs
CREATE POLICY audit_log_user_isolation ON audit_log
FOR ALL
USING (user_id = current_setting('app.current_user_id', TRUE)::text);
```

**Important**: RLS policies use PostgreSQL's `current_setting('app.current_user_id')` which must be set by the application:

```python
# When executing queries, set the user context:
await db.execute("SET app.current_user_id TO $1", [user_id])
```

---

## 3. API Authentication

### 3.1 Protected Endpoints

**All endpoints currently use hardcoded `test_user_1` because `ENABLE_SUPABASE_AUTH=false`**.

**Example Endpoints**:

```python
# Sessions endpoints
POST /api/v1/sessions - Create session
GET /api/v1/sessions - List user's sessions
GET /api/v1/sessions/{session_id} - Get session details

# Control endpoints
POST /api/v1/sessions/{session_id}/start - Start deliberation
POST /api/v1/sessions/{session_id}/pause - Pause deliberation
POST /api/v1/sessions/{session_id}/resume - Resume from checkpoint
POST /api/v1/sessions/{session_id}/kill - Kill session (ownership checked)

# Admin endpoints (require X-Admin-Key)
GET /api/admin/sessions/active - List all active sessions
POST /api/admin/sessions/{session_id}/kill - Kill any session (no ownership check)
POST /api/admin/sessions/kill-all - Emergency kill all sessions
```

### 3.2 User Extraction in Control Endpoints

**File**: `/Users/si/projects/bo1/backend/api/control.py` (lines 31-45)

```python
def _get_user_id_from_header() -> str:
    """Get user ID from request header.

    For MVP, we'll use a hardcoded user ID. In production (Week 7+),
    this will extract user ID from JWT token.
    """
    # TODO(Week 7): Extract from JWT token
    # For now, use a test user ID
    user_id = "test_user_1"

    # Validate user ID format (prevents injection even with hardcoded value)
    return validate_user_id(user_id)
```

**Session Ownership Check** in `SessionManager`:

```python
async def kill_session(
    self, session_id: str, user_id: str, reason: str = "User requested"
) -> bool:
    """Kill a session (user can only kill own sessions)."""
    # Check ownership
    metadata = self._load_session_metadata(session_id)
    if metadata.get("user_id") != user_id:
        raise PermissionError(
            f"User {user_id} cannot kill session {session_id} owned by {metadata.get('user_id')}"
        )

    # Kill the session
    return await self._kill_session_internal(session_id, user_id, reason)
```

---

## 4. Authorization & Access Control

### 4.1 Ownership-Based Access Control

The system enforces **session ownership** at the application level:

1. **SessionManager** tracks who owns each session
2. **Control endpoints** check ownership before allowing operations
3. **Sessions table** stores `user_id` foreign key for accountability

### 4.2 Admin Privileges

**File**: `/Users/si/projects/bo1/backend/api/dependencies.py`

```python
def get_session_manager() -> SessionManager:
    """Get singleton session manager instance."""
    redis_manager = get_redis_manager()

    # Load admin user IDs from environment
    # Format: Comma-separated list (e.g., "admin,user123")
    admin_users_env = os.getenv("ADMIN_USER_IDS", "admin")
    admin_user_ids = {user.strip() for user in admin_users_env.split(",") if user.strip()}

    return SessionManager(redis_manager, admin_user_ids=admin_user_ids)
```

**Admin User Checks** in `SessionManager`:

```python
def is_admin(self, user_id: str) -> bool:
    """Check if user has admin privileges."""
    return user_id in self.admin_user_ids

async def admin_kill_session(
    self, session_id: str, admin_user_id: str, reason: str = "Admin terminated"
) -> bool:
    """Kill any session (admin only, no ownership check)."""
    if not self.is_admin(admin_user_id):
        raise PermissionError(f"User {admin_user_id} is not an admin")

    return await self._kill_session_internal(session_id, admin_user_id, reason, is_admin=True)
```

### 4.3 Permission Matrix (Future v2+)

| Action | User | Admin | Support |
|--------|------|-------|---------|
| Create session | ✅ (own) | ✅ (any) | ❌ |
| View session | ✅ (own) | ✅ (any) | ✅ (with consent) |
| Delete session | ❌ | ✅ | ❌ |
| View cost metrics | ❌ | ✅ | ❌ |
| Export user data | ✅ (own) | ✅ (any) | ✅ (with consent) |
| Anonymize user | ✅ (own) | ✅ (any) | ❌ |
| View audit logs | ❌ | ✅ | ❌ |

---

## 5. Environment Configuration

### 5.1 Auth-Related Environment Variables

**File**: `/Users/si/projects/bo1/.env.example`

```bash
# =============================================================================
# Self-Hosted Supabase Auth (Week 6+)
# =============================================================================
SUPABASE_URL=http://localhost:9999
SUPABASE_ANON_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
SUPABASE_JWT_SECRET=your_jwt_secret_here  # Generate with: openssl rand -base64 32

# OAuth Provider Credentials (Google, LinkedIn, GitHub)
GOOGLE_OAUTH_CLIENT_ID=your_google_oauth_client_id_here
GOOGLE_OAUTH_CLIENT_SECRET=your_google_oauth_client_secret_here
LINKEDIN_OAUTH_CLIENT_ID=your_linkedin_oauth_client_id_here
LINKEDIN_OAUTH_CLIENT_SECRET=your_linkedin_oauth_client_secret_here
GITHUB_OAUTH_CLIENT_ID=your_github_oauth_client_id_here
GITHUB_OAUTH_CLIENT_SECRET=your_github_oauth_client_secret_here

# Admin API Configuration
ADMIN_API_KEY=your_admin_api_key_here  # Admin API key for /api/admin/* endpoints
ADMIN_USER_IDS=admin,user123  # Comma-separated list of admin user IDs

# Feature Flags
ENABLE_SUPABASE_AUTH=false  # Set to true in production to enable real auth
```

### 5.2 Docker Compose Environment Setup

**File**: `/Users/si/projects/bo1/docker-compose.yml`

The API container receives:
```yaml
environment:
  - ADMIN_API_KEY=${ADMIN_API_KEY}
  - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:3000,http://localhost:5173}
  - DATABASE_URL=postgresql://bo1:${POSTGRES_PASSWORD:-bo1_dev_password}@postgres:5432/boardofone
```

**File**: `/Users/si/projects/bo1/docker-compose.prod.yml`

Production configuration includes:
```yaml
environment:
  - PYTHONHASHSEED=random  # Security: Random hash seed
  - DEBUG=false
  - LOG_LEVEL=INFO
```

---

## 6. For Closed Beta (~10 Users)

### 6.1 MVP Approach (Current)

**Advantages**:
- ✅ Zero external dependencies (no Supabase server needed)
- ✅ Simple deployment and debugging
- ✅ Fast iteration on features
- ✅ Perfect for testing with a known set of users

**Limitations**:
- ❌ All users share the same user ID (`test_user_1`)
- ❌ Cannot distinguish between beta testers
- ❌ Audit logs show all activity under one user
- ❌ Not production-ready (no real auth)

### 6.2 Recommended Enhancement for Closed Beta

To support 10 distinct users while keeping it simple:

**Option 1: Hardcoded User Mapping** (5 minutes implementation)

```python
# backend/api/middleware/auth.py
DEFAULT_USERS = {
    "alice": {
        "user_id": "user_alice",
        "email": "alice@example.com",
        "role": "authenticated",
        "subscription_tier": "free",
    },
    "bob": {
        "user_id": "user_bob",
        "email": "bob@example.com",
        "role": "authenticated",
        "subscription_tier": "free",
    },
    # ... 8 more users
}

# Header-based user selection
async def verify_jwt(authorization: str = Header(None)) -> dict[str, Any]:
    if not ENABLE_SUPABASE_AUTH:
        # Extract user from X-User-ID header (closed beta only)
        user_id = authorization or "test_user_1"
        if user_id not in DEFAULT_USERS:
            raise HTTPException(status_code=401, detail="Unknown user")
        return DEFAULT_USERS[user_id]
```

**Usage**:
```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "X-User-ID: alice" \
  -H "Content-Type: application/json" \
  -d '{"problem_statement": "Should we invest in X?"}'
```

**Option 2: Query Parameter** (Alternative)

```bash
curl -X POST "http://localhost:8000/api/v1/sessions?user=alice" \
  -H "Content-Type: application/json" \
  -d '{"problem_statement": "Should we invest in X?"}'
```

### 6.3 Closed Beta Testing Setup

1. **Set up PostgreSQL** (for audit trail):
   ```bash
   make setup  # Creates .env
   make build
   make up     # Starts postgres + redis + api
   ```

2. **Run migrations**:
   ```bash
   make shell
   alembic upgrade head
   ```

3. **Pre-populate 10 beta users** (SQL):
   ```sql
   INSERT INTO users (id, email, auth_provider, subscription_tier) VALUES
   ('user_alice', 'alice@betatesters.com', 'supabase', 'free'),
   ('user_bob', 'bob@betatesters.com', 'supabase', 'free'),
   -- ... 8 more
   ```

4. **Test with hardcoded mapping** (see Option 1 above)

5. **Track usage in audit logs**:
   ```bash
   SELECT user_id, action, resource_type, COUNT(*) as count
   FROM audit_log
   GROUP BY user_id, action, resource_type;
   ```

---

## 7. Production Readiness Roadmap

### 7.1 v2.0 - Full Supabase Integration

**Timeline**: Week 6-7 (planned)

**Steps**:

1. **Enable Supabase OAuth**:
   - Set `ENABLE_SUPABASE_AUTH=true`
   - Provide `SUPABASE_URL`, `SUPABASE_JWT_SECRET`, OAuth credentials
   - Auth middleware will validate JWT tokens instead of hardcoding

2. **Implement JWT Validation**:
   ```python
   # When ENABLE_SUPABASE_AUTH=true, this code runs:
   supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
   user_response = supabase.auth.get_user(token)

   return {
       "user_id": user_response.user.id,
       "email": user_response.user.email,
       "role": user_response.user.role or "authenticated",
       "subscription_tier": user_response.user.user_metadata.get("subscription_tier", "free"),
   }
   ```

3. **Enforce RLS Policies**:
   ```python
   # Before executing queries, set user context:
   await db.execute("SET app.current_user_id TO $1", [user_id])
   # Now all RLS policies will enforce user isolation
   ```

4. **User Registration Flow**:
   - Frontend: Supabase login UI (OAuth + email/password)
   - Backend: Auto-create `users` table entry on first login
   - Dashboard: User sees only own sessions

### 7.2 Supabase Auth Configuration

**File**: `/Users/si/projects/bo1/supabase/config/auth.yml`

Pre-configured settings:
```yaml
# JWT Configuration
jwt_secret: ${SUPABASE_JWT_SECRET}
jwt_exp: 3600  # Access token expiry (1 hour)

# Signup & Email
disable_signup: false
require_email_confirmation: false  # Set to true in production

# OAuth Providers
external:
  google:
    enabled: ${GOOGLE_OAUTH_ENABLED:-false}
    client_id: ${GOOGLE_OAUTH_CLIENT_ID}
    secret: ${GOOGLE_OAUTH_CLIENT_SECRET}

  linkedin:
    enabled: ${LINKEDIN_OAUTH_ENABLED:-false}
    client_id: ${LINKEDIN_OAUTH_CLIENT_ID}
    secret: ${LINKEDIN_OAUTH_CLIENT_SECRET}

  github:
    enabled: ${GITHUB_OAUTH_ENABLED:-false}
    client_id: ${GITHUB_OAUTH_CLIENT_ID}
    secret: ${GITHUB_OAUTH_CLIENT_SECRET}

# Rate Limiting
rate_limit_email_sent: 4  # Max emails per hour
rate_limit_token_refresh: 150  # Max token refreshes per hour
```

### 7.3 Security & Compliance (Planned)

**File**: `/Users/si/projects/bo1/zzz_project/detail/SECURITY_COMPLIANCE.md`

Comprehensive security guide including:

- **GDPR Compliance**:
  - User data export (`/api/v1/user/export`)
  - Account deletion with anonymization (`/api/v1/user/delete`)
  - 30-day grace period before hard deletion
  - 7-year audit log retention for compliance

- **Data Protection**:
  - Encryption at rest (AES-256 via PostgreSQL)
  - TLS 1.3 in transit
  - Row-level security (RLS) for multi-tenancy
  - Audit logging for all data access

- **Authentication**:
  - JWT tokens (1-hour expiry)
  - Refresh tokens (7-day expiry, httpOnly cookies)
  - Password hashing (bcrypt, 10 rounds)
  - Optional MFA (TOTP via authenticator app)

- **Authorization**:
  - Role-based access control (User, Admin, Support)
  - Ownership-based session control
  - Permission matrix for all actions

### 7.4 Key Files for Production

| File | Purpose |
|------|---------|
| `/backend/api/middleware/auth.py` | JWT validation & user extraction |
| `/backend/api/middleware/admin.py` | Admin API key validation |
| `/migrations/versions/ced8f3f148bb_initial_schema.py` | Database schema |
| `/migrations/versions/396e8f26d0a5_create_rls_policies.py` | RLS policies |
| `/backend/api/dependencies.py` | SessionManager with ownership checks |
| `/zzz_project/detail/SECURITY_COMPLIANCE.md` | GDPR & security compliance guide |
| `/supabase/config/auth.yml` | Supabase auth configuration |

---

## 8. Quick Reference

### 8.1 Enable Full Auth (v2+)

1. **Deploy Supabase**:
   ```bash
   docker run --name supabase-auth \
     -e SUPABASE_JWT_SECRET=$(openssl rand -base64 32) \
     -e SITE_URL=http://localhost:3000 \
     -p 9999:8000 \
     supabase/gotrue:latest
   ```

2. **Set environment variables**:
   ```bash
   ENABLE_SUPABASE_AUTH=true
   SUPABASE_URL=http://localhost:9999
   SUPABASE_ANON_KEY=eyJxxx...
   GOOGLE_OAUTH_CLIENT_ID=xxx.apps.googleusercontent.com
   GOOGLE_OAUTH_CLIENT_SECRET=xxx
   ```

3. **Restart API**:
   ```bash
   make up
   ```

### 8.2 Add Admin User

```bash
# Set in environment or .env
ADMIN_API_KEY=your_random_uuid_here
ADMIN_USER_IDS=alice,bob,charlie  # Comma-separated list
```

### 8.3 Test Auth Endpoints

```bash
# Without real auth (MVP mode)
curl -X GET http://localhost:8000/api/v1/sessions

# With admin key (any mode)
curl -X GET http://localhost:8000/api/admin/sessions/active \
  -H "X-Admin-Key: your_random_uuid_here"
```

### 8.4 Check Session Ownership

```python
# SessionManager.kill_session() enforces this:
# 1. Load session metadata from Redis
# 2. Check if metadata["user_id"] == current_user_id
# 3. If mismatch, raise PermissionError
# 4. Otherwise, kill the session
```

---

## 9. Summary Table

| Aspect | Current (MVP) | Future (v2+) |
|--------|---------------|--------------|
| **User Authentication** | Hardcoded `test_user_1` | Supabase OAuth (Google, LinkedIn, GitHub) + Email |
| **Admin Auth** | `X-Admin-Key` header | Same + Role-based access control |
| **Session Ownership** | Tracked in Redis metadata | Tracked in PostgreSQL + RLS enforced |
| **User Isolation** | Application-level (metadata checks) | Database-level (RLS policies) |
| **User Count** | 1 (shared) | Unlimited (per OAuth provider) |
| **Audit Trail** | Console logs | PostgreSQL `audit_log` table |
| **GDPR Compliance** | Not applicable (test data) | Full (RTBF, data export, anonymization) |
| **Rate Limiting** | None | Per-user tier-based |
| **MFA** | Not supported | Optional (TOTP) |

---

## 10. Recommended Next Steps for Closed Beta

1. **Verify Current Setup**:
   ```bash
   curl -X GET http://localhost:8000/api/v1/sessions -v
   # Should return 200 with sessions for test_user_1
   ```

2. **Optional: Implement User Mapping** (see Section 6.2):
   - Add hardcoded 10-user mapping
   - Extract user from header or query param
   - Track usage in PostgreSQL

3. **Enable PostgreSQL Tracking**:
   ```bash
   make up  # Starts PostgreSQL
   alembic upgrade head  # Run migrations
   ```

4. **Monitor Admin Panel**:
   ```bash
   curl -X GET http://localhost:8000/api/admin/sessions/active \
     -H "X-Admin-Key: $ADMIN_API_KEY"
   ```

5. **When Ready for v2+**:
   - Set `ENABLE_SUPABASE_AUTH=true`
   - Deploy Supabase auth server
   - Update OAuth provider credentials
   - Frontend implements Supabase login UI

---

**For questions or implementation details, refer to**:
- Auth middleware: `/Users/si/projects/bo1/backend/api/middleware/auth.py`
- Security guide: `/Users/si/projects/bo1/zzz_project/detail/SECURITY_COMPLIANCE.md`
- Session management: `/Users/si/projects/bo1/bo1/graph/execution.py`
- Database schema: `/Users/si/projects/bo1/migrations/versions/ced8f3f148bb_initial_schema.py`
