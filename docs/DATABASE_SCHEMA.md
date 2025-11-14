# Database Schema Documentation

**Database**: PostgreSQL 15+ with pgvector extension
**Migration Tool**: Alembic
**Status**: Week 3.5 Complete

---

## Schema Overview

The database schema supports multi-tenant SaaS with user isolation via Row Level Security (RLS).

### Tables

1. **users** - User accounts and subscription information
2. **personas** - Static persona data (45 experts, seeded from personas.json)
3. **sessions** - Deliberation sessions (problems being solved)
4. **contributions** - Persona deliberation contributions
5. **votes** - Persona votes on final recommendations
6. **audit_log** - Compliance and security audit trail

---

## Table Schemas

### `users`

User accounts with authentication and subscription tracking.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | VARCHAR(255) | PRIMARY KEY | User ID (from Supabase Auth) |
| `email` | VARCHAR(255) | NOT NULL, UNIQUE | User email address |
| `auth_provider` | VARCHAR(50) | NOT NULL | Auth provider (supabase, google, linkedin, github) |
| `subscription_tier` | VARCHAR(50) | NOT NULL, DEFAULT 'free' | Subscription tier (free, pro, enterprise) |
| `gdpr_consent_at` | TIMESTAMP WITH TIME ZONE | NULL | GDPR consent timestamp |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Account creation timestamp |
| `updated_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Last update timestamp |

**RLS**: No RLS (users managed by Supabase Auth)

---

### `personas`

Static persona definitions (seeded from `bo1/data/personas.json`).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Internal ID |
| `code` | VARCHAR(50) | NOT NULL, UNIQUE | Unique persona code (e.g., "growth_hacker") |
| `name` | VARCHAR(255) | NOT NULL | Persona name (e.g., "Zara Morales") |
| `expertise` | VARCHAR(500) | NOT NULL | Persona description/expertise |
| `system_prompt` | TEXT | NOT NULL | LLM system prompt |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Seed timestamp |

**RLS**: No RLS (public read-only data)

**Seed Command**: `python scripts/seed_personas.py`

---

### `sessions`

Deliberation sessions (problems being solved by AI personas).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | VARCHAR(255) | PRIMARY KEY | Session UUID |
| `user_id` | VARCHAR(255) | NOT NULL, FK(users.id) CASCADE | Session owner |
| `problem_statement` | TEXT | NOT NULL | User's problem description |
| `problem_context` | JSON | NULL | Additional problem context |
| `status` | VARCHAR(50) | NOT NULL, DEFAULT 'active' | Status (active, paused, completed, failed, killed) |
| `phase` | VARCHAR(50) | NOT NULL, DEFAULT 'problem_decomposition' | Current phase |
| `total_cost` | NUMERIC(10,4) | NOT NULL, DEFAULT 0.0 | Total LLM cost (USD) |
| `total_tokens` | INTEGER | NOT NULL, DEFAULT 0 | Total tokens used |
| `round_number` | INTEGER | NOT NULL, DEFAULT 0 | Current round number |
| `max_rounds` | INTEGER | NOT NULL, DEFAULT 10 | Maximum rounds allowed |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Session start time |
| `updated_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Last update time |
| `completed_at` | TIMESTAMP WITH TIME ZONE | NULL | Completion timestamp |
| `killed_at` | TIMESTAMP WITH TIME ZONE | NULL | Kill timestamp |
| `killed_by` | VARCHAR(255) | NULL | User ID or 'admin' |
| `kill_reason` | VARCHAR(500) | NULL | Reason for termination |

**Indexes**:
- `idx_sessions_user_id` ON `user_id`
- `idx_sessions_status` ON `status`
- `idx_sessions_created_at` ON `created_at`

**RLS**: Users can only access their own sessions
**Policy**: `user_id = current_setting('app.current_user_id')`

---

### `contributions`

Persona deliberation contributions (messages from AI experts).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Internal ID |
| `session_id` | VARCHAR(255) | NOT NULL, FK(sessions.id) CASCADE | Session reference |
| `persona_code` | VARCHAR(50) | NOT NULL, FK(personas.code) | Persona who contributed |
| `content` | TEXT | NOT NULL | Contribution text |
| `round_number` | INTEGER | NOT NULL | Deliberation round number |
| `phase` | VARCHAR(50) | NOT NULL | Phase (initial_round, deliberation, moderator_intervention) |
| `cost` | NUMERIC(10,4) | NOT NULL, DEFAULT 0.0 | LLM cost for this contribution (USD) |
| `tokens` | INTEGER | NOT NULL, DEFAULT 0 | Tokens used |
| `model` | VARCHAR(100) | NOT NULL | LLM model used |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Contribution timestamp |

**Indexes**:
- `idx_contributions_session_id` ON `session_id`
- `idx_contributions_round_number` ON `round_number`

**RLS**: Users can only see contributions from their own sessions
**Policy**: `session_id IN (SELECT id FROM sessions WHERE user_id = current_setting('app.current_user_id'))`

---

### `votes`

Persona votes on final recommendations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Internal ID |
| `session_id` | VARCHAR(255) | NOT NULL, FK(sessions.id) CASCADE | Session reference |
| `persona_code` | VARCHAR(50) | NOT NULL, FK(personas.code) | Persona who voted |
| `vote_choice` | VARCHAR(100) | NOT NULL | Vote choice (sub-problem ID or option) |
| `reasoning` | TEXT | NOT NULL | Vote reasoning |
| `confidence` | NUMERIC(3,2) | NULL | Confidence score (0.0 to 1.0) |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Vote timestamp |

**Indexes**:
- `idx_votes_session_id` ON `session_id`

**RLS**: Users can only see votes from their own sessions
**Policy**: `session_id IN (SELECT id FROM sessions WHERE user_id = current_setting('app.current_user_id'))`

---

### `audit_log`

Compliance and security audit trail (GDPR, session kills, logins).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Internal ID |
| `user_id` | VARCHAR(255) | NULL, FK(users.id) SET NULL | User who performed action |
| `action` | VARCHAR(100) | NOT NULL | Action type (session_created, session_killed, user_login, etc.) |
| `resource_type` | VARCHAR(50) | NOT NULL | Resource type (session, user, persona) |
| `resource_id` | VARCHAR(255) | NULL | Resource ID |
| `details` | JSON | NULL | Additional details |
| `ip_address` | VARCHAR(45) | NULL | IP address (IPv6 support) |
| `user_agent` | VARCHAR(500) | NULL | User agent string |
| `timestamp` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Action timestamp |

**Indexes**:
- `idx_audit_log_user_id` ON `user_id`
- `idx_audit_log_timestamp` ON `timestamp`
- `idx_audit_log_resource` ON `resource_type, resource_id`

**RLS**: Users can only see their own audit logs (admins bypass RLS)
**Policy**: `user_id = current_setting('app.current_user_id')`

---

## Row Level Security (RLS)

All user-facing tables have RLS enabled to enforce multi-tenancy.

### How RLS Works

1. Application sets `app.current_user_id` session variable when user authenticates
2. PostgreSQL enforces RLS policies on all queries
3. Users can only see/modify their own data
4. Admin queries use service role (bypasses RLS)

### RLS Policies

| Table | Policy Name | Rule |
|-------|-------------|------|
| `sessions` | `sessions_user_isolation` | `user_id = current_setting('app.current_user_id')` |
| `contributions` | `contributions_user_isolation` | Session belongs to user |
| `votes` | `votes_user_isolation` | Session belongs to user |
| `audit_log` | `audit_log_user_isolation` | `user_id = current_setting('app.current_user_id')` |

---

## Migrations

### Running Migrations

```bash
# Upgrade to latest schema
alembic upgrade head

# Downgrade one migration
alembic downgrade -1

# Check current version
alembic current

# Show migration history
alembic history
```

### Creating Migrations

```bash
# Create new migration
alembic revision -m "description"

# Auto-generate from models (future)
alembic revision --autogenerate -m "description"
```

### Migration Files

- **001_initial_schema** (`ced8f3f148bb`): Creates all tables, indexes, enables RLS
- **002_create_rls_policies** (`396e8f26d0a5`): Creates RLS policies for multi-tenancy

---

## Database Setup (Day 21)

1. **Install PostgreSQL 15+ with pgvector**:
   ```bash
   docker-compose up -d postgres
   ```

2. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

3. **Seed personas**:
   ```bash
   python scripts/seed_personas.py
   ```

4. **Verify**:
   ```bash
   docker exec bo1-postgres psql -U bo1 -d boardofone -c "\dt"
   ```

---

## Database Connection

**Local Development**:
```
DATABASE_URL=postgresql://bo1:bo1_dev_password@localhost:5432/boardofone
```

**Docker Container**:
```
DATABASE_URL=postgresql://bo1:bo1_dev_password@postgres:5432/boardofone
```

**Production** (Week 13):
```
DATABASE_URL=postgresql://bo1:STRONG_PASSWORD@hostname:5432/boardofone
```

---

## Future Enhancements

- **Week 4**: Add LangGraph-specific tables (checkpoints)
- **Week 6**: Add user sessions table (web authentication)
- **Week 8**: Add payments table (Stripe subscriptions)
- **Week 10**: Add analytics views (cost breakdowns, session metrics)
- **Week 12**: Add email templates table (Resend integration)
