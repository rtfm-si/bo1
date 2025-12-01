# Board of One - Platform Architecture
**Production Infrastructure & Backend Design**

**Version**: 1.0
**Date**: 2025-11-14
**Status**: Architecture Design
**Stack**: SvelteKit 5 + Supabase Auth + PostgreSQL + pgvector

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Technology Stack](#2-technology-stack)
3. [Database Design](#3-database-design)
4. [Authentication & Authorization](#4-authentication--authorization)
5. [Payment Integration (Stripe)](#5-payment-integration-stripe)
6. [Observability & Monitoring](#6-observability--monitoring)
7. [Infrastructure & Deployment](#7-infrastructure--deployment)
8. [Load Balancing & Scaling](#8-load-balancing--scaling)
9. [Data Retention & Lifecycle](#9-data-retention--lifecycle)
10. [API Architecture](#10-api-architecture)

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USERS                                │
│                          │                                  │
│              ┌───────────┴───────────┐                      │
│              │                       │                      │
│         Console/CLI              Web App                    │
│         (Admin/Debug)         (End Users)                   │
│              │                       │                      │
└──────────────┼───────────────────────┼──────────────────────┘
               │                       │
               │                       │
┌──────────────┴───────────────────────┴──────────────────────┐
│                    Traefik (Reverse Proxy)                  │
│            - SSL Termination                                │
│            - Load Balancing                                 │
│            - Rate Limiting                                  │
└──────────────┬───────────────────────┬──────────────────────┘
               │                       │
     ┌─────────┴─────────┐   ┌────────┴──────────┐
     │   Console API     │   │   Web API          │
     │   (Python/FastAPI)│   │   (SvelteKit SSR)  │
     │   - Admin only    │   │   - Public         │
     │   - Full access   │   │   - User-scoped    │
     └─────────┬─────────┘   └────────┬───────────┘
               │                      │
               │                      │
┌──────────────┴──────────────────────┴──────────────────────┐
│                   Application Layer                         │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐ │
│  │ Bo1 Core        │  │ Supabase Auth   │  │ Stripe     │ │
│  │ (bo1/ module)   │  │ - Social OAuth  │  │ - Payments │ │
│  │ - Deliberation  │  │ - JWT tokens    │  │ - Webhooks │ │
│  │ - LLM calls     │  │ - User mgmt     │  │            │ │
│  └────────┬────────┘  └────────┬────────┘  └─────┬──────┘ │
│           │                    │                  │        │
└───────────┼────────────────────┼──────────────────┼────────┘
            │                    │                  │
            │                    │                  │
┌───────────┴────────────────────┴──────────────────┴────────┐
│                    Data Layer                               │
│                                                             │
│  ┌──────────────────┐   ┌──────────────┐   ┌────────────┐ │
│  │  PostgreSQL      │   │  Redis       │   │  S3/Blob   │ │
│  │  - User data     │   │  - Sessions  │   │  - Exports │ │
│  │  - Sessions      │   │  - Cache     │   │  - PDFs    │ │
│  │  - Personas      │   │  - Pub/Sub   │   │            │ │
│  │                  │   │              │   │            │ │
│  │  pgvector        │   │              │   │            │ │
│  │  - Embeddings    │   │              │   │            │ │
│  │  - Similarity    │   │              │   │            │ │
│  └──────────────────┘   └──────────────┘   └────────────┘ │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  Observability Layer                        │
│                                                             │
│  ┌───────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐ │
│  │Prometheus │  │  Grafana  │  │  Sentry  │  │   Logs   │ │
│  │ - Metrics │  │ - Dashbds │  │ - Errors │  │ - Aggr.  │ │
│  └───────────┘  └───────────┘  └──────────┘  └──────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Dual-Mode Access Pattern

**Console/CLI Mode** (Admin & Debug):
- Direct access to Python Bo1 core (`bo1/` module)
- Full Redis access for state inspection
- Admin-only API endpoints (`/api/admin/*`)
- Cost metrics, token usage, debug logs visible
- No authentication required (local/VPN only)

**Web Mode** (Paying End Users):
- SvelteKit SSR frontend
- Supabase Auth (social logins)
- User-scoped API endpoints (`/api/v1/*`)
- Cost metrics hidden, focus on UX
- Stripe integration for payments
- Multi-tenancy with row-level security (RLS)

### 1.3 Separation of Concerns

| Layer | Console Mode | Web Mode |
|-------|--------------|----------|
| **Auth** | None (localhost/VPN) | Supabase (JWT) |
| **API** | FastAPI (`/api/admin/*`) | SvelteKit endpoints (`/api/v1/*`) |
| **Data Access** | Direct PostgreSQL | RLS-protected views |
| **UI** | Rich/Textual (Python) | SvelteKit 5 |
| **Cost Visibility** | Full (tokens, cost, cache) | Hidden (admin only) |
| **Rate Limits** | None | Tiered (Stripe plans) |

---

## 2. Technology Stack

### 2.1 Frontend

**Framework**: SvelteKit 5 (Svelte 5 Runes)
- SSR for SEO and performance
- File-based routing
- Server actions for mutations
- Progressive enhancement

**Styling**: Tailwind CSS + shadcn-svelte
- Utility-first CSS
- Pre-built accessible components
- Dark mode support

**State Management**:
- Svelte stores (reactive)
- Server-side state via load functions
- WebSocket subscriptions for real-time

**Real-time**: WebSocket + SSE fallback
- Deliberation streaming
- Live cost updates (admin view)
- Session status changes

### 2.2 Backend

**Primary API**: SvelteKit Server Endpoints
- `/src/routes/api/v1/*` - User-facing endpoints
- Supabase JWT validation middleware
- Row-level security enforcement
- Rate limiting per user tier

**Admin API**: FastAPI (Python)
- `/api/admin/*` - Admin-only endpoints
- Direct Bo1 core integration
- Full debugging capabilities
- No authentication (VPN/localhost only)

**Background Jobs**: Python + Celery (optional for v2)
- Async summarization
- Embedding generation
- Cleanup jobs
- Email notifications

### 2.3 Authentication

**Provider**: Supabase Auth
- Social OAuth: Google, LinkedIn, GitHub
- Email/password fallback
- JWT-based sessions
- Automatic token refresh
- Row-level security (RLS) integration

**Authorization Model**:
```typescript
interface User {
  id: uuid;
  email: string;
  auth_provider: 'google' | 'linkedin' | 'github' | 'email';
  subscription_tier: 'free' | 'pro' | 'enterprise';
  created_at: timestamp;
  last_login: timestamp;

  // GDPR fields
  gdpr_consent_at?: timestamp;
  data_retention_days: number; // default 365
  anonymized_at?: timestamp; // soft delete
}
```

### 2.4 Database

**Primary**: PostgreSQL 15+
- ACID compliance
- Robust indexes
- Full-text search
- JSON support

**Vector Extension**: pgvector
- Embedding storage (1536 dimensions for Voyage)
- Similarity search (cosine, L2, inner product)
- HNSW indexes for fast retrieval

**Session Cache**: Redis 7+
- In-progress session state
- Real-time pub/sub (deliberation events)
- Rate limiting counters
- Cache for LLM responses

**Blob Storage**: S3-compatible (AWS S3 / Cloudflare R2 / Supabase Storage)
- Exported PDFs
- Session transcripts
- User avatars (optional)

### 2.5 Payments

**Provider**: Stripe
- Subscription management
- Usage-based billing (optional)
- Webhooks for events
- Customer portal for self-service

### 2.6 Observability

**Metrics**: Prometheus
- Application metrics (deliberation time, LLM latency)
- Infrastructure metrics (CPU, memory, DB connections)
- Custom business metrics (sessions created, conversion rate)

**Visualization**: Grafana
- Pre-built dashboards
- Alerts (PagerDuty integration)
- Cost tracking (admin view)

**Error Tracking**: Sentry
- Real-time error monitoring
- Source maps for frontend
- Stack traces for backend
- User context (anonymized)

**Logging**: Structured JSON logs
- Aggregated to Loki or CloudWatch
- Searchable by session_id, user_id, trace_id
- Retention: 30 days (compliance)

### 2.7 Infrastructure

**Reverse Proxy**: Traefik
- Automatic SSL (Let's Encrypt)
- Load balancing (round-robin, least-conn)
- Rate limiting (per IP, per user)
- HTTP/2, gRPC support

**Containerization**: Docker + Docker Compose (dev) / Kubernetes (prod)
- Multi-stage builds (optimized images)
- Health checks
- Resource limits

**Deployment**: Railway / Render / Fly.io (initial) → AWS ECS/EKS (scale)
- CI/CD: GitHub Actions
- Environment management (dev/staging/prod)
- Secrets management (Doppler / AWS Secrets Manager)

---

## 3. Database Design

### 3.1 Schema Overview

```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector"; -- pgvector

-- Core Tables
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  auth_provider TEXT NOT NULL CHECK (auth_provider IN ('google', 'linkedin', 'github', 'email')),
  supabase_user_id UUID UNIQUE NOT NULL, -- Links to auth.users

  -- Subscription
  subscription_tier TEXT NOT NULL DEFAULT 'free' CHECK (subscription_tier IN ('free', 'pro', 'enterprise')),
  stripe_customer_id TEXT UNIQUE,
  stripe_subscription_id TEXT,

  -- GDPR & Privacy
  gdpr_consent_at TIMESTAMPTZ,
  data_retention_days INTEGER DEFAULT 365,
  anonymized_at TIMESTAMPTZ, -- Soft delete marker
  anonymization_reason TEXT, -- 'user_request', 'auto_cleanup', 'account_closure'

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  last_login TIMESTAMPTZ
);

CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  -- Session data
  problem_statement TEXT NOT NULL,
  problem_context JSONB, -- {budget, timeline, constraints}
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived', 'failed')),
  current_phase TEXT NOT NULL DEFAULT 'intake' CHECK (current_phase IN ('intake', 'decomposition', 'selection', 'initial_round', 'discussion', 'voting', 'synthesis', 'complete')),

  -- Deliberation state (denormalized for quick access)
  sub_problems JSONB[], -- Array of sub-problem objects
  selected_personas TEXT[], -- Array of persona codes
  current_round INTEGER DEFAULT 0,
  max_rounds INTEGER DEFAULT 10,

  -- Cost tracking (admin only)
  total_cost NUMERIC(10, 4) DEFAULT 0.00, -- USD
  total_tokens INTEGER DEFAULT 0,
  cache_hits INTEGER DEFAULT 0,
  cache_misses INTEGER DEFAULT 0,

  -- Metrics (visible to user)
  convergence_score NUMERIC(3, 2), -- 0.00-1.00
  confidence_level TEXT, -- 'low', 'medium', 'high'
  duration_seconds INTEGER, -- Total deliberation time

  -- GDPR
  anonymized_at TIMESTAMPTZ, -- Null if not anonymized

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE contributions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

  -- Contribution metadata
  persona_code TEXT NOT NULL, -- e.g., 'zara', 'maria', 'facilitator'
  persona_name TEXT NOT NULL,
  round_number INTEGER NOT NULL,
  contribution_type TEXT NOT NULL CHECK (contribution_type IN ('initial', 'response', 'moderator', 'facilitator')),

  -- Content
  content TEXT NOT NULL, -- Markdown (anonymized if session anonymized)
  thinking TEXT, -- Internal reasoning (optional, anonymized)

  -- Cost tracking (admin only)
  tokens INTEGER DEFAULT 0,
  cost NUMERIC(10, 4) DEFAULT 0.00,
  cached BOOLEAN DEFAULT FALSE,

  -- LLM metadata
  model TEXT, -- e.g., 'claude-sonnet-4-5-20250929'
  temperature NUMERIC(2, 1),

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE votes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

  -- Vote data
  persona_code TEXT NOT NULL,
  persona_name TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('yes', 'no', 'abstain', 'conditional')),
  reasoning TEXT NOT NULL,
  confidence NUMERIC(3, 2) NOT NULL, -- 0.00-1.00
  conditions TEXT[], -- Array of condition strings (if conditional)

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE synthesis_reports (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE UNIQUE,

  -- Report content (markdown, anonymized if session anonymized)
  executive_summary TEXT NOT NULL,
  key_insights TEXT NOT NULL,
  vote_distribution JSONB NOT NULL, -- {option: count}
  dissenting_views TEXT,
  conditions TEXT[],
  next_steps TEXT NOT NULL,

  -- Full report (all sections combined)
  full_report TEXT NOT NULL,

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE personas (
  code TEXT PRIMARY KEY, -- 'zara', 'maria', etc.
  name TEXT NOT NULL,
  archetype TEXT NOT NULL,
  category TEXT NOT NULL, -- 'marketing', 'finance', etc.
  system_prompt TEXT NOT NULL, -- Bespoke identity (879 chars avg)
  traits JSONB NOT NULL, -- {creative: 0.8, analytical: 0.3, ...}
  temperature NUMERIC(2, 1) DEFAULT 0.7,

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Embeddings for convergence/drift detection
CREATE TABLE embeddings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  contribution_id UUID REFERENCES contributions(id) ON DELETE CASCADE,

  -- Embedding data
  embedding vector(1536), -- Voyage-3 dimensions
  embedding_type TEXT NOT NULL CHECK (embedding_type IN ('contribution', 'sub_problem', 'synthesis')),

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit log (GDPR compliance)
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL, -- Null if user anonymized
  session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,

  -- Event data
  event_type TEXT NOT NULL, -- 'session_created', 'user_anonymized', 'export_requested', etc.
  event_data JSONB, -- Additional context
  ip_address INET, -- Anonymized after retention period
  user_agent TEXT, -- Anonymized after retention period

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);
CREATE INDEX idx_contributions_session_id ON contributions(session_id);
CREATE INDEX idx_votes_session_id ON votes(session_id);
CREATE INDEX idx_embeddings_session_id ON embeddings(session_id);
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops); -- HNSW in production
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- Row-Level Security (RLS) Policies
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE contributions ENABLE ROW LEVEL SECURITY;
ALTER TABLE votes ENABLE ROW LEVEL SECURITY;
ALTER TABLE synthesis_reports ENABLE ROW LEVEL SECURITY;

-- Users can only see their own sessions
CREATE POLICY "Users can view own sessions" ON sessions
  FOR SELECT USING (auth.uid() = (SELECT supabase_user_id FROM users WHERE id = sessions.user_id));

CREATE POLICY "Users can create own sessions" ON sessions
  FOR INSERT WITH CHECK (auth.uid() = (SELECT supabase_user_id FROM users WHERE id = sessions.user_id));

CREATE POLICY "Users can update own sessions" ON sessions
  FOR UPDATE USING (auth.uid() = (SELECT supabase_user_id FROM users WHERE id = sessions.user_id));

-- Similar policies for contributions, votes, synthesis_reports
-- (Omitted for brevity, follow same pattern)
```

### 3.2 Anonymization Strategy (GDPR/RTBF)

**Principle**: Never delete data, obfuscate PII instead.

**Anonymization Process** (triggered on account closure or RTBF request):

1. **Mark user as anonymized**:
   ```sql
   UPDATE users SET
     email = 'anonymized_' || id || '@deleted.local',
     anonymized_at = NOW(),
     anonymization_reason = 'user_request',
     gdpr_consent_at = NULL,
     stripe_customer_id = NULL,
     stripe_subscription_id = NULL
   WHERE id = $1;
   ```

2. **Anonymize sessions**:
   ```sql
   UPDATE sessions SET
     problem_statement = '[REDACTED]',
     problem_context = '{}',
     anonymized_at = NOW()
   WHERE user_id = $1;
   ```

3. **Anonymize contributions**:
   ```sql
   UPDATE contributions SET
     content = '[Content redacted due to account deletion]',
     thinking = NULL
   WHERE session_id IN (SELECT id FROM sessions WHERE user_id = $1);
   ```

4. **Retain metadata for analytics** (anonymized):
   - Keep session count, total cost, durations (aggregate metrics)
   - Keep persona usage stats (no PII)
   - Keep audit logs (with user_id nulled)

5. **Audit trail**:
   ```sql
   INSERT INTO audit_log (user_id, event_type, event_data)
   VALUES ($1, 'user_anonymized', '{"reason": "user_request", "timestamp": "2025-11-14T10:00:00Z"}');
   ```

**Retention Policy**:
- Active users: Retain all data
- Inactive users (365 days): Automatic anonymization prompt
- Anonymized users: Keep anonymized records indefinitely (for analytics)
- Audit logs: Retain for 7 years (compliance)

---

## 4. Authentication & Authorization

### 4.1 Supabase Auth Integration

**Setup**:
```typescript
// src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js';

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
);
```

**Social OAuth Providers**:
- **Google**: OAuth 2.0 (email, profile scope)
- **LinkedIn**: OAuth 2.0 (r_emailaddress, r_liteprofile)
- **GitHub**: OAuth 2.0 (user:email scope)

**Sign-in Flow**:
```typescript
// Sign in with Google
const { data, error } = await supabase.auth.signInWithOAuth({
  provider: 'google',
  options: {
    redirectTo: `${window.location.origin}/auth/callback`
  }
});

// Callback handler (src/routes/auth/callback/+server.ts)
export const GET = async ({ url, cookies }) => {
  const code = url.searchParams.get('code');

  if (code) {
    const { data, error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      // Set session cookie (httpOnly, secure)
      cookies.set('sb-session', data.session.access_token, {
        path: '/',
        httpOnly: true,
        secure: true,
        sameSite: 'lax',
        maxAge: 60 * 60 * 24 * 7 // 7 days
      });

      // Create user record if first login
      await createUserIfNotExists(data.user);

      redirect(303, '/dashboard');
    }
  }

  redirect(303, '/login?error=auth_failed');
};
```

**Session Management**:
```typescript
// src/hooks.server.ts (SvelteKit middleware)
export const handle = async ({ event, resolve }) => {
  const token = event.cookies.get('sb-session');

  if (token) {
    const { data: { user }, error } = await supabase.auth.getUser(token);
    if (user && !error) {
      event.locals.user = user;
      event.locals.dbUser = await getUserFromDB(user.id);
    }
  }

  return resolve(event);
};
```

### 4.2 Authorization Model

**Role-Based Access**:
- **Admin** (console mode): Full access, no restrictions
- **Pro User** (web mode): 50 sessions/month, priority support
- **Free User** (web mode): 5 sessions/month, standard support

**Middleware**:
```typescript
// src/lib/auth/middleware.ts
export function requireAuth(event: RequestEvent) {
  if (!event.locals.user) {
    throw redirect(303, '/login');
  }
  return event.locals.dbUser;
}

export function requireTier(tier: SubscriptionTier) {
  return (event: RequestEvent) => {
    const user = requireAuth(event);
    if (!canAccessTier(user.subscription_tier, tier)) {
      throw error(403, 'Upgrade required');
    }
    return user;
  };
}
```

**Rate Limiting** (per tier):
```typescript
// src/lib/ratelimit.ts
import { Redis } from 'ioredis';

const redis = new Redis(process.env.REDIS_URL);

export async function checkRateLimit(userId: string, tier: SubscriptionTier) {
  const limits = {
    free: { sessions: 5, requests: 100 },
    pro: { sessions: 50, requests: 1000 },
    enterprise: { sessions: -1, requests: -1 } // Unlimited
  };

  const key = `ratelimit:${userId}:sessions`;
  const count = await redis.incr(key);
  await redis.expire(key, 30 * 24 * 60 * 60); // 30 days

  const limit = limits[tier].sessions;
  if (limit !== -1 && count > limit) {
    throw error(429, 'Rate limit exceeded. Upgrade to continue.');
  }
}
```

---

## 5. Payment Integration (Stripe)

### 5.1 Subscription Tiers

| Tier | Price | Sessions/Month | Features |
|------|-------|----------------|----------|
| **Free** | $0 | 5 | Basic deliberations, 3 personas max, standard support |
| **Pro** | $29/month | 50 | All personas, priority LLM access, export to PDF, priority support |
| **Enterprise** | Custom | Unlimited | Custom personas, API access, SLA, dedicated support |

### 5.2 Stripe Integration

**Setup**:
```typescript
// src/lib/stripe.ts
import Stripe from 'stripe';

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16'
});

// Create customer on first login
export async function createStripeCustomer(user: User) {
  const customer = await stripe.customers.create({
    email: user.email,
    metadata: { supabase_user_id: user.id }
  });

  await db.update(users).set({
    stripe_customer_id: customer.id
  }).where(eq(users.id, user.id));

  return customer;
}
```

**Checkout Flow**:
```typescript
// src/routes/api/v1/checkout/+server.ts
export const POST = async ({ locals, request }) => {
  const user = requireAuth({ locals });
  const { tier } = await request.json();

  const priceId = tier === 'pro' ? process.env.STRIPE_PRO_PRICE_ID : process.env.STRIPE_ENTERPRISE_PRICE_ID;

  const session = await stripe.checkout.sessions.create({
    customer: user.stripe_customer_id,
    mode: 'subscription',
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: `${url.origin}/settings/billing?success=true`,
    cancel_url: `${url.origin}/settings/billing?canceled=true`,
    metadata: { user_id: user.id }
  });

  return json({ url: session.url });
};
```

**Webhook Handler** (subscription updates):
```typescript
// src/routes/api/webhooks/stripe/+server.ts
import { buffer } from 'micro';

export const POST = async ({ request }) => {
  const sig = request.headers.get('stripe-signature')!;
  const body = await request.text();

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(body, sig, process.env.STRIPE_WEBHOOK_SECRET!);
  } catch (err) {
    return new Response('Webhook signature verification failed', { status: 400 });
  }

  // Handle events
  switch (event.type) {
    case 'customer.subscription.created':
    case 'customer.subscription.updated':
      const subscription = event.data.object as Stripe.Subscription;
      await updateUserSubscription(subscription);
      break;

    case 'customer.subscription.deleted':
      const deletedSub = event.data.object as Stripe.Subscription;
      await downgradeUserToFree(deletedSub.customer as string);
      break;
  }

  return new Response(null, { status: 200 });
};

async function updateUserSubscription(subscription: Stripe.Subscription) {
  const tier = subscription.items.data[0].price.id === process.env.STRIPE_PRO_PRICE_ID ? 'pro' : 'enterprise';

  await db.update(users).set({
    subscription_tier: tier,
    stripe_subscription_id: subscription.id
  }).where(eq(users.stripe_customer_id, subscription.customer));
}
```

### 5.3 Usage-Based Billing (Optional)

For future metered billing (e.g., pay per session beyond quota):

```typescript
// Report usage to Stripe
await stripe.subscriptionItems.createUsageRecord(
  subscriptionItemId,
  {
    quantity: 1, // 1 session
    timestamp: Math.floor(Date.now() / 1000),
    action: 'increment'
  }
);
```

---

## 6. Observability & Monitoring

### 6.1 Metrics Collection (Prometheus)

**Application Metrics**:
```python
# bo1/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Deliberation metrics
deliberation_created = Counter('bo1_deliberations_created_total', 'Total deliberations created', ['tier'])
deliberation_duration = Histogram('bo1_deliberation_duration_seconds', 'Deliberation duration', ['tier'])
deliberation_cost = Histogram('bo1_deliberation_cost_usd', 'Deliberation cost in USD', ['tier'])

# LLM metrics
llm_requests = Counter('bo1_llm_requests_total', 'Total LLM requests', ['model', 'persona'])
llm_latency = Histogram('bo1_llm_latency_seconds', 'LLM request latency', ['model'])
llm_tokens = Histogram('bo1_llm_tokens', 'LLM tokens used', ['model', 'type']) # type: input/output
cache_hits = Counter('bo1_cache_hits_total', 'Cache hits', ['model'])
cache_misses = Counter('bo1_cache_misses_total', 'Cache misses', ['model'])

# Business metrics
users_active = Gauge('bo1_users_active', 'Active users (last 30 days)')
revenue_mrr = Gauge('bo1_revenue_mrr_usd', 'Monthly Recurring Revenue')
```

**Export Endpoint**:
```python
# FastAPI
from prometheus_client import generate_latest

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

### 6.2 Dashboards (Grafana)

**Dashboard 1: Deliberation Performance**
- Deliberations created (last 7 days) - Line chart
- Average deliberation duration - Gauge
- P95 deliberation duration - Gauge
- Deliberations by tier - Pie chart

**Dashboard 2: LLM Operations**
- LLM requests per second - Line chart
- Cache hit rate - Gauge (target: >70%)
- Average LLM latency (by model) - Bar chart
- Token usage (input vs output) - Stacked area chart

**Dashboard 3: Business Metrics**
- Active users (DAU, WAU, MAU) - Line chart
- MRR - Line chart with trend
- Conversion rate (free → pro) - Gauge
- Churn rate - Gauge

**Dashboard 4: Infrastructure**
- CPU usage (by service) - Line chart
- Memory usage (by service) - Line chart
- Database connections - Gauge
- Redis memory usage - Gauge
- Request latency (P50, P95, P99) - Heatmap

**Alerts**:
- LLM latency > 10s (P95)
- Cache hit rate < 50%
- Database connection pool exhausted
- Error rate > 1%
- Deliberation creation rate drop > 50%

### 6.3 Error Tracking (Sentry)

**Setup**:
```typescript
// SvelteKit
import * as Sentry from '@sentry/sveltekit';

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  tracesSampleRate: 0.1, // 10% of transactions
  beforeSend(event, hint) {
    // Scrub PII
    if (event.user) {
      delete event.user.email;
      delete event.user.ip_address;
    }
    return event;
  }
});
```

**Context Enrichment**:
```typescript
Sentry.setUser({ id: user.id, tier: user.subscription_tier });
Sentry.setContext('session', { id: session.id, phase: session.current_phase });
```

### 6.4 Logging

**Structured JSON Logs**:
```python
# Python (structlog)
import structlog

logger = structlog.get_logger()

logger.info(
  "deliberation.started",
  session_id=session.id,
  user_id=user.id,
  tier=user.subscription_tier,
  personas=selected_personas
)
```

**Log Aggregation**:
- Local: stdout (Docker Compose)
- Production: Grafana Loki or AWS CloudWatch
- Retention: 30 days (compliance)

**Searchable Fields**:
- `session_id`: Track full deliberation lifecycle
- `user_id`: User-scoped debugging
- `trace_id`: Distributed tracing across services
- `tier`: Identify tier-specific issues

---

## 7. Infrastructure & Deployment

### 7.1 Development Environment

**Docker Compose** (`docker-compose.yml`):
```yaml
version: '3.8'

services:
  web:
    build:
      context: ./web
      dockerfile: Dockerfile
    ports:
      - "5173:5173" # Vite dev server
    environment:
      - VITE_SUPABASE_URL=${SUPABASE_URL}
      - VITE_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
    volumes:
      - ./web:/app
      - /app/node_modules
    depends_on:
      - postgres
      - redis

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000" # FastAPI
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/bo1
      - REDIS_URL=redis://redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - .:/app
    depends_on:
      - postgres
      - redis

  postgres:
    image: pgvector/pgvector:pg15
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=bo1
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./observability/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

### 7.2 Production Deployment

**Option 1: Railway** (Recommended for MVP)
- Automatic deployments from GitHub
- Built-in PostgreSQL + Redis
- Auto-scaling (horizontal)
- Easy environment management

**Option 2: Render**
- Similar to Railway
- Better for static sites (SvelteKit adapter)
- Managed PostgreSQL

**Option 3: Fly.io**
- Closer to production setup
- Multi-region deployments
- Custom Dockerfile support

**Option 4: AWS ECS/EKS** (Long-term scale)
- Full control
- Multi-AZ deployments
- Auto-scaling groups
- More complex setup

**CI/CD Pipeline** (GitHub Actions):
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - run: npm ci
      - run: npm test
      - run: npm run build

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Railway
        run: railway up --service web
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

### 7.3 Environment Configuration

**Secrets Management** (Doppler or AWS Secrets Manager):
```bash
# Production secrets
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJxxx
SUPABASE_SERVICE_KEY=eyJxxx (server-side only)
ANTHROPIC_API_KEY=sk-ant-xxx
VOYAGE_API_KEY=pa-xxx
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379
SENTRY_DSN=https://xxx@sentry.io/xxx
```

---

## 8. Load Balancing & Scaling

### 8.1 Traefik Configuration

**Setup** (`traefik.yml`):
```yaml
# Static configuration
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"

certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@boardof.one
      storage: /acme.json
      httpChallenge:
        entryPoint: web

providers:
  docker:
    exposedByDefault: false

# Dynamic configuration (docker-compose labels)
services:
  web:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.web.rule=Host(`app.boardof.one`)"
      - "traefik.http.routers.web.entrypoints=websecure"
      - "traefik.http.routers.web.tls.certresolver=letsencrypt"
      - "traefik.http.services.web.loadbalancer.server.port=5173"

  api:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.boardof.one`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"
      - "traefik.http.services.api.loadbalancer.server.port=8000"
```

**Rate Limiting**:
```yaml
# traefik.yml
http:
  middlewares:
    ratelimit:
      rateLimit:
        average: 100 # requests
        period: 1m
        burst: 50
```

### 8.2 Horizontal Scaling

**Auto-scaling Triggers**:
- CPU > 70% (sustained 5 min) → Scale up
- CPU < 30% (sustained 10 min) → Scale down
- Request queue depth > 100 → Scale up

**Database Connection Pooling** (PgBouncer):
```ini
# pgbouncer.ini
[databases]
bo1 = host=postgres port=5432 dbname=bo1

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
reserve_pool_size = 5
```

**Redis Clustering** (Optional for scale):
- Master-replica setup (read replicas)
- Sentinel for automatic failover
- Cluster mode for horizontal scaling (sharding)

---

## 9. Data Retention & Lifecycle

### 9.1 Retention Policies

| Data Type | Retention Period | Action After Period |
|-----------|------------------|---------------------|
| Active user sessions | Indefinite | Keep until user deletes |
| Inactive user sessions | 365 days | Prompt for deletion |
| Anonymized user data | Indefinite | Keep for analytics |
| Audit logs | 7 years | Delete (compliance) |
| LLM response cache | 30 days | Evict from Redis |
| Exported PDFs | 90 days | Move to cold storage |

### 9.2 Cleanup Jobs

**Daily Cron** (clean expired sessions):
```python
# Celery task or cron job
async def cleanup_expired_sessions():
    cutoff = datetime.now() - timedelta(days=365)
    sessions = await db.query(
        "SELECT id, user_id FROM sessions WHERE updated_at < $1 AND status = 'active'",
        cutoff
    )

    for session in sessions:
        # Notify user
        await send_email(session.user_id, "Session expiring soon", ...)

        # Auto-archive after 30 days
        if datetime.now() - session.updated_at > timedelta(days=395):
            await db.execute("UPDATE sessions SET status = 'archived' WHERE id = $1", session.id)
```

**Weekly Cron** (anonymize inactive users):
```python
async def anonymize_inactive_users():
    cutoff = datetime.now() - timedelta(days=365)
    users = await db.query(
        "SELECT id FROM users WHERE last_login < $1 AND anonymized_at IS NULL",
        cutoff
    )

    for user in users:
        # Notify before anonymization
        await send_email(user.id, "Account will be anonymized in 30 days", ...)

        # Anonymize after 30-day grace period
        if datetime.now() - user.last_login > timedelta(days=395):
            await anonymize_user(user.id)
```

---

## 10. API Architecture

### 10.1 API Versioning

**Endpoints**:
- `/api/v1/*` - Public web API (SvelteKit)
- `/api/admin/*` - Admin API (FastAPI, localhost/VPN only)

### 10.2 Public API (SvelteKit)

**Session Management**:
```typescript
// GET /api/v1/sessions - List user's sessions
export const GET = async ({ locals }) => {
  const user = requireAuth({ locals });
  const sessions = await db.query.sessions.findMany({
    where: eq(sessions.user_id, user.id),
    orderBy: desc(sessions.created_at)
  });
  return json({ sessions });
};

// POST /api/v1/sessions - Create new session
export const POST = async ({ locals, request }) => {
  const user = requireAuth({ locals });
  await checkRateLimit(user.id, user.subscription_tier);

  const { problem_statement, problem_context } = await request.json();
  const session = await createSession(user.id, problem_statement, problem_context);

  return json({ session }, { status: 201 });
};
```

**Deliberation**:
```typescript
// POST /api/v1/sessions/:id/deliberation/start
export const POST = async ({ locals, params }) => {
  const user = requireAuth({ locals });
  const session = await getSession(params.id, user.id); // RLS check

  // Trigger deliberation (async)
  await deliberationQueue.add({ session_id: session.id });

  return json({ status: 'started' });
};

// WebSocket /api/v1/sessions/:id/stream
export const GET = async ({ locals, params }) => {
  const user = requireAuth({ locals });
  const session = await getSession(params.id, user.id);

  // Upgrade to WebSocket
  const { socket, response } = Deno.upgradeWebSocket(request);

  // Subscribe to Redis pub/sub
  const sub = redis.duplicate();
  await sub.subscribe(`session:${session.id}`);

  sub.on('message', (channel, message) => {
    socket.send(message);
  });

  return response;
};
```

### 10.3 Admin API (FastAPI)

**Cost Analytics**:
```python
# GET /api/admin/analytics/cost
@app.get("/api/admin/analytics/cost")
async def get_cost_analytics(
    start_date: datetime,
    end_date: datetime,
    tier: Optional[str] = None
):
    """Get cost breakdown by date range and tier"""
    query = """
        SELECT
            DATE(created_at) as date,
            subscription_tier,
            COUNT(*) as sessions,
            SUM(total_cost) as total_cost,
            AVG(total_cost) as avg_cost,
            SUM(total_tokens) as total_tokens
        FROM sessions
        JOIN users ON sessions.user_id = users.id
        WHERE created_at BETWEEN $1 AND $2
        GROUP BY DATE(created_at), subscription_tier
        ORDER BY date DESC
    """
    results = await db.fetch_all(query, [start_date, end_date])
    return {"analytics": results}
```

**Session Inspection**:
```python
# GET /api/admin/sessions/:id/full
@app.get("/api/admin/sessions/{session_id}/full")
async def get_full_session(session_id: str):
    """Get complete session with all contributions, votes, costs"""
    session = await db.fetch_one("SELECT * FROM sessions WHERE id = $1", [session_id])
    contributions = await db.fetch_all("SELECT * FROM contributions WHERE session_id = $1", [session_id])
    votes = await db.fetch_all("SELECT * FROM votes WHERE session_id = $1", [session_id])

    return {
        "session": session,
        "contributions": contributions,
        "votes": votes,
        "total_cost": session["total_cost"],
        "cache_hit_rate": session["cache_hits"] / (session["cache_hits"] + session["cache_misses"])
    }
```

---

## Appendix: Migration from v1 Console to v2 Web

**Phase 1: Dual-mode support** (v1 console + v2 web coexist)
- Shared Redis/PostgreSQL backend
- Console mode: Direct Python access
- Web mode: API layer (FastAPI/SvelteKit)

**Phase 2: Feature parity**
- Web UI implements all console features
- Admin-only views for cost/tokens
- Debug panel (hidden by default)

**Phase 3: Console becomes admin tool**
- Primary UX shifts to web
- Console for power users/debugging only
- Separate deployments (console on VPN, web public)

**Data Migration**: None required (shared DB from day 1)

---

**END OF PLATFORM ARCHITECTURE**

This document provides the complete backend infrastructure design for Board of One's production deployment, with emphasis on dual-mode access (console for admins, web for users), GDPR compliance, and scalable architecture.
