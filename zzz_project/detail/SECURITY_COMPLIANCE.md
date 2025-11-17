# Board of One - Security & Compliance
**GDPR, Data Privacy, Security Architecture**

**Version**: 1.0
**Date**: 2025-11-14
**Status**: Security Design
**Compliance**: GDPR, CCPA, SOC 2 (future)

---

## Table of Contents

1. [Security Overview](#1-security-overview)
2. [GDPR Compliance](#2-gdpr-compliance)
3. [Right to be Forgotten (RTBF)](#3-right-to-be-forgotten-rtbf)
4. [Data Classification & Handling](#4-data-classification--handling)
5. [Authentication Security](#5-authentication-security)
6. [Authorization & Access Control](#6-authorization--access-control)
7. [Data Encryption](#7-data-encryption)
8. [API Security](#8-api-security)
9. [Secrets Management](#9-secrets-management)
10. [Incident Response](#10-incident-response)
11. [Compliance Checklist](#11-compliance-checklist)

---

## 1. Security Overview

### 1.1 Security Principles

**Defense in Depth**:
- Multiple layers of security controls
- No single point of failure
- Fail securely (deny by default)

**Principle of Least Privilege**:
- Users/services only get minimum required permissions
- Time-limited access tokens
- Regular permission audits

**Data Minimization** (GDPR Art. 5):
- Collect only necessary data
- Pseudonymize where possible
- Automatic data expiry

**Transparency**:
- Clear privacy policy
- User-accessible data export
- Audit logs for all data access

### 1.2 Threat Model

**Threats**:
1. **Unauthorized Access**: Attacker gains user account access
2. **Data Breach**: Database compromised, PII exposed
3. **API Abuse**: Rate limit bypass, scraping, DDoS
4. **Insider Threat**: Malicious admin/employee access
5. **Supply Chain**: Compromised dependencies
6. **Social Engineering**: Phishing, account takeover

**Mitigations** (detailed in sections below):
- Multi-factor authentication (MFA)
- Encryption at rest and in transit
- Rate limiting and WAF
- Audit logging with alerting
- Dependency scanning (Dependabot, Snyk)
- Security awareness training

---

## 2. GDPR Compliance

### 2.1 Legal Basis for Processing

**Lawful Basis** (GDPR Art. 6):
- **Contract Performance** (Art. 6(1)(b)): Processing necessary to provide deliberation service
- **Consent** (Art. 6(1)(a)): Marketing emails, analytics cookies
- **Legitimate Interest** (Art. 6(1)(f)): Fraud prevention, security monitoring

**Special Categories** (GDPR Art. 9):
- Bo1 does NOT process special category data (health, biometric, political, etc.)
- If user inputs sensitive data in problem statement → Automatic anonymization on account closure

### 2.2 Data Controller vs Processor

**Bo1 = Data Controller**:
- Determines purposes and means of processing
- Responsible for GDPR compliance
- Liable for data breaches

**Data Processors** (third-party services):
- **Supabase**: Auth provider (DPA required)
- **Anthropic**: LLM provider (DPA required, data not retained per their policy)
- **Stripe**: Payment processor (GDPR-compliant, PCI-DSS certified)
- **Sentry**: Error tracking (DPA required, PII scrubbing enabled)

**Data Processing Agreements (DPA)**: Required for all processors (already provided by Supabase, Anthropic, Stripe, Sentry)

### 2.3 User Rights (GDPR Chapter 3)

| Right | Implementation | Endpoint | Timeline |
|-------|---------------|----------|----------|
| **Right to Access (Art. 15)** | User can download all their data (JSON export) | `/api/v1/user/export` | 30 days |
| **Right to Rectification (Art. 16)** | User can edit profile, email | `/api/v1/user/profile` | Immediate |
| **Right to Erasure (Art. 17)** | Account deletion → Anonymization (not hard delete) | `/api/v1/user/delete` | 30 days |
| **Right to Restrict Processing (Art. 18)** | User can pause account (no new sessions) | `/api/v1/user/pause` | Immediate |
| **Right to Data Portability (Art. 20)** | Export in machine-readable format (JSON) | `/api/v1/user/export` | 30 days |
| **Right to Object (Art. 21)** | Opt-out of marketing, analytics | `/settings/privacy` | Immediate |

### 2.4 Privacy by Design (GDPR Art. 25)

**Built-in Protections**:
- ✅ **Pseudonymization**: User IDs are UUIDs (not sequential, not email-based)
- ✅ **Encryption**: TLS 1.3 in transit, AES-256 at rest
- ✅ **Data Minimization**: No tracking pixels, minimal analytics
- ✅ **Access Controls**: Row-level security (RLS) in PostgreSQL
- ✅ **Audit Logs**: All data access logged (GDPR Art. 30)

**Default Settings**:
- Analytics cookies: **Opt-in** (not opt-out)
- Marketing emails: **Opt-in**
- Data retention: **365 days** (configurable by user)

### 2.5 Privacy Policy & Notices

**Required Disclosures** (GDPR Art. 13):
- Identity of data controller (Board of One, Inc.)
- Contact details of Data Protection Officer (DPO) - Required if >250 employees or high-risk processing
- Purposes of processing (provide deliberation service)
- Legal basis (contract, consent)
- Data retention periods (365 days default, 7 years for audit logs)
- User rights (access, erasure, portability, etc.)
- Right to lodge complaint with supervisory authority (e.g., ICO in UK)

**Cookie Consent** (ePrivacy Directive):
- Banner on first visit (opt-in for non-essential cookies)
- Categories: Strictly necessary (auth), Analytics (opt-in), Marketing (opt-in)
- Tool: Cookiebot or custom implementation

**Privacy Policy URL**: `/privacy-policy`
**Terms of Service URL**: `/terms-of-service`

### 2.6 Data Breach Notification (GDPR Art. 33-34)

**Timeline**:
- **72 hours** to notify supervisory authority (e.g., ICO)
- **Without undue delay** to notify affected users (if high risk)

**Breach Response Plan** (see Section 10: Incident Response)

---

## 3. Right to be Forgotten (RTBF)

### 3.1 Anonymization Strategy

**Principle**: Never hard-delete data, obfuscate PII instead.

**Why Not Hard Delete?**
- Preserve referential integrity (foreign keys)
- Keep aggregate analytics (anonymized)
- Comply with legal retention (audit logs: 7 years)
- Maintain service quality (avoid breaking historical sessions)

**Anonymization = GDPR-compliant "Deletion"**:
- GDPR Art. 17 allows retention if "no longer possible to identify the data subject"
- Anonymized data is NOT personal data (GDPR Recital 26)

### 3.2 Anonymization Process

**Triggered By**:
1. User requests account deletion (`/api/v1/user/delete`)
2. Inactive user auto-cleanup (365 days no login + 30-day grace period)
3. Admin-initiated (support request)

**Step-by-Step**:

```sql
-- 1. Mark user as anonymized
UPDATE users SET
  email = 'anonymized_' || id || '@deleted.local',
  supabase_user_id = NULL, -- Unlink from auth
  anonymized_at = NOW(),
  anonymization_reason = 'user_request', -- or 'auto_cleanup', 'admin_request'
  gdpr_consent_at = NULL,
  stripe_customer_id = NULL, -- Cancel subscription separately
  stripe_subscription_id = NULL
WHERE id = $user_id;

-- 2. Anonymize sessions (problem statements contain PII)
UPDATE sessions SET
  problem_statement = '[REDACTED - Account deleted]',
  problem_context = '{}', -- Remove all context (budget, timeline, etc.)
  anonymized_at = NOW()
WHERE user_id = $user_id;

-- 3. Anonymize contributions (user inputs may contain PII)
UPDATE contributions SET
  content = '[Content redacted due to account deletion]',
  thinking = NULL -- Remove internal reasoning
WHERE session_id IN (SELECT id FROM sessions WHERE user_id = $user_id);

-- 4. Anonymize synthesis reports (may reference user-specific data)
UPDATE synthesis_reports SET
  executive_summary = '[Report redacted due to account deletion]',
  key_insights = '[Redacted]',
  dissenting_views = NULL,
  conditions = '{}',
  next_steps = '[Redacted]',
  full_report = '[Full report redacted due to account deletion]'
WHERE session_id IN (SELECT id FROM sessions WHERE user_id = $user_id);

-- 5. Nullify user_id in audit logs (keep event data for compliance)
UPDATE audit_log SET
  user_id = NULL,
  ip_address = NULL, -- Remove IP after anonymization
  user_agent = NULL  -- Remove user agent
WHERE user_id = $user_id;

-- 6. Delete Supabase auth record (separate API call)
-- This happens via Supabase Admin API
await supabase.auth.admin.deleteUser(supabase_user_id);

-- 7. Cancel Stripe subscription (if active)
if (stripe_subscription_id) {
  await stripe.subscriptions.cancel(stripe_subscription_id);
  await stripe.customers.delete(stripe_customer_id);
}

-- 8. Log anonymization event (new audit log entry)
INSERT INTO audit_log (user_id, event_type, event_data) VALUES (
  NULL, -- User ID already nulled
  'user_anonymized',
  jsonb_build_object(
    'anonymized_user_id', $user_id,
    'reason', 'user_request',
    'timestamp', NOW(),
    'sessions_affected', (SELECT COUNT(*) FROM sessions WHERE user_id = $user_id)
  )
);
```

**What Remains** (Anonymized, Non-PII):
- Session count (aggregate analytics)
- Deliberation durations (performance metrics)
- Persona usage stats (e.g., "Zara used in 1000 sessions")
- Cost metrics (aggregate, not user-attributable)
- Audit log events (without user_id, IP, user agent)

**What is Deleted** (PII):
- Email address → `anonymized_{uuid}@deleted.local`
- Problem statements → `[REDACTED]`
- User inputs (context, contributions) → `[REDACTED]`
- Supabase auth record → Deleted
- Stripe customer → Deleted

### 3.3 User-Initiated Deletion Flow

**Frontend**:
```typescript
// src/routes/settings/account/+page.svelte
async function deleteAccount() {
  const confirmed = confirm(
    "Are you sure? This will permanently delete your account and all data. " +
    "This action cannot be undone."
  );

  if (!confirmed) return;

  // Second confirmation (enter email)
  const email = prompt("Type your email to confirm:");
  if (email !== user.email) {
    alert("Email does not match. Deletion canceled.");
    return;
  }

  try {
    await fetch('/api/v1/user/delete', { method: 'DELETE' });
    alert("Account deletion scheduled. You will receive a confirmation email.");
    await supabase.auth.signOut();
    goto('/');
  } catch (err) {
    alert("Failed to delete account. Please contact support.");
  }
}
```

**Backend**:
```typescript
// src/routes/api/v1/user/delete/+server.ts
export const DELETE = async ({ locals }) => {
  const user = requireAuth({ locals });

  // Schedule anonymization (async job)
  await anonymizationQueue.add({
    user_id: user.id,
    reason: 'user_request',
    requested_at: new Date()
  });

  // Send confirmation email
  await sendEmail(user.email, 'Account deletion confirmation', {
    message: 'Your account will be anonymized within 30 days. You can cancel by logging in.'
  });

  // Log event
  await logAuditEvent({
    user_id: user.id,
    event_type: 'deletion_requested',
    event_data: { reason: 'user_request' }
  });

  return json({ status: 'scheduled', eta_days: 30 });
};
```

**Grace Period** (30 days):
- User can cancel deletion by logging in (before anonymization runs)
- If user logs in during grace period → Cancel anonymization job
- After 30 days → Irreversible anonymization

### 3.4 Data Retention Lifecycle

```
User Account Created
  ↓
Active Use (indefinite)
  ↓
Last Login
  ↓
+365 days → Email warning: "Account inactive"
  ↓
+30 days → Email final notice: "Account will be anonymized in 30 days"
  ↓
+30 days → Automatic anonymization
  ↓
Anonymized State (indefinite retention for analytics)
```

**User Can Extend Retention**:
- Settings → Privacy → Data Retention: 365 days (default), 730 days, Indefinite

---

## 4. Data Classification & Handling

### 4.1 Data Categories

| Category | Examples | Storage | Encryption | Retention |
|----------|----------|---------|------------|-----------|
| **PII (Personally Identifiable)** | Email, name (if provided) | PostgreSQL | AES-256 at rest | Until anonymization |
| **Sensitive User Input** | Problem statements, context | PostgreSQL | AES-256 at rest | Until anonymization |
| **Session Metadata** | Session ID, timestamps, status | PostgreSQL | AES-256 at rest | Anonymized after user deletion |
| **LLM Responses** | Contributions, votes, synthesis | PostgreSQL | AES-256 at rest | Anonymized after user deletion |
| **Payment Data** | Stripe customer ID (not card numbers) | PostgreSQL | AES-256 at rest | Deleted on anonymization |
| **Audit Logs** | User actions, IP addresses | PostgreSQL | AES-256 at rest | 7 years (compliance), then deleted |
| **Analytics** | Aggregate session counts, durations | PostgreSQL | AES-256 at rest | Indefinite (anonymized) |

**No Credit Card Storage**:
- All payment details handled by Stripe (PCI-DSS compliant)
- Bo1 only stores `stripe_customer_id` and `stripe_subscription_id` (non-sensitive tokens)

### 4.2 Data Flow Map

```
User Input (Browser)
  ↓ HTTPS (TLS 1.3)
SvelteKit Server
  ↓ PostgreSQL connection (SSL)
PostgreSQL Database (encrypted at rest)
  ↓ Background job
LLM API (Anthropic)
  ↓ Anthropic policy: No retention beyond processing
(Response not stored by Anthropic)
  ↓ HTTPS
SvelteKit Server
  ↓ Save to PostgreSQL
PostgreSQL Database
  ↓ HTTPS
User Browser
```

**Third-Party Data Sharing**:
- **Anthropic**: Problem statement, contributions (ephemeral, not retained)
- **Voyage AI**: Contributions for embeddings (ephemeral, not retained)
- **Stripe**: Email, customer ID (GDPR-compliant processor)
- **Sentry**: Error logs (PII scrubbed before sending)

**No Data Sharing With**:
- Advertisers (no ads)
- Data brokers (no data sales)
- Analytics providers beyond essential (Plausible/Fathom, privacy-focused)

---

## 5. Authentication Security

### 5.1 Supabase Auth Configuration

**Providers**:
- Google OAuth 2.0
- LinkedIn OAuth 2.0
- GitHub OAuth 2.0
- Email/Password (fallback)

**Security Settings**:
```typescript
// Supabase Dashboard → Authentication → Settings
{
  "DISABLE_SIGNUP": false, // Allow new signups
  "SITE_URL": "https://app.boardof.one",
  "EXTERNAL_EMAIL_ENABLED": true,
  "MAILER_AUTOCONFIRM": false, // Require email confirmation
  "SECURITY_CAPTCHA_ENABLED": true, // Prevent bot signups (hCaptcha)
  "PASSWORD_MIN_LENGTH": 12,
  "PASSWORD_REQUIRED_CHARACTERS": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*",
  "JWT_EXP": 3600, // 1 hour token expiry
  "REFRESH_TOKEN_ROTATION_ENABLED": true,
  "SECURITY_REFRESH_TOKEN_REUSE_INTERVAL": 10 // seconds
}
```

**Email Confirmation Flow**:
1. User signs up → Supabase sends confirmation email
2. User clicks link → Email verified
3. User redirected to `/auth/callback?type=signup`
4. SvelteKit creates user record in `users` table

**Rate Limiting** (Supabase built-in):
- Max 5 login attempts per 5 minutes per IP
- Max 3 password reset requests per hour per email

### 5.2 Multi-Factor Authentication (MFA)

**Status**: v2 feature (post-MVP)

**Implementation** (Supabase MFA):
```typescript
// Enable TOTP MFA
const { data, error } = await supabase.auth.mfa.enroll({
  factorType: 'totp'
});

// User scans QR code with authenticator app (Google Authenticator, Authy)

// Verify TOTP code
await supabase.auth.mfa.challengeAndVerify({
  factorId: data.id,
  code: '123456' // User enters from app
});
```

**Enforcement**:
- Optional for Free tier
- Recommended for Pro tier
- Required for Enterprise tier

### 5.3 Session Management

**JWT Tokens**:
- **Access Token**: Short-lived (1 hour), contains user claims
- **Refresh Token**: Long-lived (7 days), httpOnly cookie

**Token Storage**:
```typescript
// Server-side only (httpOnly cookies)
cookies.set('sb-access-token', accessToken, {
  path: '/',
  httpOnly: true,
  secure: true, // HTTPS only
  sameSite: 'lax', // CSRF protection
  maxAge: 60 * 60 // 1 hour
});

cookies.set('sb-refresh-token', refreshToken, {
  path: '/',
  httpOnly: true,
  secure: true,
  sameSite: 'lax',
  maxAge: 60 * 60 * 24 * 7 // 7 days
});
```

**Token Refresh** (automatic):
```typescript
// src/hooks.server.ts
export const handle = async ({ event, resolve }) => {
  const accessToken = event.cookies.get('sb-access-token');
  const refreshToken = event.cookies.get('sb-refresh-token');

  if (!accessToken && refreshToken) {
    // Access token expired, refresh it
    const { data, error } = await supabase.auth.refreshSession({ refreshToken });
    if (data.session) {
      // Update cookies
      event.cookies.set('sb-access-token', data.session.access_token, { ... });
      event.locals.user = data.session.user;
    }
  }

  return resolve(event);
};
```

**Session Revocation**:
- User logout → Delete cookies, revoke Supabase session
- Password change → Revoke all sessions (re-login required)
- Account suspension → Admin revokes all sessions

### 5.4 Password Security

**Requirements**:
- Minimum 12 characters
- Must include: uppercase, lowercase, number, symbol
- No common passwords (checked against breached password list)

**Hashing** (Supabase default):
- bcrypt with 10 rounds
- Salted per-user

**Password Reset**:
1. User clicks "Forgot Password" → Enters email
2. Supabase sends password reset link (valid 1 hour)
3. User clicks link → Redirected to `/reset-password?token=xxx`
4. User enters new password → Supabase updates hash
5. All sessions revoked (re-login required)

---

## 6. Authorization & Access Control

### 6.1 Row-Level Security (RLS)

**PostgreSQL RLS Policies**:
```sql
-- Users can only see their own sessions
CREATE POLICY "users_own_sessions" ON sessions
  FOR SELECT
  USING (auth.uid() = (SELECT supabase_user_id FROM users WHERE id = sessions.user_id));

-- Users can only create sessions for themselves
CREATE POLICY "users_create_own_sessions" ON sessions
  FOR INSERT
  WITH CHECK (auth.uid() = (SELECT supabase_user_id FROM users WHERE id = sessions.user_id));

-- Users can only update their own sessions
CREATE POLICY "users_update_own_sessions" ON sessions
  FOR UPDATE
  USING (auth.uid() = (SELECT supabase_user_id FROM users WHERE id = sessions.user_id));

-- Users CANNOT delete sessions (only admins via direct SQL)
-- No DELETE policy = DELETE disallowed for all users

-- Admin bypass (for console mode)
ALTER TABLE sessions FORCE ROW LEVEL SECURITY; -- Enforce RLS even for table owner
-- Admin uses service role key (bypasses RLS) for direct access
```

**Supabase Service Role** (admin-only):
- Used by console mode / admin API
- Bypasses all RLS policies
- **Never exposed to client** (server-side only)

### 6.2 Role-Based Access Control (RBAC)

**Roles**:
- **User** (default): Create sessions, view own data, export data
- **Admin** (console mode): Full access, view all data, cost metrics, debug logs
- **Support** (future): View user data (with consent), assist with issues

**Permission Matrix**:

| Action | User | Admin | Support |
|--------|------|-------|---------|
| Create session | ✅ (own) | ✅ (any) | ❌ |
| View session | ✅ (own) | ✅ (any) | ✅ (with consent) |
| Delete session | ❌ | ✅ | ❌ |
| View cost metrics | ❌ | ✅ | ❌ |
| Export user data | ✅ (own) | ✅ (any) | ✅ (with consent) |
| Anonymize user | ✅ (own) | ✅ (any) | ❌ |
| View audit logs | ❌ | ✅ | ❌ |

### 6.3 API Authorization

**Middleware** (SvelteKit):
```typescript
// src/lib/auth/middleware.ts
export function requireAuth(event: RequestEvent) {
  if (!event.locals.user) {
    throw redirect(303, '/login');
  }
  return event.locals.dbUser;
}

export function requireTier(minTier: 'free' | 'pro' | 'enterprise') {
  return (event: RequestEvent) => {
    const user = requireAuth(event);
    const tierOrder = ['free', 'pro', 'enterprise'];
    if (tierOrder.indexOf(user.subscription_tier) < tierOrder.indexOf(minTier)) {
      throw error(403, 'Upgrade required');
    }
    return user;
  };
}

export function requireAdmin(event: RequestEvent) {
  // Admin check: Only allow from localhost/VPN (console mode)
  if (!event.request.headers.get('x-admin-key') === process.env.ADMIN_API_KEY) {
    throw error(403, 'Admin access required');
  }
}
```

**Usage**:
```typescript
// User endpoint
export const GET = async ({ locals }) => {
  const user = requireAuth({ locals });
  // ... user can only access own data (RLS enforced)
};

// Pro-tier endpoint
export const POST = async ({ locals }) => {
  const user = requireTier('pro')({ locals });
  // ... feature available to pro+ users
};

// Admin endpoint
export const GET = async ({ request }) => {
  requireAdmin({ request });
  // ... unrestricted access to all data
};
```

---

## 7. Data Encryption

### 7.1 Encryption in Transit

**TLS 1.3** (All connections):
- Client ↔ Traefik: TLS 1.3 (Let's Encrypt certificate)
- Traefik ↔ SvelteKit: TLS 1.2+ (internal, optional for localhost)
- SvelteKit ↔ PostgreSQL: SSL/TLS (required, `sslmode=require`)
- SvelteKit ↔ Redis: TLS (optional, recommended for production)
- SvelteKit ↔ Anthropic API: HTTPS (TLS 1.2+)
- SvelteKit ↔ Supabase: HTTPS (TLS 1.2+)

**Certificate Management**:
- Automatic renewal via Let's Encrypt (Traefik ACME)
- Wildcard certificate for subdomains (*.boardof.one)
- HSTS header: `Strict-Transport-Security: max-age=31536000; includeSubDomains`

### 7.2 Encryption at Rest

**PostgreSQL** (transparent data encryption):
```bash
# Enable encryption at rest (cloud provider managed)
# AWS RDS: Enable encryption on instance creation
# Render/Railway: Encryption enabled by default

# Self-hosted: Use LUKS or dm-crypt for disk encryption
cryptsetup luksFormat /dev/sdb
cryptsetup luksOpen /dev/sdb postgres_data
mkfs.ext4 /dev/mapper/postgres_data
mount /dev/mapper/postgres_data /var/lib/postgresql/data
```

**Application-Level Encryption** (for sensitive fields):
```sql
-- pgcrypto extension (optional, if extra encryption needed)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypt email before storing (if not using managed encryption)
INSERT INTO users (email_encrypted) VALUES (
  pgp_sym_encrypt('user@example.com', 'encryption_key')
);

-- Decrypt on read
SELECT pgp_sym_decrypt(email_encrypted, 'encryption_key') AS email FROM users;
```

**Note**: For most use cases, cloud provider encryption (AWS RDS, Render, Railway) is sufficient. Application-level encryption adds complexity and is only needed for extra-sensitive data.

### 7.3 Encryption Keys

**Key Management**:
- **Symmetric Keys** (AES-256): For data at rest (managed by cloud provider)
- **Asymmetric Keys** (RSA 2048): For JWT signing (Supabase managed)

**Key Rotation**:
- Database encryption keys: Rotated annually (cloud provider)
- JWT signing keys: Rotated quarterly (Supabase)
- API keys: Rotated on compromise or quarterly

**Storage**:
- **Production**: AWS Secrets Manager or Doppler
- **Development**: `.env` file (gitignored)

---

## 8. API Security

### 8.1 Rate Limiting

**Per-User Limits** (enforced by tier):
```typescript
// src/lib/ratelimit.ts
const limits = {
  free: {
    sessions_per_month: 5,
    requests_per_minute: 10,
    requests_per_day: 100
  },
  pro: {
    sessions_per_month: 50,
    requests_per_minute: 30,
    requests_per_day: 1000
  },
  enterprise: {
    sessions_per_month: -1, // Unlimited
    requests_per_minute: 100,
    requests_per_day: 10000
  }
};

export async function checkRateLimit(userId: string, tier: string, action: string) {
  const key = `ratelimit:${userId}:${action}`;
  const limit = limits[tier][`${action}_per_minute`];

  const count = await redis.incr(key);
  await redis.expire(key, 60); // 1 minute window

  if (count > limit) {
    throw error(429, 'Rate limit exceeded. Please try again later.');
  }
}
```

**Per-IP Limits** (DDoS protection):
```yaml
# Traefik rate limit (per IP)
http:
  middlewares:
    ratelimit-ip:
      rateLimit:
        average: 100 # requests per second
        burst: 200
```

### 8.2 Input Validation

**Zod Schemas** (SvelteKit):
```typescript
// src/lib/schemas.ts
import { z } from 'zod';

export const createSessionSchema = z.object({
  problem_statement: z.string().min(50).max(5000),
  problem_context: z.object({
    budget: z.number().optional(),
    timeline: z.string().optional(),
    constraints: z.array(z.string()).optional()
  }).optional()
});

// Usage in endpoint
export const POST = async ({ request, locals }) => {
  const user = requireAuth({ locals });
  const body = await request.json();

  const validated = createSessionSchema.parse(body); // Throws if invalid

  // ... proceed with validated data
};
```

**SQL Injection Prevention**:
- ✅ **Parameterized Queries** (always use `$1, $2` placeholders)
- ❌ **String Concatenation** (never do this)

```typescript
// ✅ SAFE
const result = await db.query('SELECT * FROM users WHERE email = $1', [email]);

// ❌ UNSAFE (vulnerable to SQL injection)
const result = await db.query(`SELECT * FROM users WHERE email = '${email}'`);
```

**XSS Prevention**:
- ✅ Svelte auto-escapes all HTML by default
- ✅ Use `{@html}` only for sanitized markdown (via `marked` + `DOMPurify`)

```svelte
<!-- ✅ SAFE (auto-escaped) -->
<p>{userInput}</p>

<!-- ⚠️ USE WITH CAUTION (only for sanitized HTML) -->
<div>{@html sanitizedMarkdown}</div>
```

### 8.3 CORS Policy

**Allowed Origins** (production):
```typescript
// src/hooks.server.ts
const allowedOrigins = [
  'https://app.boardof.one',
  'https://www.boardof.one'
];

export const handle = async ({ event, resolve }) => {
  const origin = event.request.headers.get('origin');

  if (origin && allowedOrigins.includes(origin)) {
    return resolve(event, {
      headers: {
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Credentials': 'true'
      }
    });
  }

  return resolve(event);
};
```

**Development**:
```typescript
// Allow localhost in dev
const allowedOrigins = process.env.NODE_ENV === 'development'
  ? ['http://localhost:5173', 'http://localhost:3000']
  : ['https://app.boardof.one'];
```

### 8.4 CSRF Protection

**SameSite Cookies**:
```typescript
cookies.set('sb-access-token', token, {
  sameSite: 'lax', // Prevents CSRF (cookies not sent on cross-site POST)
  httpOnly: true,
  secure: true
});
```

**CSRF Tokens** (for state-changing requests):
```typescript
// Generate CSRF token
const csrfToken = crypto.randomUUID();
cookies.set('csrf-token', csrfToken, { httpOnly: false }); // Readable by JS

// Validate on POST
export const POST = async ({ request, cookies }) => {
  const csrfFromHeader = request.headers.get('x-csrf-token');
  const csrfFromCookie = cookies.get('csrf-token');

  if (csrfFromHeader !== csrfFromCookie) {
    throw error(403, 'CSRF token mismatch');
  }

  // ... proceed
};
```

---

## 9. Secrets Management

### 9.1 Environment Variables

**Never Commit**:
- ❌ API keys (Anthropic, Voyage, Stripe, Supabase)
- ❌ Database URLs (contain passwords)
- ❌ JWT secrets
- ❌ Encryption keys

**Use `.env` file** (local development):
```bash
# .env (gitignored)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJxxx
SUPABASE_SERVICE_KEY=eyJxxx
ANTHROPIC_API_KEY=sk-ant-xxx
VOYAGE_API_KEY=pa-xxx
STRIPE_SECRET_KEY=sk_test_xxx
DATABASE_URL=postgresql://user:pass@localhost:5432/bo1
REDIS_URL=redis://localhost:6379
ADMIN_API_KEY=random_uuid_here
```

### 9.2 Production Secrets (Doppler or AWS Secrets Manager)

**Doppler** (Recommended for simplicity):
```bash
# Install Doppler CLI
curl -Ls https://cli.doppler.com/install.sh | sh

# Login
doppler login

# Fetch secrets
doppler run -- npm run dev # Auto-injects env vars
```

**AWS Secrets Manager** (Enterprise):
```typescript
// Fetch secrets at runtime
import { SecretsManagerClient, GetSecretValueCommand } from '@aws-sdk/client-secrets-manager';

const client = new SecretsManagerClient({ region: 'us-east-1' });
const response = await client.send(new GetSecretValueCommand({ SecretId: 'bo1/production' }));
const secrets = JSON.parse(response.SecretString);

process.env.ANTHROPIC_API_KEY = secrets.ANTHROPIC_API_KEY;
```

### 9.3 Secret Rotation

**Quarterly Rotation**:
- Supabase service role key
- Admin API key
- Encryption keys (if self-managed)

**On Compromise**:
- Immediate rotation
- Revoke all active sessions
- Notify users if PII exposed

---

## 10. Incident Response

### 10.1 Data Breach Response Plan

**Phase 1: Detection & Containment** (0-4 hours):
1. Alert triggered (Sentry, Grafana, manual report)
2. Assess scope: What data? How many users?
3. Contain breach: Disable affected service, revoke credentials
4. Preserve evidence: Snapshot database, save logs

**Phase 2: Investigation** (4-24 hours):
1. Root cause analysis: How did breach occur?
2. Affected users: Query database for impacted records
3. Data exposure: What PII was accessed/exfiltrated?

**Phase 3: Notification** (24-72 hours):
1. **Supervisory Authority** (GDPR Art. 33): Notify ICO within 72 hours
2. **Affected Users** (GDPR Art. 34): Email notification (if high risk)
3. **Public Disclosure**: Blog post if widespread impact

**Phase 4: Remediation** (1-4 weeks):
1. Patch vulnerability
2. Rotate all secrets
3. Security audit (third-party penetration test)
4. Implement additional controls
5. Post-mortem report

### 10.2 Notification Templates

**Email to Affected Users**:
```
Subject: Important Security Notice - Board of One Data Incident

Dear [User],

We are writing to inform you of a security incident that may have affected your account.

On [DATE], we discovered that [DESCRIPTION OF INCIDENT]. Our investigation indicates that [DATA EXPOSED] may have been accessed by an unauthorized party.

What We're Doing:
- We have secured the vulnerability and taken steps to prevent future incidents.
- We have reset your password as a precaution. Please create a new password when you log in.
- We are offering [FREE CREDIT MONITORING / OTHER REMEDIATION] for affected users.

What You Should Do:
- Change your password immediately (if not already reset).
- Enable two-factor authentication (recommended).
- Monitor your accounts for suspicious activity.

We sincerely apologize for this incident and are committed to protecting your data.

For more information, visit: https://boardof.one/security-incident

Sincerely,
Board of One Security Team
```

### 10.3 Contact Information

**Data Protection Officer** (DPO):
- Email: dpo@boardof.one
- Required for GDPR if >250 employees OR high-risk processing

**Security Team**:
- Email: security@boardof.one
- Responsible disclosure: Acknowledge within 24h, remediate within 90 days

**Supervisory Authority** (GDPR):
- UK: Information Commissioner's Office (ICO) - ico.org.uk
- EU: Relevant national data protection authority

---

## 11. Compliance Checklist

### 11.1 GDPR Compliance

- [x] **Privacy Policy** published at `/privacy-policy`
- [x] **Cookie Consent** banner (opt-in for non-essential)
- [x] **Data Processing Agreements** (DPAs) with all processors (Supabase, Anthropic, Stripe, Sentry)
- [x] **User Rights** implemented:
  - [x] Right to Access (`/api/v1/user/export`)
  - [x] Right to Rectification (`/settings/profile`)
  - [x] Right to Erasure (`/api/v1/user/delete`)
  - [x] Right to Data Portability (`/api/v1/user/export`)
- [x] **Data Minimization** (collect only necessary data)
- [x] **Encryption** at rest (AES-256) and in transit (TLS 1.3)
- [x] **Anonymization** instead of deletion (preserve analytics)
- [x] **Audit Logs** for all data access (7-year retention)
- [x] **Breach Notification** plan (72-hour timeline)
- [ ] **DPO Appointment** (required if >250 employees) - Future

### 11.2 Security Best Practices

- [x] **Authentication**: Supabase Auth with social OAuth + email/password
- [x] **Authorization**: Row-level security (RLS) in PostgreSQL
- [x] **Password Hashing**: bcrypt (10 rounds)
- [x] **Session Management**: httpOnly cookies, short-lived tokens (1h)
- [x] **Rate Limiting**: Per-user and per-IP limits
- [x] **Input Validation**: Zod schemas for all API inputs
- [x] **SQL Injection Prevention**: Parameterized queries only
- [x] **XSS Prevention**: Auto-escaping in Svelte
- [x] **CSRF Protection**: SameSite cookies + CSRF tokens
- [x] **TLS 1.3**: All external connections
- [x] **Secrets Management**: Doppler or AWS Secrets Manager
- [ ] **Multi-Factor Authentication** (MFA) - v2 feature
- [ ] **Penetration Testing** - Before production launch
- [ ] **SOC 2 Compliance** - Enterprise tier requirement

### 11.3 Operational Security

- [x] **Error Tracking**: Sentry (PII scrubbed)
- [x] **Logging**: Structured JSON logs (30-day retention)
- [x] **Metrics**: Prometheus + Grafana dashboards
- [x] **Alerting**: PagerDuty for critical incidents
- [x] **Incident Response Plan**: Documented breach response
- [x] **Backup Strategy**: Daily PostgreSQL backups (30-day retention)
- [x] **Disaster Recovery**: RPO 24h, RTO 4h
- [ ] **Security Training**: Annual training for employees - Future
- [ ] **Bug Bounty Program**: HackerOne or Bugcrowd - Future

---

**END OF SECURITY & COMPLIANCE**

This document provides comprehensive security and compliance guidelines for Board of One, with emphasis on GDPR compliance, user privacy, and secure architecture.
