# Authentication Provider Evaluation for Board of One

**Date:** 2025-11-20
**Context:** Evaluating auth providers after discovering Supabase GoTrue doesn't support server-side PKCE for external OAuth

## Requirements

- **Confidential data protection**: Business strategy, PII
- **Cost attack prevention**: Users can incur LLM costs
- **Zero token exposure**: Tokens never in frontend
- **BFF pattern**: Backend-for-Frontend with httpOnly cookies
- **OAuth providers**: Google, LinkedIn, GitHub
- **Self-hosted**: Must run in Docker
- **Production-ready**: Stable, well-documented

---

## Option 1: Keycloak ⭐ **RECOMMENDED**

### Pros
- ✅ **Industry standard** (Red Hat, enterprise-grade)
- ✅ **Full OAuth 2.0/OIDC support** (all flows, including Authorization Code + PKCE)
- ✅ **Server-side token exchange** (exactly what we need)
- ✅ **Battle-tested** (used by Fortune 500)
- ✅ **Self-hosted** (Docker image available)
- ✅ **Multi-provider** (Google, GitHub, LinkedIn, SAML, etc.)
- ✅ **Admin UI** (user management, audit logs)
- ✅ **Token management** (refresh, revocation, rotation)
- ✅ **RBAC built-in** (roles, permissions, groups)
- ✅ **Extensive docs** (10+ years of documentation)
- ✅ **Active community** (millions of deployments)

### Cons
- ❌ **Heavy** (~500MB Docker image, Java-based)
- ❌ **Complex setup** (many configuration options)
- ❌ **Learning curve** (steeper than alternatives)
- ⚠️ **Resource intensive** (requires 1-2GB RAM)
- ⚠️ **Slower startup** (15-30 seconds)

### Architecture Fit
- **Perfect for BFF pattern** (designed for it)
- **Backend exchanges code** with Keycloak
- **Keycloak exchanges with Google**
- **Tokens stored in Keycloak session**
- **Backend gets session cookie** (httpOnly)

### Implementation Estimate
- **Setup time**: 1 day (Docker, config, realm setup)
- **Integration time**: 1 day (backend endpoints, middleware)
- **Total**: 2 days

### Best For
- Production apps with security requirements
- Enterprise customers
- Need audit trails and compliance
- Future SSO/SAML needs

---

## Option 2: Authentik

### Pros
- ✅ **Modern UI** (React-based, beautiful admin panel)
- ✅ **Full OAuth/OIDC support** (Authorization Code + PKCE)
- ✅ **Self-hosted** (Docker Compose stack)
- ✅ **Lightweight** (~200MB vs Keycloak's 500MB)
- ✅ **Fast startup** (5-10 seconds)
- ✅ **Good docs** (well-organized, modern)
- ✅ **Flow-based policies** (flexible authorization)
- ✅ **Multi-tenancy** (if you need it later)
- ✅ **Active development** (frequent updates)

### Cons
- ⚠️ **Younger project** (2019 vs Keycloak's 2014)
- ⚠️ **Smaller community** (less Stack Overflow content)
- ⚠️ **Fewer integrations** (growing, but not as extensive)
- ❌ **Less enterprise adoption** (fewer case studies)
- ⚠️ **Breaking changes** (still pre-1.0 mentality)

### Architecture Fit
- **Works for BFF pattern**
- **Server-side token exchange** supported
- **Session management** built-in
- **Similar flow to Keycloak**

### Implementation Estimate
- **Setup time**: 0.5 days (simpler config)
- **Integration time**: 1 day (backend integration)
- **Total**: 1.5 days

### Best For
- Startups wanting modern UX
- Teams preferring Python ecosystem (it's Django-based)
- Need something lighter than Keycloak
- Okay with slightly less stability

---

## Option 3: SuperTokens

### Pros
- ✅ **Built for BFF pattern** (explicitly designed for it!)
- ✅ **Session management** (automatic refresh, revocation)
- ✅ **Lightweight** (~50MB Docker image)
- ✅ **Developer-friendly** (SDKs for Python/FastAPI)
- ✅ **Modern docs** (excellent tutorials, examples)
- ✅ **Active development** (Y Combinator backed)
- ✅ **Fast integration** (pre-built FastAPI middleware)
- ✅ **Multi-tenancy** (built-in)
- ✅ **Open core model** (self-hosted free, cloud paid)

### Cons
- ❌ **Youngest project** (2020)
- ⚠️ **Smallest community** (limited Stack Overflow)
- ⚠️ **Fewer OAuth providers** (Google, GitHub, Apple out of box)
- ⚠️ **Less battle-tested** (fewer large deployments)
- ⚠️ **Vendor risk** (startup, could pivot/shutdown)
- ❌ **LinkedIn OAuth not built-in** (need custom provider)

### Architecture Fit
- **PERFECT for BFF** (this is their main use case)
- **Session cookies** (httpOnly by default)
- **Backend SDK** handles everything
- **Minimal code** needed

### Implementation Estimate
- **Setup time**: 0.25 days (docker-compose up)
- **Integration time**: 0.5 days (SDK installation)
- **Total**: 0.75 days (FASTEST)

### Best For
- Fast MVP to production
- Teams wanting minimal auth code
- Python/FastAPI projects (we are!)
- Okay with smaller ecosystem

---

## Option 4: Direct Google OAuth (Option A from earlier)

### Pros
- ✅ **Maximum control** (you own all code)
- ✅ **Zero dependencies** (no auth service)
- ✅ **Lightest weight** (no extra containers)
- ✅ **Exactly what you need** (no extra features)
- ✅ **Easy to debug** (all code in your repo)
- ✅ **No vendor lock-in**

### Cons
- ❌ **Most code to write** (~500 lines)
- ❌ **You maintain auth logic** (security responsibility)
- ❌ **No admin UI** (must build user management)
- ❌ **Each provider = more code** (LinkedIn, GitHub separate)
- ❌ **No token management** (must build refresh, revocation)
- ❌ **No audit logs** (must build yourself)

### Implementation Estimate
- **Google OAuth**: 1 day
- **Session management**: 0.5 days (already have Redis)
- **Token refresh**: 0.5 days
- **Per additional provider**: 0.5 days each
- **Total**: 2 days (Google only), 3+ days (all providers)

### Best For
- Full control freaks
- Learning exercise
- Very specific requirements
- Not recommended for production security-critical apps

---

## Comparison Matrix

| Feature | Keycloak | Authentik | SuperTokens | Direct OAuth |
|---------|----------|-----------|-------------|--------------|
| **BFF Support** | ✅ Perfect | ✅ Good | ✅ Perfect | ✅ DIY |
| **Server-side PKCE** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **OAuth Providers** | ✅ All | ✅ Most | ⚠️ Major | ⚠️ Manual |
| **Battle-tested** | ✅ Enterprise | ⚠️ Growing | ⚠️ Startup | ❌ You |
| **Resource Usage** | ❌ Heavy | ✅ Medium | ✅ Light | ✅ Minimal |
| **Setup Time** | ⚠️ 1 day | ✅ 0.5 day | ✅ 0.25 day | ❌ 2+ days |
| **Maintenance** | ✅ Low | ✅ Low | ✅ Low | ❌ High |
| **Admin UI** | ✅ Full | ✅ Modern | ✅ Basic | ❌ None |
| **Audit Logs** | ✅ Built-in | ✅ Built-in | ✅ Built-in | ❌ DIY |
| **Community** | ✅ Huge | ⚠️ Growing | ⚠️ Small | N/A |
| **Docs Quality** | ✅ Extensive | ✅ Good | ✅ Great | ⚠️ Google's |

---

## Security Comparison

All four options support proper BFF pattern with zero frontend token exposure:

| Security Feature | Keycloak | Authentik | SuperTokens | Direct OAuth |
|------------------|----------|-----------|-------------|--------------|
| **Authorization Code Flow** | ✅ | ✅ | ✅ | ✅ |
| **PKCE Support** | ✅ | ✅ | ✅ | ✅ |
| **httpOnly Cookies** | ✅ | ✅ | ✅ | ✅ (DIY) |
| **Token Refresh** | ✅ Auto | ✅ Auto | ✅ Auto | ❌ Manual |
| **Token Revocation** | ✅ | ✅ | ✅ | ❌ Manual |
| **Session Management** | ✅ | ✅ | ✅ | ⚠️ Redis |
| **CSRF Protection** | ✅ | ✅ | ✅ | ❌ DIY |
| **Rate Limiting** | ✅ | ✅ | ⚠️ Basic | ❌ DIY |
| **Audit Logs** | ✅ Full | ✅ Full | ✅ Basic | ❌ None |

**Verdict:** All dedicated auth providers are equally secure. Direct OAuth requires you to implement all security features.

---

## Recommendations by Scenario

### Scenario 1: **Best Overall Choice** ⭐
**KEYCLOAK**

**When:**
- Production app with real users
- Need maximum security confidence
- Okay with 1-2GB RAM usage
- Want enterprise-grade stability

**Why:**
- Industry standard (can't get fired for choosing Keycloak)
- Most mature codebase
- Best documentation and community support
- Future-proof (SSO, SAML if needed)

---

### Scenario 2: **Best Developer Experience**
**SUPERTOKENS**

**When:**
- Want to ship fast
- Using Python/FastAPI (we are!)
- BFF pattern is primary goal
- Okay with smaller ecosystem

**Why:**
- Built specifically for BFF pattern
- FastAPI SDK makes integration trivial
- Fastest implementation (0.75 days)
- Modern, developer-friendly docs

---

### Scenario 3: **Best Middle Ground**
**AUTHENTIK**

**When:**
- Want modern UI for managing users
- Need lighter footprint than Keycloak
- Growing startup (might need multi-tenancy)
- Python-friendly team

**Why:**
- Best admin UI of all options
- Lighter than Keycloak, more mature than SuperTokens
- Good balance of features vs complexity
- Active development, growing community

---

### Scenario 4: **Maximum Control**
**DIRECT GOOGLE OAUTH**

**When:**
- Very specific security requirements
- Team has strong auth expertise
- Want zero external dependencies
- Willing to maintain auth code

**Why:**
- You control everything
- No vendor lock-in
- Minimal resource usage
- Learn auth deeply

---

## Final Recommendation for Board of One

### 🏆 **PRIMARY RECOMMENDATION: KEYCLOAK**

**Reasoning:**
1. **Your security requirements are HIGH** (confidential data, PII, cost attacks)
2. **Enterprise-grade = peace of mind** (can show customers/investors)
3. **Most battle-tested** (proven in production at scale)
4. **Future-proof** (if you need SSO for enterprise customers)
5. **Best documentation** (easier for team to maintain)

**Resource cost is acceptable:**
- You're already running Postgres, Redis, Supabase
- 1-2GB RAM for auth service is standard
- Worth it for security-critical application

---

### 🥈 **RUNNER-UP: SUPERTOKENS**

**If you prioritize:**
- Fastest implementation (ship by tomorrow)
- Developer experience over maturity
- Lightweight over enterprise features
- You're comfortable with younger project

**Perfect for:**
- Getting to market quickly
- Can always migrate to Keycloak later if needed
- BFF pattern is your only requirement

---

## Implementation Plan (Next Message)

I'll write detailed implementation plans for:
1. **Keycloak integration** (recommended)
2. **SuperTokens integration** (fast alternative)
3. **Direct Google OAuth** (Option A from earlier, for reference)

Each plan will include:
- Docker configuration
- Backend code changes
- Frontend code changes
- Testing checklist
- Migration from current Supabase setup

**Which would you like to see first?**
