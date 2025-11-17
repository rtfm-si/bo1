# Board of One - MVP Launch Readiness

**Version**: 1.0
**Date**: 2025-11-14
**Status**: Pre-Launch Checklist
**Target**: Public Beta / MVP Release

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Core Systems Required](#2-core-systems-required)
3. [Resend Email Integration](#3-resend-email-integration)
4. [MVP Feature Checklist](#4-mvp-feature-checklist)
5. [Infrastructure Requirements](#5-infrastructure-requirements)
6. [Security & Compliance](#6-security--compliance)
7. [Monitoring & Observability](#7-monitoring--observability)
8. [Pre-Launch Testing](#8-pre-launch-testing)
9. [Go-Live Checklist](#9-go-live-checklist)
10. [Post-Launch (Future Enhancements)](#10-post-launch-future-enhancements)

---

## 1. Executive Summary

### 1.1 MVP Definition

**Board of One MVP** provides:
- ✅ **Console interface** (v1 complete, Week 3 validated)
- ✅ **Web UI** (LangGraph migration, Weeks 1-9)
- ✅ **Admin dashboard** (monitoring, analytics, Weeks 10-11)
- ✅ **User authentication** (Supabase Auth with social logins)
- ✅ **Payment processing** (Stripe integration, 3 tiers)
- ✅ **Email notifications** (Resend - NEW)
- ✅ **System monitoring** (ntfy.sh alerts for admins)

**What's NOT in MVP** (Phase 2):
- ❌ Sentry error tracking (add Week 12)
- ❌ PostHog analytics (add Week 13)
- ❌ Advanced A/B testing
- ❌ Mobile apps (iOS/Android)
- ❌ API for third-party integrations

### 1.2 MVP Timeline

```
Week 1-2:   Console → LangGraph migration
Week 3-4:   Web API adapter (FastAPI + SSE)
Week 5-6:   SvelteKit UI (real-time streaming)
Week 7-8:   Advanced features (time travel, human-in-loop)
Week 9:     Production hardening (load testing, monitoring)
Week 10-11: Admin dashboard (monitoring, analytics, kill switches)
Week 12:    Resend integration + email templates
Week 13:    Final QA, security audit, load testing
Week 14:    LAUNCH 🚀
```

**Total timeline**: 14 weeks from start to public beta

---

## 2. Core Systems Required

### 2.1 System Dependencies

| System | Purpose | Status | Cost | Critical? |
|--------|---------|--------|------|-----------|
| **PostgreSQL** | User data, sessions, metrics | ✅ Planned | $0 (Supabase free tier) | ✅ YES |
| **Redis** | Session state, caching, pub/sub | ✅ Complete | $0 (Docker local) | ✅ YES |
| **Supabase Auth** | User authentication, JWT | ✅ Planned | $0 (free tier) | ✅ YES |
| **Stripe** | Payment processing | ✅ Planned | 2.9% + 30¢/tx | ✅ YES |
| **Anthropic API** | Claude LLM (Sonnet 4.5, Haiku 4.5) | ✅ Complete | Pay-as-you-go | ✅ YES |
| **Voyage AI** | Embeddings (similarity checks) | ✅ Complete | Pay-as-you-go | ✅ YES |
| **Resend** | Transactional emails | 🔧 **NEW** | $0 (3k emails/mo free) | ✅ YES |
| **ntfy.sh** | Admin notifications (runaway alerts) | ✅ Planned | $0 (self-hosted) | ⚠️ NICE-TO-HAVE |
| **Traefik** | Reverse proxy, SSL, rate limiting | ✅ Planned | $0 (self-hosted) | ✅ YES |
| **Docker** | Containerization, dev environment | ✅ Complete | $0 | ✅ YES |

### 2.2 Third-Party Services

**Authentication**:
- Supabase Auth (Google, LinkedIn, GitHub OAuth)
- JWT tokens (HS256, 1-hour expiry, auto-refresh)

**Payments**:
- Stripe Checkout (hosted payment page)
- Stripe Webhooks (subscription events)
- Stripe Customer Portal (self-service)

**Email** (NEW):
- Resend (transactional emails)
- SPF/DKIM/DMARC configured
- Email templates (React Email)

**Notifications**:
- ntfy.sh (admin alerts - runaway sessions, cost reports)
- Optional: Web push notifications (future)

**Monitoring** (Phase 2):
- Sentry (error tracking) - Week 12+
- PostHog (product analytics) - Week 13+
- Prometheus + Grafana (system metrics) - Optional

### 2.3 Infrastructure Stack

**Development**:
```
Docker Compose (local dev)
├── app (Python 3.12 + FastAPI)
├── redis (Redis 7)
├── postgres (PostgreSQL 15 with pgvector)
└── traefik (reverse proxy)
```

**Production** (Render.com or Railway.app):
```
Render Web Service (FastAPI backend)
├── Environment: Python 3.12
├── Build: uv sync --frozen
├── Start: uvicorn bo1.api.main:app
├── Health check: /api/health
└── Auto-scaling: 1-5 instances

PostgreSQL (Supabase)
├── Free tier: 500MB
├── Upgrade: Pro ($25/mo, 8GB)
└── Backups: Daily automatic

Redis (Upstash or Render Redis)
├── Free tier: 10k commands/day
├── Upgrade: $10/mo (100k/day)
└── Persistence: AOF enabled
```

---

## 3. Resend Email Integration

### 3.1 Why Resend?

**Rationale**:
- ✅ **Developer-friendly**: Simple REST API (like Stripe)
- ✅ **Modern**: Built for transactional emails (not marketing)
- ✅ **React Email integration**: Type-safe templates with JSX
- ✅ **Generous free tier**: 3,000 emails/month (enough for MVP)
- ✅ **Reliable**: 99.9% deliverability SLA
- ✅ **Fast**: <1s send time, webhook delivery confirmations
- ✅ **EU-hosted option**: GDPR-compliant data residency

**Alternatives considered**:
- ❌ SendGrid: Complex pricing, marketing-focused, heavyweight SDK
- ❌ Mailgun: Aging API, less developer-friendly
- ❌ AWS SES: Cheap but complex setup, deliverability issues on free tier
- ❌ Postmark: Great but more expensive ($10/mo minimum)

### 3.2 Resend Setup

**1. Account Setup**:
```bash
# Sign up at resend.com
# Verify domain (boardof.one)
# Add DNS records:
#   TXT: resend._domainkey.boardof.one (DKIM)
#   TXT: boardof.one (SPF: v=spf1 include:resend.com ~all)
#   TXT: _dmarc.boardof.one (DMARC: v=DMARC1; p=none)
# Get API key
```

**2. Environment Variables**:
```bash
# .env
RESEND_API_KEY=re_abc123...
RESEND_FROM_EMAIL=noreply@boardof.one
RESEND_FROM_NAME="Board of One"
RESEND_REPLY_TO=support@boardof.one
```

**3. Python SDK Installation**:
```bash
uv add resend
```

**4. Email Service Module**:
```python
# bo1/services/email.py
import os
from typing import Optional
import resend

resend.api_key = os.getenv("RESEND_API_KEY")

class EmailService:
    """Transactional email service using Resend."""

    FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "noreply@boardof.one")
    FROM_NAME = os.getenv("RESEND_FROM_NAME", "Board of One")
    REPLY_TO = os.getenv("RESEND_REPLY_TO", "support@boardof.one")

    @staticmethod
    async def send_email(
        to: str,
        subject: str,
        html: str,
        text: Optional[str] = None,
        tags: Optional[list[dict]] = None
    ) -> dict:
        """Send transactional email via Resend.

        Args:
            to: Recipient email
            subject: Email subject
            html: HTML body (required)
            text: Plain text fallback (optional, auto-generated if None)
            tags: List of tags for tracking (e.g., [{"name": "category", "value": "welcome"}])

        Returns:
            Response with email ID: {"id": "abc123..."}
        """
        params = {
            "from": f"{EmailService.FROM_NAME} <{EmailService.FROM_EMAIL}>",
            "to": [to],
            "subject": subject,
            "html": html,
            "reply_to": EmailService.REPLY_TO
        }

        if text:
            params["text"] = text

        if tags:
            params["tags"] = tags

        # Send email (synchronous, but fast <1s)
        response = resend.Emails.send(params)
        return response

# Usage example
email_service = EmailService()
```

### 3.3 Email Templates

**Email Types** (MVP):
1. ✅ **Welcome email** (after signup)
2. ✅ **Email verification** (Supabase handles this, but custom branding)
3. ✅ **Deliberation complete** (with summary + link to results)
4. ✅ **Payment receipt** (Stripe sends invoice, but we send thank-you)
5. ✅ **Weekly digest** (optional - "You had 3 deliberations this week")
6. ✅ **Password reset** (Supabase handles, but custom branding)

**Template Engine**: React Email (JSX-based, type-safe)

**Setup**:
```bash
# Install React Email
npm install react-email @react-email/components

# Create templates directory
mkdir -p emails/templates
```

**Example Template** (`emails/templates/welcome.tsx`):
```tsx
import {
  Body, Container, Head, Heading, Html, Link, Text
} from '@react-email/components';
import * as React from 'react';

interface WelcomeEmailProps {
  userEmail: string;
  userName?: string;
}

export const WelcomeEmail = ({ userEmail, userName }: WelcomeEmailProps) => (
  <Html>
    <Head />
    <Body style={main}>
      <Container style={container}>
        <Heading style={h1}>Welcome to Board of One!</Heading>
        <Text style={text}>
          Hi {userName || userEmail},
        </Text>
        <Text style={text}>
          Thanks for joining Board of One. You now have access to:
        </Text>
        <ul>
          <li>🧠 Multi-agent deliberation (up to 5 experts)</li>
          <li>📊 Problem decomposition & synthesis</li>
          <li>💾 Session history & exports</li>
        </ul>
        <Text style={text}>
          <Link href="https://boardof.one/new-session" style={link}>
            Start your first deliberation →
          </Link>
        </Text>
        <Text style={footer}>
          Questions? Reply to this email or visit our{' '}
          <Link href="https://boardof.one/help">Help Center</Link>.
        </Text>
      </Container>
    </Body>
  </Html>
);

const main = { backgroundColor: '#f6f9fc', fontFamily: 'sans-serif' };
const container = { margin: '0 auto', padding: '20px 0 48px', maxWidth: '580px' };
const h1 = { color: '#333', fontSize: '24px', fontWeight: 'bold' };
const text = { color: '#333', fontSize: '16px', lineHeight: '26px' };
const link = { color: '#5469d4', textDecoration: 'underline' };
const footer = { color: '#8898aa', fontSize: '12px', marginTop: '32px' };

export default WelcomeEmail;
```

**Render Template to HTML** (`bo1/services/email_templates.py`):
```python
import subprocess
import json
from pathlib import Path

class EmailTemplates:
    """Render React Email templates to HTML."""

    TEMPLATES_DIR = Path(__file__).parent.parent.parent / "emails" / "templates"

    @staticmethod
    def render_welcome_email(user_email: str, user_name: str = None) -> str:
        """Render welcome email template."""
        # Option 1: Use React Email CLI (requires Node.js)
        # npx react-email export --html --out ./emails/rendered/welcome.html

        # Option 2: Pre-render templates at build time
        # Store rendered HTML in bo1/templates/emails/

        # For MVP: Use simple Python string templates
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: sans-serif; background: #f6f9fc; padding: 20px;">
            <div style="max-width: 580px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px;">
                <h1 style="color: #333; font-size: 24px;">Welcome to Board of One!</h1>
                <p style="color: #333; font-size: 16px; line-height: 26px;">
                    Hi {user_name or user_email},
                </p>
                <p style="color: #333; font-size: 16px; line-height: 26px;">
                    Thanks for joining Board of One. You now have access to:
                </p>
                <ul style="color: #333; font-size: 16px; line-height: 26px;">
                    <li>🧠 Multi-agent deliberation (up to 5 experts)</li>
                    <li>📊 Problem decomposition & synthesis</li>
                    <li>💾 Session history & exports</li>
                </ul>
                <p style="color: #333; font-size: 16px; line-height: 26px;">
                    <a href="https://boardof.one/new-session"
                       style="color: #5469d4; text-decoration: underline;">
                        Start your first deliberation →
                    </a>
                </p>
                <p style="color: #8898aa; font-size: 12px; margin-top: 32px;">
                    Questions? Reply to this email or visit our
                    <a href="https://boardof.one/help" style="color: #5469d4;">Help Center</a>.
                </p>
            </div>
        </body>
        </html>
        """
        return html

    @staticmethod
    def render_deliberation_complete_email(
        user_email: str,
        problem_title: str,
        session_id: str,
        summary: str,
        duration: str,
        rounds: int
    ) -> str:
        """Render deliberation complete email."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: sans-serif; background: #f6f9fc; padding: 20px;">
            <div style="max-width: 580px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px;">
                <h1 style="color: #333; font-size: 24px;">Your deliberation is complete! ✅</h1>
                <p style="color: #333; font-size: 16px; line-height: 26px;">
                    <strong>Problem:</strong> {problem_title}
                </p>
                <div style="background: #f6f9fc; padding: 16px; border-radius: 4px; margin: 16px 0;">
                    <p style="color: #666; font-size: 14px; margin: 4px 0;">
                        <strong>Duration:</strong> {duration}
                    </p>
                    <p style="color: #666; font-size: 14px; margin: 4px 0;">
                        <strong>Rounds:</strong> {rounds}
                    </p>
                </div>
                <h2 style="color: #333; font-size: 18px;">Summary</h2>
                <p style="color: #333; font-size: 16px; line-height: 26px;">
                    {summary[:300]}...
                </p>
                <p style="color: #333; font-size: 16px; line-height: 26px;">
                    <a href="https://boardof.one/sessions/{session_id}"
                       style="display: inline-block; background: #5469d4; color: white;
                              padding: 12px 24px; text-decoration: none; border-radius: 4px;">
                        View Full Results →
                    </a>
                </p>
                <p style="color: #8898aa; font-size: 12px; margin-top: 32px;">
                    Want to share your insights?
                    <a href="https://boardof.one/sessions/{session_id}/share"
                       style="color: #5469d4;">Share this deliberation</a>
                </p>
            </div>
        </body>
        </html>
        """
        return html
```

### 3.4 Email Triggers

**When to send emails**:

| Event | Template | Trigger | Priority | Tags |
|-------|----------|---------|----------|------|
| **User signup** | Welcome email | Supabase Auth webhook (`user.created`) | HIGH | `category:welcome` |
| **Email verification** | Verify email | Supabase Auth (built-in) | HIGH | `category:auth` |
| **Deliberation complete** | Summary + link | Session state = `completed` | MEDIUM | `category:session` |
| **Payment success** | Thank you + receipt | Stripe webhook (`invoice.paid`) | MEDIUM | `category:payment` |
| **Subscription cancel** | Feedback request | Stripe webhook (`subscription.deleted`) | LOW | `category:churn` |
| **Weekly digest** | Activity summary | Cron job (Sunday 6pm local time) | LOW | `category:digest` |

**Implementation** (`bo1/api/webhooks/supabase.py`):
```python
from fastapi import APIRouter, Request
from bo1.services.email import EmailService
from bo1.services.email_templates import EmailTemplates

router = APIRouter()

@router.post("/webhooks/supabase/auth")
async def handle_supabase_auth_webhook(request: Request):
    """Handle Supabase Auth webhooks (user signup)."""
    payload = await request.json()

    event_type = payload.get("type")
    user = payload.get("record")

    if event_type == "INSERT" and user:
        # Send welcome email
        user_email = user["email"]
        user_name = user.get("raw_user_meta_data", {}).get("name")

        html = EmailTemplates.render_welcome_email(user_email, user_name)

        await EmailService.send_email(
            to=user_email,
            subject="Welcome to Board of One! 🎉",
            html=html,
            tags=[{"name": "category", "value": "welcome"}]
        )

    return {"status": "ok"}

@router.post("/webhooks/deliberation/complete")
async def handle_deliberation_complete(session_id: str):
    """Send email when deliberation completes."""
    from bo1.state.redis_manager import RedisManager

    redis = RedisManager()
    state = redis.load_state(session_id)
    metadata = redis.load_metadata(session_id)

    user_email = metadata["user_email"]
    problem_title = state.problem_statement[:100]
    summary = state.final_synthesis.reasoning[:300]

    html = EmailTemplates.render_deliberation_complete_email(
        user_email=user_email,
        problem_title=problem_title,
        session_id=session_id,
        summary=summary,
        duration=f"{metadata['duration_seconds'] // 60} minutes",
        rounds=state.round_number
    )

    await EmailService.send_email(
        to=user_email,
        subject=f"Your deliberation is complete: {problem_title}",
        html=html,
        tags=[{"name": "category", "value": "session"}]
    )

    return {"status": "ok"}
```

### 3.5 Resend Configuration

**API Limits** (Free Tier):
- 3,000 emails/month
- 100 emails/day
- 10 emails/second
- 40KB max email size

**Upgrade Path**:
- $20/month: 50,000 emails
- $80/month: 500,000 emails
- Custom: 1M+ emails

**Monitoring**:
- Resend Dashboard: Delivery status, bounce rate, click tracking
- Webhooks: `email.delivered`, `email.bounced`, `email.complained`

**Best Practices**:
- ✅ Use tags for categorization (e.g., `category:welcome`, `user_tier:pro`)
- ✅ Track opens/clicks (optional, add `tracking=true` param)
- ✅ Handle bounces (webhook → mark user email as invalid)
- ✅ Respect unsubscribes (Resend auto-manages unsubscribe list)

### 3.6 GDPR Compliance for Emails

**Data Minimization**:
- Only send necessary emails (transactional only for MVP)
- No marketing emails without explicit consent

**User Rights**:
- User can opt out of non-transactional emails (weekly digest)
- Resend manages unsubscribe list automatically
- Transactional emails (password reset, receipts) CANNOT be opted out per GDPR Art. 6(1)(b)

**Data Retention**:
- Resend retains email logs for 30 days (delivery status)
- Email content NOT stored by Resend (only metadata)
- DPA available: https://resend.com/dpa

---

## 4. MVP Feature Checklist

### 4.1 Core Features (MUST HAVE)

- [ ] **User Authentication**
  - [ ] Google OAuth (Supabase)
  - [ ] LinkedIn OAuth (Supabase)
  - [ ] GitHub OAuth (Supabase)
  - [ ] Email/password fallback (Supabase)
  - [ ] Email verification (Supabase + Resend custom branding)
  - [ ] Password reset (Supabase + Resend custom branding)
  - [ ] JWT token management (auto-refresh)

- [ ] **Deliberation Engine** (LangGraph)
  - [ ] Console interface (v1 complete)
  - [ ] Web interface (streaming SSE)
  - [ ] Problem decomposition (1-5 sub-problems)
  - [ ] Persona selection (3-5 experts from 45 total)
  - [ ] Multi-round deliberation (5-15 rounds)
  - [ ] Facilitator orchestration (continue/vote/research/moderator)
  - [ ] Voting & consensus detection (semantic similarity)
  - [ ] Final synthesis
  - [ ] Checkpoint recovery (pause/resume)
  - [ ] Kill switches (user own, admin all)
  - [ ] Infinite loop prevention (5 layers)

- [ ] **Session Management**
  - [ ] Create new session
  - [ ] List user sessions (paginated)
  - [ ] View session details (full transcript)
  - [ ] Resume paused session
  - [ ] Delete session (soft delete → anonymization)
  - [ ] Export session (JSON, Markdown, PDF)
  - [ ] Share session (public link, optional)

- [ ] **Payment & Subscriptions** (Stripe)
  - [ ] Free tier (5 sessions/month, 5 rounds max)
  - [ ] Pro tier ($29/mo, 50 sessions/month, 15 rounds max)
  - [ ] Enterprise tier (custom pricing, unlimited)
  - [ ] Stripe Checkout integration
  - [ ] Stripe webhooks (subscription events)
  - [ ] Customer Portal (self-service cancellation)
  - [ ] Usage tracking (sessions, rounds, costs)
  - [ ] Invoice generation (Stripe auto-sends)

- [ ] **Admin Dashboard** (Weeks 10-11)
  - [ ] Real-time session monitoring (top 10 longest/expensive)
  - [ ] Runaway detection (>2x median duration)
  - [ ] One-click kill with confirmation
  - [ ] AI cost analytics (by phase, tier, time)
  - [ ] User engagement metrics (DAU, sessions/user, retention)
  - [ ] Revenue margin analysis
  - [ ] ntfy.sh alerts (runaway, daily/weekly cost reports)

- [ ] **Email Notifications** (Resend - NEW)
  - [ ] Welcome email (after signup)
  - [ ] Deliberation complete (with summary + link)
  - [ ] Payment receipt (thank you + invoice link)
  - [ ] Weekly digest (optional, opt-in)

### 4.2 Nice-to-Have (Post-MVP)

- [ ] **Advanced Features**
  - [ ] Time travel (rewind to any checkpoint)
  - [ ] Graph visualization (current node, available paths)
  - [ ] Human-in-loop breakpoints (approval gates)
  - [ ] Parallel sub-problem processing
  - [ ] Multi-session orchestration

- [ ] **Social Features**
  - [ ] Public deliberation gallery (opt-in sharing)
  - [ ] Social media sharing (Twitter, LinkedIn)
  - [ ] Embed widget (iframe for blogs)

- [ ] **Mobile**
  - [ ] iOS app (React Native)
  - [ ] Android app (React Native)

- [ ] **Integrations**
  - [ ] API for third-party apps
  - [ ] Zapier integration
  - [ ] Slack bot

---

## 5. Infrastructure Requirements

### 5.1 Production Environment

**Hosting Options**:

| Service | Provider | Cost | Pros | Cons |
|---------|----------|------|------|------|
| **Web Service** | Render.com | $7/mo (starter) | Easy deploy, auto-scaling | Limited free tier |
| **Web Service** | Railway.app | $5/mo + usage | Developer-friendly, monorepo support | Usage-based pricing |
| **Web Service** | Fly.io | $0 (free tier) | Global edge, fast | Complex config |
| **Database** | Supabase | $0 (free), $25 (pro) | Managed Postgres, Auth included | 500MB free limit |
| **Redis** | Upstash | $0 (free), $10 (pro) | Serverless, global | 10k commands/day free |
| **Reverse Proxy** | Traefik | Self-hosted | Full control, rate limiting | Requires management |

**Recommended Stack (MVP)**:
- **Web**: Render.com ($7/mo, 1 instance, auto-scaling up to 5)
- **Database**: Supabase Free Tier ($0, upgrade to Pro $25/mo when >500MB)
- **Redis**: Upstash Free Tier ($0, upgrade to $10/mo when >10k commands/day)
- **Email**: Resend Free Tier ($0, upgrade to $20/mo when >3k emails/month)
- **Stripe**: Pay-as-you-go (2.9% + 30¢ per transaction)
- **Total**: **$7/mo** initially, scales to ~$70/mo at 1,000 users

### 5.2 Domain & SSL

**Domain**: boardof.one (purchase via Namecheap or Cloudflare)
- Cost: $10-15/year

**DNS Records**:
```
A      boardof.one          → Render/Railway IP
CNAME  www.boardof.one      → boardof.one
CNAME  api.boardof.one      → boardof.one
TXT    boardof.one          → SPF: v=spf1 include:resend.com ~all
TXT    resend._domainkey...    → DKIM (from Resend)
TXT    _dmarc.boardof.one   → DMARC: v=DMARC1; p=none; rua=mailto:...
```

**SSL**: Auto-provisioned by Render/Railway (Let's Encrypt)

### 5.3 Environment Variables

**Required for Production**:
```bash
# App
ENVIRONMENT=production
LOG_LEVEL=info
SECRET_KEY=<random-256-bit-key>
ALLOWED_ORIGINS=https://boardof.one,https://www.boardof.one

# Database
DATABASE_URL=postgresql://user:pass@db.supabase.co:5432/postgres
SUPABASE_URL=https://xyz.supabase.co
SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>

# Redis
REDIS_URL=redis://default:pass@redis.upstash.io:6379

# LLM APIs
ANTHROPIC_API_KEY=<api-key>
VOYAGE_API_KEY=<api-key>

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Resend (NEW)
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=noreply@boardof.one
RESEND_FROM_NAME="Board of One"
RESEND_REPLY_TO=support@boardof.one

# ntfy.sh (Admin Notifications)
NTFY_SERVER=https://ntfy.sh
NTFY_TOPIC_RUNAWAY=bo1_runaway_sessions
NTFY_TOPIC_COST=bo1_cost_reports
NTFY_TOPIC_USERS=bo1_user_acquisition
NTFY_TOPIC_HEALTH=bo1_system_health

# Security
RATE_LIMIT_PER_MINUTE=60  # Free tier
RATE_LIMIT_PER_HOUR=1000
SESSION_TIMEOUT_HOURS=24
MAX_COST_PER_SESSION_USD=1.00
```

---

## 6. Security & Compliance

### 6.1 GDPR Checklist

- [ ] **Privacy Policy** (`/privacy-policy`) published
- [ ] **Terms of Service** (`/terms-of-service`) published
- [ ] **Cookie Consent Banner** (opt-in for analytics)
- [ ] **Data Export** endpoint (`/api/v1/user/export`)
- [ ] **Account Deletion** endpoint (`/api/v1/user/delete`)
- [ ] **Data Retention Policy** (365 days default, user configurable)
- [ ] **DPAs signed** with Supabase, Anthropic, Stripe, Resend
- [ ] **Audit Logs** for all data access (admin + user)
- [ ] **Encryption** (TLS 1.3 in transit, AES-256 at rest)
- [ ] **Breach Response Plan** documented (72-hour notification)

### 6.2 Security Hardening

- [ ] **Authentication**
  - [ ] JWT tokens (HS256, 1-hour expiry)
  - [ ] Refresh tokens (7-day expiry)
  - [ ] Rate limiting on login (5 attempts/hour)
  - [ ] Password requirements (min 8 chars, no common passwords)
  - [ ] Optional MFA (TOTP via Supabase)

- [ ] **API Security**
  - [ ] Rate limiting (60 req/min free, 300 req/min pro)
  - [ ] CORS configured (whitelist frontend domains)
  - [ ] Input validation (Pydantic models)
  - [ ] SQL injection prevention (parameterized queries)
  - [ ] XSS prevention (HTML escaping)

- [ ] **Infrastructure**
  - [ ] SSL/TLS 1.3 only (no TLS 1.0/1.1)
  - [ ] Security headers (CSP, HSTS, X-Frame-Options)
  - [ ] DDoS protection (Cloudflare or Traefik rate limiting)
  - [ ] Regular dependency updates (Dependabot)
  - [ ] Secrets in environment variables (never in code)

### 6.3 Data Backup & Recovery

- [ ] **PostgreSQL Backups**
  - [ ] Daily automatic backups (Supabase Pro)
  - [ ] Point-in-time recovery (PITR) enabled
  - [ ] Backup retention: 7 days (free), 30 days (pro)
  - [ ] Test restore procedure quarterly

- [ ] **Redis Persistence**
  - [ ] AOF enabled (append-only file)
  - [ ] Snapshots every 5 minutes
  - [ ] Backup retention: 7 days

- [ ] **Disaster Recovery Plan**
  - [ ] RTO (Recovery Time Objective): 4 hours
  - [ ] RPO (Recovery Point Objective): 1 hour
  - [ ] Runbook for common failures (DB down, Redis down, API down)

---

## 7. Monitoring & Observability

### 7.1 MVP Monitoring (Week 13)

**Health Checks**:
- [ ] `/api/health` endpoint (200 OK if app healthy)
- [ ] `/api/health/db` (PostgreSQL connection)
- [ ] `/api/health/redis` (Redis connection)
- [ ] `/api/health/anthropic` (API key valid)
- [ ] Uptime monitoring (UptimeRobot or Better Uptime, free tier)

**Admin Notifications** (ntfy.sh):
- [ ] Runaway session alerts (duration >2x median)
- [ ] Daily cost reports (9:00 AM UTC)
- [ ] Weekly cost summaries (Monday 9:00 AM UTC)
- [ ] System health alerts (error rate >5%, latency >2s)

**Manual Monitoring** (Admin Dashboard):
- [ ] Active sessions table (top 10 longest/expensive)
- [ ] Cost analytics (by phase, tier, time)
- [ ] User engagement metrics (DAU, sessions/user)

### 7.2 Post-MVP Monitoring (Week 14+)

**Sentry** (Error Tracking):
- [ ] Install Sentry SDK (`uv add sentry-sdk`)
- [ ] Configure error reporting (all uncaught exceptions)
- [ ] PII scrubbing (strip email addresses, user IDs)
- [ ] Release tracking (git commit SHA)
- [ ] Performance monitoring (transaction traces)

**PostHog** (Product Analytics):
- [ ] Install PostHog SDK (`uv add posthog`)
- [ ] Track key events (session start, session complete, upgrade, churn)
- [ ] Funnel analysis (signup → first session → upgrade)
- [ ] Retention cohorts (Day 1, 7, 30 retention)
- [ ] Feature flags (A/B testing)

**Prometheus + Grafana** (System Metrics - Optional):
- [ ] Prometheus exporter (`prometheus-fastapi-instrumentator`)
- [ ] Grafana dashboards (request rate, latency, error rate)
- [ ] Alerting (Slack/email on high error rate)

---

## 8. Pre-Launch Testing

### 8.1 Functional Testing

- [ ] **Authentication Flow**
  - [ ] Sign up with Google OAuth
  - [ ] Sign up with LinkedIn OAuth
  - [ ] Sign up with GitHub OAuth
  - [ ] Email verification
  - [ ] Password reset
  - [ ] Token refresh
  - [ ] Logout

- [ ] **Deliberation Flow**
  - [ ] Create new session (simple problem)
  - [ ] Create new session (complex problem)
  - [ ] Stream contributions in real-time (SSE)
  - [ ] Pause session (checkpoint saved)
  - [ ] Resume session (checkpoint restored)
  - [ ] Kill session (graceful shutdown)
  - [ ] Convergence detection (early stop)
  - [ ] Max rounds reached (hard cap)
  - [ ] Timeout watchdog (1-hour limit)
  - [ ] Cost kill switch ($1 limit)
  - [ ] Export results (JSON, Markdown, PDF)

- [ ] **Payment Flow**
  - [ ] Free tier signup (no payment)
  - [ ] Upgrade to Pro (Stripe Checkout)
  - [ ] Usage limits enforced (5 sessions → 50 sessions)
  - [ ] Payment success webhook (subscription.created)
  - [ ] Cancel subscription (Stripe Portal)
  - [ ] Downgrade to Free (usage limits restored)

- [ ] **Admin Dashboard**
  - [ ] View active sessions (real-time)
  - [ ] Kill runaway session (confirmation modal)
  - [ ] View cost analytics (by phase, tier)
  - [ ] View engagement metrics (DAU, retention)
  - [ ] Receive ntfy.sh alerts (runaway, daily cost)

### 8.2 Performance Testing

- [ ] **Load Testing** (Week 13)
  - [ ] Simulate 100 concurrent users (Locust or k6)
  - [ ] Target: <500ms median API latency (p50)
  - [ ] Target: <2s p95 API latency
  - [ ] Target: <5s p99 API latency
  - [ ] Target: 99.9% uptime (8.7 hours downtime/year)

- [ ] **Cost Testing**
  - [ ] Average deliberation cost <$0.15 (vs target $0.10)
  - [ ] Prompt caching working (60-70% cost reduction)
  - [ ] Summarization using Haiku (not Sonnet)

### 8.3 Security Testing

- [ ] **OWASP Top 10**
  - [ ] SQL Injection (parameterized queries)
  - [ ] XSS (HTML escaping)
  - [ ] CSRF (SameSite cookies)
  - [ ] Broken Authentication (JWT expiry, refresh tokens)
  - [ ] Sensitive Data Exposure (TLS 1.3, encrypted DB fields)
  - [ ] Broken Access Control (RLS in PostgreSQL)
  - [ ] Security Misconfiguration (security headers)
  - [ ] Using Components with Known Vulnerabilities (Dependabot)

- [ ] **Penetration Testing** (Optional for MVP, recommended for post-launch)
  - [ ] Third-party security audit (e.g., HackerOne bug bounty)

---

## 9. Go-Live Checklist

### 9.1 Week 13 (Final QA)

- [ ] All MVP features complete (Section 4.1)
- [ ] All tests passing (unit, integration, end-to-end)
- [ ] Load testing complete (100 concurrent users)
- [ ] Security audit complete (OWASP Top 10)
- [ ] GDPR compliance verified (privacy policy, cookie consent, data export)
- [ ] Email templates tested (welcome, deliberation complete, receipt)
- [ ] Admin dashboard functional (monitoring, analytics, kill switches)
- [ ] ntfy.sh alerts working (runaway, daily/weekly cost reports)

### 9.2 Week 14 (Launch Day)

**T-7 days (Monday)**:
- [ ] Final code freeze (only critical bug fixes)
- [ ] Staging environment smoke tests
- [ ] Backup production database (pre-launch snapshot)

**T-3 days (Friday)**:
- [ ] Deploy to production (blue-green deployment)
- [ ] Verify all environment variables set
- [ ] Verify DNS records (A, CNAME, TXT for SPF/DKIM)
- [ ] Verify SSL certificate (Let's Encrypt auto-renewed)
- [ ] Run production smoke tests (health checks, auth flow, payment flow)

**T-1 day (Sunday)**:
- [ ] Final smoke tests
- [ ] Monitor logs for errors
- [ ] Verify ntfy.sh alerts working
- [ ] Prepare launch announcement (Twitter, LinkedIn, ProductHunt)

**Launch Day (Monday 9:00 AM UTC)**:
- [ ] Make site public (remove "Coming Soon" page)
- [ ] Post launch announcement (social media)
- [ ] Monitor Sentry for errors (first 24 hours)
- [ ] Monitor Stripe webhooks (payment confirmations)
- [ ] Monitor Resend (email deliverability)
- [ ] Monitor admin dashboard (active sessions, costs)

**T+1 week**:
- [ ] Review Week 1 metrics (signups, sessions, costs, errors)
- [ ] Fix critical bugs (P0 issues)
- [ ] Gather user feedback (support emails, Twitter mentions)
- [ ] Plan Week 2 improvements

---

## 10. Post-Launch (Future Enhancements)

### 10.1 Week 15+ (Observability)

- [ ] **Sentry Integration** (Error Tracking)
  - [ ] Install SDK, configure error reporting
  - [ ] PII scrubbing, release tracking
  - [ ] Performance monitoring

- [ ] **PostHog Integration** (Product Analytics)
  - [ ] Install SDK, track key events
  - [ ] Funnel analysis, retention cohorts
  - [ ] Feature flags for A/B testing

### 10.2 Week 16+ (Advanced Features)

- [ ] **Time Travel** (rewind to any checkpoint)
- [ ] **Graph Visualization** (show current node, available paths)
- [ ] **Human-in-Loop** (approval gates, intervention points)
- [ ] **Parallel Processing** (process sub-problems concurrently)

### 10.3 Week 20+ (Mobile & Integrations)

- [ ] **Mobile Apps** (React Native)
  - [ ] iOS app (App Store)
  - [ ] Android app (Google Play)

- [ ] **API for Third-Party Integrations**
  - [ ] REST API with OAuth2
  - [ ] Zapier integration
  - [ ] Slack bot

---

## Summary

### MVP System Dependencies (14 Weeks)

| System | Status | Cost | Critical? | When? |
|--------|--------|------|-----------|-------|
| PostgreSQL (Supabase) | ✅ Planned | $0 (free) | YES | Week 3 |
| Redis (Upstash) | ✅ Complete | $0 (free) | YES | Week 1 |
| Supabase Auth | ✅ Planned | $0 (free) | YES | Week 3 |
| Stripe | ✅ Planned | 2.9% + 30¢ | YES | Week 5 |
| Anthropic API | ✅ Complete | Pay-as-you-go | YES | Week 1 |
| Voyage AI | ✅ Complete | Pay-as-you-go | YES | Week 1 |
| **Resend (NEW)** | 🔧 **Week 12** | $0 (3k emails/mo) | YES | **Week 12** |
| ntfy.sh | ✅ Planned | $0 (self-hosted) | NICE | Week 11 |
| Traefik | ✅ Planned | $0 (self-hosted) | YES | Week 9 |

### Post-MVP (Week 15+)

| System | Cost | When? |
|--------|------|-------|
| Sentry | $26/mo (Team plan, 50k errors/mo) | Week 15 |
| PostHog | $0 (free tier, <1M events/mo) | Week 16 |
| Prometheus + Grafana | $0 (self-hosted) | Optional |

### Total MVP Cost (First 3 Months)

**Development**: 14 weeks @ 1 engineer
**Infrastructure**: ~$7-10/mo initially
**LLM Usage**: ~$50-100/mo (testing + early users)
**Total First 3 Months**: ~$200 infrastructure + development time

**At 1,000 Users** (steady state):
- Infrastructure: ~$70/mo
- LLM usage: ~$1,000/mo (offset by Pro subscriptions)
- Email: ~$20/mo (Resend)
- Observability: ~$50/mo (Sentry + PostHog paid tiers)
- **Total**: ~$1,140/mo operational costs

---

**Questions?**
Contact: Technical Lead, Product Manager, Engineering Team

**Next Steps**:
1. Review & approve Resend integration (Section 3)
2. Confirm MVP feature scope (Section 4)
3. Begin Week 12 implementation (Resend setup + email templates)
4. Week 13: Final QA, security audit, load testing
5. Week 14: LAUNCH 🚀

---

**Document Status**: Ready for Review
**Approval Required From**:
- [ ] Technical Lead
- [ ] Product Manager
- [ ] Engineering Team

**Related Documents**:
- LangGraph Migration Proposal: `zzz_project/LANGGRAPH_MIGRATION_PROPOSAL.md`
- Executive Summary: `zzz_project/LANGGRAPH_EXECUTIVE_SUMMARY.md`
- Admin Dashboard Spec: `zzz_project/ADMIN_DASHBOARD_SPECIFICATION.md`
- Platform Architecture: `zzz_project/PLATFORM_ARCHITECTURE.md`
- Security & Compliance: `zzz_project/SECURITY_COMPLIANCE.md`
