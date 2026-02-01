# SEO Analysis & Implementation Report for boardof.one

**Date:** 2026-02-01
**Status:** Analysis Complete, Implementation Pending

---

## Executive Summary

Board of One has solid technical SEO foundations but critical gaps in content strategy and search visibility. The site is well-built but essentially invisible to search engines for target keywords.

**Key Problems:**

1. **Zero search visibility** - doesn't rank for any target keywords
2. **Only ~11 indexed URLs** - far too thin for topical authority
3. **No programmatic content** - missing the "decision library" opportunity
4. **High-friction conversion** - "Request Early Access" as primary CTA

---

## Current State Analysis

### Technical SEO (Score: 7/10)

| Component      | Status     | Notes                                    |
| -------------- | ---------- | ---------------------------------------- |
| robots.txt     | ✅ Good    | Proper disallows, AI crawlers allowed    |
| sitemap.xml    | ✅ Good    | Dynamic, includes blog posts             |
| Meta tags      | ✅ Good    | Title, description, OG, Twitter cards    |
| Schema markup  | ⚠️ Partial | Article/Blog schema only                 |
| Canonical tags | ✅ Present | On landing page                          |
| /pricing       | ✅ Fixed   | Full page exists (was previously broken) |

**Current Schema Implementation:**

- `frontend/src/lib/utils/jsonld.ts` has `createArticleSchema()` and `createBlogSchema()`
- Missing: Organization, FAQPage, SoftwareApplication, BreadcrumbList

**Missing Schema Types:**

```json
// Organization (homepage) - MISSING
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Board of One",
  "url": "https://boardof.one",
  "logo": "https://boardof.one/logo.png",
  "description": "AI-powered management operating system for founders",
  "sameAs": []
}

// FAQPage (homepage has FAQ section but no markup) - MISSING
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is Board of One?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "..."
      }
    }
  ]
}

// SoftwareApplication - MISSING
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Board of One",
  "applicationCategory": "BusinessApplication",
  "operatingSystem": "Web",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "GBP"
  }
}

// BreadcrumbList (blog posts) - MISSING
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [...]
}
```

### Content SEO (Score: 2/10)

| Metric           | Current | Target |
| ---------------- | ------- | ------ |
| Indexed pages    | ~11     | 100+   |
| Blog posts       | 2       | 50+    |
| Decision pages   | 0       | 60+    |
| Use case pages   | 0       | 10+    |
| Comparison pages | 0       | 5+     |

**Critical Gap:** No content targeting actual search queries founders make.

**Current Sitemap Pages:**

- `/` (homepage)
- `/blog` (listing)
- `/features`
- `/pricing`
- `/about`
- `/waitlist`
- `/legal/privacy`
- `/legal/terms`
- `/legal/cookies`
- - 2 blog posts

### Search Visibility (Score: 1/10)

- **Zero rankings** for target keywords
- Doesn't appear for "founder decision software", "solo founder management", etc.
- Competitors (OnBoard, Govenda, BoardEffect) dominate board/decision software space
- No backlinks from authoritative sources

**Target Keywords (not ranking):**

- "founder decision making tool"
- "solo founder management"
- "AI advisory board"
- "startup decision framework"
- "hire vs contractor decision"
- "freemium vs paid trial"
- "when to raise funding"

### Conversion (Score: 6/10)

| Element           | Status                                             |
| ----------------- | -------------------------------------------------- |
| Value proposition | ✅ Clear ("Management-Grade Thinking")             |
| Multiple CTAs     | ✅ 4x placement throughout page                    |
| Testimonials      | ✅ 3 quotes with context                           |
| Social proof      | ⚠️ No logos/metrics/customer count                 |
| Demo/sandbox      | ❌ Missing - samples exist but no interactive demo |
| Pricing clarity   | ✅ Full pricing page exists                        |
| Trust badges      | ❌ Missing (GDPR mentioned but no badge)           |

---

## Verified Findings vs ChatGPT Analysis

| ChatGPT Claim           | Verified      | Notes                                |
| ----------------------- | ------------- | ------------------------------------ |
| Blog is empty           | ✅ TRUE       | Only 2 posts in sitemap              |
| One long homepage       | ⚠️ PARTIAL    | /features, /about, /pricing exist    |
| Decision pages needed   | ✅ TRUE       | Highest leverage opportunity         |
| Duplicate content issue | ❓ UNVERIFIED | Need GSC access to confirm           |
| Schema missing          | ✅ TRUE       | No FAQPage, Organization on homepage |
| Pricing broken          | ❌ FALSE      | Full pricing page exists             |

---

## Implementation Plan

### Phase 1: Technical Foundation (Week 1)

**1.1 Add missing schema markup to homepage**

File: `frontend/src/routes/+page.svelte`

Add to `<svelte:head>`:

- Organization schema
- FAQPage schema (FAQ section already exists in UI)
- SoftwareApplication schema

**1.2 Extend jsonld.ts utilities**

File: `frontend/src/lib/utils/jsonld.ts`

Add functions:

- `createOrganizationSchema()`
- `createFAQSchema(faqs: Array<{question: string, answer: string}>)`
- `createSoftwareApplicationSchema()`
- `createBreadcrumbSchema(items: Array<{name: string, url: string}>)`

**1.3 Add breadcrumbs to blog posts**

File: `frontend/src/routes/blog/[slug]/+page.svelte`

Add BreadcrumbList schema: Home → Blog → [Post Title]

### Phase 2: Decision Library (Weeks 2-3)

**2.1 Create programmatic routes**

```
/decisions/[category]/[slug]
```

Example URLs:

- `/decisions/hiring/first-engineer-vs-contractors`
- `/decisions/pricing/freemium-vs-paid-trial`
- `/decisions/fundraising/raise-now-vs-bootstrap`
- `/decisions/product/build-vs-buy`
- `/decisions/growth/paid-ads-vs-content-marketing`

**2.2 Decision page template structure**

```svelte
<!-- frontend/src/routes/decisions/[category]/[slug]/+page.svelte -->

<svelte:head>
  <title>{decision.question} | Board of One</title>
  <meta name="description" content="{decision.metaDescription}" />
  <!-- Article + FAQPage + HowTo schema -->
</svelte:head>

<article>
  <Breadcrumbs items={[
    { name: 'Home', url: '/' },
    { name: 'Decisions', url: '/decisions' },
    { name: category.name, url: `/decisions/${category.slug}` },
    { name: decision.title, url: currentUrl }
  ]} />

  <h1>{decision.question}</h1>

  <section class="founder-context">
    <!-- Stage, constraints, typical situation -->
  </section>

  <section class="board-analysis">
    <!-- Simulated Board of One output -->
  </section>

  <section class="deep-dive">
    <!-- 800-1500 words explanation -->
  </section>

  <section class="faq">
    <!-- 6-10 related questions -->
  </section>

  <section class="cta">
    <!-- "Run this decision in Board of One" -->
  </section>
</article>
```

**2.3 Content categories**

| Category    | Example Decisions                                      | Target Pages |
| ----------- | ------------------------------------------------------ | ------------ |
| Hiring      | First hire, contractors vs FTE, when to hire Head of X | 10           |
| Pricing     | Freemium vs paid, price increases, bundling            | 8            |
| Fundraising | Raise vs bootstrap, timing, amount                     | 8            |
| Product     | Build vs buy, feature prioritization, pivots           | 10           |
| Growth      | Channel selection, paid vs organic, partnerships       | 8            |
| Operations  | Tools, processes, automation                           | 8            |
| Strategy    | Market entry, competition, positioning                 | 8            |

**Target:** 60 decision pages total

**2.4 Content backend options**

Option A: Static markdown in repo

```
/content/decisions/hiring/first-engineer.md
```

Option B: API endpoint + admin

```
GET /api/v1/decisions/{category}/{slug}
```

Recommend Option A for simplicity and build-time generation.

### Phase 3: Supporting Pages (Week 4)

**3.1 Use case pages**

| URL                                 | Target Keyword                      |
| ----------------------------------- | ----------------------------------- |
| `/use-cases/delay-management-hires` | "delay hiring managers startup"     |
| `/use-cases/founder-bottleneck`     | "founder bottleneck solutions"      |
| `/use-cases/operating-without-org`  | "lean startup management"           |
| `/use-cases/strategic-decisions`    | "startup strategic decision making" |
| `/use-cases/advisor-alternative`    | "startup advisor alternative"       |

**3.2 Comparison pages**

| URL                                       | Target Keyword                      |
| ----------------------------------------- | ----------------------------------- |
| `/compare/board-of-one-vs-coaching`       | "founder coaching alternative"      |
| `/compare/board-of-one-vs-advisory-board` | "advisory board alternative"        |
| `/compare/board-of-one-vs-chatgpt`        | "chatgpt for business decisions"    |
| `/compare/board-of-one-vs-consultants`    | "management consultant alternative" |
| `/compare/board-of-one-vs-masterminds`    | "mastermind group alternative"      |

**3.3 Update sitemap**

File: `frontend/src/routes/sitemap.xml/+server.ts`

Add:

- Decision pages with priority 0.7
- Use case pages with priority 0.6
- Comparison pages with priority 0.6

### Phase 4: Conversion Optimization (Week 4)

**4.1 Interactive demo (sandbox)**

- Public sandbox: run one decision without login
- Shows real Board of One output
- Gates full access after demo
- Lower friction than "Request Early Access"

**4.2 Trust signals**

- Customer count if available
- "Trusted by X founders"
- Security badges (GDPR compliance badge)
- Press mentions / "As seen in"

**4.3 CTA optimization**

Current: "Request Early Access" (high friction)
Add: "Try Free Demo" button alongside existing CTA

---

## Files to Modify

| File                                           | Changes                                               |
| ---------------------------------------------- | ----------------------------------------------------- |
| `frontend/src/routes/+page.svelte`             | Add Organization, FAQPage, SoftwareApplication schema |
| `frontend/src/lib/utils/jsonld.ts`             | Add schema generator functions                        |
| `frontend/src/routes/sitemap.xml/+server.ts`   | Add decision/use-case/comparison URLs                 |
| `frontend/src/routes/blog/[slug]/+page.svelte` | Add BreadcrumbList schema                             |

## Files to Create

| File                                                              | Purpose                |
| ----------------------------------------------------------------- | ---------------------- |
| `frontend/src/routes/decisions/+page.svelte`                      | Decision library index |
| `frontend/src/routes/decisions/[category]/+page.svelte`           | Category listing       |
| `frontend/src/routes/decisions/[category]/[slug]/+page.svelte`    | Decision template      |
| `frontend/src/routes/decisions/[category]/[slug]/+page.server.ts` | Data loader            |
| `frontend/src/routes/use-cases/[slug]/+page.svelte`               | Use case template      |
| `frontend/src/routes/compare/[slug]/+page.svelte`                 | Comparison template    |
| `frontend/src/lib/components/seo/Breadcrumbs.svelte`              | Breadcrumb component   |
| `frontend/src/lib/components/landing/DemoSandbox.svelte`          | Interactive demo       |
| `content/decisions/*.md`                                          | Decision content files |

---

## Content Templates

### Decision Page Template

```markdown
---
title: "Should I Hire My First Engineer or Use Contractors?"
category: hiring
slug: first-engineer-vs-contractors
metaDescription: "A structured framework for deciding between hiring your first full-time engineer or continuing with contractors. Includes trade-offs, decision criteria, and action steps."
keywords:
  - first engineering hire
  - startup contractor vs employee
  - when to hire first engineer
  - technical cofounder alternative
publishedAt: 2026-02-01
---

# Should I Hire My First Engineer or Use Contractors?

## The Founder Context

You're a non-technical founder at £50-200k ARR. Your product works but development is slow. You're paying contractors £500-800/day and wondering if a full-time hire makes more sense.

**Typical constraints:**

- Limited runway (12-18 months)
- No technical co-founder
- Product-market fit still being refined
- Need flexibility to pivot

## What the Board Says

_Simulated Board of One deliberation output_

### The Growth Operator's View

"At your stage, speed of iteration matters more than cost efficiency. A full-time engineer aligned with your vision will ship faster than contractors who context-switch between clients."

### The Financial Strategist's View

"Run the numbers: £80k salary + 20% overhead = £96k/year. Contractors at £600/day × 200 days = £120k. But contractors give you flexibility to scale down if needed."

### The Risk Analyst's View

"Your biggest risk isn't cost—it's dependency. One contractor holds all the knowledge. Hire someone who can own the codebase long-term."

## Deep Dive

[800-1500 words covering:]

- Decision criteria framework
- Hidden costs of each option
- Transition strategies
- Real founder examples
- Warning signs you've chosen wrong

## Frequently Asked Questions

1. **How do I evaluate engineering candidates as a non-technical founder?**
2. **What equity should I offer my first engineer?**
3. **Can I convert a contractor to full-time?**
4. **What if I hire wrong?**
5. **Should I hire senior or junior?**
6. **Remote or local?**

## Make This Decision in Board of One

Stop wondering. Get structured analysis from multiple expert perspectives in minutes, not weeks.

[CTA: Run This Decision →]
```

### Use Case Page Template

```markdown
---
title: "Delay Management Hires"
slug: delay-management-hires
metaDescription: "How Board of One helps founders get management-level thinking without management-level headcount."
---

# Delay Your Next Management Hire

## The Problem

You need a Head of Marketing. Or a VP of Sales. Or a COO.

But at £100-150k+ salary, you can't justify the hire until you hit £500k+ ARR. So you're stuck:

- Making decisions without senior input
- Spending hours on problems a Head of X would solve in minutes
- Feeling like you're always behind

## The Board of One Solution

[Specific features and how they address this use case]

## Who This Is For

- Founders at £10k-£500k ARR
- Solo operators who "should" have a management team
- Bootstrapped companies staying lean by choice

## How It Works

[3-step process with screenshots]

## Results

[Testimonials and outcomes]

[CTA: Get Started →]
```

### Comparison Page Template

```markdown
---
title: "Board of One vs Executive Coaching"
slug: board-of-one-vs-coaching
metaDescription: "Compare Board of One to executive coaching: cost, availability, depth of analysis, and which is right for your stage."
---

# Board of One vs Executive Coaching

## Quick Comparison

| Factor          | Board of One          | Executive Coaching  |
| --------------- | --------------------- | ------------------- |
| Cost            | £X/month              | £500-2000/session   |
| Availability    | Instant, 24/7         | Weekly/biweekly     |
| Perspectives    | 3-5 expert viewpoints | 1 coach's viewpoint |
| Documentation   | Full decision logs    | Your notes          |
| Personalization | Learns your context   | Builds relationship |

## When to Choose Board of One

- You need answers now, not next Tuesday
- You want multiple perspectives, not one
- You're making 10+ strategic decisions/month
- Budget is a constraint

## When to Choose Coaching

- You need accountability, not analysis
- Personal development is the goal
- You value long-term relationship
- You have budget and time

## Can You Use Both?

Yes. Many founders use Board of One for rapid decision support and coaching for longer-term development.

[CTA: Try Board of One Free →]
```

---

## Verification Checklist

After implementation:

1. **Schema validation**
   - [ ] Run Google Rich Results Test on homepage
   - [ ] Run Rich Results Test on decision pages
   - [ ] Verify FAQPage schema renders in test tool

2. **Sitemap verification**
   - [ ] Fetch /sitemap.xml
   - [ ] Verify all new URLs present
   - [ ] Check lastmod dates are current

3. **Index monitoring**
   - [ ] Submit sitemap to Google Search Console
   - [ ] Request indexing for priority pages
   - [ ] Monitor index status over 2-4 weeks

4. **Performance**
   - [ ] Lighthouse audit on decision pages (target 90+)
   - [ ] Core Web Vitals pass
   - [ ] Mobile-friendly test pass

5. **Conversion tracking**
   - [ ] Set up demo CTA tracking
   - [ ] A/B test demo vs "Request Access"
   - [ ] Track decision page → signup funnel

---

## Priority Order (Impact vs Effort)

| Priority | Task                                    | Effort | Impact    |
| -------- | --------------------------------------- | ------ | --------- |
| 1        | Add homepage schema (Organization, FAQ) | Low    | Medium    |
| 2        | Add breadcrumbs to blog posts           | Low    | Low       |
| 3        | Create 5 decision pages                 | Medium | High      |
| 4        | Create decision page template + routing | Medium | High      |
| 5        | Add interactive demo                    | Medium | High      |
| 6        | Create use case pages (3)               | Medium | Medium    |
| 7        | Create comparison pages (3)             | Medium | Medium    |
| 8        | Scale to 60 decision pages              | High   | Very High |

---

## Next Steps

1. Review this report and confirm priorities
2. Decide on content backend (static markdown vs API)
3. Create initial 5 decision pages as proof of concept
4. Measure indexing and ranking changes
5. Scale content production based on results

add a 'features' page, with sub pages:
data analysis (why its important to decisions)
mentor chat
seo generation
tailored to YOUR business
competitor analysis and benchmarking
project management
decisions and replanning

fix seo generation for users

fix pricing & accounts
founder supporter 20% off (+ countdown)
4 x meetings per month for 29
1 x seo
2 x analysis
unlimited chat

99
10 x meetings
4 x seo
unlimited chat

lock accounts with usage limits
