#!/usr/bin/env python3
"""Create the Bo1 product launches blog post.

Run with: docker-compose exec bo1 python -m backend.scripts.create_product_launches_article
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bo1.state.database import db_session

# Blog post content
ARTICLE = {
    "title": "Bo1 for Product Launches: From Go/No-Go to Coordinated Execution",
    "excerpt": "Product launches are high-stakes binary decisions with irreversible consequences. Bo1's multi-agent deliberation helps you stress-test readiness, align stakeholders, and coordinate execution.",
    "meta_title": "Bo1 for Product Launches: AI-Assisted Go/No-Go Decisions and Launch Planning",
    "meta_description": "Use Bo1's multi-agent deliberation for product launch decisions. Get structured go/no-go analysis, stakeholder alignment, and coordinated execution planning.",
    "content": """# Bo1 for Product Launches: From Go/No-Go to Coordinated Execution

Product launches are uniquely stressful. Unlike most business decisions that can be revised over time, a launch is binary and largely irreversible. Ship too early and you burn your first impression. Ship too late and competitors eat your market. Get the messaging wrong and customers never understand what you built.

The stakes demand rigorous deliberation. But launch teams are often too deep in execution mode to step back and stress-test their readiness. That's where structured multi-perspective analysis changes the game.

## Meeting Mode for Go/No-Go Deliberation

The classic go/no-go meeting is high-pressure: everyone in a room, opinions flying, the loudest voice often winning. Critical concerns get steamrolled by launch momentum.

Bo1's Meeting Mode creates structured deliberation that surfaces what matters. You pose your launch decision, and AI personas - representing Product, Engineering, Marketing, and Risk perspectives - debate readiness through multiple rounds.

**Example prompt:**
*"We're planning to launch our new pricing tier next Tuesday. Engineering says the billing system is ready. Marketing has the campaign loaded. Should we go, or should we delay? Context: We're switching from usage-based to flat-rate pricing, affecting 200 current customers."*

Each persona brings a distinct lens:
- **Product Strategist** evaluates market timing and competitive dynamics
- **Technical Architect** stress-tests infrastructure readiness and rollback capabilities
- **Marketing Lead** assesses campaign alignment and messaging clarity
- **Risk Analyst** identifies failure modes and customer impact scenarios

Through three rounds, they challenge each other. The Architect might surface a migration edge case the Strategist overlooked. The Risk Analyst might identify customer segments that need special handling. The Marketing Lead might flag messaging gaps that could confuse early adopters.

The synthesis doesn't just say "go" or "no-go" - it explains the reasoning and surfaces conditions that should be true before launch.

## Mentor Mode for Launch Risk Assessment

Not every launch question needs a full deliberation. Sometimes you need to think through a specific risk or plan a mitigation strategy. Mentor Mode provides focused analysis with a single expert persona.

**Example prompts:**
- *"What could go wrong in the first 24 hours after we launch? We're releasing a new onboarding flow that changes how users create accounts."*
- *"Help me create a rollback checklist. If our new checkout flow fails, what steps do we need to revert safely?"*
- *"What should our launch-day monitoring dashboard include? We're releasing a major infrastructure change."*

The mentor persona walks you through scenarios methodically, helping you anticipate problems before they become crises. This is particularly valuable for founders who haven't launched at scale before - the mentor surfaces concerns that experienced operators would raise.

## Actions System for Coordinated Execution

Launches fail in execution as often as strategy. The handoffs between teams create gaps. Critical tasks slip through. No one knows who's responsible for what when things go wrong.

Bo1's Actions system transforms launch planning from scattered task lists into coordinated execution. After each deliberation, you extract actionable next steps with owners and deadlines.

**Example actions from a launch deliberation:**
- "Engineering: Run load test at 3x expected traffic by Thursday" - *Assigned to: @alex*
- "Marketing: Update FAQ with new pricing migration details by Friday" - *Assigned to: @sara*
- "Support: Create escalation playbook for billing questions" - *Assigned to: @team-support*
- "Product: Define success metrics and monitoring thresholds" - *Assigned to: @you*

The Kanban view shows launch readiness at a glance. The Gantt view reveals dependencies that could block your timeline. When tasks get blocked, the system surfaces them before they become launch-day surprises.

## Rollback Readiness

The best launch plans include clear rollback criteria. Bo1 helps you define these upfront:

**Example prompt:**
*"What should our rollback triggers be for launching our new payment processor? We're switching from Stripe to a new provider."*

The deliberation or mentor session produces specific, measurable criteria: "If payment failure rate exceeds 2% for 10 minutes, initiate rollback." "If customer support queue exceeds 50 tickets in first hour, pause migration and triage."

Having these defined before launch - not improvised during a crisis - is the difference between controlled recovery and chaotic damage control.

## Try It For Your Next Launch

If you have a launch coming up, try this approach:

1. **Run a go/no-go meeting** a week before planned launch. Pose the decision question with all relevant context. Let the personas surface what you haven't considered.

2. **Use Mentor Mode for risk scenarios.** Pick your biggest worry and have the mentor help you plan for it.

3. **Extract actions and track them.** Make sure nothing falls through the cracks in the final sprint.

4. **Define rollback criteria upfront.** Document the specific conditions that would trigger a rollback, and what rollback looks like.

Product launches don't have to feel like rolling dice. Structured deliberation - with multiple perspectives challenging your assumptions - turns gut-feel decisions into reasoned choices. You still make the call. But you make it with more considerations weighed than any single person could generate alone.

---

*Bo1 helps product teams make better launch decisions through AI-assisted multi-agent deliberation. [Start free](https://app.boardof.one)*
""",
}


def create_article(admin_user_id: str = "system") -> int | None:
    """Create the product launches article.

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
