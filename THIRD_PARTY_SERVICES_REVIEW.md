# Third-Party Services Review & Self-Hosted Alternatives

**Date**: 2025-01-17
**Purpose**: Review all 3rd party services in MVP roadmap and identify self-hosted alternatives where possible

---

## Executive Summary

**Current Status**:
- ✅ **2 services already self-hosted** (Supabase Auth, deployment infrastructure)
- ⚠️ **4 services need evaluation** (Stripe, Resend, ntfy.sh, monitoring)
- ✅ **3 services acceptable as SaaS** (Anthropic, Voyage AI, OAuth providers)

**Recommendation**: Replace Resend with self-hosted email, keep Stripe (no viable alternative), evaluate ntfy.sh vs self-hosted alerting, use self-hosted monitoring (Prometheus + Grafana).

---

## Services Analysis

### 1. Authentication & User Management

#### ✅ Supabase Auth - SELF-HOSTED (Week 6, Day 36)
- **Current**: Self-hosted GoTrue (Supabase's auth server) in Docker
- **Status**: Configured and documented
- **Rationale**: Full control, no vendor lock-in, eliminates costs
- **Decision**: ✅ **KEEP** self-hosted approach

---

### 2. Payments

#### ⚠️ Stripe - THIRD-PARTY SaaS (Week 8)
- **Current Plan**: Stripe Checkout + webhooks
- **Cost**: 2.9% + $0.30 per transaction
- **Self-Hosted Alternative**: None viable for production

**Evaluation of Alternatives**:

| Alternative | Pros | Cons | Verdict |
|-------------|------|------|---------|
| **OpenPayments** | Open-source payment rails | No credit card processing, complex setup | ❌ Not suitable |
| **Paddle** | Similar to Stripe, merchant of record | 5% + $0.50 (more expensive) | ❌ More expensive |
| **PayPal** | Widely accepted | Poor developer experience, higher fees | ❌ Worse UX |
| **Self-hosted billing** | Full control | PCI compliance nightmare, no card processing | ❌ Not viable |

**Recommendation**: ✅ **KEEP Stripe**
- Industry standard for SaaS
- Best developer experience
- PCI compliance handled
- Cost is reasonable (2.9% + $0.30)
- No viable self-hosted alternative exists

**Mitigation for Vendor Lock-in**:
- Abstract payment logic behind interface (`PaymentProvider` protocol)
- Allow future migration to Paddle/other if needed
- Store minimal data in Stripe (use our DB as source of truth)

---

### 3. Email (Transactional)

#### ✅ Resend - THIRD-PARTY SaaS (Week 12)
- **Current Plan**: Resend API for transactional emails
- **Cost**: $20/month (100K emails)
- **Self-Hosted Alternative**: Postal (considered but rejected)

**Evaluation of Alternatives**:

| Alternative | Pros | Cons | Verdict |
|-------------|------|------|---------|
| **Resend** | Best deliverability, modern API, great DX | $20/month | ✅ **CHOSEN** |
| **Postal** | Open-source, full-featured, great UI | IP reputation warmup, deliverability risk | ❌ Too risky |
| **Mailcow** | Self-hosted, mature | More complex, designed for general email | ❌ Not transactional-focused |
| **Mailu** | Docker-based, easy setup | Less transactional-focused | ❌ Not suitable |
| **SendGrid** | Reliable, free tier (100/day) | Vendor lock-in, API changes | ❌ Poor developer experience |
| **AWS SES** | Cheap ($0.10/1000) | Complex setup, reputation management | ❌ Too complex |

**Recommendation**: ✅ **KEEP Resend**

**Why Resend Over Self-Hosted**:

1. **Deliverability is Critical**
   - Transactional emails must reach inbox (password resets, session alerts)
   - Resend has established IP reputation (years of warmup)
   - Self-hosted requires 4+ weeks IP warmup with risk of blacklisting
   - Gmail/Outlook trust established senders (Resend) over new IPs

2. **Developer Experience**
   - Modern API, excellent documentation
   - Email templates with React components
   - Built-in analytics, bounce/spam tracking
   - Webhooks for delivery status

3. **Cost-Benefit Analysis**
   - $20/month for 100K emails is reasonable for reliability
   - Self-hosted: $4/month IP + time cost + deliverability risk
   - Deliverability failure cost >> $20/month savings

4. **Risk Mitigation**
   - Abstract email behind `EmailProvider` interface
   - Easy to migrate to SendGrid/Postmark/AWS SES if needed
   - Store email templates in our codebase (portable)

**Resend Setup**:
```typescript
// backend/api/email/provider.ts
interface EmailProvider {
  send(to: string, template: string, data: any): Promise<void>
}

class ResendProvider implements EmailProvider {
  async send(to: string, template: string, data: any) {
    await resend.emails.send({
      from: 'Board of One <noreply@boardofone.com>',
      to,
      subject: templates[template].subject,
      html: renderTemplate(template, data)
    })
  }
}
```

**Implementation Plan**:
- Week 12: Integrate Resend SDK
- Create email templates (password reset, session complete, cost alerts)
- Set up webhook handlers (delivery, bounce, spam)
- Configure domain (boardofone.com) with DNS records
- Test deliverability across providers (Gmail, Outlook, ProtonMail)

---

### 4. Alerting & Notifications

#### ⚠️ ntfy.sh - THIRD-PARTY SaaS (Weeks 10-11)
- **Current Plan**: ntfy.sh for admin alerts (runaway sessions, cost reports)
- **Cost**: Free (self-hosted or public server)
- **Self-Hosted Alternative**: **ntfy.sh (self-hosted)** or **Alertmanager**

**Evaluation**:

| Alternative | Pros | Cons | Verdict |
|-------------|------|------|---------|
| **ntfy.sh (self-hosted)** | Same features, privacy, simple | Need to run server | ✅ **RECOMMENDED** |
| **Alertmanager** | Integrates with Prometheus, powerful | More complex, overkill for simple alerts | ⚙️ If using Prometheus |
| **Gotify** | Simple, self-hosted, WebSocket | Less mature, fewer integrations | ⚙️ Possible |
| **ntfy.sh (public)** | Zero setup | Data leaves infrastructure | ❌ Privacy concern |

**Recommendation**: ✅ **SELF-HOST ntfy.sh**

**ntfy.sh Self-Hosted Setup**:
```yaml
# docker-compose.yml
services:
  ntfy:
    image: binwiederhier/ntfy:latest
    command: serve
    ports:
      - "8888:80"  # Web UI + API
    volumes:
      - ntfy-data:/var/lib/ntfy
      - ./ntfy/server.yml:/etc/ntfy/server.yml
    environment:
      - NTFY_BASE_URL=https://alerts.boardofone.com
      - NTFY_CACHE_FILE=/var/lib/ntfy/cache.db
```

**Benefits**:
- **Cost**: $0/month (vs $0 public ntfy.sh, but with privacy)
- **Privacy**: Alerts stay within infrastructure
- **Control**: Custom retention, rate limits, access control
- **Features**: Web UI, mobile apps (iOS/Android), webhooks

**Implementation Plan**:
- Week 10: Add ntfy to `docker-compose.yml`
- Configure subdomain (alerts.boardofone.com)
- Create topics (runaway-sessions, cost-alerts, errors)
- Integrate with admin dashboard
- Test mobile app notifications

---

### 5. Monitoring & Observability

#### ⚠️ Prometheus + Grafana OR Datadog (Week 9, Day 42.5 recommendations)
- **Current Plan**: "Prometheus + Grafana or Datadog"
- **Cost**: Datadog ~$15/host/month, Prometheus + Grafana = free
- **Self-Hosted Alternative**: **Prometheus + Grafana** (already listed!)

**Recommendation**: ✅ **USE Prometheus + Grafana (self-hosted)**

**Setup**:
```yaml
# docker-compose.yml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false

  node-exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
```

**Metrics to Track**:
- Connection pool: Size, active connections, wait time
- API latency: P50, P95, P99
- Deliberation cost: Per session, per day, per user
- LLM usage: Tokens, cost, cache hit rate
- Redis: Memory usage, keyspace, evictions
- PostgreSQL: Connections, query time, cache hit ratio

**Benefits**:
- **Cost**: $0/month (vs $15/month Datadog)
- **Privacy**: Metrics stay within infrastructure
- **Control**: Custom dashboards, retention policies
- **Ecosystem**: Industry standard, extensive integrations

---

### 6. Secrets Management

#### ⚠️ Doppler / AWS Secrets Manager / 1Password (Week 3.5, Day 21)
- **Current Plan**: "Doppler, AWS Secrets Manager, or 1Password"
- **Self-Hosted Alternative**: **Vault by HashiCorp** or **Git-crypt**

**Evaluation**:

| Alternative | Pros | Cons | Verdict |
|-------------|------|------|---------|
| **Vault (HashiCorp)** | Industry standard, powerful | Complex setup, overkill for small team | ⚙️ Future consideration |
| **Git-crypt** | Simple, Git-native | Not a secrets manager, basic | ⚙️ For small teams |
| **Infisical** | Open-source, modern UI, Kubernetes-ready | Newer, less mature | ✅ **RECOMMENDED** |
| **Doppler** | Great UX, team-friendly | Vendor lock-in, $10/user/month | ❌ Paid SaaS |
| **1Password** | Secure, CLI support | Not designed for app secrets, $7.99/user/month | ❌ Paid SaaS |
| **AWS Secrets Manager** | Integrated with AWS | Vendor lock-in, $0.40/secret/month | ❌ AWS dependency |

**Recommendation**: ✅ **USE Infisical (self-hosted)**

**Infisical Setup**:
```yaml
# docker-compose.yml
services:
  infisical:
    image: infisical/infisical:latest
    ports:
      - "8080:8080"
    environment:
      - ENCRYPTION_KEY=${INFISICAL_ENCRYPTION_KEY}
      - JWT_SECRET=${INFISICAL_JWT_SECRET}
      - MONGO_URL=mongodb://mongo:27017/infisical
    depends_on:
      - mongo

  mongo:
    image: mongo:6
    volumes:
      - infisical-mongo:/data/db
```

**Benefits**:
- **Cost**: $0/month (vs $10/user Doppler)
- **Privacy**: Secrets stay within infrastructure
- **Features**: Web UI, CLI, SDKs, access control, audit logs
- **Team-friendly**: Role-based access, multiple projects/environments

**Alternative for Minimal Setup**:
- Use `.env` files with `git-crypt` for small team (<5 people)
- Migrate to Infisical when team grows

---

### 7. LLM APIs (Anthropic, Voyage AI)

#### ✅ Anthropic Claude API - THIRD-PARTY SaaS
- **Status**: Core product dependency
- **Cost**: Pay-as-you-go (~$0.12/deliberation)
- **Self-Hosted Alternative**: None viable

**Recommendation**: ✅ **KEEP Anthropic**
- No self-hosted alternative for Claude 4.5 quality
- Open-source LLMs (LLaMA, Mistral) don't match quality for reasoning tasks
- Self-hosting would require expensive GPUs ($1000+/month)

#### ✅ Voyage AI Embeddings API - THIRD-PARTY SaaS
- **Status**: Research cache feature
- **Cost**: $0.06/1M tokens (10x cheaper than OpenAI)
- **Self-Hosted Alternative**: **sentence-transformers** (possible)

**Evaluation**:

| Alternative | Pros | Cons | Verdict |
|-------------|------|------|---------|
| **Voyage AI** | Best quality, cheap | Vendor dependency | ✅ **KEEP** for MVP |
| **sentence-transformers** | Free, self-hosted | Lower quality, GPU needed | ⚙️ Future consideration |
| **OpenAI ada-002** | Good quality | 10x more expensive | ❌ More expensive |

**Recommendation**: ✅ **KEEP Voyage AI for MVP**
- Cost is minimal ($0.06/1M tokens)
- Quality is excellent for semantic search
- Can migrate to self-hosted `sentence-transformers` later if needed

---

### 8. OAuth Providers (Google, LinkedIn, GitHub)

#### ✅ OAuth Providers - THIRD-PARTY SaaS
- **Status**: Authentication delegation
- **Cost**: Free
- **Self-Hosted Alternative**: None (by definition)

**Recommendation**: ✅ **KEEP OAuth providers**
- Users expect social login
- Free to use
- No data stored with providers (only used for auth)
- Self-hosting OAuth would defeat the purpose

---

### 9. Deployment Platform

#### ✅ DigitalOcean - INFRASTRUCTURE SaaS
- **Current Plan**: DigitalOcean Droplets + App Platform
- **Cost**: ~$20-50/month (droplets)
- **Self-Hosted Alternative**: Own data center (not viable)

**Recommendation**: ✅ **KEEP DigitalOcean**
- Self-managed VPS (full control, no lock-in)
- Can migrate to Hetzner, Linode, Vultr, etc. with minimal effort
- Docker-first approach makes migration easy

---

## Implementation Roadmap Changes

### Week 8 (Payments + Rate Limiting + GDPR)
- **KEEP**: Stripe integration (no viable alternative)
- **UPDATE**: Add payment abstraction layer (`PaymentProvider` interface)

### Week 10-11 (Admin Dashboard + Monitoring)
- **REPLACE**: ntfy.sh public → ntfy.sh self-hosted
- **REPLACE**: "Prometheus + Grafana or Datadog" → "Prometheus + Grafana (self-hosted)"
- **ADD**: Infisical for secrets management

### Week 12 (Email Integration)
- **REPLACE**: Resend → Postal (self-hosted)
- **ADD**: IP warmup schedule (Week 12, Day 1-3)
- **ADD**: DNS configuration (SPF, DKIM, DMARC)

---

## Summary of Changes

### Services to Self-Host (4)
1. ✅ **Supabase Auth** → Self-hosted GoTrue (DONE)
2. ✅ **ntfy.sh** → Self-hosted ntfy.sh (Week 10)
3. ✅ **Monitoring** → Prometheus + Grafana (Week 9/10)
4. ✅ **Secrets** → Infisical self-hosted (Week 3.5 update)

### Services to Keep as SaaS (6)
1. ✅ **Stripe** - No viable alternative, industry standard
2. ✅ **Resend** - Deliverability critical, established reputation
3. ✅ **Anthropic Claude** - Core product, no alternative
4. ✅ **Voyage AI** - Low cost, high quality (can migrate later)
5. ✅ **OAuth Providers** - By definition, can't self-host
6. ✅ **DigitalOcean** - Infrastructure (self-managed VPS, easy migration)

---

## Cost Comparison

| Service | SaaS Cost/Month | Self-Hosted Cost/Month | Decision |
|---------|----------------|------------------------|----------|
| **Resend** | $20 | $4 (+ deliverability risk) | **Keep SaaS** |
| **ntfy.sh** | $0 (public) | $0 (self-hosted) | **Self-host** (privacy) |
| **Monitoring** | $15 (Datadog) | $0 (Prometheus + Grafana) | **Self-host** ($15/mo saved) |
| **Secrets** | $10 (Doppler) | $0 (Infisical) | **Self-host** ($10/mo saved) |
| **Total Savings** | | | **$25/month** |

**Annual Savings**: $300/year (prioritizing deliverability over cost)

**Additional Benefits**:
- Privacy: No data leaves infrastructure
- Control: Full customization, no API limits
- Portability: Easy migration between cloud providers
- Compliance: Easier GDPR compliance (no third-party data processors)

---

## Next Steps

1. **Week 10** (Admin Dashboard):
   - Add ntfy.sh to `docker-compose.yml`
   - Add Prometheus + Grafana to `docker-compose.yml`
   - Create Grafana dashboards for key metrics

2. **Week 12** (Email Integration):
   - Integrate Resend SDK
   - Create email templates (React components)
   - Configure boardofone.com domain with Resend
   - Set up webhook handlers (delivery, bounce, spam)
   - Test deliverability across email providers

3. **Week 3.5 Update** (Retroactive):
   - Document Infisical as recommended secrets manager
   - Add Infisical setup instructions to `CLAUDE.md`

4. **Update Roadmap**:
   - Keep Resend for email (deliverability priority)
   - Replace "Prometheus + Grafana or Datadog" with "Prometheus + Grafana"
   - Replace "Doppler, AWS Secrets Manager, or 1Password" with "Infisical (self-hosted)"
   - Add ntfy.sh self-hosted setup to Week 10
   - Document email abstraction layer (`EmailProvider` interface)

---

## Conclusion

**Self-Hosting Strategy**: Maximize control and privacy while keeping critical SaaS dependencies where no viable alternative exists.

**Final Stack**:
- ✅ **Self-Hosted**: Auth (Supabase/GoTrue), Alerts (ntfy.sh), Monitoring (Prometheus + Grafana), Secrets (Infisical)
- ✅ **SaaS**: Email (Resend), Payments (Stripe), LLM (Anthropic), Embeddings (Voyage AI), OAuth (Google/LinkedIn/GitHub), Infrastructure (DigitalOcean)

**Result**: Production-grade stack with minimal vendor lock-in, maximum privacy, prioritizing deliverability over cost ($300/year savings).
