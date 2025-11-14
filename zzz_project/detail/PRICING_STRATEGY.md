# Board of One - Pricing Strategy & Tier Design
**Revenue Model, Feature Gates, Fraud Prevention**

**Version**: 1.0
**Date**: 2025-11-14
**Status**: Pricing Strategy
**Currency**: GBP (£) - UK market focus

---

## Table of Contents

1. [Pricing Philosophy](#1-pricing-philosophy)
2. [Tier Comparison](#2-tier-comparison)
3. [Trial Tier (Free)](#3-trial-tier-free)
4. [Core Tier (£25/month)](#4-core-tier-25month)
5. [Pro Tier (£50/month)](#5-pro-tier-50month)
6. [Founders Discount Program](#6-founders-discount-program)
7. [Promotions System](#7-promotions-system)
8. [Fraud Prevention](#8-fraud-prevention)
9. [Conversion Optimization](#9-conversion-optimization)
10. [Database Schema](#10-database-schema)
11. [Implementation](#11-implementation)

---

## 1. Pricing Philosophy

### 1.1 Core Principles

**High Conversion Over Free Usage**:
- Trial tier MUST demonstrate value (not just a demo)
- Limited but powerful: 2 experts, 2-3 deliberations total
- Focus on quality over quantity (better to convert 20% than give away 100%)

**Value-Based Pricing**:
- Price based on outcomes (better decisions) not inputs (LLM costs)
- Core tier for solopreneurs/indie hackers (£25/month)
- Pro tier for agencies/teams (£50/month)

**Sticky Features**:
- Action tracking (post-deliberation accountability)
- Progress monitoring (deadlines, reminders)
- Not just answers—help users achieve success

**Founders Discount**:
- Permanent 10-20% discount for first 300 paying customers
- Applies to any tier (Core or Pro)
- Lifetime retention incentive

**Flexible Promotions**:
- "+2 experts on next deliberation"
- "+2 deliberations this month"
- Time-limited campaigns (Black Friday, Product Hunt launch, etc.)

---

## 2. Tier Comparison

### 2.1 Feature Matrix

| Feature | Trial (Free) | Core (£25/month) | Pro (£50/month) |
|---------|--------------|------------------|-----------------|
| **Deliberations** | 2-3 total (lifetime) | 4/month | 8/month |
| **Personas per sub-problem** | 2 | 3 | 5 |
| **Sub-problem limit** | 2 | 5 (standard) | 8 (extended) |
| **Complexity limit** | Simple only (1-4) | All (1-10) | All (1-10) |
| **Max rounds per sub-problem** | 5 | 7 (moderate) | 10 (complex) |
| **Persona library** | Curated 10 | All 45 | All 45 + custom (future) |
| **Export formats** | Markdown only | Markdown + PDF | Markdown + PDF + JSON |
| **Public sharing** | ❌ Locked (CTA) | ✅ Enabled | ✅ Enabled |
| **Action tracking** | ❌ Locked (visible, CTA) | ✅ Basic (5 actions) | ✅ Advanced (unlimited) |
| **Action reminders** | ❌ | Email only | Email + in-app |
| **Progress reports** | ❌ | Monthly summary | Weekly + monthly |
| **Priority LLM access** | ❌ | ❌ | ✅ (faster responses) |
| **Support** | Community (Discord) | Email (48h response) | Priority email (24h) |
| **Cache optimization** | Standard | Standard | Priority (higher hit rate) |
| **Historical archive** | Last 2 sessions | Last 6 months | Unlimited |

### 2.2 Tier Positioning

**Trial (Free)**: "Prove the concept"
- Target: Skeptical users, first-time AI tool users
- Goal: Demonstrate value with 2-3 high-quality deliberations
- Conversion trigger: Ran out of deliberations, want more personas/complexity

**Core (£25/month)**: "Solopreneur standard"
- Target: Solo founders, indie hackers, freelancers
- Goal: Regular decision-making tool (4 deliberations/month = 1/week)
- Value prop: "Your personal advisory board for £25/month"

**Pro (£50/month)**: "Power user / small team"
- Target: Agencies, small teams (2-5 people), product managers
- Goal: High-frequency use (8 deliberations/month = 2/week)
- Value prop: "Unlimited complexity, advanced action tracking, priority support"

---

## 3. Trial Tier (Free)

### 3.1 Feature Constraints

**Deliberation Limits**:
- **Total deliberations**: 2 (strict limit, lifetime)
- **Bonus deliberation**: +1 if user shares synthesis on LinkedIn/Twitter (verified via callback)
- **No monthly refresh**: Not "2 per month", it's "2 total" (forces conversion)

**Persona Limits**:
- **Max personas per sub-problem**: 2 (minimum for debate)
- **Persona library**: Curated 10 personas only (strategic, financial, risk, ops, etc.)
- **Rationale**: Show multi-perspective value, but limited diversity

**Sub-Problem Limits**:
- **Max sub-problems**: 2 (simplified deliberations)
- **Complexity limit**: Simple only (1-4 complexity score)
- **Rationale**: Can still solve real problems, but not highly complex ones

**Round Limits**:
- **Max rounds**: 5 per sub-problem (early stop still applies)
- **Rationale**: Sufficient for convergence on simple problems

**Feature Locks**:
- ❌ **Action tracking**: Visible but locked with upgrade CTA
- ❌ **Public sharing**: Locked (upgrade to share)
- ❌ **PDF export**: Markdown only
- ❌ **Historical archive**: Only current + last deliberation visible

**UX Nudges**:
```svelte
<!-- After completing 1st deliberation -->
<div class="trial-progress">
  <p>🎉 You've completed 1 of 2 trial deliberations!</p>
  <p>💡 Unlock unlimited deliberations with Core (£25/month)</p>
  <a href="/pricing">View Plans</a>
</div>

<!-- After completing 2nd deliberation -->
<div class="trial-exhausted">
  <h2>Trial Complete!</h2>
  <p>You've used all 2 trial deliberations.</p>

  <div class="upgrade-options">
    <div class="option">
      <h3>Get +1 Free Deliberation</h3>
      <p>Share your synthesis on LinkedIn to unlock 1 more</p>
      <button on:click={shareForBonus}>Share on LinkedIn</button>
    </div>

    <div class="option highlighted">
      <h3>Upgrade to Core</h3>
      <p>4 deliberations/month, 3 personas, all features</p>
      <a href="/pricing" class="btn-primary">Upgrade for £25/month</a>
    </div>
  </div>
</div>
```

### 3.2 Conversion Triggers

**Deliberation Exhaustion**:
- After 2nd deliberation → Immediate upgrade prompt
- In-session reminder: "This is your last trial deliberation"

**Persona Limitation**:
- User tries to add 3rd persona → "Upgrade to Core for 3+ personas"
- Show locked personas in picker with upgrade badge

**Complexity Limitation**:
- Problem decomposed to 3+ sub-problems → "Upgrade to Core for complex problems"
- Complexity score >4 → "Upgrade to Core for moderate/complex deliberations"

**Action Tracking Preview**:
- Show action tracking UI (grayed out) at end of deliberation
- "Upgrade to Core to track and achieve your goals" CTA

### 3.3 Social Share Bonus

**Mechanism**:
1. User completes 2nd deliberation → Trial exhausted
2. Sees "Get +1 free deliberation by sharing on LinkedIn"
3. Clicks "Share on LinkedIn" → Generates auto-filled post
4. User publishes post → LinkedIn redirects to callback URL
5. Backend verifies share (OAuth callback) → Grants +1 deliberation
6. User sees "Bonus deliberation unlocked! 🎉"

**Implementation**:
```typescript
// src/routes/api/v1/bonus/linkedin-share/+server.ts
export const POST = async ({ locals, request }) => {
  const user = requireAuth({ locals });
  const { shareUrl } = await request.json(); // LinkedIn post URL

  // Verify share (check if post exists, contains our link)
  const isValid = await verifyLinkedInShare(shareUrl, user.id);

  if (isValid) {
    // Grant +1 deliberation
    await db.update(users).set({
      trial_deliberations_remaining: user.trial_deliberations_remaining + 1,
      bonus_share_claimed: true
    }).where(eq(users.id, user.id));

    // Log event
    await logAuditEvent({
      user_id: user.id,
      event_type: 'bonus_deliberation_granted',
      event_data: { reason: 'linkedin_share', share_url: shareUrl }
    });

    return json({ status: 'granted', deliberations_remaining: 1 });
  }

  return json({ status: 'invalid' }, { status: 400 });
};
```

**Fraud Prevention**:
- One-time bonus per user (can't spam shares)
- Requires verified LinkedIn OAuth (not just clicking link)
- Checks if post actually contains Bo1 link

---

## 4. Core Tier (£25/month)

### 4.1 Feature Set

**Deliberation Quota**:
- **4 deliberations/month** (1 per week, sustainable pace)
- **Rollover**: Unused deliberations do NOT rollover (use it or lose it)
- **Rationale**: Prevents stockpiling, encourages consistent usage

**Persona Access**:
- **3 personas per sub-problem** (sweet spot for debate)
- **All 45 personas** in library (full diversity)
- **Rationale**: 3 personas = meaningful multi-perspective debate without overwhelming cost

**Sub-Problem Limit**:
- **5 sub-problems max** (standard PRD limit)
- **All complexity levels** (1-10)
- **Max rounds**: 7 per sub-problem (moderate complexity)

**Action Tracking**:
- **Basic action tracking**: 5 actions per deliberation
- **Email reminders**: Daily/weekly digests for overdue actions
- **Progress reporting**: Monthly summary (completion rate, insights)

**Export & Sharing**:
- **Markdown + PDF export** (styled reports)
- **Public sharing enabled** (shareable links, LinkedIn/Twitter posts)

**Support**:
- **Email support**: 48-hour response time
- **Community access**: Discord server (Core+ members only)

**Historical Archive**:
- **6-month retention**: View/download past deliberations
- **Auto-archive**: Older sessions auto-archived (still accessible)

### 4.2 Pricing Psychology

**£25/month** = **£300/year**
- Comparable to: Notion ($10/month), ChatGPT Plus ($20/month), Grammarly ($30/month)
- Positioning: "Professional tool for serious founders"
- Value narrative: "1 good decision per month pays for itself"

**Annual Discount** (Optional):
- Monthly: £25/month (£300/year)
- Annual: £250/year (£20.83/month, ~17% discount)
- Rationale: Locks in revenue, reduces churn

### 4.3 Upsell Triggers

**Deliberation Quota Exhaustion**:
- Used 4/4 deliberations → "Upgrade to Pro for 8/month (only £25 more)"
- Mid-month reminder: "You've used 3/4 deliberations this month"

**Persona Limitation**:
- Tries to add 4th persona → "Upgrade to Pro for 5 personas per sub-problem"
- Show Pro benefits: "5 personas = richer debate, better recommendations"

**Action Tracking Limitation**:
- Creates 5th action → "Upgrade to Pro for unlimited actions"
- Show Pro features: "Advanced tracking, weekly reports, in-app reminders"

**Complexity Limitation**:
- Decomposes to 6+ sub-problems → "Upgrade to Pro for extended complexity (8 sub-problems)"

---

## 5. Pro Tier (£50/month)

### 5.1 Feature Set

**Deliberation Quota**:
- **8 deliberations/month** (2 per week, power user pace)
- **No rollover** (use it or lose it)
- **Rationale**: High-frequency decision-making for teams/agencies

**Persona Access**:
- **5 personas per sub-problem** (full PRD capacity)
- **All 45 personas** + future custom personas (Enterprise feature preview)
- **Rationale**: Maximum debate diversity, better recommendations

**Sub-Problem Limit**:
- **8 sub-problems max** (extended complexity)
- **All complexity levels** (1-10)
- **Max rounds**: 10 per sub-problem (complex problems)

**Action Tracking**:
- **Advanced action tracking**: Unlimited actions per deliberation
- **In-app reminders**: Real-time notifications for overdue actions
- **Weekly + monthly reports**: Detailed progress tracking, completion rates
- **Action templates**: Pre-built templates for common workflows (product launch, fundraising, etc.)

**Export & Sharing**:
- **Markdown + PDF + JSON export** (API-ready format)
- **Public sharing** + analytics (track views, engagement)

**Priority Features**:
- **Priority LLM access**: Faster responses (lower queue priority)
- **Higher cache hit rate**: Optimized cache allocation (save on repeated queries)
- **Priority support**: 24-hour email response time
- **Early access**: New features (beta testing, feedback loop)

**Historical Archive**:
- **Unlimited retention**: All deliberations accessible forever
- **Advanced search**: Filter by date, persona, problem type

### 5.2 Pricing Psychology

**£50/month** = **£600/year**
- Comparable to: GitHub Teams ($48/month), Figma Professional ($45/month), Notion Plus ($48/month)
- Positioning: "Team/agency tool, not just solo founder"
- Value narrative: "Pay for itself with 1 strategic decision per quarter"

**Annual Discount** (Optional):
- Monthly: £50/month (£600/year)
- Annual: £500/year (£41.67/month, ~17% discount)

### 5.3 Target Customers

**Power Users**:
- Founders making frequent high-stakes decisions (pivot, fundraising, hiring)
- Product managers running weekly roadmap prioritization
- Consultants using Bo1 for client work (white-label future feature)

**Small Teams** (2-5 people):
- Shared account (1 login, multiple use cases)
- Agency decision-making (client strategy, campaign planning)
- Startup leadership team (CTO, CPO, CEO using same tool)

---

## 6. Founders Discount Program

### 6.1 Program Details

**Eligibility**:
- First 300 paying customers (Core or Pro)
- Must sign up before cutoff date (announced via email/blog)
- One-time enrollment (can't join later)

**Discount Structure**:
- **10% discount** (conservative, sustainable)
- OR **20% discount** (aggressive, higher LTV focus)
- Recommendation: **15% discount** (balanced)

**Lifetime Guarantee**:
- Discount applies to ANY tier, forever
- Example: User on Core (£25/month) pays £21.25/month (15% off)
- User upgrades to Pro (£50/month) → Pays £42.50/month (15% off retained)
- User downgrades to Core → Still pays £21.25/month (discount persists)

**Display**:
```svelte
<!-- Billing page -->
<div class="founders-discount-badge">
  🎖️ Founder Member #127 of 300
  <p>You save 15% forever on any plan</p>
</div>

<div class="pricing-breakdown">
  <p>Pro Tier: <s>£50/month</s> £42.50/month</p>
  <p class="savings">You save: £7.50/month (£90/year)</p>
</div>
```

### 6.2 Marketing Value

**Scarcity**:
- "Only 300 spots available" → Creates urgency
- "173 / 300 claimed" → Progress bar on landing page

**Social Proof**:
- "Join 127 founder members saving 15% forever"
- Badge in community (Discord, LinkedIn group)

**Retention**:
- Discount is permanent → Strong incentive to stay subscribed
- Harder to justify canceling when you're getting 15% off

**LTV Impact**:
```
Standard Core user: £25/month * 12 months * 2 years = £600 LTV
Founder Core user: £21.25/month * 12 months * 3 years = £765 LTV
  (Lower monthly revenue, but higher retention = higher LTV)
```

### 6.3 Database Schema

```sql
ALTER TABLE users ADD COLUMN founders_discount_enrolled BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN founders_discount_percentage INTEGER; -- 10, 15, or 20
ALTER TABLE users ADD COLUMN founders_member_number INTEGER UNIQUE; -- 1-300

-- Grant discount
UPDATE users SET
  founders_discount_enrolled = TRUE,
  founders_discount_percentage = 15,
  founders_member_number = (SELECT COALESCE(MAX(founders_member_number), 0) + 1 FROM users WHERE founders_discount_enrolled = TRUE)
WHERE id = $user_id;

-- Calculate discounted price
SELECT
  subscription_tier,
  CASE subscription_tier
    WHEN 'core' THEN 25.00 * (1 - COALESCE(founders_discount_percentage, 0) / 100.0)
    WHEN 'pro' THEN 50.00 * (1 - COALESCE(founders_discount_percentage, 0) / 100.0)
    ELSE 0
  END AS monthly_price
FROM users WHERE id = $user_id;
```

---

## 7. Promotions System

### 7.1 Promotion Types

**Deliberation Boosts**:
- "+2 deliberations this month" (one-time)
- "+1 deliberation per month for 3 months" (recurring)

**Persona Boosts**:
- "+2 personas on next deliberation" (e.g., trial user can use 4 personas once)
- "+1 persona on next 5 deliberations" (Core user can use 4 personas, not 3)

**Time-Limited Campaigns**:
- "Black Friday: 50% off first 3 months"
- "Product Hunt launch: First month free"

**Referral Bonuses**:
- "Refer a friend → Both get +2 deliberations"
- "Refer 3 friends → Get 1 month free"

### 7.2 Implementation

**Database Schema**:
```sql
CREATE TABLE promotions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code TEXT UNIQUE NOT NULL, -- 'BLACKFRIDAY2025', 'PH_LAUNCH', etc.
  promotion_type TEXT NOT NULL, -- 'deliberation_boost', 'persona_boost', 'discount', 'free_month'
  promotion_value JSONB NOT NULL, -- {deliberations: 2, duration: 'once'} or {discount_percentage: 50, duration_months: 3}

  -- Constraints
  max_uses INTEGER, -- Null = unlimited, 100 = first 100 users
  uses_count INTEGER DEFAULT 0,
  valid_from TIMESTAMPTZ DEFAULT NOW(),
  valid_until TIMESTAMPTZ,

  -- Eligibility
  eligible_tiers TEXT[], -- ['trial', 'core'] or NULL (all tiers)

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_promotions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  promotion_id UUID NOT NULL REFERENCES promotions(id) ON DELETE CASCADE,

  -- Redemption
  redeemed_at TIMESTAMPTZ DEFAULT NOW(),
  promotion_value JSONB NOT NULL, -- Snapshot of promotion value at redemption

  -- Status
  status TEXT NOT NULL DEFAULT 'active', -- 'active', 'expired', 'consumed'
  remaining_uses INTEGER, -- For recurring promotions (e.g., +1 deliberation for 3 months → 3 remaining)

  UNIQUE(user_id, promotion_id) -- User can only redeem each promotion once
);
```

**Promotion Application**:
```typescript
// Apply promotion code
export const POST = async ({ locals, request }) => {
  const user = requireAuth({ locals });
  const { code } = await request.json();

  // Fetch promotion
  const promotion = await db.query.promotions.findFirst({
    where: and(
      eq(promotions.code, code.toUpperCase()),
      lte(promotions.valid_from, new Date()),
      or(gte(promotions.valid_until, new Date()), isNull(promotions.valid_until)),
      or(lt(promotions.uses_count, promotions.max_uses), isNull(promotions.max_uses))
    )
  });

  if (!promotion) {
    return json({ error: 'Invalid or expired promotion code' }, { status: 400 });
  }

  // Check eligibility
  if (promotion.eligible_tiers && !promotion.eligible_tiers.includes(user.subscription_tier)) {
    return json({ error: 'This promotion is not available for your tier' }, { status: 403 });
  }

  // Check if already redeemed
  const existingRedemption = await db.query.user_promotions.findFirst({
    where: and(
      eq(user_promotions.user_id, user.id),
      eq(user_promotions.promotion_id, promotion.id)
    )
  });

  if (existingRedemption) {
    return json({ error: 'You have already redeemed this promotion' }, { status: 400 });
  }

  // Apply promotion
  await db.transaction(async (tx) => {
    // Increment promotion uses
    await tx.update(promotions).set({
      uses_count: sql`${promotions.uses_count} + 1`
    }).where(eq(promotions.id, promotion.id));

    // Create user_promotion record
    await tx.insert(user_promotions).values({
      user_id: user.id,
      promotion_id: promotion.id,
      promotion_value: promotion.promotion_value,
      status: 'active',
      remaining_uses: promotion.promotion_value.duration === 'recurring'
        ? promotion.promotion_value.duration_count
        : null
    });

    // Apply benefit immediately (if one-time)
    if (promotion.promotion_type === 'deliberation_boost') {
      await tx.update(users).set({
        deliberations_remaining: sql`${users.deliberations_remaining} + ${promotion.promotion_value.deliberations}`
      }).where(eq(users.id, user.id));
    }
  });

  return json({ status: 'applied', promotion: promotion.promotion_value });
};
```

**UI**:
```svelte
<!-- Settings > Promotions -->
<div class="promotion-input">
  <label>Have a promotion code?</label>
  <input type="text" bind:value={promoCode} placeholder="Enter code" />
  <button on:click={applyPromotion}>Apply</button>
</div>

{#if activePromotions.length > 0}
  <div class="active-promotions">
    <h3>Active Promotions</h3>
    {#each activePromotions as promo}
      <div class="promo-badge">
        🎁 {promo.description}
        {#if promo.remaining_uses}
          <span>({promo.remaining_uses} uses remaining)</span>
        {/if}
      </div>
    {/each}
  </div>
{/if}
```

### 7.3 Example Promotions

**Product Hunt Launch**:
```sql
INSERT INTO promotions (code, promotion_type, promotion_value, max_uses, valid_until, eligible_tiers) VALUES (
  'PH_LAUNCH_2025',
  'free_month',
  '{"months": 1}',
  100, -- First 100 users
  '2025-12-31 23:59:59',
  ARRAY['trial'] -- Trial users only
);
```

**Black Friday**:
```sql
INSERT INTO promotions (code, promotion_type, promotion_value, valid_from, valid_until) VALUES (
  'BLACKFRIDAY2025',
  'discount',
  '{"discount_percentage": 50, "duration_months": 3}',
  '2025-11-25 00:00:00',
  '2025-11-30 23:59:59'
);
```

**Referral Bonus**:
```sql
INSERT INTO promotions (code, promotion_type, promotion_value) VALUES (
  'REFERRAL_BONUS',
  'deliberation_boost',
  '{"deliberations": 2, "duration": "once"}'
);
```

---

## 8. Fraud Prevention

### 8.1 Multi-Account Abuse Detection

**Problem**: Users create multiple trial accounts with different emails to bypass 2-deliberation limit.

**Detection Signals**:
1. **IP Address**: Same IP used for multiple trial signups
2. **Browser Fingerprint**: Device ID, user agent, screen resolution, timezone
3. **Email Pattern**: Similar email addresses (john+1@gmail.com, john+2@gmail.com)
4. **Payment Method**: Same credit card for multiple "trial → paid" conversions (Stripe detects this)
5. **Behavioral Patterns**: Same problem statements, similar deliberation patterns

### 8.2 Implementation

**IP-Based Rate Limiting**:
```sql
CREATE TABLE signup_attempts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  ip_address INET NOT NULL,
  email TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_signup_attempts_ip ON signup_attempts(ip_address, created_at);

-- Check if IP has created multiple trial accounts
SELECT COUNT(*) FROM signup_attempts
WHERE ip_address = $ip_address
  AND created_at > NOW() - INTERVAL '7 days';

-- If count > 3, block signup or require email verification
```

**Browser Fingerprinting** (FingerprintJS):
```typescript
// src/routes/signup/+page.svelte
import FingerprintJS from '@fingerprintjs/fingerprintjs';

const fp = await FingerprintJS.load();
const result = await fp.get();
const visitorId = result.visitorId; // Unique device fingerprint

// Send to backend
await fetch('/api/v1/auth/signup', {
  method: 'POST',
  body: JSON.stringify({ email, fingerprint: visitorId })
});
```

```sql
CREATE TABLE device_fingerprints (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  fingerprint TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Check if fingerprint used for multiple trial accounts
SELECT COUNT(DISTINCT user_id) FROM device_fingerprints
WHERE fingerprint = $fingerprint
  AND user_id IN (SELECT id FROM users WHERE subscription_tier = 'trial');

-- If count > 2, flag as suspicious
```

**Email Pattern Detection**:
```typescript
function detectEmailAbuse(email: string, existingEmails: string[]): boolean {
  // Normalize email (remove +aliases, dots in Gmail)
  const normalized = normalizeEmail(email);

  // Check if normalized email matches existing users
  for (const existing of existingEmails) {
    if (normalizeEmail(existing) === normalized) {
      return true; // Abuse detected
    }
  }

  return false;
}

function normalizeEmail(email: string): string {
  const [local, domain] = email.toLowerCase().split('@');

  // Remove Gmail aliases (+foo)
  const cleanLocal = local.split('+')[0];

  // Remove dots from Gmail (john.doe = johndoe)
  if (domain === 'gmail.com') {
    return cleanLocal.replace(/\./g, '') + '@' + domain;
  }

  return cleanLocal + '@' + domain;
}
```

### 8.3 Mitigation Strategies

**Soft Blocks** (Recommended):
- Don't hard-block suspicious users (false positives)
- Require email verification (send code, not just click link)
- Add CAPTCHA on signup (hCaptcha, reCAPTCHA)
- Show warning: "We noticed multiple signups from your network. Please verify your email."

**Hard Blocks** (For egregious cases):
- Ban IP address (after 5+ trial accounts from same IP)
- Ban device fingerprint (after 3+ trial accounts from same device)
- Require manual review (admin approval for flagged signups)

**Positive Signals** (Reduce friction for legitimate users):
- User completes OAuth with Google/LinkedIn → Lower fraud risk (verified account)
- User has existing GitHub/LinkedIn profile → Trust signal
- User refers from trusted source (Product Hunt, tech blog) → Lower fraud risk

### 8.4 Monitoring Dashboard (Admin)

```svelte
<!-- /admin/fraud-detection -->
<section class="fraud-detection">
  <h2>Suspicious Signups</h2>

  <table>
    <thead>
      <tr>
        <th>Email</th>
        <th>IP Address</th>
        <th>Fingerprint</th>
        <th>Risk Score</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {#each suspiciousUsers as user}
        <tr class:high-risk={user.risk_score > 0.7}>
          <td>{user.email}</td>
          <td>{user.ip_address}</td>
          <td>{user.fingerprint.slice(0, 8)}...</td>
          <td>{(user.risk_score * 100).toFixed(0)}%</td>
          <td>
            <button on:click={() => approveUser(user.id)}>Approve</button>
            <button on:click={() => blockUser(user.id)}>Block</button>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</section>
```

**Risk Score Calculation**:
```typescript
function calculateRiskScore(user: User): number {
  let score = 0;

  // Same IP used for 3+ trial accounts
  if (user.ip_duplicate_count >= 3) score += 0.4;

  // Same fingerprint for 2+ trial accounts
  if (user.fingerprint_duplicate_count >= 2) score += 0.3;

  // Email pattern match (normalized email exists)
  if (user.email_normalized_match) score += 0.2;

  // Signup within 24h of previous account creation (same IP)
  if (user.rapid_signup) score += 0.1;

  return Math.min(score, 1.0); // Cap at 1.0
}
```

---

## 9. Conversion Optimization

### 9.1 Conversion Funnel

```
Landing Page → Signup → Trial Deliberation #1 → Trial Deliberation #2 → Upgrade Prompt → Payment
```

**Target Conversion Rates**:
- Landing → Signup: 10% (100 visitors → 10 signups)
- Signup → Deliberation #1: 80% (10 signups → 8 complete deliberation)
- Deliberation #1 → Deliberation #2: 60% (8 → 5 complete 2nd)
- Deliberation #2 → Upgrade: 20% (5 → 1 pays) **← CRITICAL METRIC**
- **Overall**: 100 visitors → 1 paying customer (1% conversion)

**Improvement Levers**:
- Increase trial value → Higher deliberation completion rate
- Better upgrade prompts → Higher trial → paid conversion
- Referral program → Lower CAC

### 9.2 Upgrade Prompt Optimization

**Timing**:
- **After 1st deliberation**: Soft nudge ("1 of 2 trial deliberations used")
- **After 2nd deliberation**: Hard prompt (modal, can't dismiss without choosing)

**Messaging**:
```svelte
<!-- After 2nd deliberation -->
<Modal open={trialExhausted} closeButton={false}>
  <h2>🎉 Trial Complete!</h2>
  <p>You've successfully completed 2 expert deliberations.</p>

  <div class="value-recap">
    <h3>What you achieved:</h3>
    <ul>
      <li>✅ Decomposed 2 complex problems</li>
      <li>✅ Got recommendations from {totalPersonas} expert perspectives</li>
      <li>✅ Achieved {avgConvergence}% consensus on decisions</li>
    </ul>
  </div>

  <div class="upgrade-options">
    <div class="option">
      <h3>Get +1 Free Deliberation</h3>
      <p>Share your synthesis on LinkedIn</p>
      <button class="btn-secondary" on:click={shareForBonus}>Share to Unlock</button>
    </div>

    <div class="option highlighted">
      <h3>Upgrade to Core</h3>
      <p class="price">£25/month</p>
      <ul class="benefits">
        <li>✅ 4 deliberations/month</li>
        <li>✅ 3 personas per deliberation</li>
        <li>✅ Action tracking & reminders</li>
        <li>✅ PDF export + sharing</li>
      </ul>
      <a href="/pricing" class="btn-primary">Upgrade Now</a>
      <p class="guarantee">30-day money-back guarantee</p>
    </div>
  </div>

  <button class="link-secondary" on:click={notNow}>Not ready yet (close)</button>
</Modal>
```

**A/B Test Variations**:
- **Value Recap**: Show vs hide (hypothesis: showing value increases conversion)
- **Social Proof**: "Join 500+ founders" vs no social proof
- **Pricing Anchor**: Show annual price (£300/year) vs monthly (£25/month)
- **Urgency**: "Limited time: First month 50% off" vs no urgency

### 9.3 Email Nurture Campaign

**For Trial Users Who Haven't Upgraded**:

**Day 1** (After signup):
- Subject: "Welcome to Board of One 🧠"
- Content: How to get started, example deliberations

**Day 3** (After 1st deliberation):
- Subject: "Great job on your first deliberation!"
- Content: Tips for better deliberations, invite to 2nd session

**Day 7** (If no 2nd deliberation):
- Subject: "You have 1 trial deliberation remaining"
- Content: Use cases, testimonials, CTA to start 2nd deliberation

**Day 14** (If 2nd deliberation not completed):
- Subject: "Your trial expires soon—don't miss out"
- Content: Last chance to use trial, upgrade benefits

**Day 30** (If trial exhausted but not upgraded):
- Subject: "Special offer: 50% off your first month"
- Content: Limited-time discount, success stories

---

## 10. Database Schema

### 10.1 Users Table (Updated)

```sql
ALTER TABLE users ADD COLUMN subscription_tier TEXT NOT NULL DEFAULT 'trial' CHECK (subscription_tier IN ('trial', 'core', 'pro'));
ALTER TABLE users ADD COLUMN deliberations_quota INTEGER NOT NULL DEFAULT 2; -- Monthly quota
ALTER TABLE users ADD COLUMN deliberations_used INTEGER NOT NULL DEFAULT 0; -- This month's usage
ALTER TABLE users ADD COLUMN quota_reset_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '1 month'); -- Auto-reset monthly

-- Trial-specific fields
ALTER TABLE users ADD COLUMN trial_deliberations_total INTEGER DEFAULT 2; -- Total trial deliberations allowed
ALTER TABLE users ADD COLUMN trial_deliberations_used INTEGER DEFAULT 0; -- Lifetime trial usage
ALTER TABLE users ADD COLUMN bonus_share_claimed BOOLEAN DEFAULT FALSE; -- LinkedIn share bonus

-- Founders discount
ALTER TABLE users ADD COLUMN founders_discount_enrolled BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN founders_discount_percentage INTEGER; -- 10, 15, or 20
ALTER TABLE users ADD COLUMN founders_member_number INTEGER UNIQUE; -- 1-300

-- Fraud detection
ALTER TABLE users ADD COLUMN signup_ip_address INET;
ALTER TABLE users ADD COLUMN device_fingerprint TEXT;
ALTER TABLE users ADD COLUMN risk_score NUMERIC(3, 2); -- 0.00-1.00
```

### 10.2 Quota Reset (Cron Job)

```sql
-- Reset monthly quotas (run daily at midnight)
UPDATE users SET
  deliberations_used = 0,
  quota_reset_at = quota_reset_at + INTERVAL '1 month'
WHERE quota_reset_at < NOW()
  AND subscription_tier IN ('core', 'pro');
```

```typescript
// Cron job (runs daily)
export async function resetMonthlyQuotas() {
  await db.execute(sql`
    UPDATE users SET
      deliberations_used = 0,
      quota_reset_at = quota_reset_at + INTERVAL '1 month'
    WHERE quota_reset_at < NOW()
      AND subscription_tier IN ('core', 'pro')
  `);

  console.log('Monthly quotas reset');
}
```

---

## 11. Implementation

### 11.1 Feature Gates (Middleware)

```typescript
// src/lib/auth/feature-gates.ts
export function canCreateDeliberation(user: User): { allowed: boolean; reason?: string } {
  // Trial tier
  if (user.subscription_tier === 'trial') {
    if (user.trial_deliberations_used >= user.trial_deliberations_total) {
      return { allowed: false, reason: 'Trial limit reached. Upgrade to continue.' };
    }
    return { allowed: true };
  }

  // Core / Pro tier
  if (user.deliberations_used >= user.deliberations_quota) {
    return {
      allowed: false,
      reason: `Monthly quota reached (${user.deliberations_quota}/${user.deliberations_quota}). Resets ${formatDate(user.quota_reset_at)}.`
    };
  }

  return { allowed: true };
}

export function getMaxPersonas(user: User, subProblemComplexity?: number): number {
  if (user.subscription_tier === 'trial') return 2;
  if (user.subscription_tier === 'core') return 3;
  if (user.subscription_tier === 'pro') return 5;
  return 2; // Default fallback
}

export function getMaxSubProblems(user: User): number {
  if (user.subscription_tier === 'trial') return 2;
  if (user.subscription_tier === 'core') return 5;
  if (user.subscription_tier === 'pro') return 8;
  return 2;
}

export function getMaxRounds(user: User, complexity: number): number {
  if (user.subscription_tier === 'trial') return 5;
  if (user.subscription_tier === 'core') return 7;
  if (user.subscription_tier === 'pro') return 10;

  // Fallback: complexity-based (from PRD)
  if (complexity <= 4) return 5;
  if (complexity <= 6) return 7;
  return 10;
}
```

### 11.2 Upgrade Flow

```svelte
<!-- src/routes/pricing/+page.svelte -->
<script>
  import { page } from '$app/stores';
  export let data; // { user, foundersAvailable, foundersRemaining }

  const tiers = [
    {
      id: 'core',
      name: 'Core',
      price: 25,
      annualPrice: 250,
      features: ['4 deliberations/month', '3 personas', '5 sub-problems', 'Basic action tracking', 'PDF export']
    },
    {
      id: 'pro',
      name: 'Pro',
      price: 50,
      annualPrice: 500,
      features: ['8 deliberations/month', '5 personas', '8 sub-problems', 'Advanced action tracking', 'Priority support'],
      popular: true
    }
  ];

  async function subscribe(tierId: string, billingCycle: 'monthly' | 'annual') {
    const response = await fetch('/api/v1/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ tier: tierId, billing_cycle: billingCycle })
    });

    const { url } = await response.json();
    window.location.href = url; // Redirect to Stripe Checkout
  }
</script>

<section class="pricing">
  <h1>Choose Your Plan</h1>

  {#if data.foundersAvailable}
    <div class="founders-banner">
      🎖️ Founders Discount Available!
      <p>First 300 customers get 15% off forever. {data.foundersRemaining} spots left.</p>
    </div>
  {/if}

  <div class="pricing-tiers">
    {#each tiers as tier}
      <div class="tier" class:highlighted={tier.popular}>
        {#if tier.popular}
          <div class="badge">Most Popular</div>
        {/if}

        <h2>{tier.name}</h2>
        <p class="price">
          £{tier.price}<span>/month</span>
        </p>

        <ul class="features">
          {#each tier.features as feature}
            <li>✅ {feature}</li>
          {/each}
        </ul>

        <button class="btn-primary" on:click={() => subscribe(tier.id, 'monthly')}>
          Subscribe Monthly
        </button>

        <button class="btn-secondary" on:click={() => subscribe(tier.id, 'annual')}>
          Save 17% with Annual (£{tier.annualPrice}/year)
        </button>
      </div>
    {/each}
  </div>
</section>
```

---

**END OF PRICING STRATEGY**

This document provides a complete pricing strategy with tier comparison, feature gates, fraud prevention, and conversion optimization. Ready for implementation with database schema and feature gate middleware included.

**Next**: Create ACTION_TRACKING_FEATURE.md for post-deliberation accountability system.
