# Board of One - Social Sharing & Landing Page
**Marketing Features & Public Presence**

**Version**: 1.0
**Date**: 2025-11-14
**Status**: Feature Design
**Priority**: Phase 3-4 (Post-MVP)

---

## Table of Contents

1. [Social Sharing](#1-social-sharing)
2. [Landing Page](#2-landing-page)
3. [SEO & Discoverability](#3-seo--discoverability)
4. [Content Strategy](#4-content-strategy)

---

## 1. Social Sharing

### 1.1 Overview

**Goal**: Allow users to share their deliberation synthesis on social media with a nicely formatted post.

**Supported Platforms**:
- LinkedIn (primary - professional audience)
- Twitter/X (secondary - tech audience)
- Optional: Facebook, email

### 1.2 LinkedIn Sharing

**Feature**: "Share on LinkedIn" button in synthesis report

**Flow**:
1. User completes deliberation → Synthesis report displayed
2. User clicks "Share on LinkedIn" button
3. System generates formatted post (pre-filled text + link)
4. LinkedIn share dialog opens (OAuth not required for basic sharing)
5. User can edit post before publishing
6. Optional: Track clicks via UTM parameters

**Post Format** (Auto-generated):
```
🧠 Just completed an AI-powered expert deliberation on [PROBLEM TOPIC]

After consulting with [N] expert perspectives and [N] rounds of discussion, here's what I learned:

✅ Key Insight 1: [INSIGHT]
✅ Key Insight 2: [INSIGHT]
✅ Key Insight 3: [INSIGHT]

Recommendation: [1-SENTENCE SUMMARY]

Powered by Board of One - AI-powered decision-making for complex problems.

[View Full Report] → https://app.boardof.one/share/[SESSION_ID]

#DecisionMaking #AITools #ProductStrategy #BoardOfOne
```

**Implementation**:
```typescript
// src/routes/sessions/[id]/synthesis/+page.svelte
function shareOnLinkedIn() {
  const synthesis = synthesisReport;

  // Generate shareable text
  const postText = `
🧠 Just completed an AI-powered expert deliberation on ${extractTopic(session.problem_statement)}

After consulting with ${session.selected_personas.length} expert perspectives and ${session.current_round} rounds of discussion, here's what I learned:

${synthesis.key_insights.slice(0, 3).map((insight, i) => `✅ Key Insight ${i+1}: ${insight}`).join('\n')}

Recommendation: ${synthesis.executive_summary.split('.')[0]}.

Powered by Board of One - AI-powered decision-making for complex problems.

View Full Report → ${shareUrl}

#DecisionMaking #AITools #ProductStrategy #BoardOfOne
`.trim();

  // LinkedIn share URL (no OAuth needed)
  const linkedInUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}&summary=${encodeURIComponent(postText)}`;

  // Open in new window
  window.open(linkedInUrl, '_blank', 'width=600,height=600');
}
```

**Shareable Report URL**:
- Public read-only link: `https://app.boardof.one/share/[SESSION_ID]`
- Requires session owner to enable sharing (privacy control)
- Displays: Executive summary, key insights, vote distribution (NOT full transcript)
- Anonymizes: User email, cost metrics, internal reasoning

**Database Schema**:
```sql
-- Add sharing column to sessions table
ALTER TABLE sessions ADD COLUMN shared_publicly BOOLEAN DEFAULT FALSE;
ALTER TABLE sessions ADD COLUMN share_token TEXT UNIQUE; -- UUID for public link

-- Generate share token when user enables sharing
UPDATE sessions SET
  shared_publicly = TRUE,
  share_token = uuid_generate_v4()
WHERE id = $session_id;
```

**Public Share Page**:
```typescript
// src/routes/share/[token]/+page.svelte
export const load = async ({ params }) => {
  const session = await db.query.sessions.findFirst({
    where: and(
      eq(sessions.share_token, params.token),
      eq(sessions.shared_publicly, true)
    ),
    with: {
      synthesis_report: true
    }
  });

  if (!session) {
    throw error(404, 'Shared report not found');
  }

  return {
    session: {
      problem_statement: session.problem_statement,
      created_at: session.created_at,
      duration_seconds: session.duration_seconds,
      convergence_score: session.convergence_score
    },
    synthesis: session.synthesis_report
  };
};
```

**Privacy Controls**:
```svelte
<!-- src/routes/sessions/[id]/synthesis/+page.svelte -->
<div class="privacy-controls">
  <label>
    <input type="checkbox" bind:checked={sharePublicly} on:change={toggleSharing} />
    Allow public sharing (generates shareable link)
  </label>

  {#if sharePublicly}
    <div class="share-link">
      <input type="text" readonly value={shareUrl} />
      <button on:click={copyLink}>Copy Link</button>
    </div>

    <div class="share-buttons">
      <button on:click={shareOnLinkedIn}>Share on LinkedIn</button>
      <button on:click={shareOnTwitter}>Share on Twitter</button>
    </div>
  {/if}
</div>
```

### 1.3 Twitter/X Sharing

**Post Format** (280 char limit):
```
🧠 AI-powered deliberation on [PROBLEM]

After [N] expert perspectives & [N] rounds:

Recommendation: [1-SENTENCE]

Full report → [SHORTENED_URL]

#DecisionMaking #AITools
```

**Implementation**:
```typescript
function shareOnTwitter() {
  const tweetText = `
🧠 AI-powered deliberation on ${extractTopic(session.problem_statement)}

After ${session.selected_personas.length} expert perspectives & ${session.current_round} rounds:

Recommendation: ${synthesis.executive_summary.split('.')[0]}.

Full report → ${shareUrl}

#DecisionMaking #AITools
`.trim();

  const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(tweetText)}`;
  window.open(twitterUrl, '_blank', 'width=600,height=600');
}
```

### 1.4 Email Sharing

**Feature**: Send synthesis report via email (to self or others)

**UI**:
```svelte
<button on:click={emailReport}>Email Report</button>

<Modal bind:open={emailModalOpen}>
  <h2>Email Report</h2>

  <label>
    Recipients (comma-separated)
    <input type="text" bind:value={emailRecipients} placeholder="alice@example.com, bob@example.com" />
  </label>

  <label>
    Message (optional)
    <textarea bind:value={emailMessage} placeholder="Here's the expert analysis I mentioned..."></textarea>
  </label>

  <button on:click={sendEmail}>Send</button>
</Modal>
```

**Backend**:
```typescript
// src/routes/api/v1/sessions/[id]/email/+server.ts
export const POST = async ({ locals, params, request }) => {
  const user = requireAuth({ locals });
  const session = await getSession(params.id, user.id);

  const { recipients, message } = await request.json();

  // Send email via SendGrid/Mailgun
  await sendEmail({
    to: recipients,
    from: 'noreply@boardof.one',
    subject: `Expert deliberation: ${session.problem_statement.slice(0, 50)}...`,
    html: renderEmailTemplate({
      session,
      synthesis: session.synthesis_report,
      userMessage: message,
      shareUrl: `https://app.boardof.one/share/${session.share_token}`
    })
  });

  return json({ status: 'sent' });
};
```

---

## 2. Landing Page

### 2.1 Overview

**URL**: `https://www.boardof.one` (or `https://app.boardof.one`)

**Goal**: Convert visitors to users (free signups)

**Target Audience**:
- Solo founders & solopreneurs
- Product managers
- Startup executives
- Independent consultants

### 2.2 Page Structure

**Sections**:
1. Hero
2. How It Works
3. Use Cases
4. Pricing
5. Social Proof
6. FAQ
7. CTA

### 2.3 Hero Section

```svelte
<section class="hero">
  <h1>Make Complex Decisions with Confidence</h1>
  <p class="subtitle">
    Get expert perspectives on your toughest decisions through
    AI-powered multi-agent deliberation.
  </p>

  <div class="cta-buttons">
    <a href="/signup" class="btn-primary">Start Free Deliberation</a>
    <a href="#how-it-works" class="btn-secondary">See How It Works →</a>
  </div>

  <p class="social-proof">
    Trusted by 1,000+ founders to make critical decisions
  </p>

  <!-- Demo video or animated GIF -->
  <div class="demo">
    <video autoplay loop muted>
      <source src="/demo.mp4" type="video/mp4">
    </video>
  </div>
</section>
```

**Hero Headline Variations** (A/B test):
- "Make Complex Decisions with Confidence"
- "Get Expert Advice on Any Decision in Minutes"
- "Your Personal Board of Advisors, Powered by AI"
- "Deliberate Like a Board, Decide Like a Founder"

### 2.4 How It Works

```svelte
<section id="how-it-works" class="how-it-works">
  <h2>How It Works</h2>
  <p>Transform complex problems into actionable recommendations in 3 simple steps</p>

  <div class="steps">
    <div class="step">
      <div class="step-number">1</div>
      <h3>Describe Your Problem</h3>
      <p>
        Share your decision or challenge in plain language.
        Our AI breaks it down into manageable sub-problems.
      </p>
      <img src="/screenshots/problem-input.png" alt="Problem input screen" />
    </div>

    <div class="step">
      <div class="step-number">2</div>
      <h3>Expert Deliberation</h3>
      <p>
        Watch as 3-5 AI expert personas debate your problem from
        multiple perspectives over several rounds.
      </p>
      <img src="/screenshots/deliberation.png" alt="Live deliberation screen" />
    </div>

    <div class="step">
      <div class="step-number">3</div>
      <h3>Get Recommendations</h3>
      <p>
        Receive a comprehensive synthesis with key insights,
        vote distribution, and actionable next steps.
      </p>
      <img src="/screenshots/synthesis.png" alt="Synthesis report screen" />
    </div>
  </div>
</section>
```

### 2.5 Use Cases

```svelte
<section class="use-cases">
  <h2>Trusted by Founders for Critical Decisions</h2>

  <div class="use-case-grid">
    <div class="use-case">
      <h3>🚀 Product Direction</h3>
      <p>
        "Should I build feature A or feature B first?"
        Get expert input on product roadmap decisions.
      </p>
    </div>

    <div class="use-case">
      <h3>💰 Pricing Strategy</h3>
      <p>
        "How should I price my SaaS product?"
        Validate pricing models with diverse perspectives.
      </p>
    </div>

    <div class="use-case">
      <h3>📈 Growth Channels</h3>
      <p>
        "Which marketing channel should I prioritize?"
        Optimize limited resources with data-driven recommendations.
      </p>
    </div>

    <div class="use-case">
      <h3>🔧 Technical Decisions</h3>
      <p>
        "Refactor now or ship features?"
        Balance tech debt vs. feature velocity.
      </p>
    </div>

    <div class="use-case">
      <h3>🎯 Market Positioning</h3>
      <p>
        "Should I pivot to a vertical niche?"
        Evaluate strategic pivots with expert input.
      </p>
    </div>

    <div class="use-case">
      <h3>👥 Co-founder Decisions</h3>
      <p>
        "Should I bring on a co-founder?"
        Weigh equity vs. hiring vs. staying solo.
      </p>
    </div>
  </div>
</section>
```

### 2.6 Pricing

```svelte
<section id="pricing" class="pricing">
  <h2>Simple, Transparent Pricing</h2>
  <p>Start free, upgrade when you need more</p>

  <div class="pricing-tiers">
    <!-- Free Tier -->
    <div class="tier tier-free">
      <h3>Free</h3>
      <p class="price">$0<span>/month</span></p>

      <ul class="features">
        <li>✅ 5 deliberations/month</li>
        <li>✅ 3 personas max</li>
        <li>✅ Basic export (Markdown)</li>
        <li>✅ Standard support</li>
      </ul>

      <a href="/signup" class="btn-secondary">Start Free</a>
    </div>

    <!-- Pro Tier -->
    <div class="tier tier-pro highlighted">
      <div class="badge">Most Popular</div>
      <h3>Pro</h3>
      <p class="price">$29<span>/month</span></p>

      <ul class="features">
        <li>✅ 50 deliberations/month</li>
        <li>✅ All 45 personas</li>
        <li>✅ Priority LLM access</li>
        <li>✅ PDF export (styled)</li>
        <li>✅ Public sharing</li>
        <li>✅ Priority support</li>
      </ul>

      <a href="/signup?tier=pro" class="btn-primary">Start Pro Trial</a>
      <p class="trial-note">14-day free trial, no credit card required</p>
    </div>

    <!-- Enterprise Tier -->
    <div class="tier tier-enterprise">
      <h3>Enterprise</h3>
      <p class="price">Custom</p>

      <ul class="features">
        <li>✅ Unlimited deliberations</li>
        <li>✅ Custom personas</li>
        <li>✅ API access</li>
        <li>✅ SLA (99.9% uptime)</li>
        <li>✅ Dedicated support</li>
        <li>✅ SSO (SAML)</li>
      </ul>

      <a href="/contact-sales" class="btn-secondary">Contact Sales</a>
    </div>
  </div>
</section>
```

### 2.7 Social Proof

```svelte
<section class="social-proof">
  <h2>Loved by Founders & Product Leaders</h2>

  <div class="testimonials">
    <div class="testimonial">
      <p class="quote">
        "Board of One helped me decide whether to pivot to a niche vertical.
        The multi-perspective deliberation surfaced trade-offs I hadn't
        considered. Worth every penny."
      </p>
      <div class="author">
        <img src="/avatars/sarah.jpg" alt="Sarah Chen" />
        <div>
          <p class="name">Sarah Chen</p>
          <p class="title">Founder, DevTools SaaS</p>
        </div>
      </div>
    </div>

    <div class="testimonial">
      <p class="quote">
        "I used Board of One for a critical pricing decision. The expert
        personas challenged my assumptions and helped me land on a strategy
        that increased MRR by 40%."
      </p>
      <div class="author">
        <img src="/avatars/james.jpg" alt="James Rodriguez" />
        <div>
          <p class="name">James Rodriguez</p>
          <p class="title">Solo Founder, B2B Marketplace</p>
        </div>
      </div>
    </div>

    <div class="testimonial">
      <p class="quote">
        "Finally, a tool that helps me think through complex decisions without
        spending $5K on consultants. The deliberation transcripts are pure gold."
      </p>
      <div class="author">
        <img src="/avatars/priya.jpg" alt="Priya Sharma" />
        <div>
          <p class="name">Priya Sharma</p>
          <p class="title">Product Manager, Fintech</p>
        </div>
      </div>
    </div>
  </div>

  <!-- Logo wall (if applicable) -->
  <div class="logo-wall">
    <p>Trusted by teams at</p>
    <div class="logos">
      <!-- Placeholder for company logos -->
      <img src="/logos/company1.svg" alt="Company 1" />
      <img src="/logos/company2.svg" alt="Company 2" />
      <img src="/logos/company3.svg" alt="Company 3" />
    </div>
  </div>
</section>
```

### 2.8 FAQ

```svelte
<section class="faq">
  <h2>Frequently Asked Questions</h2>

  <div class="faq-list">
    <details>
      <summary>How is this different from ChatGPT?</summary>
      <p>
        ChatGPT provides a single perspective. Board of One simulates a
        multi-agent deliberation with 3-5 expert personas, each with unique
        backgrounds and decision-making styles. This surfaces trade-offs,
        challenges assumptions, and prevents groupthink—just like a real
        board of advisors.
      </p>
    </details>

    <details>
      <summary>How long does a deliberation take?</summary>
      <p>
        Typical deliberations complete in 5-15 minutes, depending on problem
        complexity. Simple decisions may finish in 3-5 rounds (5 minutes),
        while complex ones may take 7-10 rounds (12-15 minutes).
      </p>
    </details>

    <details>
      <summary>Can I customize the expert personas?</summary>
      <p>
        Free and Pro tiers use our curated library of 45 expert personas.
        Enterprise customers can create custom personas tailored to their
        industry or company context.
      </p>
    </details>

    <details>
      <summary>Is my data private?</summary>
      <p>
        Yes. We're GDPR-compliant and never share your data with third parties
        (except processors like Anthropic for LLM calls, which don't retain
        data). You can request full data export or account deletion anytime.
      </p>
    </details>

    <details>
      <summary>What if I'm not satisfied with the recommendation?</summary>
      <p>
        Board of One provides recommendations, not directives. You're always
        in control. If the recommendation doesn't resonate, you can re-run
        the deliberation with different personas or adjust the problem framing.
        Pro users get priority support to optimize deliberations.
      </p>
    </details>

    <details>
      <summary>Do you offer refunds?</summary>
      <p>
        Yes. Pro subscriptions come with a 30-day money-back guarantee, no
        questions asked. Email us at support@boardof.one for a refund.
      </p>
    </details>
  </div>
</section>
```

### 2.9 Final CTA

```svelte
<section class="cta-final">
  <h2>Ready to Make Better Decisions?</h2>
  <p>
    Join 1,000+ founders using Board of One to solve complex problems
    with confidence.
  </p>

  <a href="/signup" class="btn-primary-large">Start Your First Deliberation</a>
  <p class="cta-note">Free tier, no credit card required</p>
</section>
```

### 2.10 Footer

```svelte
<footer>
  <div class="footer-grid">
    <div class="footer-column">
      <h4>Product</h4>
      <ul>
        <li><a href="/features">Features</a></li>
        <li><a href="/pricing">Pricing</a></li>
        <li><a href="/changelog">Changelog</a></li>
        <li><a href="/roadmap">Roadmap</a></li>
      </ul>
    </div>

    <div class="footer-column">
      <h4>Company</h4>
      <ul>
        <li><a href="/about">About Us</a></li>
        <li><a href="/blog">Blog</a></li>
        <li><a href="/contact">Contact</a></li>
        <li><a href="/careers">Careers</a></li>
      </ul>
    </div>

    <div class="footer-column">
      <h4>Resources</h4>
      <ul>
        <li><a href="/docs">Documentation</a></li>
        <li><a href="/help">Help Center</a></li>
        <li><a href="/examples">Example Deliberations</a></li>
        <li><a href="/api">API Reference</a></li>
      </ul>
    </div>

    <div class="footer-column">
      <h4>Legal</h4>
      <ul>
        <li><a href="/privacy-policy">Privacy Policy</a></li>
        <li><a href="/terms-of-service">Terms of Service</a></li>
        <li><a href="/security">Security</a></li>
        <li><a href="/gdpr">GDPR</a></li>
      </ul>
    </div>
  </div>

  <div class="footer-bottom">
    <p>&copy; 2025 Board of One, Inc. All rights reserved.</p>
    <div class="social-links">
      <a href="https://twitter.com/boardofone">Twitter</a>
      <a href="https://linkedin.com/company/boardofone">LinkedIn</a>
      <a href="https://github.com/boardofone">GitHub</a>
    </div>
  </div>
</footer>
```

---

## 3. SEO & Discoverability

### 3.1 Meta Tags

**Homepage** (`/`):
```html
<head>
  <title>Board of One - AI-Powered Decision Making for Founders</title>
  <meta name="description" content="Get expert perspectives on complex decisions through AI-powered multi-agent deliberation. Trusted by 1,000+ founders and product leaders.">

  <!-- Open Graph (LinkedIn, Facebook) -->
  <meta property="og:title" content="Board of One - AI-Powered Decision Making">
  <meta property="og:description" content="Expert deliberation for complex decisions. Get recommendations from diverse AI perspectives in minutes.">
  <meta property="og:image" content="https://www.boardof.one/og-image.png">
  <meta property="og:url" content="https://www.boardof.one">
  <meta property="og:type" content="website">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Board of One - AI-Powered Decision Making">
  <meta name="twitter:description" content="Expert deliberation for complex decisions. Get recommendations from diverse AI perspectives in minutes.">
  <meta name="twitter:image" content="https://www.boardof.one/twitter-card.png">

  <!-- Canonical URL -->
  <link rel="canonical" href="https://www.boardof.one">
</head>
```

**Shared Report** (`/share/[token]`):
```html
<head>
  <title>{problemTitle} - Expert Deliberation on Board of One</title>
  <meta name="description" content="See the expert analysis and recommendations for: {problemSummary}">

  <meta property="og:title" content="{problemTitle} - Expert Deliberation">
  <meta property="og:description" content="{synthesisExcerpt}">
  <meta property="og:image" content="{dynamicOgImage}">
  <meta property="og:url" content="https://app.boardof.one/share/{token}">

  <!-- Prevent indexing of shared reports (privacy) -->
  <meta name="robots" content="noindex, nofollow">
</head>
```

### 3.2 Sitemap

**Generated Sitemap** (`/sitemap.xml`):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://www.boardof.one</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://www.boardof.one/pricing</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.boardof.one/how-it-works</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <!-- Blog posts (dynamic) -->
  <url>
    <loc>https://www.boardof.one/blog/post-slug</loc>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
</urlset>
```

### 3.3 Structured Data (Schema.org)

**Organization**:
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Board of One",
  "url": "https://www.boardof.one",
  "logo": "https://www.boardof.one/logo.png",
  "description": "AI-powered decision making platform for founders and product leaders",
  "sameAs": [
    "https://twitter.com/boardofone",
    "https://linkedin.com/company/boardofone"
  ]
}
</script>
```

**Software Application**:
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Board of One",
  "applicationCategory": "BusinessApplication",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.8",
    "reviewCount": "127"
  }
}
</script>
```

---

## 4. Content Strategy

### 4.1 Blog Topics (SEO + Thought Leadership)

**Target Keywords**:
- "AI decision making tools"
- "multi-agent deliberation"
- "founder decision making"
- "product strategy framework"
- "solopreneur tools"

**Article Ideas**:
1. "How to Make Complex Decisions as a Solo Founder" (evergreen)
2. "Multi-Agent AI vs. Single LLM: Why Diverse Perspectives Matter" (technical)
3. "Case Study: How Board of One Helped X Pivot to $50K MRR" (social proof)
4. "The Science of Decision-Making: Convergence, Dissent, and Synthesis" (research)
5. "5 Common Founder Decisions (and How to Deliberate Them)" (listicle)

### 4.2 Demo Videos

**3-Minute Demo** (YouTube, landing page):
- Show complete flow (problem → deliberation → synthesis)
- Real example: "Should I build feature A or B?"
- Voiceover explaining each step
- CTA: "Try it free at boardof.one"

**Short Clips** (Twitter, LinkedIn):
- 30-second clips of deliberation in action
- "Watch AI experts debate pricing strategy"
- "See how convergence detection works"

### 4.3 Example Deliberations (Public)

**Public Gallery** (`/examples`):
- 5-10 curated deliberations (anonymized)
- "Pricing Strategy for SaaS Startup"
- "Should I Hire a Co-Founder?"
- "Product Roadmap Prioritization"
- Each example shows full synthesis report (read-only)
- CTA: "Run your own deliberation"

---

**END OF SOCIAL SHARING & LANDING PAGE**

This document provides complete designs for social sharing features (LinkedIn, Twitter) and a conversion-optimized landing page, ready for implementation in Phase 3-4 of the project.
