#!/usr/bin/env python3
"""Create the Bo1 dogfooding blog post.

Run with: docker-compose exec bo1 python -m backend.scripts.create_dogfooding_article
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bo1.state.database import db_session

# Blog post content
ARTICLE = {
    "title": "How We Built Bo1 Using Bo1: A Dogfooding Story",
    "excerpt": "We used Bo1's multi-agent deliberation to make key decisions while building Bo1 itself. Here's what we learned about AI-assisted decision-making.",
    "meta_title": "Building Bo1 with Bo1: Inside Our Dogfooding Journey",
    "meta_description": "Discover how Bo1's multi-agent deliberation helped us make better decisions during product development. Real examples from prioritization to go-to-market strategy.",
    "content": """# How We Built Bo1 Using Bo1: A Dogfooding Story

When we started building Bo1, we faced the same challenge every founder knows: too many decisions, too little time, and no guaranteed right answers. So we did what any self-respecting AI product team would do - we used our own tool to build itself.

This isn't just marketing. Bo1's multi-agent deliberation actually shaped how we prioritized features, chose our architecture, and defined our go-to-market strategy. Here's the story.

## The Challenge: 100 Features, 10 Weeks

Like most startups, we had a backlog that could fill a year. But we had 10 weeks to launch an MVP that would prove the concept. The traditional approach - gut feeling plus spreadsheets - wasn't going to cut it.

We needed a systematic way to evaluate trade-offs that considered multiple perspectives: user value, technical feasibility, competitive differentiation, and resource constraints.

## Using Meeting Mode for Prioritization

Our first major decision was which features to build for launch. We created a Bo1 meeting with the question:

*"Which 5 features should we prioritize for our 10-week MVP that will best demonstrate Bo1's value proposition?"*

The AI personas - a Product Strategist, Technical Architect, User Advocate, and Business Analyst - each brought different lenses to the problem.

**The Strategist** pushed for differentiation features that would set us apart from ChatGPT and other AI tools. **The Architect** raised concerns about implementation complexity for features like real-time collaboration. **The User Advocate** argued for simplicity and immediate value. **The Business Analyst** focused on what would drive conversions.

Through three rounds of deliberation, something interesting happened. The personas challenged each other's assumptions. The Strategist's "cool" feature ideas got reality-checked by the Architect. The Advocate's user-centric view balanced against business needs.

The final recommendation prioritized:
1. Multi-agent deliberation (core differentiator)
2. Meeting history with search (immediate utility)
3. Action items with tracking (tangible outcomes)
4. Context persistence (smarter conversations)
5. Simple export (low friction to share results)

We shipped exactly these five features. And the prioritization held - users consistently cited these as the features that made Bo1 valuable.

## Mentor Mode for Go-to-Market

Pricing decisions are notoriously hard. We used Mentor Mode to think through our pricing strategy, asking:

*"What pricing model will maximize long-term value while being accessible to solo founders?"*

The mentor persona walked us through trade-offs between usage-based vs. flat-rate pricing, free tiers vs. paid-only, and annual vs. monthly billing.

Key insight that emerged: Usage-based pricing creates anxiety for exactly the users we wanted to serve - solo founders who can't predict their AI usage. The mentor recommended a tiered flat-rate model with generous limits.

We launched with exactly that structure. Early feedback validated the approach - users mentioned pricing simplicity as a positive factor in their decision to subscribe.

## Actions System for Launch Tasks

We also used Bo1's Actions feature to manage our own launch. After each meeting, we extracted actionable next steps and tracked them through completion.

This created an interesting feedback loop: we were simultaneously the user and the builder, experiencing friction points firsthand. When we found the action extraction too verbose, we fixed it. When we wanted progress visibility, we built the Kanban view.

Dogfooding through Actions meant every UX improvement came from real frustration, not speculation.

## What We Learned

Building Bo1 with Bo1 taught us three things:

**1. Multi-perspective deliberation catches blind spots.** The AI personas identified risks and opportunities we hadn't considered. The Architect's concerns about our original sync architecture saved us weeks of refactoring.

**2. Structured decision-making reduces regret.** When you can look back at the reasoning behind a decision, you learn faster. Our meeting transcripts became a decision journal we referenced throughout development.

**3. AI assistance works best as augmentation.** Bo1 didn't make decisions for us - it made our decision-making process more thorough. We still applied judgment, but with better-informed options.

## Try It Yourself

If you're building something new, consider using Bo1 from day one. Not because AI is magic, but because systematic deliberation - even AI-assisted - beats scattered thinking.

Start with your hardest open question. Create a meeting. Let the personas debate. Then make your decision with more perspectives considered than you could generate alone.

That's the Bo1 approach. We built it this way because we believed in it. Now we believe in it because we built it this way.

---

*Bo1 helps founders and small teams make better decisions through AI-assisted multi-agent deliberation. [Start free](https://app.boardof.one)*
""",
}


def create_article(admin_user_id: str = "system") -> int | None:
    """Create the dogfooding article.

    Args:
        admin_user_id: User ID to assign the article to

    Returns:
        Article ID if created, None if already exists
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Check if article already exists
            cur.execute(
                "SELECT id FROM seo_blog_articles WHERE title = %s",
                (ARTICLE["title"],),
            )
            if cur.fetchone():
                print(f"Article already exists: {ARTICLE['title']}")
                return None

            # Insert article
            cur.execute(
                """
                INSERT INTO seo_blog_articles
                (user_id, title, excerpt, content, meta_title, meta_description, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'draft')
                RETURNING id
                """,
                (
                    admin_user_id,
                    ARTICLE["title"],
                    ARTICLE["excerpt"],
                    ARTICLE["content"],
                    ARTICLE["meta_title"],
                    ARTICLE["meta_description"],
                ),
            )
            row = cur.fetchone()
            article_id = row["id"] if isinstance(row, dict) else row[0]
            conn.commit()
            print(f"Created article id={article_id}: {ARTICLE['title']}")
            return article_id


if __name__ == "__main__":
    create_article()
