#!/usr/bin/env python3
"""Create the Bo1 solo founders blog post.

Run with: docker-compose exec bo1 python -m backend.scripts.create_solo_founders_article
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bo1.state.database import db_session

# Blog post content
ARTICLE = {
    "title": "Bo1 for Solo Founders: Your Board in a Box",
    "excerpt": "Solo founders lack sounding boards. Bo1's multi-agent deliberation gives you structured perspectives on critical decisions - from pivots to pricing to hiring.",
    "meta_title": "Bo1 for Solo Founders: Multi-Perspective Decision Making Without a Board",
    "meta_description": "Solo founders need trusted perspectives on critical decisions. Bo1's AI deliberation provides structured debate from multiple viewpoints - like having a board without the overhead.",
    "content": """# Bo1 for Solo Founders: Your Board in a Box

Solo founders face a unique challenge: every major decision lands on one desk. No co-founder to debate with. No board to pressure-test ideas. Just you, your judgment, and stakes that feel impossibly high.

You know the feeling. Should you pivot or persist? Raise now or bootstrap longer? Hire that contractor or stretch yourself thinner? These decisions keep you up at night - not because you lack intelligence, but because you lack perspectives.

Bo1 was built for exactly this situation.

## The "Board in a Box" for Critical Decisions

When funded startups face major decisions, they convene their board. VCs, experienced operators, and domain experts debate the options. Multiple viewpoints surface risks and opportunities the founder might miss.

Solo founders deserve the same structured deliberation - without the cap table complexity.

Bo1's Meeting Mode creates that experience. You pose a question, and AI personas representing different expertise - strategy, operations, user experience, finance - debate your options through multiple rounds. They challenge assumptions. Surface trade-offs. Push back on weak reasoning.

**Example prompt:**
*"I'm considering pivoting from B2B SaaS to a marketplace model. My current ARR is $8K with 12 customers. What should I consider?"*

You'll get structured analysis from perspectives you might not have: competitive dynamics from a strategist, unit economics from a finance lens, implementation complexity from a technical view, and customer impact from a user advocate.

The synthesis surfaces a recommendation with reasoning - not a magic answer, but a more thoroughly examined question.

## Meeting Prep: From Messy Notes to Structured Agenda

Even without a co-founder, you still have stakeholders. Investors, advisors, key customers, prospective partners. These conversations matter, and showing up prepared signals competence.

Use Mentor Mode to transform scattered thoughts into meeting structure:

**Example prompt:**
*"I'm meeting with a potential enterprise customer next week. Here are my notes: [paste notes]. Help me create a structured agenda and anticipate their concerns."*

The mentor persona will organize your thoughts, identify gaps in your preparation, suggest questions to ask, and help you anticipate objections. You walk in with confidence instead of anxiety.

This works for investor updates, advisor check-ins, partnership discussions, or any high-stakes conversation where preparation matters.

## SMB Team Alignment: Decisions Without Politics

Small teams face a different problem. Multiple stakeholders, multiple opinions, and no clear framework for weighing trade-offs. Decisions become political instead of analytical.

Bo1's Meeting Mode works for team decisions too. Instead of a meeting where the loudest voice wins, you create a structured deliberation where AI personas represent different valid perspectives - and the humans evaluate the synthesis together.

**Example prompt:**
*"Our 4-person team is debating: should we build our own analytics or integrate a third-party solution? We're budget-constrained but need enterprise-grade reliability."*

The deliberation surfaces trade-offs in build-vs-buy, evaluates options against your actual constraints, and produces a recommendation with explicit reasoning. Your team discusses the synthesis, not each other's biases.

This approach removes personal politics from the decision. Nobody's "winning" or "losing" - you're all evaluating structured analysis.

## How to Start

If you're a solo founder or small team drowning in decisions, try this approach:

1. **Pick your hardest open question.** The one you've been avoiding because you don't know how to think about it.

2. **Create a Bo1 meeting.** Phrase it as a clear decision question with relevant context.

3. **Let the personas deliberate.** Watch how they challenge assumptions and surface considerations you hadn't thought of.

4. **Make your decision.** You still hold the judgment - but with more perspectives informing your choice.

The goal isn't to outsource your thinking. It's to make your thinking more thorough. Solo founders succeed by making better decisions faster. Bo1 helps you do both.

---

*Bo1 helps founders make better decisions through AI-assisted multi-agent deliberation. No board required. [Start free](https://app.boardof.one)*
""",
}


def create_article(admin_user_id: str = "system") -> int | None:
    """Create the solo founders article.

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
