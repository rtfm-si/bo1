Here’s what’s holding **boardof.one** back right now, and the fastest path to real organic growth.

## What I see on the site today (impacting SEO)

1. **Most “Features / Examples / How it works” content is effectively one long homepage**
   - The nav items appear to resolve to the same single page / sections (anchors), not separate indexable pages with unique intent + metadata. That caps how many keywords you can rank for and makes it harder to earn deep links. ([Board of One][1])

2. **Your Blog exists, but it’s basically empty**
   - There’s a blog landing page and newsletter form, but no visible articles listed. That means you’re not building topical authority, and you have very few pages for Google to rank. ([Board of One][2])

3. **Your “money” content is good, but it’s not packaged as search-targetable landing pages**
   - The homepage copy is strong and differentiated (“compress management work”, “management OS”, “minutes not meetings”), plus you already have sample decisions _inside_ the page. ([Board of One][1])
   - But those samples aren’t separate URLs that can each rank for a specific query.

4. **Possible duplicate content / scraping signals**
   - Google is showing “Board of One” pages on unrelated domains (e.g. crozierbuilders.com) that appear to mirror your content. That can dilute trust and make attribution harder. ([crozierbuilders.com][3])

---

## The highest-leverage SEO move: turn your product into 50–200 indexable pages

You’re selling “board-level thinking on demand” for founders. SEO works when you match _specific_ searches:

### A) Programmatic “decision” pages (your secret weapon)

Create individual pages for your best decision templates and sample outputs.

**Structure**

- `/decisions/hiring/first-engineer-vs-contractors`
- `/decisions/marketing/50k-ads-vs-content-marketer`
- `/decisions/fundraising/raise-now-vs-bootstrap-6-months`
- `/decisions/pricing/freemium-vs-paid-trial`
- `/decisions/strategy/b2c-to-b2b-pivot`

**Each page contains**

- The question (H1 exactly matching the query)
- Who it’s for (founder stage, constraints)
- The “board” output (bottom line + key actions) _plus_ 800–1500 words of explanation
- A lightweight “run this decision in Board of One” CTA
- FAQ section (for long-tail snippets)
- `Article`/`HowTo`/`FAQPage` schema (more on schema below)

You already have the raw material (sample decisions) on the homepage. ([Board of One][1])
You just need to **explode them into separate URLs**.

### B) “Use case” landing pages (commercial intent)

- `/use-cases/delay-management-hires`
- `/use-cases/founder-bottleneck`
- `/use-cases/operating-without-the-org`
  These map directly to your positioning and will convert well. ([Board of One][1])

### C) “Alternatives / comparisons” (high intent, high conversion)

- “Board of One vs coaching”
- “Board of One vs advisory board”
- “Board of One vs consultants”
- “Board of One vs ChatGPT” (you already address this objection—make it a page). ([Board of One][1])

---

## Technical SEO checklist (quick wins)

### 1) Indexing basics (must be clean)

- Ensure you have:
  - `robots.txt` that **allows** crawling of marketing pages and points to a sitemap
  - `sitemap.xml` that lists all canonical marketing URLs
    (Google uses these for crawling guidance; robots.txt is about crawler access, not “hiding” pages.) ([Google for Developers][4])

- Make sure app/auth pages are `noindex` (sign-in, dashboard, app routes), while marketing/content pages are indexable.

### 2) Metadata hygiene (every page unique)

For every new page:

- Unique `<title>` (primary keyword + brand)
- Unique meta description (benefit + CTA)
- Canonical tags (avoid duplicates)
- OpenGraph/Twitter cards (helps sharing + link previews)

### 3) Schema (get richer SERP real estate)

Implement:

- `Organization` + `WebSite` + `WebPage`
- `FAQPage` on decision pages with 6–10 FAQs
- `Article` on blog posts / insights
  This improves eligibility for rich results (not guaranteed, but worth it).

### 4) Performance / Core Web Vitals

Your homepage is content-heavy; keep it fast:

- aggressively lazy-load non-critical components
- compress images
- minimize JS for the marketing site
  (If you tell me your stack for the marketing site—SvelteKit?—I’ll give you exact implementation moves.)

---

## Content strategy that fits your product (and doesn’t become “generic startup blog”)

Your blog tagline is good, but right now it’s not building authority because there are no posts. ([Board of One][2])

Do **two** content streams:

### Stream 1: “Decision Library” (evergreen, product-led)

Publish 2–3 pages/week until you have 60+. Each one is a decision people actually Google:

- “When to hire Head of Sales”
- “Raise seed now or wait for traction”
- “Switch from agencies to in-house marketing”
- “Pricing: annual vs monthly”
- “Kill a feature or double down”
  These pages double as **product demos**.

### Stream 2: “Founder Operating System” (authority moat)

Write opinionated posts aligned with your positioning:

- “Most managers don’t decide—they prepare decisions” (already on homepage) ([Board of One][1])
- “Decision logs beat memory”
- “The coordination tax and how to delete it”
- “How to run a ‘board meeting’ alone”

Keep them punchy, specific, and full of frameworks/checklists.

---

## Fix the “interest” problem: add a no-friction interactive demo

Right now the CTA is “Request Early Access.” ([Board of One][1])
That’s fine for beta, but it throttles conversion from organic.

Add one of these:

1. **Public sandbox decision** (no login) → generates a short sample output
2. **Downloadable sample PDF report** per decision page (lead magnet)
3. **Email-gated “Decision Pack”** (e.g., 10 templates for founders at £10k–£2m ARR)

If you want people to _want_ the app, let them taste the output immediately.

---

## Off-page: how to earn links in a way that’s actually doable

- Publish **1 flagship “Decision Playbook for Solo Founders”** (free, high quality, 30–50 pages)
- Pitch it to:
  - founder newsletters
  - indie hacker communities
  - accelerators / fractional CFOs / fractional COOs
    They’ll link because it’s useful, not because it’s “press”.

Also: build 10–20 “tool pages” that are linkable:

- burn-rate runway calculator + “what should I do next?” decision output
- simple pricing experiment planner
- “hire vs contractor” cost model

---

## The duplicate/scrape issue (worth addressing)

Because your content appears indexed on other domains, do this:

- Make sure your pages have canonical tags pointing to your domain
- If it’s outright copied, file removals where appropriate and tighten brand signals (Organization schema, consistent citations, strong internal linking). ([crozierbuilders.com][3])

---

## A practical 30-day plan

**Week 1**

- Add sitemap + robots + index/noindex rules
- Create 10 decision pages (from your existing samples + 5 new)
- Implement FAQPage schema on those pages

**Week 2**

- Create 10 more decision pages + 5 comparison pages
- Add internal linking blocks: “Related decisions” + “Next decision to run”

**Week 3**

- Launch 5 use-case pages + 2 authority blog posts
- Add a lightweight public demo (even a constrained one)

**Week 4**

- Publish 10 more decision pages
- Start outreach with the flagship playbook/tool pages

---

If you tell me what stack generates the marketing pages (and whether you can do programmatic routes easily), I’ll turn the “Decision Library” into a concrete URL map + page template (title tags, H1s, FAQ sets, schema JSON-LD, and internal linking rules) you can drop straight into your codebase.

[1]: https://boardof.one/ "Board of One - Think Better. Decide Faster"
[2]: https://boardof.one/blog "Board of One - Think Better. Decide Faster"
[3]: https://crozierbuilders.com/dashboard?utm_source=chatgpt.com "Think Better. Decide Faster - Board of One"
[4]: https://developers.google.com/search/docs/crawling-indexing/robots/intro?utm_source=chatgpt.com "Robots.txt Introduction and Guide | Google Search Central"
